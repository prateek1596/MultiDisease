"""Models performance routes — graceful empty responses when no models trained."""

from fastapi import APIRouter, HTTPException
from loguru import logger
from typing import Dict, Any

from app.ml.evaluation.evaluator import get_all_metrics, load_cached_metrics

router = APIRouter()


@router.get("/models/performance")
async def get_performance() -> Dict[str, Any]:
    """
    Return all model metrics grouped by disease.
    Returns empty dict (not 404) when no models trained yet —
    the frontend handles the empty state gracefully.
    """
    try:
        metrics = get_all_metrics()
    except Exception as e:
        logger.warning(f"get_all_metrics failed: {e}")
        metrics = {}

    if not metrics:
        # Return empty structure — let frontend show 'train first' message
        return {"heart": {}, "diabetes": {}, "kidney": {}}

    clean = {}
    for disease, models in metrics.items():
        clean[disease] = {}
        for model_name, m in models.items():
            if not isinstance(m, dict):
                continue
            clean[disease][model_name] = {
                k: v for k, v in m.items()
                if k not in ("roc_fpr", "roc_tpr", "classification_report", "confusion_matrix")
            }
    return clean


@router.get("/models/performance/{disease}")
async def get_disease_performance(disease: str) -> Dict[str, Any]:
    """Return model metrics for a specific disease."""
    if disease not in ("heart", "diabetes", "kidney"):
        raise HTTPException(status_code=400, detail=f"Unknown disease: {disease}")
    try:
        metrics = load_cached_metrics(disease)
    except Exception as e:
        logger.warning(f"load_cached_metrics failed for {disease}: {e}")
        metrics = {}
    return metrics or {}


@router.get("/models/comparison")
async def get_comparison_table() -> Dict[str, Any]:
    """Return a flat comparison table across all diseases and models."""
    try:
        all_metrics = get_all_metrics()
    except Exception as e:
        logger.warning(f"get_all_metrics failed: {e}")
        return {"rows": [], "total": 0}

    rows = []
    for disease, models in all_metrics.items():
        for model_name, m in models.items():
            if not isinstance(m, dict) or "error" in m:
                continue
            rows.append({
                "disease":   disease,
                "model":     model_name,
                "accuracy":  round(m.get("accuracy",  0), 4),
                "precision": round(m.get("precision", 0), 4),
                "recall":    round(m.get("recall",    0), 4),
                "f1_score":  round(m.get("f1_score",  0), 4),
                "roc_auc":   round(m.get("roc_auc",   0), 4),
                "is_best":   m.get("is_best", False),
            })
    return {"rows": rows, "total": len(rows)}
