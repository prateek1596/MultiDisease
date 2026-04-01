"""Preprocessing pipeline builders for each disease dataset."""

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
import pandas as pd
import numpy as np
from typing import List


def build_numeric_pipeline(strategy: str = "median") -> Pipeline:
    """Numeric features: impute → scale."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy=strategy)),
        ("scaler", StandardScaler()),
    ])


def build_full_pipeline(numeric_features: List[str]) -> ColumnTransformer:
    """Full column transformer for numeric-only datasets."""
    return ColumnTransformer(
        transformers=[
            ("num", build_numeric_pipeline(), numeric_features),
        ],
        remainder="drop",
    )


def get_feature_names(disease: str) -> List[str]:
    """Return ordered feature names for a disease dataset."""
    from app.ml.data_loader import DISEASE_FEATURE_NAMES
    return DISEASE_FEATURE_NAMES.get(disease, [])
