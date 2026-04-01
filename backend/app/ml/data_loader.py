"""
Data loaders for all disease datasets.

Loads from  backend/ml/data/{heart,diabetes,kidney}.csv
Falls back to synthetic data if files are missing (dev/demo).

Also exposes the constants used by trainer.py and preprocessing.py.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger

from app.core.config import settings


def _data_path(filename: str) -> Path:
    return Path(settings.DATA_PATH) / filename


# ─── Heart Disease ────────────────────────────────────────────────────────────

def load_heart_disease() -> pd.DataFrame:
    path = _data_path("heart.csv")
    if path.exists():
        df = pd.read_csv(path)
        logger.info(f"Loaded heart.csv  shape={df.shape}")
    else:
        logger.warning("heart.csv not found — using synthetic data")
        df = _synthetic_heart()
    return df


def _synthetic_heart(n: int = 1000) -> pd.DataFrame:
    np.random.seed(42)
    return pd.DataFrame({
        "age":      np.random.randint(29, 80, n).astype(float),
        "sex":      np.random.randint(0, 2, n).astype(float),
        "cp":       np.random.randint(0, 4, n).astype(float),
        "trestbps": np.random.randint(90, 200, n).astype(float),
        "chol":     np.random.randint(120, 570, n).astype(float),
        "fbs":      np.random.randint(0, 2, n).astype(float),
        "restecg":  np.random.randint(0, 3, n).astype(float),
        "thalach":  np.random.randint(70, 210, n).astype(float),
        "exang":    np.random.randint(0, 2, n).astype(float),
        "oldpeak":  np.round(np.random.uniform(0, 6.2, n), 1),
        "slope":    np.random.randint(0, 3, n).astype(float),
        "ca":       np.random.randint(0, 5, n).astype(float),
        "thal":     np.random.randint(0, 4, n).astype(float),
        "target":   np.random.randint(0, 2, n),
    })


# ─── Diabetes ─────────────────────────────────────────────────────────────────

def load_diabetes() -> pd.DataFrame:
    path = _data_path("diabetes.csv")
    if path.exists():
        df = pd.read_csv(path)
        logger.info(f"Loaded diabetes.csv  shape={df.shape}")
    else:
        logger.warning("diabetes.csv not found — using synthetic data")
        df = _synthetic_diabetes()
    return df


def _synthetic_diabetes(n: int = 1000) -> pd.DataFrame:
    np.random.seed(42)
    return pd.DataFrame({
        "Pregnancies":              np.random.randint(0, 15, n),
        "Glucose":                  np.random.randint(70, 200, n).astype(float),
        "BloodPressure":            np.random.randint(40, 130, n).astype(float),
        "SkinThickness":            np.random.randint(10, 80, n).astype(float),
        "Insulin":                  np.random.randint(10, 850, n).astype(float),
        "BMI":                      np.round(np.random.uniform(18, 60, n), 1),
        "DiabetesPedigreeFunction": np.round(np.random.uniform(0.07, 2.5, n), 3),
        "Age":                      np.random.randint(21, 80, n),
        "Outcome":                  np.random.randint(0, 2, n),
    })


# ─── Chronic Kidney Disease ───────────────────────────────────────────────────

def load_kidney_disease() -> pd.DataFrame:
    path = _data_path("kidney.csv")
    if path.exists():
        # UCI kidney CSV often has issues — read carefully
        try:
            df = pd.read_csv(path)
        except Exception:
            df = pd.read_csv(path, encoding="latin-1")
        logger.info(f"Loaded kidney.csv  shape={df.shape}  cols={list(df.columns[:5])}…")
    else:
        logger.warning("kidney.csv not found — using synthetic data")
        df = _synthetic_kidney()
    return df


def _synthetic_kidney(n: int = 1000) -> pd.DataFrame:
    np.random.seed(42)
    return pd.DataFrame({
        "age":                    np.random.randint(2, 90, n).astype(float),
        "blood_pressure":         np.random.randint(50, 180, n).astype(float),
        "specific_gravity":       np.random.choice([1.005,1.010,1.015,1.020,1.025], n),
        "albumin":                np.random.randint(0, 5, n).astype(float),
        "sugar":                  np.random.randint(0, 5, n).astype(float),
        "red_blood_cells":        np.random.randint(0, 2, n).astype(float),
        "pus_cell":               np.random.randint(0, 2, n).astype(float),
        "pus_cell_clumps":        np.random.randint(0, 2, n).astype(float),
        "bacteria":               np.random.randint(0, 2, n).astype(float),
        "blood_glucose_random":   np.random.randint(70, 490, n).astype(float),
        "blood_urea":             np.random.randint(10, 391, n).astype(float),
        "serum_creatinine":       np.round(np.random.uniform(0.4, 15.0, n), 1),
        "sodium":                 np.random.randint(111, 163, n).astype(float),
        "potassium":              np.round(np.random.uniform(2.5, 9.0, n), 1),
        "haemoglobin":            np.round(np.random.uniform(3.1, 17.8, n), 1),
        "packed_cell_volume":     np.random.randint(9, 54, n).astype(float),
        "white_blood_cell_count": np.random.randint(2200, 26400, n).astype(float),
        "red_blood_cell_count":   np.round(np.random.uniform(2.1, 8.0, n), 1),
        "hypertension":           np.random.randint(0, 2, n).astype(float),
        "diabetes_mellitus":      np.random.randint(0, 2, n).astype(float),
        "coronary_artery_disease":np.random.randint(0, 2, n).astype(float),
        "appetite":               np.random.randint(0, 2, n).astype(float),
        "pedal_edema":            np.random.randint(0, 2, n).astype(float),
        "anemia":                 np.random.randint(0, 2, n).astype(float),
        "classification":         np.random.randint(0, 2, n),
    })


# ─── Registry / constants ─────────────────────────────────────────────────────

DISEASE_LOADERS = {
    "heart":    load_heart_disease,
    "diabetes": load_diabetes,
    "kidney":   load_kidney_disease,
}

# Target column name in each raw CSV
# (preprocessing.py handles all the renaming edge-cases)
DISEASE_TARGET_COLS = {
    "heart":    "target",          # preprocessing handles 'condition' / 'num'
    "diabetes": "Outcome",
    "kidney":   "classification",  # preprocessing renames to 'target'
}

# Default feature names (used when no cached JSON exists)
DISEASE_FEATURE_NAMES = {
    "heart": [
        "age","sex","cp","trestbps","chol","fbs","restecg",
        "thalach","exang","oldpeak","slope","ca","thal",
    ],
    "diabetes": [
        "Pregnancies","Glucose","BloodPressure","SkinThickness",
        "Insulin","BMI","DiabetesPedigreeFunction","Age",
    ],
    "kidney": [
        "age","blood_pressure","specific_gravity","albumin","sugar",
        "red_blood_cells","pus_cell","pus_cell_clumps","bacteria",
        "blood_glucose_random","blood_urea","serum_creatinine","sodium",
        "potassium","haemoglobin","packed_cell_volume",
        "white_blood_cell_count","red_blood_cell_count",
        "hypertension","diabetes_mellitus","coronary_artery_disease",
        "appetite","pedal_edema","anemia",
    ],
}


def get_dataset(disease: str):
    """Return (X DataFrame, y Series) for a disease."""
    loader = DISEASE_LOADERS.get(disease)
    if loader is None:
        raise ValueError(f"Unknown disease: '{disease}'")
    df = loader()
    target = DISEASE_TARGET_COLS[disease]

    # Apply light cleaning so target column is usable
    from app.ml.pipelines.preprocessing import _clean_heart, _clean_kidney, _clean_diabetes
    if disease == "heart":
        df = _clean_heart(df)
        target = "target"
    elif disease == "diabetes":
        df = _clean_diabetes(df)
    elif disease == "kidney":
        df = _clean_kidney(df)
        if "classification" in df.columns:
            df.rename(columns={"classification": "target"}, inplace=True)
            target = "target"

    X = df.drop(columns=[target], errors="ignore").select_dtypes(include=[np.number])
    y = pd.to_numeric(df.get(target, pd.Series(dtype=float)), errors="coerce").fillna(0).astype(int)
    return X, y
