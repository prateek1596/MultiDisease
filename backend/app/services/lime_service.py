"""
LIME Explanation Service — provides local interpretable explanations.

Uses LIME (Local Interpretable Model-agnostic Explanations) to explain
individual predictions by approximating the model locally with an
interpretable model.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from loguru import logger

try:
    from lime import lime_tabular
    LIME_AVAILABLE = True
except ImportError:
    LIME_AVAILABLE = False
    logger.warning("LIME not installed. Run: pip install lime")

from app.ml.data_loader import DISEASE_LOADERS, DISEASE_TARGET_COLS


class LimeExplainerService:
    """Provides LIME explanations for predictions."""

    def __init__(self):
        self._explainers: Dict[str, Any] = {}
        self._training_data: Dict[str, np.ndarray] = {}

    def _get_training_data(self, disease: str) -> Tuple[np.ndarray, List[str]]:
        """Load training data for creating LIME explainer."""
        if disease in self._training_data:
            return self._training_data[disease]
        
        df = DISEASE_LOADERS[disease]()
        target_col = DISEASE_TARGET_COLS[disease]
        
        X = df.drop(columns=[target_col], errors='ignore')
        feature_names = list(X.columns)
        
        # Convert to numeric
        X_numeric = X.apply(pd.to_numeric, errors='coerce').fillna(0)
        
        self._training_data[disease] = (X_numeric.values, feature_names)
        return X_numeric.values, feature_names

    def _get_explainer(self, disease: str):
        """Get or create LIME explainer for a disease."""
        if not LIME_AVAILABLE:
            raise ImportError("LIME library not available")
        
        if disease in self._explainers:
            return self._explainers[disease]
        
        training_data, feature_names = self._get_training_data(disease)
        
        explainer = lime_tabular.LimeTabularExplainer(
            training_data,
            feature_names=feature_names,
            class_names=['Negative', 'Positive'],
            mode='classification',
            discretize_continuous=True,
        )
        
        self._explainers[disease] = explainer
        logger.info(f"Created LIME explainer for {disease}")
        return explainer

    def explain_prediction(
        self,
        disease: str,
        model: Any,
        input_array: np.ndarray,
        feature_names: List[str],
        num_features: int = 10,
    ) -> Dict[str, Any]:
        """
        Generate LIME explanation for a prediction.
        
        Args:
            disease: Disease type
            model: Trained classifier with predict_proba
            input_array: Input features as numpy array (1 row)
            feature_names: List of feature names
            num_features: Number of top features to explain
            
        Returns:
            Dict with explanation details
        """
        if not LIME_AVAILABLE:
            return {
                "available": False,
                "error": "LIME library not installed",
            }
        
        try:
            explainer = self._get_explainer(disease)
            
            # Ensure input is 1D
            instance = input_array.flatten()
            
            # Generate explanation
            exp = explainer.explain_instance(
                instance,
                model.predict_proba,
                num_features=num_features,
                top_labels=1,
            )
            
            # Get the predicted class
            predicted_class = model.predict(input_array.reshape(1, -1))[0]
            
            # Extract explanation for predicted class
            explanation_list = exp.as_list(label=int(predicted_class))
            
            # Parse into structured format
            contributions = []
            for feature_desc, weight in explanation_list:
                # Parse feature description (e.g., "age > 50" or "glucose <= 120")
                contributions.append({
                    "feature": feature_desc,
                    "contribution": float(weight),
                    "direction": "increases" if weight > 0 else "decreases",
                    "abs_contribution": abs(float(weight)),
                })
            
            # Sort by absolute contribution
            contributions.sort(key=lambda x: x["abs_contribution"], reverse=True)
            
            # Get intercept (base prediction)
            intercept = exp.intercept[int(predicted_class)]
            
            # Calculate local prediction accuracy
            local_pred = exp.local_pred[0] if hasattr(exp, 'local_pred') else None
            
            return {
                "available": True,
                "contributions": contributions,
                "intercept": float(intercept),
                "local_prediction": float(local_pred) if local_pred else None,
                "predicted_class": int(predicted_class),
                "num_features_shown": len(contributions),
            }
            
        except Exception as e:
            logger.error(f"LIME explanation failed: {e}")
            return {
                "available": False,
                "error": str(e),
            }

    def get_feature_importance_summary(
        self,
        disease: str,
        model: Any,
        feature_names: List[str],
        num_samples: int = 100,
    ) -> Dict[str, float]:
        """
        Get aggregate feature importance by averaging LIME explanations
        over multiple samples.
        """
        if not LIME_AVAILABLE:
            return {}
        
        try:
            training_data, _ = self._get_training_data(disease)
            
            # Sample from training data
            n_samples = min(num_samples, len(training_data))
            indices = np.random.choice(len(training_data), n_samples, replace=False)
            samples = training_data[indices]
            
            # Aggregate contributions
            importance_sums = {name: 0.0 for name in feature_names}
            count = 0
            
            for sample in samples:
                exp_result = self.explain_prediction(
                    disease, model, sample, feature_names, num_features=len(feature_names)
                )
                if exp_result.get("available"):
                    for contrib in exp_result["contributions"]:
                        # Try to match feature name
                        for name in feature_names:
                            if name.lower() in contrib["feature"].lower():
                                importance_sums[name] += contrib["abs_contribution"]
                                break
                    count += 1
            
            # Average
            if count > 0:
                importance_avg = {k: v / count for k, v in importance_sums.items()}
                # Normalize
                total = sum(importance_avg.values())
                if total > 0:
                    importance_avg = {k: v / total for k, v in importance_avg.items()}
                return importance_avg
            
            return {}
            
        except Exception as e:
            logger.error(f"Feature importance summary failed: {e}")
            return {}


# Singleton
lime_service = LimeExplainerService()
