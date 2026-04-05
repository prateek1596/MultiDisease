"""
Analytics routes — outlier detection, LIME explanations, performance curves.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from loguru import logger

from app.core.security import get_current_user
from app.services.outlier_service import outlier_service
from app.services.lime_service import lime_service, LIME_AVAILABLE
from app.services.performance_curves_service import performance_curves_service
from app.ml.training.trainer import training_service

router = APIRouter()


# ─── Schemas ───────────────────────────────────────────────────────────────────

class OutlierCheckRequest(BaseModel):
    disease: str
    input_data: Dict[str, Any]
    z_threshold: float = 3.0


class OutlierAlert(BaseModel):
    feature: str
    value: float
    severity: str
    reason: str
    expected_range: str


class OutlierCheckResponse(BaseModel):
    has_outliers: bool
    alerts: List[OutlierAlert]
    checked_features: int


class LimeExplanationRequest(BaseModel):
    disease: str
    input_data: Dict[str, Any]
    model_name: str = "best"
    num_features: int = 10


class FeatureContribution(BaseModel):
    feature: str
    contribution: float
    direction: str
    abs_contribution: float


class LimeExplanationResponse(BaseModel):
    available: bool
    contributions: Optional[List[FeatureContribution]] = None
    intercept: Optional[float] = None
    predicted_class: Optional[int] = None
    error: Optional[str] = None


# ─── Outlier Detection Endpoints ───────────────────────────────────────────────

@router.post("/analytics/outliers/check", response_model=OutlierCheckResponse)
async def check_outliers(
    request: OutlierCheckRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Check input data for outliers based on training data distribution.
    Returns alerts for values outside expected ranges.
    """
    if request.disease not in ("heart", "diabetes", "kidney"):
        raise HTTPException(status_code=400, detail=f"Unknown disease: {request.disease}")
    
    try:
        alerts = outlier_service.detect_outliers(
            disease=request.disease,
            input_data=request.input_data,
            z_threshold=request.z_threshold,
        )
        
        stats = outlier_service.get_feature_stats(request.disease)
        
        return OutlierCheckResponse(
            has_outliers=len(alerts) > 0,
            alerts=[OutlierAlert(**a) for a in alerts],
            checked_features=len(stats),
        )
    except Exception as e:
        logger.error(f"Outlier check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/outliers/bounds/{disease}")
async def get_feature_bounds(
    disease: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get feature bounds from training data for frontend validation.
    Returns min, max, mean, and typical range for each feature.
    """
    if disease not in ("heart", "diabetes", "kidney"):
        raise HTTPException(status_code=400, detail=f"Unknown disease: {disease}")
    
    try:
        bounds = outlier_service.get_all_feature_bounds(disease)
        return {"disease": disease, "bounds": bounds}
    except Exception as e:
        logger.error(f"Get bounds failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analytics/outliers/compute-stats/{disease}")
async def compute_feature_stats(
    disease: str,
    current_user: dict = Depends(get_current_user),
):
    """Recompute feature statistics from training data."""
    if disease not in ("heart", "diabetes", "kidney"):
        raise HTTPException(status_code=400, detail=f"Unknown disease: {disease}")
    
    try:
        stats = outlier_service.compute_feature_stats(disease)
        return {
            "disease": disease,
            "features_computed": len(stats),
            "message": "Feature statistics computed successfully",
        }
    except Exception as e:
        logger.error(f"Compute stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── LIME Explanation Endpoints ────────────────────────────────────────────────

@router.get("/analytics/lime/status")
async def lime_status():
    """Check if LIME explanations are available."""
    return {
        "available": LIME_AVAILABLE,
        "message": "LIME library installed" if LIME_AVAILABLE else "Install lime: pip install lime",
    }


@router.post("/analytics/lime/explain")
async def explain_with_lime(
    request: LimeExplanationRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate LIME explanation for a prediction.
    Shows which features contributed most to the prediction.
    """
    if request.disease not in ("heart", "diabetes", "kidney"):
        raise HTTPException(status_code=400, detail=f"Unknown disease: {request.disease}")
    
    if not LIME_AVAILABLE:
        return LimeExplanationResponse(
            available=False,
            error="LIME library not installed. Run: pip install lime",
        )
    
    try:
        import numpy as np
        import pandas as pd
        
        # Load model
        model_name = request.model_name
        if model_name == "best":
            model_name = training_service.get_best_model_name(request.disease)
        
        clf, feature_names = training_service.load_model(request.disease, model_name)
        
        # Prepare input
        normalized = {
            k.lower().replace("-", "_").replace(" ", "_"): v
            for k, v in request.input_data.items()
        }
        
        row = []
        for feat in feature_names:
            key = feat.lower().replace("-", "_").replace(" ", "_")
            val = normalized.get(key, 0)
            row.append(float(val) if val is not None else 0.0)
        
        input_array = np.array(row)
        
        # Generate explanation
        result = lime_service.explain_prediction(
            disease=request.disease,
            model=clf,
            input_array=input_array,
            feature_names=feature_names,
            num_features=request.num_features,
        )
        
        if result.get("available"):
            return LimeExplanationResponse(
                available=True,
                contributions=[FeatureContribution(**c) for c in result["contributions"]],
                intercept=result.get("intercept"),
                predicted_class=result.get("predicted_class"),
            )
        else:
            return LimeExplanationResponse(
                available=False,
                error=result.get("error"),
            )
            
    except Exception as e:
        logger.error(f"LIME explanation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Performance Curves Endpoints ──────────────────────────────────────────────

@router.get("/analytics/curves/{disease}")
async def get_performance_curves(
    disease: str,
    model_name: str = "best",
    current_user: dict = Depends(get_current_user),
):
    """
    Get ROC and precision-recall curves for a model.
    Includes confusion matrices at various thresholds.
    """
    if disease not in ("heart", "diabetes", "kidney"):
        raise HTTPException(status_code=400, detail=f"Unknown disease: {disease}")
    
    try:
        curves = performance_curves_service.generate_curves(disease, model_name)
        return curves
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Generate curves failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/curves/{disease}/compare")
async def compare_model_curves(
    disease: str,
    current_user: dict = Depends(get_current_user),
):
    """Compare ROC curves across all trained models for a disease."""
    if disease not in ("heart", "diabetes", "kidney"):
        raise HTTPException(status_code=400, detail=f"Unknown disease: {disease}")
    
    try:
        comparison = performance_curves_service.compare_models(disease)
        return comparison
    except Exception as e:
        logger.error(f"Compare models failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/curves/{disease}/threshold/{threshold}")
async def get_threshold_metrics(
    disease: str,
    threshold: float,
    model_name: str = "best",
    current_user: dict = Depends(get_current_user),
):
    """Get confusion matrix and metrics at a specific threshold."""
    if disease not in ("heart", "diabetes", "kidney"):
        raise HTTPException(status_code=400, detail=f"Unknown disease: {disease}")
    
    if not 0 <= threshold <= 1:
        raise HTTPException(status_code=400, detail="Threshold must be between 0 and 1")
    
    try:
        metrics = performance_curves_service.get_threshold_metrics(
            disease, model_name, threshold
        )
        return {"disease": disease, "model_name": model_name, "threshold": threshold, **metrics}
    except Exception as e:
        logger.error(f"Get threshold metrics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Feature Importance Endpoints ──────────────────────────────────────────────

@router.get("/analytics/importance/{disease}")
async def get_feature_importance(
    disease: str,
    model_name: str = "best",
    current_user: dict = Depends(get_current_user),
):
    """
    Get feature importance for a model.
    Works with tree-based and linear models.
    """
    if disease not in ("heart", "diabetes", "kidney"):
        raise HTTPException(status_code=400, detail=f"Unknown disease: {disease}")
    
    try:
        importance = performance_curves_service.get_feature_importance(disease, model_name)
        
        # Convert to list format for easier frontend use
        importance_list = [
            {"feature": k, "importance": v}
            for k, v in importance.items()
        ]
        
        return {
            "disease": disease,
            "model_name": model_name,
            "importance": importance,
            "importance_list": importance_list,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Get feature importance failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
