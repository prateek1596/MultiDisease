"""
SHAP explainability: generates SHAP values and plots for predictions.
"""

import shap
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger

from app.core.config import settings


def get_shap_explanation(
    model,
    X_input: np.ndarray,
    feature_names: List[str],
    model_name: str = "unknown",
) -> Dict[str, Any]:
    """
    Compute SHAP values for a single prediction.
    Returns a dict with feature importances and top contributors.
    """
    try:
        clf = model.named_steps.get("clf") or model[-1]
        # Get preprocessed input
        steps = list(model.named_steps.items())
        # Apply all steps except the final classifier
        X_transformed = X_input.copy()
        for name, step in steps[:-1]:
            X_transformed = step.transform(X_transformed)

        explainer = _build_explainer(clf, X_transformed, model_name)
        shap_values = explainer.shap_values(X_transformed)

        # For binary classifiers, take class-1 values
        if isinstance(shap_values, list):
            sv = np.array(shap_values[1][0])
        else:
            sv = np.array(shap_values[0])

        # Limit to number of features
        sv = sv[:len(feature_names)]

        base_value = float(
            explainer.expected_value[1]
            if isinstance(explainer.expected_value, (list, np.ndarray))
            else explainer.expected_value
        )

        # Top 5 features by absolute impact
        abs_sv = np.abs(sv)
        top_idx = np.argsort(abs_sv)[::-1][:5]
        top_features = [
            {
                "feature": feature_names[i],
                "shap_value": float(sv[i]),
                "abs_impact": float(abs_sv[i]),
                "direction": "increases risk" if sv[i] > 0 else "decreases risk",
            }
            for i in top_idx
        ]

        return {
            "feature_names": feature_names,
            "shap_values": sv.tolist(),
            "base_value": base_value,
            "top_features": top_features,
        }

    except Exception as e:
        logger.warning(f"SHAP explanation failed: {e}")
        return {
            "feature_names": feature_names,
            "shap_values": [0.0] * len(feature_names),
            "base_value": 0.0,
            "top_features": [],
        }


def _build_explainer(clf, X_transformed: np.ndarray, model_name: str):
    """Build the appropriate SHAP explainer for the model type."""
    tree_models = ("RandomForest", "XGB", "LGBM", "GradientBoosting", "DecisionTree")
    clf_type = type(clf).__name__

    if any(t in clf_type for t in tree_models):
        return shap.TreeExplainer(clf)
    else:
        background = shap.kmeans(X_transformed, min(50, len(X_transformed)))
        return shap.KernelExplainer(clf.predict_proba, background)


def generate_feature_importance_plot(
    model, feature_names: List[str], disease: str, model_name: str
) -> Optional[str]:
    """Generate and save feature importance bar chart."""
    try:
        clf = model.named_steps.get("clf") or model[-1]
        clf_type = type(clf).__name__

        importances = None
        if hasattr(clf, "feature_importances_"):
            importances = clf.feature_importances_
        elif hasattr(clf, "coef_"):
            importances = np.abs(clf.coef_[0])

        if importances is None:
            return None

        n = min(len(feature_names), len(importances))
        names = feature_names[:n]
        imps = importances[:n]

        sorted_idx = np.argsort(imps)
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh(
            [names[i] for i in sorted_idx],
            [imps[i] for i in sorted_idx],
            color="#3B82F6",
            alpha=0.85,
        )
        ax.set_xlabel("Feature Importance", fontsize=11)
        ax.set_title(
            f"{disease.capitalize()} — {model_name.replace('_', ' ').title()} Feature Importance",
            fontsize=12,
        )
        plt.tight_layout()

        out_dir = Path(settings.REPORT_SAVE_PATH) / "feature_importance"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{disease}_{model_name}_importance.png"
        fig.savefig(str(path), dpi=120, bbox_inches="tight")
        plt.close(fig)
        return str(path)
    except Exception as e:
        logger.warning(f"Feature importance plot failed: {e}")
        return None
