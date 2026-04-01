#!/usr/bin/env python3
"""
============================================================
  Standalone Training Script
  Multi-Disease Prediction System
============================================================

Run this ONCE to train all models and create the .joblib
artifacts that the FastAPI server needs for predictions.

Usage:
    cd backend/
    python scripts/train_all.py

    # Train specific diseases only:
    python scripts/train_all.py --diseases heart diabetes

    # Train specific models only:
    python scripts/train_all.py --models random_forest xgboost lightgbm

    # Use your existing CSV datasets:
    # Place them in backend/ml/data/
    #   heart.csv    (target column: 'target' or 'condition')
    #   diabetes.csv (target column: 'Outcome')
    #   kidney.csv   (target column: 'classification' or 'target')

    # Already have .pkl models from previous project?
    # Drop them in backend/ml/saved_models/:
    #   heart_model.pkl / diabetes_model.pkl / kidney_model.pkl
    # The script will auto-convert them to the new .joblib format.
============================================================
"""

import sys
import argparse
import os
from pathlib import Path
from datetime import datetime

# ── Make sure we can import app modules ──────────────────────────────────────
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# Load .env before importing settings
from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

# ── Now import app modules ────────────────────────────────────────────────────
from loguru import logger
from app.core.config import settings

# Ensure directories exist before anything else
Path(settings.MODEL_SAVE_PATH).mkdir(parents=True, exist_ok=True)
Path(settings.REPORT_SAVE_PATH).mkdir(parents=True, exist_ok=True)
Path(settings.DATA_PATH).mkdir(parents=True, exist_ok=True)
Path("logs").mkdir(exist_ok=True)

from app.ml.training.trainer import training_service
from app.ml.pipelines.model_registry import ALL_MODEL_NAMES
from app.ml.evaluation.evaluator import get_all_metrics


DISEASES     = ["heart", "diabetes", "kidney"]
MODEL_NAMES  = ALL_MODEL_NAMES   # all 6 by default


def parse_args():
    p = argparse.ArgumentParser(description="Train all disease prediction models")
    p.add_argument(
        "--diseases", nargs="+", default=DISEASES,
        choices=DISEASES,
        help="Diseases to train (default: all three)",
    )
    p.add_argument(
        "--models", nargs="+", default=MODEL_NAMES,
        choices=MODEL_NAMES,
        help="Models to train (default: all six)",
    )
    p.add_argument(
        "--skip-existing", action="store_true",
        help="Skip training if .joblib artifact already exists",
    )
    return p.parse_args()


def banner(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def main():
    args = parse_args()
    start = datetime.now()

    banner("MULTI-DISEASE PREDICTION SYSTEM — TRAINING")
    print(f"Diseases : {args.diseases}")
    print(f"Models   : {args.models}")
    print(f"Save path: {settings.MODEL_SAVE_PATH}")
    print(f"Data path: {settings.DATA_PATH}")

    # ── Check for existing PKLs from previous project ─────────────────────────
    model_dir = Path(settings.MODEL_SAVE_PATH)
    for disease in args.diseases:
        for fname in [f"{disease}_model.pkl", f"models/{disease}_model.pkl"]:
            if Path(fname).exists() or (model_dir / fname.split("/")[-1]).exists():
                print(f"\n  Found legacy pkl for '{disease}' — will auto-convert")

    # ── Train ─────────────────────────────────────────────────────────────────
    diseases_to_train = []
    for disease in args.diseases:
        if args.skip_existing:
            all_exist = all(
                (model_dir / f"{disease}_{m}.joblib").exists()
                for m in args.models
            )
            if all_exist:
                print(f"\n  Skipping {disease} — all artifacts exist")
                continue
        diseases_to_train.append(disease)

    if not diseases_to_train:
        print("\nAll models already trained. Use --skip-existing=False to retrain.")
    else:
        results = training_service.train_all(
            diseases=diseases_to_train,
            models=args.models,
        )
        _print_results(results)

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = (datetime.now() - start).total_seconds()
    banner("TRAINING COMPLETE")
    print(f"Time elapsed: {elapsed:.1f}s")

    all_metrics = get_all_metrics()
    if all_metrics:
        print("\nBest Models Summary:")
        for disease, models_m in all_metrics.items():
            if not models_m:
                continue
            best = max(models_m, key=lambda m: models_m[m].get("roc_auc", 0))
            auc  = models_m[best].get("roc_auc", 0)
            acc  = models_m[best].get("accuracy", 0)
            print(f"  {disease:10s}  best={best:25s}  AUC={auc:.4f}  ACC={acc:.4f}")

    print(f"\n  Artifacts saved to: {settings.MODEL_SAVE_PATH}/")
    print(f"  Reports saved to  : {settings.REPORT_SAVE_PATH}/")
    print(f"\n  Start the API server with:")
    print(f"    uvicorn app.main:app --reload --port 8000")
    print()


def _print_results(results: dict):
    for disease, model_results in results.items():
        print(f"\n  {disease.upper()}")
        for model_name, m in model_results.items():
            if "error" in m:
                print(f"    {model_name:25s}  ERROR: {m['error']}")
            else:
                flag = " ★ BEST" if m.get("is_best") else ""
                print(
                    f"    {model_name:25s}  "
                    f"ACC={m.get('accuracy',0):.4f}  "
                    f"AUC={m.get('roc_auc',0):.4f}  "
                    f"F1={m.get('f1_score',0):.4f}"
                    f"{flag}"
                )


if __name__ == "__main__":
    main()
