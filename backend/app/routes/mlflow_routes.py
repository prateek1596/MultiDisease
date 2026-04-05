"""
MLflow Model Versioning API routes — experiment tracking and model registry.

Provides endpoints for:
- Experiment management
- Run tracking with metrics
- Model versioning and stage transitions
- Experiment/model comparison
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from loguru import logger

from app.services.mlflow_service import mlflow_service, initialize_demo_tracking


router = APIRouter(prefix="/mlflow", tags=["MLflow Tracking"])


# ==================== SCHEMAS ====================

class CreateExperimentRequest(BaseModel):
    """Request to create an experiment."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    tags: Optional[Dict[str, str]] = None


class StartRunRequest(BaseModel):
    """Request to start a run."""
    experiment_id: str
    run_name: Optional[str] = None
    tags: Optional[Dict[str, str]] = None


class LogParamsRequest(BaseModel):
    """Request to log parameters."""
    run_id: str
    params: Dict[str, Any]


class LogMetricsRequest(BaseModel):
    """Request to log metrics."""
    run_id: str
    metrics: Dict[str, float]
    step: Optional[int] = None


class RegisterModelRequest(BaseModel):
    """Request to register a model."""
    name: str = Field(..., min_length=1, max_length=50)
    run_id: str
    model_path: str
    description: str = ""
    tags: Optional[Dict[str, str]] = None


class TransitionStageRequest(BaseModel):
    """Request to transition model stage."""
    name: str
    version: int
    stage: str = Field(..., pattern="^(staging|production|archived)$")


class CompareVersionsRequest(BaseModel):
    """Request to compare model versions."""
    name: str
    version1: int
    version2: int


# ==================== EXPERIMENT ENDPOINTS ====================

@router.post("/experiments")
async def create_experiment(request: CreateExperimentRequest) -> Dict[str, Any]:
    """Create a new experiment."""
    experiment = mlflow_service.create_experiment(
        name=request.name,
        description=request.description,
        tags=request.tags
    )
    return {"status": "success", "data": experiment}


@router.get("/experiments")
async def list_experiments() -> Dict[str, Any]:
    """List all experiments."""
    experiments = mlflow_service.list_experiments()
    return {"status": "success", "data": experiments, "total": len(experiments)}


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str) -> Dict[str, Any]:
    """Get experiment by ID."""
    experiment = mlflow_service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"status": "success", "data": experiment}


# ==================== RUN ENDPOINTS ====================

@router.post("/runs")
async def start_run(request: StartRunRequest) -> Dict[str, Any]:
    """Start a new run within an experiment."""
    run = mlflow_service.start_run(
        experiment_id=request.experiment_id,
        run_name=request.run_name,
        tags=request.tags
    )
    return {"status": "success", "data": run}


@router.post("/runs/params")
async def log_params(request: LogParamsRequest) -> Dict[str, Any]:
    """Log parameters to a run."""
    mlflow_service.log_params(request.run_id, request.params)
    return {"status": "success", "message": "Parameters logged"}


@router.post("/runs/metrics")
async def log_metrics(request: LogMetricsRequest) -> Dict[str, Any]:
    """Log metrics to a run."""
    mlflow_service.log_metrics(request.run_id, request.metrics, request.step)
    return {"status": "success", "message": "Metrics logged"}


@router.post("/runs/{run_id}/end")
async def end_run(
    run_id: str,
    status: str = Query("completed", pattern="^(completed|failed|killed)$")
) -> Dict[str, Any]:
    """End a run."""
    run = mlflow_service.end_run(run_id, status)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"status": "success", "data": run}


@router.get("/runs")
async def list_runs(
    experiment_id: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """List runs, optionally filtered."""
    runs = mlflow_service.list_runs(experiment_id, status)
    return {"status": "success", "data": runs, "total": len(runs)}


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> Dict[str, Any]:
    """Get run by ID."""
    run = mlflow_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"status": "success", "data": run}


# ==================== MODEL REGISTRY ENDPOINTS ====================

@router.post("/models")
async def register_model(request: RegisterModelRequest) -> Dict[str, Any]:
    """Register a model in the model registry."""
    version = mlflow_service.register_model(
        name=request.name,
        run_id=request.run_id,
        model_path=request.model_path,
        description=request.description,
        tags=request.tags
    )
    return {"status": "success", "data": version}


@router.get("/models")
async def list_models() -> Dict[str, Any]:
    """List all registered models."""
    models = mlflow_service.list_models()
    return {"status": "success", "data": models, "total": len(models)}


@router.get("/models/{name}")
async def get_model(name: str) -> Dict[str, Any]:
    """Get model from registry."""
    model = mlflow_service.get_model(name)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"status": "success", "data": model}


@router.get("/models/{name}/production")
async def get_production_model(name: str) -> Dict[str, Any]:
    """Get the production version of a model."""
    version = mlflow_service.get_production_model(name)
    if not version:
        raise HTTPException(status_code=404, detail="No production version found")
    return {"status": "success", "data": version}


@router.post("/models/transition")
async def transition_model_stage(request: TransitionStageRequest) -> Dict[str, Any]:
    """Transition a model version to a new stage."""
    try:
        version = mlflow_service.transition_model_stage(
            name=request.name,
            version=request.version,
            stage=request.stage
        )
        if not version:
            raise HTTPException(status_code=404, detail="Model or version not found")
        return {"status": "success", "data": version}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/models/compare")
async def compare_versions(request: CompareVersionsRequest) -> Dict[str, Any]:
    """Compare metrics between two model versions."""
    comparison = mlflow_service.compare_versions(
        name=request.name,
        version1=request.version1,
        version2=request.version2
    )
    if "error" in comparison:
        raise HTTPException(status_code=404, detail=comparison["error"])
    return {"status": "success", "data": comparison}


# ==================== SUMMARY ENDPOINTS ====================

@router.get("/summary")
async def get_tracking_summary() -> Dict[str, Any]:
    """Get overall tracking summary."""
    summary = mlflow_service.get_tracking_summary()
    return {"status": "success", "data": summary}


@router.post("/demo/initialize")
async def initialize_demo() -> Dict[str, Any]:
    """Initialize demo experiments and runs."""
    try:
        summary = initialize_demo_tracking()
        return {
            "status": "success",
            "message": "Demo tracking data initialized",
            "data": summary
        }
    except Exception as e:
        logger.error(f"Failed to initialize demo: {e}")
        raise HTTPException(status_code=500, detail=str(e))
