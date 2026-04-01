"""
Preprocessing pipeline — mirrors your existing src/preprocessing.py exactly,
adapted to work inside the FastAPI backend.

Handles:
  - Heart Disease  (target: 'condition' or 'target' or 'num')
  - Diabetes       (target: 'Outcome')  → zero→NaN imputation on clinical cols
  - Kidney Disease (target: 'classification' or 'target') → robust text encoding
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from imblearn.over_sampling import SMOTE
from loguru import logger
from typing import Tuple, List


# ─── Column definitions ──────────────────────────────────────────────────────

DIABETES_ZERO_COLS = [
    "Glucose", "BloodPressure", "SkinThickness", "Insulin", "BMI"
]

# Comprehensive kidney encoding map
KIDNEY_BINARY_MAP = {
    # CKD target
    "ckd":        1, "notckd":    0, "ckd\t":      1,
    # yes/no
    "yes":        1, "no":        0,
    # present/notpresent
    "present":    1, "notpresent":0,
    # normal/abnormal
    "normal":     1, "abnormal":  0,
    # good/poor
    "good":       1, "poor":      0,
    # rbc values
    "1":          1, "0":         0,
}


# ─── Public API ───────────────────────────────────────────────────────────────

def preprocess_data(
    df: pd.DataFrame,
    target_column: str,
    disease: str = None,
    test_size: float = 0.2,
    random_state: int = 42,
    apply_smote: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Full preprocessing pipeline:
      1. Disease-specific cleaning
      2. Median imputation
      3. StandardScaler
      4. Stratified train/test split
      5. SMOTE on training set only
    """
    df = df.copy()

    # ── 1. Disease-specific cleaning ─────────────────────────────────────────
    disease_key = (disease or "").lower()

    if target_column == "Outcome" or disease_key == "diabetes":
        df = _clean_diabetes(df)

    elif disease_key == "kidney":
        df = _clean_kidney(df)
        # Kidney target may be called 'classification' in the raw CSV
        if "classification" in df.columns:
            df.rename(columns={"classification": "target"}, inplace=True)
            target_column = "target"
        elif "target" not in df.columns:
            # Fall back: look for any column that looks like CKD
            for c in df.columns:
                if "class" in c.lower():
                    df.rename(columns={c: "target"}, inplace=True)
                    target_column = "target"
                    break

    elif disease_key == "heart":
        df = _clean_heart(df)
        target_column = "target"   # _clean_heart always unifies to 'target'

    # ── 2. Validate target exists ─────────────────────────────────────────────
    if target_column not in df.columns:
        available = list(df.columns)
        raise ValueError(
            f"Target column '{target_column}' not found after cleaning. "
            f"Available columns: {available}"
        )

    X = df.drop(columns=[target_column])
    y = df[target_column]

    # Drop any remaining non-numeric / all-NaN columns
    X = X.select_dtypes(include=[np.number])
    X = X.dropna(axis=1, how="all")

    # Encode target safely
    try:
        y = y.map(KIDNEY_BINARY_MAP).fillna(y).astype(float).astype(int)
    except Exception:
        y = pd.to_numeric(y, errors="coerce").fillna(0).astype(int)

    # Drop rows where target is still NaN
    valid = y.notna()
    X = X[valid]
    y = y[valid]

    # ── 3. Imputation ─────────────────────────────────────────────────────────
    imputer = SimpleImputer(strategy="median")
    X_imputed = pd.DataFrame(
        imputer.fit_transform(X),
        columns=X.columns,
    )

    # ── 4. Scaling ────────────────────────────────────────────────────────────
    scaler = StandardScaler()
    X_scaled = pd.DataFrame(
        scaler.fit_transform(X_imputed),
        columns=X.columns,
    )

    # ── 5. Train / test split ─────────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    # ── 6. SMOTE ──────────────────────────────────────────────────────────────
    if apply_smote:
        try:
            min_class_count = int(y_train.value_counts().min())
            k = min(5, max(1, min_class_count - 1))
            smote = SMOTE(random_state=random_state, k_neighbors=k)
            X_res, y_res = smote.fit_resample(X_train, y_train)
            X_train = pd.DataFrame(X_res, columns=X.columns)
            y_train = pd.Series(y_res, name=target_column)
            logger.info(
                f"SMOTE → {dict(pd.Series(y_train).value_counts())}"
            )
        except Exception as e:
            logger.warning(f"SMOTE skipped: {e}")

    logger.info(
        f"Preprocessing done | disease={disease} "
        f"train={len(X_train)} test={len(X_test)} features={len(X.columns)}"
    )
    return X_train, X_test, y_train, y_test


def get_test_size_only(disease: str) -> int:
    """
    Quickly compute the test-set row count WITHOUT loading a model.
    Used by the fairness /info endpoint.
    """
    from app.ml.data_loader import DISEASE_LOADERS, DISEASE_TARGET_COLS
    df         = DISEASE_LOADERS[disease]()
    target_col = DISEASE_TARGET_COLS[disease]
    _, X_test, _, _ = preprocess_data(
        df, target_column=target_col, disease=disease
    )
    return len(X_test)


# ─── Disease-specific cleaners ───────────────────────────────────────────────

def _clean_diabetes(df: pd.DataFrame) -> pd.DataFrame:
    """Replace physiologically impossible zeros with NaN, then median-fill."""
    present = [c for c in DIABETES_ZERO_COLS if c in df.columns]
    df[present] = df[present].replace(0, np.nan)
    for col in present:
        df[col].fillna(df[col].median(), inplace=True)
    logger.info("Diabetes: zero→median imputation applied")
    return df


def _clean_kidney(df: pd.DataFrame) -> pd.DataFrame:
    """
    Robust kidney CSV cleaner.
    Handles: tab-separated values, trailing whitespace, '?' placeholders,
    mixed case text labels, and numeric strings.
    """
    # 1. Strip column names
    df.columns = [
        c.strip().lower()
         .replace(" ", "_")
         .replace("\t", "")
        for c in df.columns
    ]

    # 2. Drop an unnamed index column if present (common in UCI kidney CSV)
    drop_cols = [c for c in df.columns if c.startswith("unnamed") or c == "id"]
    if drop_cols:
        df.drop(columns=drop_cols, inplace=True)

    # 3. Replace missing-value markers
    df.replace(["?", "\t?", " ?", "?\t", ""], np.nan, inplace=True)

    # 4. Encode each object column
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = (
                df[col].astype(str)
                       .str.strip()
                       .str.lower()
                       .str.replace("\t", "", regex=False)
                       .map(KIDNEY_BINARY_MAP)
            )

    # 5. Cast everything to numeric
    df = df.apply(pd.to_numeric, errors="coerce")
    return df


def _clean_heart(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise column names, ensure target is binary."""
    df.columns = [c.strip().lower() for c in df.columns]
    df.replace("?", np.nan, inplace=True)
    df = df.apply(pd.to_numeric, errors="coerce")

    # UCI multi-class target (0=healthy, 1-4=disease) → binary
    if "num" in df.columns and "target" not in df.columns and "condition" not in df.columns:
        df["target"] = (df["num"] > 0).astype(int)
        df.drop("num", axis=1, inplace=True)

    if "condition" in df.columns:
        df.rename(columns={"condition": "target"}, inplace=True)

    if "target" in df.columns:
        df["target"] = (df["target"] > 0).astype(int)

    return df
