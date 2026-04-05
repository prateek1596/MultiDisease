"""
Prediction service — cache + risk scoring + A/B shadow testing.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from loguru import logger

from app.ml.training.trainer import training_service
from app.ml.explainability.shap_explainer import get_shap_explanation
from app.ml.risk_scoring import risk_category
from app.ml.ab_testing.shadow_tester import ab_testing
from app.core.cache import cache, make_prediction_key
from app.schemas.schemas import PredictionResponse, SHAPExplanation

DISEASE_LABELS = {
    "heart":    {0: "No Heart Disease",      1: "Heart Disease Detected"},
    "diabetes": {0: "Non-Diabetic",          1: "Diabetic"},
    "kidney":   {0: "No Kidney Disease",     1: "Chronic Kidney Disease"},
}


class PredictionService:

    def predict(
        self,
        disease: str,
        input_data: Dict[str, Any],
        model_name: str = "best",
        explain: bool = True,
        use_cache: bool = True,
    ) -> PredictionResponse:

        # Resolve 'best'
        if model_name == "best":
            model_name = training_service.get_best_model_name(disease)
            logger.info(f"Auto-selected: {model_name} for {disease}")

        # Cache check
        cache_key = make_prediction_key(disease, model_name, input_data)
        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                logger.info(f"Cache HIT: {cache_key[:30]}")
                return PredictionResponse(**cached)

        clf, feature_names = training_service.load_model(disease, model_name)
        X = self._align_input(input_data, feature_names)

        pred       = int(clf.predict(X)[0])
        prob       = clf.predict_proba(X)[0]
        confidence = float(prob[pred])
        labels     = DISEASE_LABELS.get(disease, {0: "Negative", 1: "Positive"})
        label      = labels.get(pred, str(pred))
        probability = {
            labels.get(0, "Negative"): float(prob[0]),
            labels.get(1, "Positive"): float(prob[1]),
        }

        # Risk band
        risk = risk_category(float(prob[1]), disease)

        # SHAP
        explanation = None
        if explain:
            shap_dict = get_shap_explanation(clf, X.values, feature_names, model_name)
            explanation = SHAPExplanation(**shap_dict)

        # A/B shadow
        self._maybe_shadow(disease, model_name, X, float(prob[1]))

        logger.info(
            f"Prediction | {disease}/{model_name} -> {pred} ({label}) "
            f"conf={confidence:.3f} risk={risk['level']}"
        )

        response = PredictionResponse(
            disease=disease,
            model_used=model_name,
            prediction=pred,
            label=label,
            confidence=confidence,
            probability=probability,
            explanation=explanation,
            risk=risk,
        )

        # Cache result
        if use_cache:
            cache.set(cache_key, response.model_dump())

        return response

    def _maybe_shadow(self, disease: str, primary_model: str, X: pd.DataFrame, prob_a: float):
        """If A/B is configured and enabled, run shadow model silently."""
        try:
            cfg = ab_testing.get_config(disease)
            if not cfg or not cfg.get("enabled"):
                return
            model_b = cfg["model_b"]
            if model_b == primary_model:
                model_b = cfg["model_a"]
            clf_b, feats_b = training_service.load_model(disease, model_b)
            X_b    = X[feats_b] if all(f in X.columns for f in feats_b) else X
            prob_b = float(clf_b.predict_proba(X_b)[0][1])
            ab_testing.log_result(disease, primary_model, model_b, prob_a, prob_b)
        except Exception as e:
            logger.debug(f"Shadow test skipped: {e}")

    def _align_input(self, input_data: Dict[str, Any], feature_names: List[str]) -> pd.DataFrame:
        norm = {k.lower().replace("-","_").replace(" ","_"): v for k, v in input_data.items()}
        row  = {}
        for feat in feature_names:
            key = feat.lower().replace("-","_").replace(" ","_")
            val = norm.get(key)
            row[feat] = float(val) if val is not None else 0.0
        return pd.DataFrame([row])


prediction_service = PredictionService()
