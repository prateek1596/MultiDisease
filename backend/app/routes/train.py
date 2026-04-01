"""Training route: POST /train (admin only)"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from loguru import logger

from app.core.security import require_admin
from app.ml.training.trainer import training_service
from app.schemas.schemas import TrainRequest, TrainResponse

router = APIRouter()

_training_status = {"status": "idle", "message": "No training running"}


@router.post("/train", response_model=TrainResponse)
async def trigger_training(
    payload: TrainRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin),
):
    """Trigger model training for specified diseases and models. Admin only."""
    if _training_status["status"] == "running":
        raise HTTPException(status_code=409, detail="Training already in progress")

    diseases = [d.value for d in payload.diseases]
    models = [m.value for m in payload.models if m.value != "best"]

    background_tasks.add_task(_run_training, diseases, models)
    return TrainResponse(
        status="started",
        message=f"Training started for diseases={diseases}, models={models}",
    )


async def _run_training(diseases: list, models: list):
    _training_status["status"] = "running"
    _training_status["message"] = "Training in progress..."
    try:
        results = training_service.train_all(diseases=diseases, models=models)
        _training_status["status"] = "completed"
        _training_status["message"] = f"Training completed for {diseases}"
        logger.info("Background training completed successfully")
    except Exception as e:
        _training_status["status"] = "failed"
        _training_status["message"] = str(e)
        logger.error(f"Background training failed: {e}")


@router.get("/train/status")
async def training_status(current_user: dict = Depends(require_admin)):
    return _training_status
