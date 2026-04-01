#!/usr/bin/env python3
"""
============================================================
  Import Existing Models
  Converts your .pkl files → new .joblib format
============================================================

Usage:
    cd backend/
    python scripts/import_existing_models.py \
        --heart   ../models/heart_model.pkl \
        --diabetes ../models/diabetes_model.pkl \
        --kidney  ../models/kidney_model.pkl

Or just copy your .pkl files into backend/ml/saved_models/
with the names  heart_model.pkl / diabetes_model.pkl / kidney_model.pkl
and the system will auto-detect them.
============================================================
"""

import sys, argparse, json, joblib
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

from app.core.config import settings
from app.ml.data_loader import DISEASE_FEATURE_NAMES

SAVE_PATH = Path(settings.MODEL_SAVE_PATH)
SAVE_PATH.mkdir(parents=True, exist_ok=True)


def import_pkl(disease: str, pkl_path: str):
    pkl_path = Path(pkl_path)
    if not pkl_path.exists():
        print(f"  [{disease}] NOT FOUND: {pkl_path}")
        return False

    print(f"  [{disease}] Loading {pkl_path.name} ...")
    clf = joblib.load(pkl_path)

    feature_names = DISEASE_FEATURE_NAMES.get(disease, [])

    # Check if cached feature list exists
    fn_cache = SAVE_PATH / f"{disease}_features.json"
    if fn_cache.exists():
        feature_names = json.loads(fn_cache.read_text())
        print(f"           Using cached feature names ({len(feature_names)} features)")
    else:
        print(f"           Using default feature names ({len(feature_names)} features)")
        fn_cache.write_text(json.dumps(feature_names))

    out = SAVE_PATH / f"{disease}_random_forest.joblib"
    joblib.dump({"model": clf, "feature_names": feature_names}, out)
    (SAVE_PATH / f"{disease}_best_model.txt").write_text("random_forest")
    print(f"           Saved → {out.name}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Import existing PKL models")
    parser.add_argument("--heart",    default=None)
    parser.add_argument("--diabetes", default=None)
    parser.add_argument("--kidney",   default=None)
    args = parser.parse_args()

    mapping = {
        "heart":    args.heart    or str(SAVE_PATH / "heart_model.pkl"),
        "diabetes": args.diabetes or str(SAVE_PATH / "diabetes_model.pkl"),
        "kidney":   args.kidney   or str(SAVE_PATH / "kidney_model.pkl"),
    }

    print("\nImporting existing models...\n")
    ok = 0
    for disease, path in mapping.items():
        if import_pkl(disease, path):
            ok += 1

    print(f"\nDone: {ok}/{len(mapping)} models imported.")
    if ok > 0:
        print("You can now run the API server:")
        print("  uvicorn app.main:app --reload --port 8000\n")


if __name__ == "__main__":
    main()
