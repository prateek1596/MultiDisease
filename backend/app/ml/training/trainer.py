"""
Training service — orchestrates the full ML pipeline.

Key design decisions:
  • Uses preprocessing.py (your exact pipeline: impute → scale → SMOTE)
  • Saves per-model artifacts: {disease}_{model}.joblib
    containing {"model": clf, "feature_names": [...]}
  • Auto-detects existing .pkl models from your previous project and
    converts them to the new artifact format on first run.
"""

import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from sklearn.model_selection import StratifiedKFold, cross_val_score
from loguru import logger

from app.core.config import settings
from app.ml.data_loader import get_dataset, DISEASE_TARGET_COLS, DISEASE_FEATURE_NAMES, DISEASE_LOADERS
from app.ml.pipelines.model_registry import MODEL_REGISTRY, get_model
from app.ml.pipelines.preprocessing import preprocess_data
from app.ml.evaluation.evaluator import evaluate_model


# Disease → legacy pkl filename (from your previous project's /models/ dir)
LEGACY_PKL_MAP = {
    "heart":    "heart_model.pkl",
    "diabetes": "diabetes_model.pkl",
    "kidney":   "kidney_model.pkl",
}


class TrainingService:
    """Full training lifecycle for all diseases x all models."""

    def __init__(self):
        self.save_path = Path(settings.MODEL_SAVE_PATH)
        self.save_path.mkdir(parents=True, exist_ok=True)

    # ── Public ────────────────────────────────────────────────────────────────

    def train_all(
        self,
        diseases: List[str] = None,
        models: List[str] = None,
    ) -> Dict[str, Any]:
        diseases = diseases or ["heart", "diabetes", "kidney"]
        models   = models   or list(MODEL_REGISTRY.keys())
        results = {}
        for disease in diseases:
            logger.info(f"{'='*50}")
            logger.info(f"Training disease: {disease.upper()}")
            results[disease] = self.train_disease(disease, models)
        return results

    def train_disease(self, disease: str, model_names: List[str]) -> Dict[str, Any]:
        """Train all requested models for one disease."""
        df = DISEASE_LOADERS[disease]()
        target_col = DISEASE_TARGET_COLS[disease]

        X_train, X_test, y_train, y_test = preprocess_data(
            df, target_column=target_col, disease=disease
        )
        feature_names = list(X_train.columns)
        self._save_feature_names(disease, feature_names)

        disease_results = {}
        best_auc = 0.0
        best_name = None

        for model_name in model_names:
            try:
                logger.info(f"  → {model_name}")
                clf = get_model(model_name)
                metrics = self._train_and_evaluate(
                    clf, model_name, disease,
                    X_train, y_train, X_test, y_test, feature_names
                )
                disease_results[model_name] = metrics
                self._save_artifact(clf, disease, model_name, feature_names)

                if metrics.get("roc_auc", 0) > best_auc:
                    best_auc = metrics["roc_auc"]
                    best_name = model_name

            except Exception as e:
                logger.error(f"  x {model_name}: {e}")
                disease_results[model_name] = {"error": str(e)}

        if best_name and best_name in disease_results:
            disease_results[best_name]["is_best"] = True
            self._persist_best_model_name(disease, best_name)
            logger.info(f"  Best: {best_name}  AUC={best_auc:.4f}")

        return disease_results

    # ── Inference helpers ─────────────────────────────────────────────────────

    def load_model(self, disease: str, model_name: str) -> Tuple[Any, List[str]]:
        """Load trained model + feature list. Falls back to legacy pkl."""
        path = self._artifact_path(disease, model_name)

        if path.exists():
            artifact = joblib.load(path)
            return artifact["model"], artifact["feature_names"]

        # Try legacy pkl from your previous project
        legacy = self._try_load_legacy(disease, model_name)
        if legacy:
            return legacy

        raise FileNotFoundError(
            f"No trained model found for '{disease}/{model_name}'.\n"
            f"Options:\n"
            f"  1. Place your .pkl files in {self.save_path}/ as:\n"
            f"     heart_model.pkl / diabetes_model.pkl / kidney_model.pkl\n"
            f"  2. Run POST /api/train (requires admin login)"
        )

    def get_best_model_name(self, disease: str) -> str:
        """Return best model name for a disease."""
        # 1. Check saved pointer
        pointer = self.save_path / f"{disease}_best_model.txt"
        if pointer.exists():
            name = pointer.read_text().strip()
            if self._artifact_path(disease, name).exists():
                return name

        # 2. Scan metrics JSON
        metrics_path = self.save_path / f"{disease}_metrics.json"
        if metrics_path.exists():
            metrics = json.loads(metrics_path.read_text())
            valid = {
                k: v for k, v in metrics.items()
                if "roc_auc" in v and self._artifact_path(disease, k).exists()
            }
            if valid:
                return max(valid, key=lambda m: valid[m]["roc_auc"])

        # 3. Scan any .joblib for this disease
        existing = sorted(self.save_path.glob(f"{disease}_*.joblib"))
        if existing:
            return existing[0].stem.replace(f"{disease}_", "")

        # 4. Try legacy pkl → auto-register as random_forest
        legacy = self._try_load_legacy(disease, "random_forest")
        if legacy:
            return "random_forest"

        raise FileNotFoundError(
            f"No trained models found for '{disease}'. "
            f"Please run POST /api/train or place .pkl files in {self.save_path}/"
        )

    # ── Private ───────────────────────────────────────────────────────────────

    def _train_and_evaluate(
        self, clf, model_name, disease,
        X_train, y_train, X_test, y_test, feature_names
    ) -> Dict[str, Any]:
        clf.fit(X_train, y_train)

        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(clf, X_train, y_train, cv=skf, scoring="roc_auc")
        logger.info(f"    CV AUC: {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}")

        metrics = evaluate_model(clf, X_test, y_test, disease, model_name, feature_names)
        metrics["cv_auc_mean"] = float(cv_scores.mean())
        metrics["cv_auc_std"]  = float(cv_scores.std())
        return metrics

    def _save_artifact(self, clf, disease: str, model_name: str, feature_names: list):
        path = self._artifact_path(disease, model_name)
        joblib.dump({"model": clf, "feature_names": feature_names}, path)
        logger.info(f"    Saved {path.name}")

    def _save_feature_names(self, disease: str, feature_names: list):
        (self.save_path / f"{disease}_features.json").write_text(
            json.dumps(feature_names)
        )

    def _persist_best_model_name(self, disease: str, model_name: str):
        (self.save_path / f"{disease}_best_model.txt").write_text(model_name)

    def _artifact_path(self, disease: str, model_name: str) -> Path:
        return self.save_path / f"{disease}_{model_name}.joblib"

    def _legacy_pkl_path(self, disease: str) -> Optional[Path]:
        filename = LEGACY_PKL_MAP.get(disease)
        if not filename:
            return None
        # Search common locations
        candidates = [
            self.save_path / filename,
            Path("models") / filename,
            Path("../models") / filename,
        ]
        for p in candidates:
            if p.resolve().exists():
                return p.resolve()
        return None

    def _try_load_legacy(self, disease: str, model_name: str):
        """Load your existing .pkl and register it as random_forest artifact."""
        if model_name not in ("random_forest", "best"):
            return None
        pkl_path = self._legacy_pkl_path(disease)
        if pkl_path is None:
            return None
        try:
            clf = joblib.load(pkl_path)
            # Infer feature names
            fn_path = self.save_path / f"{disease}_features.json"
            if fn_path.exists():
                feature_names = json.loads(fn_path.read_text())
            else:
                feature_names = DISEASE_FEATURE_NAMES.get(disease, [])

            logger.info(f"Loaded legacy pkl: {pkl_path}")
            # Cache as new-format artifact
            self._save_artifact(clf, disease, "random_forest", feature_names)
            self._persist_best_model_name(disease, "random_forest")
            return clf, feature_names
        except Exception as e:
            logger.warning(f"Could not load legacy pkl {pkl_path}: {e}")
            return None


# Singleton
training_service = TrainingService()
