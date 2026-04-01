"""Prediction routes: POST /predict/{disease}"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import json

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.schemas import PredictionRequest, PredictionResponse
from app.services.prediction_service import prediction_service
from app.models.db_models import Prediction, DiseaseType as DBDiseaseType

router = APIRouter()


async def _save_prediction(
    db: AsyncSession,
    disease: str,
    result: PredictionResponse,
    input_data: dict,
    user_id: int = None,
):
    """Background task: persist prediction to DB."""
    try:
        shap_data = None
        if result.explanation:
            shap_data = {
                "top_features": result.explanation.top_features,
                "base_value": result.explanation.base_value,
            }
        record = Prediction(
            user_id=user_id,
            disease_type=DBDiseaseType(disease),
            model_used=result.model_used,
            input_data=input_data,
            prediction_result=result.prediction,
            prediction_label=result.label,
            confidence=result.confidence,
            shap_values=shap_data,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        logger.info(f"Prediction saved to DB: id={record.id}")
        return record.id
    except Exception as e:
        logger.error(f"Failed to save prediction: {e}")


@router.post("/predict/{disease}", response_model=PredictionResponse)
async def predict(
    disease: str,
    payload: PredictionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Run disease prediction.
    - disease: heart | diabetes | kidney
    - model_name: logistic_regression | random_forest | svm | xgboost | lightgbm | stacking | best
    """
    if disease not in ("heart", "diabetes", "kidney"):
        raise HTTPException(status_code=400, detail=f"Unknown disease: {disease}")

    try:
        result = prediction_service.predict(
            disease=disease,
            input_data=payload.input_data,
            model_name=payload.model_name.value,
            explain=payload.explain,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

    user_id = int(current_user.get("sub", 0)) if current_user else None
    background_tasks.add_task(
        _save_prediction, db, disease, result, payload.input_data, user_id
    )

    return result


@router.get("/predictions/history")
async def prediction_history(
    disease: str = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get prediction history for the current user."""
    from sqlalchemy import select
    user_id = int(current_user.get("sub", 0))
    query = (
        select(Prediction)
        .where(Prediction.user_id == user_id)
        .order_by(Prediction.created_at.desc())
        .limit(limit)
    )
    if disease:
        query = query.where(Prediction.disease_type == disease)

    result = await db.execute(query)
    records = result.scalars().all()
    return [
        {
            "id": r.id,
            "disease_type": r.disease_type,
            "model_used": r.model_used,
            "prediction_result": r.prediction_result,
            "prediction_label": r.prediction_label,
            "confidence": r.confidence,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]
