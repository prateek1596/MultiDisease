"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class DiseaseType(str, Enum):
    heart = "heart"
    diabetes = "diabetes"
    kidney = "kidney"


class ModelName(str, Enum):
    logistic_regression = "logistic_regression"
    random_forest = "random_forest"
    svm = "svm"
    xgboost = "xgboost"
    lightgbm = "lightgbm"
    stacking = "stacking"
    best = "best"


# ─── Auth Schemas ───────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = "user"


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ─── Prediction Schemas ──────────────────────────────────────────────────────

class HeartDiseaseInput(BaseModel):
    age: float = Field(..., ge=1, le=120, description="Age in years")
    sex: float = Field(..., ge=0, le=1, description="0=Female, 1=Male")
    cp: float = Field(..., ge=0, le=3, description="Chest pain type (0-3)")
    trestbps: float = Field(..., ge=60, le=250, description="Resting blood pressure (mm Hg)")
    chol: float = Field(..., ge=100, le=600, description="Serum cholesterol (mg/dl)")
    fbs: float = Field(..., ge=0, le=1, description="Fasting blood sugar > 120 mg/dl")
    restecg: float = Field(..., ge=0, le=2, description="Resting ECG results (0-2)")
    thalach: float = Field(..., ge=60, le=250, description="Maximum heart rate achieved")
    exang: float = Field(..., ge=0, le=1, description="Exercise induced angina")
    oldpeak: float = Field(..., ge=0, le=10, description="ST depression induced by exercise")
    slope: float = Field(..., ge=0, le=2, description="Slope of peak exercise ST segment")
    ca: float = Field(..., ge=0, le=4, description="Number of major vessels colored by fluoroscopy")
    thal: float = Field(..., ge=0, le=3, description="Thalassemia (0-3)")


class DiabetesInput(BaseModel):
    pregnancies: float = Field(..., ge=0, le=20, description="Number of times pregnant")
    glucose: float = Field(..., ge=0, le=300, description="Plasma glucose concentration")
    blood_pressure: float = Field(..., ge=0, le=150, description="Diastolic blood pressure (mm Hg)")
    skin_thickness: float = Field(..., ge=0, le=100, description="Triceps skin fold thickness (mm)")
    insulin: float = Field(..., ge=0, le=900, description="2-Hour serum insulin (mu U/ml)")
    bmi: float = Field(..., ge=0, le=70, description="Body mass index")
    diabetes_pedigree: float = Field(..., ge=0, le=3, description="Diabetes pedigree function")
    age: float = Field(..., ge=1, le=120, description="Age in years")


class KidneyDiseaseInput(BaseModel):
    age: float = Field(..., ge=1, le=120)
    blood_pressure: float = Field(..., ge=50, le=200)
    specific_gravity: float = Field(..., ge=1.0, le=1.03)
    albumin: float = Field(..., ge=0, le=5)
    sugar: float = Field(..., ge=0, le=5)
    red_blood_cells: float = Field(..., ge=0, le=1, description="0=abnormal, 1=normal")
    pus_cell: float = Field(..., ge=0, le=1)
    pus_cell_clumps: float = Field(..., ge=0, le=1)
    bacteria: float = Field(..., ge=0, le=1)
    blood_glucose_random: float = Field(..., ge=50, le=500)
    blood_urea: float = Field(..., ge=5, le=400)
    serum_creatinine: float = Field(..., ge=0.1, le=20)
    sodium: float = Field(..., ge=100, le=200)
    potassium: float = Field(..., ge=2, le=10)
    haemoglobin: float = Field(..., ge=3, le=20)
    packed_cell_volume: float = Field(..., ge=10, le=60)
    white_blood_cell_count: float = Field(..., ge=2000, le=30000)
    red_blood_cell_count: float = Field(..., ge=1, le=10)
    hypertension: float = Field(..., ge=0, le=1)
    diabetes_mellitus: float = Field(..., ge=0, le=1)
    coronary_artery_disease: float = Field(..., ge=0, le=1)
    appetite: float = Field(..., ge=0, le=1)
    pedal_edema: float = Field(..., ge=0, le=1)
    anemia: float = Field(..., ge=0, le=1)


class PredictionRequest(BaseModel):
    disease: DiseaseType
    model_name: ModelName = ModelName.best
    input_data: Dict[str, Any]
    explain: bool = True


class SHAPExplanation(BaseModel):
    feature_names: List[str]
    shap_values: List[float]
    base_value: float
    top_features: List[Dict[str, Any]]


class PredictionResponse(BaseModel):
    disease: str
    model_used: str
    prediction: int
    label: str
    confidence: float
    probability: Dict[str, float]
    explanation: Optional[SHAPExplanation] = None
    prediction_id: Optional[int] = None


# ─── Model Performance Schemas ────────────────────────────────────────────────

class ModelPerformance(BaseModel):
    disease_type: str
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    is_best_model: bool
    trained_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PerformanceResponse(BaseModel):
    heart: List[ModelPerformance] = []
    diabetes: List[ModelPerformance] = []
    kidney: List[ModelPerformance] = []


# ─── Training Schemas ─────────────────────────────────────────────────────────

class TrainRequest(BaseModel):
    diseases: List[DiseaseType] = [DiseaseType.heart, DiseaseType.diabetes, DiseaseType.kidney]
    models: List[ModelName] = [
        ModelName.logistic_regression, ModelName.random_forest,
        ModelName.svm, ModelName.xgboost, ModelName.lightgbm
    ]


class TrainResponse(BaseModel):
    status: str
    message: str
    results: Optional[Dict[str, Any]] = None
