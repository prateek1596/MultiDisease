"""
Research API routes — multi-label prediction, uncertainty, and clinical rules.

Provides endpoints for advanced research features:
- Multi-label disease prediction with comorbidity analysis
- Uncertainty quantification with confidence intervals
- Clinical decision rules comparison
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from loguru import logger

from app.services.multilabel_service import multilabel_service
from app.services.uncertainty_service import uncertainty_service
from app.services.clinical_rules_service import clinical_rules_service


router = APIRouter(prefix="/research", tags=["Research"])


# ==================== SCHEMAS ====================

class PatientData(BaseModel):
    """Patient data for predictions."""
    age: float = Field(..., ge=0, le=120)
    sex: int = Field(..., ge=0, le=1)
    # Heart disease features
    cp: Optional[int] = None
    trestbps: Optional[float] = None
    chol: Optional[float] = None
    fbs: Optional[int] = None
    restecg: Optional[int] = None
    thalach: Optional[float] = None
    exang: Optional[int] = None
    oldpeak: Optional[float] = None
    slope: Optional[int] = None
    ca: Optional[int] = None
    thal: Optional[int] = None
    # Diabetes features
    pregnancies: Optional[int] = None
    glucose: Optional[float] = None
    blood_pressure: Optional[float] = None
    skin_thickness: Optional[float] = None
    insulin: Optional[float] = None
    bmi: Optional[float] = None
    diabetes_pedigree: Optional[float] = None
    # Kidney features
    bgr: Optional[float] = None
    bu: Optional[float] = None
    sc: Optional[float] = None
    sod: Optional[float] = None
    pot: Optional[float] = None
    hemo: Optional[float] = None
    pcv: Optional[float] = None
    wc: Optional[float] = None
    rc: Optional[float] = None
    htn: Optional[int] = None
    dm: Optional[int] = None
    cad: Optional[int] = None
    appet: Optional[int] = None
    pe: Optional[int] = None
    ane: Optional[int] = None
    sg: Optional[float] = None
    al: Optional[float] = None
    su: Optional[float] = None
    rbc: Optional[int] = None
    pc: Optional[int] = None
    
    class Config:
        extra = "allow"


class MultiLabelRequest(BaseModel):
    """Request for multi-label prediction."""
    patient_data: Dict[str, Any]


class UncertaintyRequest(BaseModel):
    """Request for uncertainty quantification."""
    disease: str = Field(..., pattern="^(heart|diabetes|kidney)$")
    patient_data: Dict[str, Any]
    n_simulations: int = Field(default=100, ge=10, le=1000)


class ClinicalRulesRequest(BaseModel):
    """Request for clinical rules comparison."""
    disease: str = Field(..., pattern="^(heart|diabetes|kidney)$")
    patient_data: Dict[str, Any]
    ml_prediction: float = Field(..., ge=0, le=1)


# ==================== MULTI-LABEL ENDPOINTS ====================

@router.post("/multi-label/predict")
async def predict_all_diseases(request: MultiLabelRequest) -> Dict[str, Any]:
    """
    Predict risk for all diseases simultaneously.
    
    Returns predictions, probabilities, and comorbidity analysis.
    """
    try:
        result = multilabel_service.predict_all_diseases(request.patient_data)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"Multi-label prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/multi-label/comorbidity-matrix")
async def get_comorbidity_matrix() -> Dict[str, Any]:
    """
    Get the comorbidity correlation matrix.
    
    Shows disease-disease interaction strengths.
    """
    return {
        "status": "success",
        "data": multilabel_service.get_comorbidity_matrix()
    }


# ==================== UNCERTAINTY ENDPOINTS ====================

@router.post("/uncertainty/quantify")
async def quantify_uncertainty(request: UncertaintyRequest) -> Dict[str, Any]:
    """
    Compute uncertainty estimates for a prediction.
    
    Returns confidence intervals, ensemble variance, and stability assessment.
    """
    try:
        result = uncertainty_service.quantify_uncertainty(
            disease=request.disease,
            patient_data=request.patient_data,
            n_simulations=request.n_simulations
        )
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"Uncertainty quantification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/uncertainty/calibration/{disease}")
async def get_calibration_curve(
    disease: str,
    n_bins: int = 10
) -> Dict[str, Any]:
    """
    Get calibration curve data for a disease model.
    
    Shows predicted vs actual probabilities.
    """
    if disease not in ['heart', 'diabetes', 'kidney']:
        raise HTTPException(status_code=400, detail="Invalid disease type")
    
    result = uncertainty_service.get_calibration_curve(disease, n_bins)
    return {
        "status": "success",
        "data": result
    }


# ==================== CLINICAL RULES ENDPOINTS ====================

@router.post("/clinical-rules/compare")
async def compare_with_clinical_rules(request: ClinicalRulesRequest) -> Dict[str, Any]:
    """
    Compare ML prediction with established clinical decision rules.
    
    Returns clinical scores and agreement analysis.
    """
    try:
        result = clinical_rules_service.compare_with_clinical_rules(
            disease=request.disease,
            patient_data=request.patient_data,
            ml_prediction=request.ml_prediction
        )
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"Clinical rules comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clinical-rules/available")
async def get_available_rules() -> Dict[str, Any]:
    """List all available clinical decision rules by disease."""
    return {
        "status": "success",
        "data": clinical_rules_service.get_all_available_rules()
    }


@router.post("/clinical-rules/framingham")
async def calculate_framingham(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate Framingham Risk Score for a patient."""
    result = clinical_rules_service.calculate_framingham_score(patient_data)
    if result:
        return {"status": "success", "data": result}
    raise HTTPException(status_code=400, detail="Could not calculate Framingham score")


@router.post("/clinical-rules/who-cvd")
async def calculate_who_cvd(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate WHO CVD Risk Score for a patient."""
    result = clinical_rules_service.calculate_who_cvd_risk(patient_data)
    if result:
        return {"status": "success", "data": result}
    raise HTTPException(status_code=400, detail="Could not calculate WHO CVD score")


@router.post("/clinical-rules/ada-diabetes")
async def calculate_ada_diabetes(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate ADA Diabetes Risk Test score."""
    result = clinical_rules_service.calculate_ada_diabetes_risk(patient_data)
    if result:
        return {"status": "success", "data": result}
    raise HTTPException(status_code=400, detail="Could not calculate ADA score")


@router.post("/clinical-rules/kdigo")
async def calculate_kdigo(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate KDIGO CKD Risk Category."""
    result = clinical_rules_service.calculate_kdigo_risk(patient_data)
    if result:
        return {"status": "success", "data": result}
    raise HTTPException(status_code=400, detail="Could not calculate KDIGO risk")
