"""
Advanced routes — all return graceful empty responses, never 500.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from loguru import logger

from app.core.security import get_current_user, require_admin
from app.core.cache import cache
from app.ml.risk_scoring import get_all_bands, risk_category
from app.ml.ab_testing.shadow_tester import ab_testing
from app.ml.training.trainer import training_service
from app.ml.data_loader import DISEASE_LOADERS, DISEASE_TARGET_COLS
from app.ml.pipelines.preprocessing import preprocess_data
from app.services.patient_report_service import patient_report_generator

router = APIRouter()
VALID_DISEASES = ("heart", "diabetes", "kidney")


# ── Risk Scoring ──────────────────────────────────────────────────────────────

@router.get("/risk-bands/{disease}")
async def get_risk_bands(disease: str, current_user: dict = Depends(get_current_user)):
    if disease not in VALID_DISEASES:
        raise HTTPException(400, f"Unknown disease: {disease}")
    return {"disease": disease, "bands": get_all_bands(disease)}


@router.get("/risk-score/{disease}")
async def get_risk_score(
    disease: str, probability: float,
    current_user: dict = Depends(get_current_user),
):
    if disease not in VALID_DISEASES:
        raise HTTPException(400, f"Unknown disease: {disease}")
    return risk_category(probability, disease)


# ── Cache ─────────────────────────────────────────────────────────────────────

@router.get("/cache/stats")
async def cache_stats(current_user: dict = Depends(require_admin)):
    try:
        return cache.stats()
    except Exception as e:
        return {"backend": "error", "total_keys": 0, "error": str(e)}


@router.delete("/cache/flush/{disease}")
async def flush_cache(disease: str, current_user: dict = Depends(require_admin)):
    n = cache.flush_pattern(f"pred:{disease}:*")
    return {"flushed": n, "disease": disease}


@router.delete("/cache/flush-all")
async def flush_all_cache(current_user: dict = Depends(require_admin)):
    total = sum(cache.flush_pattern(f"pred:{d}:*") for d in VALID_DISEASES)
    return {"flushed": total}


# ── AutoML ────────────────────────────────────────────────────────────────────

class TuneRequest(BaseModel):
    disease:    str
    model_name: str
    n_trials:   int = Field(30, ge=5, le=200)


@router.post("/automl/tune")
async def trigger_automl_tune(
    payload: TuneRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin),
):
    if payload.disease not in VALID_DISEASES:
        raise HTTPException(400, f"Unknown disease: {payload.disease}")
    background_tasks.add_task(_run_automl, payload.disease, payload.model_name, payload.n_trials)
    return {
        "status":  "started",
        "message": f"AutoML tuning started: {payload.disease}/{payload.model_name} ({payload.n_trials} trials)",
    }


async def _run_automl(disease: str, model_name: str, n_trials: int):
    from app.ml.automl.tuner import AutoMLTuner
    try:
        df         = DISEASE_LOADERS[disease]()
        target_col = DISEASE_TARGET_COLS[disease]
        X_train, _, y_train, _ = preprocess_data(df, target_col, disease=disease)
        tuner  = AutoMLTuner(n_trials=n_trials)
        result = tuner.tune(model_name, disease, X_train, y_train)
        logger.info(f"AutoML done: {result}")
    except Exception as e:
        logger.error(f"AutoML failed: {e}")


@router.get("/automl/results/{disease}")
async def get_automl_results(disease: str, current_user: dict = Depends(get_current_user)):
    try:
        from app.ml.automl.tuner import automl_tuner
        from app.ml.pipelines.model_registry import ALL_MODEL_NAMES
        results = {}
        for model in ALL_MODEL_NAMES:
            r = automl_tuner.load(model, disease)
            if r:
                results[model] = r
        return {"disease": disease, "results": results, "total": len(results)}
    except Exception as e:
        return {"disease": disease, "results": {}, "total": 0, "error": str(e)}


# ── Counterfactual ────────────────────────────────────────────────────────────

class CounterfactualRequest(BaseModel):
    input_data:         Dict[str, Any]
    model_name:         str = "best"
    n_counterfactuals:  int = Field(3, ge=1, le=10)


@router.post("/counterfactual/{disease}")
async def get_counterfactuals(
    disease: str,
    payload: CounterfactualRequest,
    current_user: dict = Depends(get_current_user),
):
    if disease not in VALID_DISEASES:
        raise HTTPException(400, f"Unknown disease: {disease}")

    try:
        model_name = payload.model_name
        if model_name == "best":
            model_name = training_service.get_best_model_name(disease)
        clf, feature_names = training_service.load_model(disease, model_name)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

    try:
        df         = DISEASE_LOADERS[disease]()
        target_col = DISEASE_TARGET_COLS[disease]
        X_train, _, y_train, _ = preprocess_data(df, target_col, disease=disease)
    except Exception as e:
        raise HTTPException(500, f"Data loading failed: {e}")

    try:
        from app.ml.counterfactual.explorer import CounterfactualExplorer
        explorer = CounterfactualExplorer(clf, feature_names, disease)
        return explorer.find_counterfactuals(
            payload.input_data, X_train, y_train,
            n_counterfactuals=payload.n_counterfactuals,
        )
    except Exception as e:
        logger.error(f"Counterfactual error: {e}")
        raise HTTPException(500, str(e))


# ── A/B Testing ───────────────────────────────────────────────────────────────

class ABConfigPayload(BaseModel):
    model_a:     str
    model_b:     str
    enabled:     bool = True
    min_samples: int  = 30


@router.post("/ab/{disease}/configure")
async def configure_ab(
    disease: str, payload: ABConfigPayload,
    current_user: dict = Depends(require_admin),
):
    if disease not in VALID_DISEASES:
        raise HTTPException(400, f"Unknown disease: {disease}")
    return ab_testing.configure(
        disease=disease, model_a=payload.model_a,
        model_b=payload.model_b, enabled=payload.enabled,
        min_samples=payload.min_samples,
    )


@router.get("/ab/{disease}/status")
async def ab_status(disease: str, current_user: dict = Depends(get_current_user)):
    try:
        cfg     = ab_testing.get_config(disease)
        summary = ab_testing.get_log_summary(disease)
        return {"config": cfg, "summary": summary}
    except Exception as e:
        return {"config": None, "summary": {"n": 0}}


@router.get("/ab/{disease}/analyse")
async def ab_analyse(disease: str, current_user: dict = Depends(require_admin)):
    if disease not in VALID_DISEASES:
        raise HTTPException(400, f"Unknown disease: {disease}")
    return ab_testing.analyse(disease)


@router.delete("/ab/{disease}/clear")
async def ab_clear(disease: str, current_user: dict = Depends(require_admin)):
    ab_testing.clear_log(disease)
    return {"status": "cleared", "disease": disease}


# ── Patient PDF Report ────────────────────────────────────────────────────────

class PatientReportPayload(BaseModel):
    prediction_data: Dict[str, Any]
    patient_name:    str = "Anonymous Patient"
    patient_id:      Optional[str] = None
    clinician:       Optional[str] = None


@router.post("/patient-report")
async def generate_patient_report(
    payload: PatientReportPayload,
    current_user: dict = Depends(get_current_user),
):
    try:
        path = patient_report_generator.generate(
            prediction_data=payload.prediction_data,
            patient_name=payload.patient_name,
            patient_id=payload.patient_id,
            clinician=payload.clinician,
        )
        from pathlib import Path
        return FileResponse(path=path, media_type="application/pdf", filename=Path(path).name)
    except Exception as e:
        logger.error(f"Patient report error: {e}")
        raise HTTPException(500, str(e))


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/analytics")
async def get_analytics(current_user: dict = Depends(get_current_user)):
    """Return prediction analytics — always returns valid JSON, never 500."""
    empty = {
        "total_predictions": 0, "predictions_today": 0,
        "by_disease": {}, "by_model": {}, "positive_rate": 0,
        "avg_confidence": 0, "daily_counts": [],
        "cache_stats": cache.stats(),
        "note": "No prediction history yet.",
    }
    try:
        from sqlalchemy import select, func, text
        from app.core.database import AsyncSessionLocal
        from app.models.db_models import Prediction

        async with AsyncSessionLocal() as db:
            total_res = await db.execute(select(func.count(Prediction.id)))
            total     = total_res.scalar() or 0

            disease_res = await db.execute(
                select(Prediction.disease_type, func.count(Prediction.id))
                .group_by(Prediction.disease_type)
            )
            by_disease = {str(r[0]): r[1] for r in disease_res}

            model_res = await db.execute(
                select(Prediction.model_used, func.count(Prediction.id))
                .group_by(Prediction.model_used)
            )
            by_model = {r[0]: r[1] for r in model_res}

            pos_res = await db.execute(
                select(func.count(Prediction.id))
                .where(Prediction.prediction_result == 1)
            )
            n_positive = pos_res.scalar() or 0

            conf_res = await db.execute(select(func.avg(Prediction.confidence)))
            avg_conf  = float(conf_res.scalar() or 0)

            try:
                daily_res = await db.execute(text("""
                    SELECT DATE(created_at) as day, COUNT(*) as n
                    FROM predictions
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY day ORDER BY day
                """))
                daily = [{"date": str(r[0]), "count": r[1]} for r in daily_res]

                today_res = await db.execute(text(
                    "SELECT COUNT(*) FROM predictions WHERE created_at::date = CURRENT_DATE"
                ))
                today = today_res.scalar() or 0
            except Exception:
                daily = []
                today = 0

            return {
                "total_predictions": total,
                "predictions_today": today,
                "by_disease":        by_disease,
                "by_model":          by_model,
                "positive_rate":     round(n_positive / total, 4) if total > 0 else 0,
                "avg_confidence":    round(avg_conf, 4),
                "daily_counts":      daily,
                "cache_stats":       cache.stats(),
            }
    except Exception as e:
        logger.warning(f"Analytics DB query failed: {e}")
        empty["note"] = f"Database unavailable: {str(e)[:80]}"
        return empty
