"""
Minimal Feature Analysis routes.

POST /api/minimal-features/{disease}
  Body: { target_accuracy: 0.85, target_metric: "accuracy", cost_per_test: 10.0 }
  Returns: minimal config + impact table

GET /api/minimal-features/{disease}/plot
  Returns: PNG of feature reduction analysis
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from loguru import logger
from typing import Optional

from app.core.security import get_current_user
from app.ml.training.trainer import training_service
from app.ml.data_loader import DISEASE_LOADERS, DISEASE_TARGET_COLS
from app.ml.pipelines.preprocessing import preprocess_data
from app.ml.minimal_features.minimal_feature_analyzer import MinimalFeatureAnalyzer

router = APIRouter()


class MinimalFeaturesRequest(BaseModel):
    target_accuracy:  float = Field(0.85, ge=0.5, le=1.0)
    target_metric:    str   = "accuracy"    # accuracy | auc | f1
    cost_per_test_usd: float = 10.0
    generate_protocol: bool  = False


@router.post("/minimal-features/{disease}")
async def run_minimal_feature_analysis(
    disease: str,
    payload: MinimalFeaturesRequest,
    current_user: dict = Depends(get_current_user),
):
    if disease not in ("heart", "diabetes", "kidney"):
        raise HTTPException(status_code=400, detail=f"Unknown disease: {disease}")

    if payload.target_metric not in ("accuracy", "auc", "f1"):
        raise HTTPException(status_code=400, detail="target_metric must be accuracy | auc | f1")

    df = DISEASE_LOADERS[disease]()
    target_col = DISEASE_TARGET_COLS[disease]
    X_train, X_test, y_train, y_test = preprocess_data(
        df, target_column=target_col, disease=disease
    )

    try:
        analyzer = MinimalFeatureAnalyzer(X_train, y_train, X_test, y_test)
        minimal_config = analyzer.find_minimal_feature_set(
            target_accuracy=payload.target_accuracy,
            target_metric=payload.target_metric,
        )

        if minimal_config is None:
            return {
                "status": "not_achievable",
                "message": (
                    f"Cannot reach {payload.target_accuracy:.0%} "
                    f"{payload.target_metric} with any feature subset."
                ),
            }

        impact = analyzer.calculate_impact_metrics(
            minimal_config,
            cost_per_test_usd=payload.cost_per_test_usd,
        )

        plot_path = analyzer.plot_feature_reduction_analysis()

        protocol_path = None
        if payload.generate_protocol:
            protocol_path = analyzer.generate_deployment_protocol(minimal_config)

        return {
            "status":          "success",
            "disease":         disease,
            "minimal_config":  minimal_config,
            "impact_analysis": impact,
            "plot_path":       plot_path,
            "protocol_path":   protocol_path,
        }

    except Exception as e:
        logger.error(f"Minimal feature analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/minimal-features/{disease}/plot")
async def download_feature_reduction_plot(
    disease: str,
    current_user: dict = Depends(get_current_user),
):
    from pathlib import Path
    from app.core.config import settings
    path = (
        Path(settings.REPORT_SAVE_PATH)
        / "feature_reduction"
        / "feature_reduction_analysis.png"
    )
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Plot not found. Run POST /api/minimal-features/{disease} first.",
        )
    return FileResponse(str(path), media_type="image/png")
