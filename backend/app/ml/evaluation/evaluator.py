"""
Model evaluation: computes all metrics, saves confusion matrix images.
"""

import os
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Any, Optional
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
    roc_curve
)
from loguru import logger

from app.core.config import settings


METRICS_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_PATH = Path(settings.MODEL_SAVE_PATH)


def evaluate_model(
    model, X_test, y_test,
    disease: str, model_name: str,
    feature_names: List[str]
) -> Dict[str, Any]:
    """Full evaluation of a trained model."""
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_prob)),
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
        "is_best": False,
    }

    # Save confusion matrix image
    _save_confusion_matrix(cm, disease, model_name)

    # Save ROC curve data
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    metrics["roc_fpr"] = fpr.tolist()
    metrics["roc_tpr"] = tpr.tolist()

    # Cache metrics
    cache_key = f"{disease}_{model_name}"
    METRICS_CACHE[cache_key] = metrics
    _persist_metrics(disease, model_name, metrics)

    logger.info(
        f"    {model_name} | ACC={metrics['accuracy']:.4f} | "
        f"AUC={metrics['roc_auc']:.4f} | F1={metrics['f1_score']:.4f}"
    )
    return metrics


def _save_confusion_matrix(cm: np.ndarray, disease: str, model_name: str):
    """Save confusion matrix as a PNG image."""
    out_dir = Path(settings.REPORT_SAVE_PATH) / "confusion_matrices"
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(5, 4))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues", ax=ax,
        xticklabels=["No Disease", "Disease"],
        yticklabels=["No Disease", "Disease"],
    )
    ax.set_xlabel("Predicted", fontsize=11)
    ax.set_ylabel("Actual", fontsize=11)
    ax.set_title(f"{disease.capitalize()} — {model_name.replace('_', ' ').title()}", fontsize=12)
    plt.tight_layout()
    path = out_dir / f"{disease}_{model_name}_cm.png"
    fig.savefig(str(path), dpi=120, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"    Confusion matrix saved: {path}")


def _persist_metrics(disease: str, model_name: str, metrics: Dict):
    """Persist metrics to a JSON file alongside saved models."""
    CACHE_PATH.mkdir(parents=True, exist_ok=True)
    path = CACHE_PATH / f"{disease}_metrics.json"
    existing = {}
    if path.exists():
        with open(path) as f:
            existing = json.load(f)
    existing[model_name] = {
        k: v for k, v in metrics.items()
        if k not in ("roc_fpr", "roc_tpr", "classification_report")
    }
    with open(path, "w") as f:
        json.dump(existing, f, indent=2)


def load_cached_metrics(disease: str) -> Dict[str, Any]:
    """Load persisted metrics from JSON file."""
    path = CACHE_PATH / f"{disease}_metrics.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def get_all_metrics() -> Dict[str, Dict[str, Any]]:
    """Load metrics for all diseases."""
    result = {}
    for disease in ["heart", "diabetes", "kidney"]:
        metrics = load_cached_metrics(disease)
        if metrics:
            result[disease] = metrics
    return result
