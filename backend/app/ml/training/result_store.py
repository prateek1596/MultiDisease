"""Stub for saving training results to the database."""

from typing import Dict, Any
from loguru import logger


async def save_metrics_to_db(disease: str, model_name: str, metrics: Dict[str, Any]):
    """
    Persist model metrics to the model_metrics table.
    Called after training completes. Requires an active async session.
    This is wired in via the training route background task.
    """
    logger.debug(f"Metrics for {disease}/{model_name}: AUC={metrics.get('roc_auc', 0):.4f}")
