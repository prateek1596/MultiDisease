"""
AutoML — Optuna-based hyperparameter tuning for all 6 models.
Runs after base training; saves best params alongside the artifact.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    logger.warning("optuna not installed — AutoML tuning disabled. pip install optuna")

from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

from app.core.config import settings


# ── Search spaces ──────────────────────────────────────────────────────────────

def _suggest_lr(trial) -> LogisticRegression:
    return LogisticRegression(
        C=trial.suggest_float("C", 0.001, 100, log=True),
        max_iter=1000, random_state=42, class_weight="balanced",
    )

def _suggest_rf(trial) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=trial.suggest_int("n_estimators", 50, 400),
        max_depth=trial.suggest_int("max_depth", 3, 20),
        min_samples_split=trial.suggest_int("min_samples_split", 2, 20),
        random_state=42, class_weight="balanced", n_jobs=-1,
    )

def _suggest_svm(trial) -> SVC:
    return SVC(
        C=trial.suggest_float("C", 0.01, 100, log=True),
        gamma=trial.suggest_categorical("gamma", ["scale", "auto"]),
        kernel="rbf", probability=True,
        random_state=42, class_weight="balanced",
    )

def _suggest_xgb(trial) -> XGBClassifier:
    return XGBClassifier(
        n_estimators=trial.suggest_int("n_estimators", 50, 400),
        learning_rate=trial.suggest_float("learning_rate", 0.005, 0.3, log=True),
        max_depth=trial.suggest_int("max_depth", 3, 10),
        subsample=trial.suggest_float("subsample", 0.5, 1.0),
        colsample_bytree=trial.suggest_float("colsample_bytree", 0.5, 1.0),
        use_label_encoder=False, eval_metric="logloss",
        random_state=42, verbosity=0,
    )

def _suggest_lgbm(trial) -> LGBMClassifier:
    return LGBMClassifier(
        n_estimators=trial.suggest_int("n_estimators", 50, 400),
        learning_rate=trial.suggest_float("learning_rate", 0.005, 0.3, log=True),
        max_depth=trial.suggest_int("max_depth", 3, 12),
        num_leaves=trial.suggest_int("num_leaves", 15, 127),
        min_child_samples=trial.suggest_int("min_child_samples", 5, 50),
        class_weight="balanced", random_state=42, verbose=-1,
    )


MODEL_SUGGESTER = {
    "logistic_regression": _suggest_lr,
    "random_forest":        _suggest_rf,
    "svm":                  _suggest_svm,
    "xgboost":              _suggest_xgb,
    "lightgbm":             _suggest_lgbm,
}


# ── Main tuner ────────────────────────────────────────────────────────────────

class AutoMLTuner:
    """Run Optuna tuning for a single model+disease combination."""

    def __init__(self, n_trials: int = 30, cv_folds: int = 3):
        self.n_trials = n_trials
        self.cv_folds = cv_folds
        self.save_path = Path(settings.MODEL_SAVE_PATH)

    def tune(
        self,
        model_name: str,
        disease: str,
        X_train,
        y_train,
    ) -> Optional[Dict[str, Any]]:
        """
        Run Optuna study. Returns best params dict or None if not available.
        """
        if not OPTUNA_AVAILABLE:
            logger.warning("optuna not installed — skipping AutoML tuning")
            return None

        suggester = MODEL_SUGGESTER.get(model_name)
        if suggester is None:
            logger.info(f"No search space for {model_name} — skipping")
            return None

        skf = StratifiedKFold(n_splits=self.cv_folds, shuffle=True, random_state=42)

        def objective(trial):
            clf = suggester(trial)
            scores = cross_val_score(
                clf, X_train, y_train,
                cv=skf, scoring="roc_auc", n_jobs=-1,
            )
            return float(scores.mean())

        study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=42),
        )
        study.optimize(
            objective,
            n_trials=self.n_trials,
            show_progress_bar=False,
            n_jobs=1,
        )

        best = {
            "model_name":  model_name,
            "disease":     disease,
            "best_value":  round(study.best_value, 4),
            "best_params": study.best_params,
            "n_trials":    self.n_trials,
        }
        self._save(disease, model_name, best)
        logger.info(
            f"AutoML [{disease}/{model_name}] best AUC={best['best_value']} "
            f"params={best['best_params']}"
        )
        return best

    def build_tuned_model(self, model_name: str, disease: str):
        """Build a model instance using saved best params."""
        params = self.load(model_name, disease)
        if params is None:
            from app.ml.pipelines.model_registry import get_model
            return get_model(model_name)

        suggester = MODEL_SUGGESTER.get(model_name)
        if suggester is None:
            from app.ml.pipelines.model_registry import get_model
            return get_model(model_name)

        class _FakeTrial:
            def __init__(self, p):
                self._p = p
            def suggest_float(self, name, *a, **kw):   return self._p[name]
            def suggest_int(self, name, *a, **kw):     return self._p[name]
            def suggest_categorical(self, name, *a, **kw): return self._p[name]

        return suggester(_FakeTrial(params["best_params"]))

    def load(self, model_name: str, disease: str) -> Optional[Dict[str, Any]]:
        path = self._params_path(disease, model_name)
        if path.exists():
            return json.loads(path.read_text())
        return None

    def _save(self, disease: str, model_name: str, data: dict):
        self.save_path.mkdir(parents=True, exist_ok=True)
        self._params_path(disease, model_name).write_text(json.dumps(data, indent=2))

    def _params_path(self, disease: str, model_name: str) -> Path:
        return self.save_path / f"{disease}_{model_name}_optuna.json"


automl_tuner = AutoMLTuner()
