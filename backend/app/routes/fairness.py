"""
Fairness analysis routes.

GET  /api/fairness/{disease}/info
     Returns test-set size (no model needed)

POST /api/fairness/{disease}
     Body: { groups: [{label, pct}, ...], attr_name, model_name }
     Builds sensitive_attr array automatically from pct splits
     Returns full fairness report JSON

GET  /api/fairness/{disease}/dashboard
     Returns last-saved fairness dashboard PNG
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List
from loguru import logger
import numpy as np

from app.core.security import get_current_user
from app.ml.training.trainer import training_service
from app.ml.data_loader import DISEASE_LOADERS, DISEASE_TARGET_COLS
from app.ml.pipelines.preprocessing import preprocess_data, get_test_size_only
from app.ml.fairness.fairness_analyzer import FairnessAnalyzer

router = APIRouter()

VALID_DISEASES = ("heart", "diabetes", "kidney")


# ── Schemas ───────────────────────────────────────────────────────────────────

class GroupSplit(BaseModel):
    label: str
    pct:   float = Field(..., gt=0, le=100)


class FairnessRequest(BaseModel):
    groups:     List[GroupSplit]
    attr_name:  str = "Group"
    model_name: str = "best"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_attr_array(groups: List[GroupSplit], n: int) -> List[str]:
    """Build a length-n attribute array from percentage splits, exactly."""
    total = sum(g.pct for g in groups)
    counts, running = [], 0
    for i, g in enumerate(groups):
        if i == len(groups) - 1:
            counts.append(n - running)
        else:
            c = round(n * g.pct / total)
            counts.append(c)
            running += c

    attr: List[str] = []
    for g, c in zip(groups, counts):
        attr.extend([g.label] * max(0, c))

    # Guarantee exact length
    while len(attr) < n:
        attr.append(groups[-1].label)
    attr = attr[:n]

    # Shuffle so groups are mixed throughout the test set
    rng = np.random.default_rng(42)
    rng.shuffle(attr)
    return attr


def _load_test_split(disease: str):
    df         = DISEASE_LOADERS[disease]()
    target_col = DISEASE_TARGET_COLS[disease]
    _, X_test, _, y_test = preprocess_data(
        df, target_column=target_col, disease=disease
    )
    return X_test, y_test


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/fairness/{disease}/info")
async def fairness_info(
    disease: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Return the test-set size for a disease — no model required.
    The frontend uses this to display the exact sample count.
    """
    if disease not in VALID_DISEASES:
        raise HTTPException(status_code=400, detail=f"Unknown disease: {disease}")
    try:
        n = get_test_size_only(disease)
        return {"disease": disease, "test_size": n}
    except Exception as e:
        logger.error(f"fairness/info error [{disease}]: {e}")
        # Return a graceful fallback so the frontend doesn't hang
        fallback = {"heart": 61, "diabetes": 154, "kidney": 80}
        return {
            "disease": disease,
            "test_size": fallback.get(disease, 100),
            "warning": str(e),
        }


@router.post("/fairness/{disease}")
async def run_fairness_analysis(
    disease: str,
    payload: FairnessRequest,
    current_user: dict = Depends(get_current_user),
):
    """Run fairness analysis. Groups defined as percentage splits."""
    if disease not in VALID_DISEASES:
        raise HTTPException(status_code=400, detail=f"Unknown disease: {disease}")
    if len(payload.groups) < 2:
        raise HTTPException(status_code=422, detail="Need at least 2 groups.")

    # Load model
    try:
        model_name = payload.model_name
        if model_name == "best":
            model_name = training_service.get_best_model_name(disease)
        clf, feature_names = training_service.load_model(disease, model_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model loading failed: {e}")

    # Load test split
    try:
        X_test, y_test = _load_test_split(disease)
    except Exception as e:
        logger.error(f"Test split failed [{disease}]: {e}")
        raise HTTPException(status_code=500, detail=f"Data loading failed: {e}")

    n_test = len(y_test)
    attr   = _build_attr_array(payload.groups, n_test)

    logger.info(
        f"Fairness | disease={disease} model={model_name} "
        f"n={n_test} groups={[g.label for g in payload.groups]}"
    )

    # Predict
    try:
        y_pred = clf.predict(X_test)
        y_prob = clf.predict_proba(X_test)[:, 1]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    # Analyse
    try:
        analyzer = FairnessAnalyzer(
            y_true=y_test.values,
            y_pred=y_pred,
            y_prob=y_prob,
            sensitive_attr=attr,
            attr_name=payload.attr_name,
        )
        report = analyzer.generate_fairness_report()
        analyzer.plot_fairness_dashboard()
    except Exception as e:
        logger.error(f"Fairness analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    report["test_size"]  = n_test
    report["model_used"] = model_name
    return report


@router.get("/fairness/{disease}/dashboard")
async def get_fairness_dashboard(
    disease: str,
    attr_name: str = "group",
    current_user: dict = Depends(get_current_user),
):
    """Return the most recently generated fairness dashboard PNG."""
    from pathlib import Path
    from app.core.config import settings

    out_dir = Path(settings.REPORT_SAVE_PATH) / "fairness"
    path    = out_dir / f"fairness_{attr_name.lower()}.png"

    if not path.exists():
        # Return any PNG in the directory (most recent)
        pngs = sorted(out_dir.glob("*.png"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        if pngs:
            path = pngs[0]
        else:
            raise HTTPException(
                status_code=404,
                detail="No dashboard PNG found. Run POST /api/fairness/{disease} first.",
            )
    return FileResponse(str(path), media_type="image/png")
