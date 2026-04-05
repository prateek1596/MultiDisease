"""
ROC/Performance Curves Service — generates interactive visualization data.

Provides ROC curves, precision-recall curves, and confusion matrices
at various thresholds for model performance visualization.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

from sklearn.metrics import (
    roc_curve, precision_recall_curve, auc,
    confusion_matrix, classification_report
)

from app.core.config import settings
from app.ml.data_loader import DISEASE_LOADERS, DISEASE_TARGET_COLS
from app.ml.pipelines.preprocessing import preprocess_data
from app.ml.training.trainer import training_service


class PerformanceCurvesService:
    """Generates ROC, PR curves and confusion matrices."""

    def __init__(self):
        self.save_path = Path(settings.MODEL_SAVE_PATH)
        self._cache: Dict[str, Dict] = {}

    def generate_curves(
        self,
        disease: str,
        model_name: str = "best",
    ) -> Dict[str, Any]:
        """
        Generate ROC and PR curve data for a model.
        
        Returns:
            Dict with roc_curve, pr_curve, and thresholds data
        """
        cache_key = f"{disease}_{model_name}"
        
        # Check cache
        cache_file = self.save_path / f"{disease}_{model_name}_curves.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                return data
            except Exception:
                pass
        
        # Load model
        if model_name == "best":
            model_name = training_service.get_best_model_name(disease)
        
        clf, feature_names = training_service.load_model(disease, model_name)
        
        # Load and preprocess data
        df = DISEASE_LOADERS[disease]()
        target_col = DISEASE_TARGET_COLS[disease]
        
        X_train, X_test, y_train, y_test = preprocess_data(
            df, target_column=target_col, disease=disease
        )
        
        # Get predictions
        y_proba = clf.predict_proba(X_test)[:, 1]
        y_true = y_test.values if hasattr(y_test, 'values') else y_test
        
        # ROC Curve
        fpr, tpr, roc_thresholds = roc_curve(y_true, y_proba)
        roc_auc = auc(fpr, tpr)
        
        # PR Curve
        precision, recall, pr_thresholds = precision_recall_curve(y_true, y_proba)
        pr_auc = auc(recall, precision)
        
        # Sample thresholds for confusion matrices
        sample_thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        confusion_matrices = {}
        
        for thresh in sample_thresholds:
            y_pred = (y_proba >= thresh).astype(int)
            cm = confusion_matrix(y_true, y_pred)
            tn, fp, fn, tp = cm.ravel()
            
            # Calculate metrics at this threshold
            accuracy = (tp + tn) / (tp + tn + fp + fn)
            precision_t = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall_t = tp / (tp + fn) if (tp + fn) > 0 else 0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
            f1 = 2 * precision_t * recall_t / (precision_t + recall_t) if (precision_t + recall_t) > 0 else 0
            
            confusion_matrices[str(thresh)] = {
                "matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
                "tn": int(tn),
                "fp": int(fp),
                "fn": int(fn),
                "tp": int(tp),
                "accuracy": float(accuracy),
                "precision": float(precision_t),
                "recall": float(recall_t),
                "specificity": float(specificity),
                "f1": float(f1),
            }
        
        # Downsample curves for JSON (keep ~100 points)
        def downsample(arr, n=100):
            if len(arr) <= n:
                return arr.tolist()
            indices = np.linspace(0, len(arr) - 1, n, dtype=int)
            return arr[indices].tolist()
        
        result = {
            "disease": disease,
            "model_name": model_name,
            "roc_curve": {
                "fpr": downsample(fpr),
                "tpr": downsample(tpr),
                "thresholds": downsample(roc_thresholds),
                "auc": float(roc_auc),
            },
            "pr_curve": {
                "precision": downsample(precision),
                "recall": downsample(recall),
                "thresholds": downsample(pr_thresholds) if len(pr_thresholds) > 0 else [],
                "auc": float(pr_auc),
            },
            "confusion_matrices": confusion_matrices,
            "test_set_size": len(y_true),
            "positive_rate": float(np.mean(y_true)),
        }
        
        # Cache result
        cache_file.write_text(json.dumps(result, indent=2))
        
        return result

    def get_threshold_metrics(
        self,
        disease: str,
        model_name: str,
        threshold: float,
    ) -> Dict[str, Any]:
        """Get detailed metrics at a specific threshold."""
        curves = self.generate_curves(disease, model_name)
        
        # Find nearest threshold in confusion matrices
        thresholds = [float(t) for t in curves["confusion_matrices"].keys()]
        nearest = min(thresholds, key=lambda x: abs(x - threshold))
        
        return curves["confusion_matrices"][str(nearest)]

    def compare_models(
        self,
        disease: str,
        model_names: List[str] = None,
    ) -> Dict[str, Any]:
        """Compare ROC curves across multiple models."""
        from app.ml.pipelines.model_registry import MODEL_REGISTRY
        
        if model_names is None:
            model_names = list(MODEL_REGISTRY.keys())
        
        comparison = {
            "disease": disease,
            "models": {},
        }
        
        for model_name in model_names:
            try:
                curves = self.generate_curves(disease, model_name)
                comparison["models"][model_name] = {
                    "roc_auc": curves["roc_curve"]["auc"],
                    "pr_auc": curves["pr_curve"]["auc"],
                    "roc_curve": curves["roc_curve"],
                }
            except Exception as e:
                logger.warning(f"Could not generate curves for {model_name}: {e}")
        
        return comparison

    def get_feature_importance(
        self,
        disease: str,
        model_name: str = "best",
    ) -> Dict[str, float]:
        """
        Extract feature importance from model.
        Works for tree-based models and linear models.
        """
        if model_name == "best":
            model_name = training_service.get_best_model_name(disease)
        
        clf, feature_names = training_service.load_model(disease, model_name)
        
        importance = {}
        
        # Try different methods to get feature importance
        if hasattr(clf, 'feature_importances_'):
            # Tree-based models (RF, XGB, LightGBM)
            imp = clf.feature_importances_
            for name, val in zip(feature_names, imp):
                importance[name] = float(val)
        
        elif hasattr(clf, 'coef_'):
            # Linear models (LR, SVM with linear kernel)
            coef = np.abs(clf.coef_).flatten()
            for name, val in zip(feature_names, coef):
                importance[name] = float(val)
        
        elif hasattr(clf, 'named_estimators_'):
            # Stacking ensemble - aggregate from base estimators
            all_imp = {}
            for name, est in clf.named_estimators_.items():
                if hasattr(est, 'feature_importances_'):
                    for fname, val in zip(feature_names, est.feature_importances_):
                        all_imp[fname] = all_imp.get(fname, 0) + val
            
            # Average
            n_estimators = len([e for e in clf.named_estimators_.values() 
                               if hasattr(e, 'feature_importances_')])
            if n_estimators > 0:
                importance = {k: v / n_estimators for k, v in all_imp.items()}
        
        # Normalize to sum to 1
        total = sum(importance.values())
        if total > 0:
            importance = {k: v / total for k, v in importance.items()}
        
        # Sort by importance
        importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
        
        return importance


# Singleton
performance_curves_service = PerformanceCurvesService()
