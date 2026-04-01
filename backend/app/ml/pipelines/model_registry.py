"""
Model registry — returns raw sklearn estimators (no internal scaler).
Preprocessing is handled by preprocessing.py before training.
"""

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.svm import SVC
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from typing import Dict, Any


def build_logistic_regression():
    return LogisticRegression(
        max_iter=1000, random_state=42,
        class_weight="balanced", C=1.0,
    )

def build_random_forest():
    return RandomForestClassifier(
        n_estimators=200, max_depth=10,
        min_samples_split=5, random_state=42,
        class_weight="balanced", n_jobs=-1,
    )

def build_svm():
    return SVC(
        probability=True, kernel="rbf",
        C=1.0, gamma="scale",
        random_state=42, class_weight="balanced",
    )

def build_xgboost():
    return XGBClassifier(
        n_estimators=200, learning_rate=0.05,
        max_depth=6, subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42, verbosity=0,
    )

def build_lightgbm():
    return LGBMClassifier(
        n_estimators=200, learning_rate=0.05,
        max_depth=6, num_leaves=31,
        class_weight="balanced",
        random_state=42, verbose=-1,
    )

def build_stacking_ensemble():
    base = [
        ("lr",  LogisticRegression(max_iter=1000, random_state=42)),
        ("rf",  RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)),
        ("xgb", XGBClassifier(
            n_estimators=100, use_label_encoder=False,
            eval_metric="logloss", random_state=42, verbosity=0,
        )),
    ]
    meta = LogisticRegression(max_iter=1000, random_state=42)
    return StackingClassifier(
        estimators=base,
        final_estimator=meta,
        cv=5, passthrough=False, n_jobs=-1,
    )


MODEL_REGISTRY: Dict[str, Any] = {
    "logistic_regression": build_logistic_regression,
    "random_forest":       build_random_forest,
    "svm":                 build_svm,
    "xgboost":             build_xgboost,
    "lightgbm":            build_lightgbm,
    "stacking":            build_stacking_ensemble,
}

ALL_MODEL_NAMES = list(MODEL_REGISTRY.keys())

def get_model(model_name: str):
    builder = MODEL_REGISTRY.get(model_name)
    if builder is None:
        raise ValueError(
            f"Unknown model: '{model_name}'. Available: {ALL_MODEL_NAMES}"
        )
    return builder()
