"""
Counterfactual / What-If Explorer.

Primary: DiCE (Diverse Counterfactual Explanations) if installed.
Fallback: greedy single-feature perturbation search — no extra deps.

Usage:
    explorer = CounterfactualExplorer(clf, feature_names, disease)
    result = explorer.find_counterfactuals(input_dict, n=3)
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from loguru import logger


DICE_AVAILABLE = False
try:
    import dice_ml
    DICE_AVAILABLE = True
except ImportError:
    logger.info("dice_ml not installed — using greedy counterfactual fallback")


class CounterfactualExplorer:
    """
    Find minimal input changes that would flip the prediction outcome.
    """

    def __init__(self, clf, feature_names: List[str], disease: str):
        self.clf           = clf
        self.feature_names = feature_names
        self.disease       = disease

    def find_counterfactuals(
        self,
        input_dict: Dict[str, float],
        X_train: pd.DataFrame,
        y_train: pd.Series,
        n_counterfactuals: int = 3,
        proximity_weight: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Generate counterfactual explanations.

        Returns dict with:
          - original_prediction: int
          - original_probability: float
          - counterfactuals: list of {features_changed, new_input, new_prediction, new_probability, changes}
          - method: 'dice' | 'greedy'
        """
        # Build aligned input
        row = self._align(input_dict)
        orig_pred  = int(self.clf.predict(row)[0])
        orig_prob  = float(self.clf.predict_proba(row)[0][orig_pred])
        target_class = 1 - orig_pred   # flip the outcome

        if DICE_AVAILABLE:
            try:
                return self._dice_counterfactuals(
                    row, X_train, y_train,
                    orig_pred, orig_prob, target_class,
                    n_counterfactuals,
                )
            except Exception as e:
                logger.warning(f"DiCE failed ({e}) — falling back to greedy")

        return self._greedy_counterfactuals(
            row, X_train, orig_pred, orig_prob,
            target_class, n_counterfactuals,
        )

    # ── DiCE ─────────────────────────────────────────────────────────────────

    def _dice_counterfactuals(
        self, row, X_train, y_train,
        orig_pred, orig_prob, target_class, n,
    ) -> Dict[str, Any]:
        import dice_ml

        df_train = X_train.copy()
        df_train["target"] = y_train.values

        data_obj = dice_ml.Data(
            dataframe=df_train,
            continuous_features=self.feature_names,
            outcome_name="target",
        )
        model_obj = dice_ml.Model(model=self.clf, backend="sklearn")
        exp = dice_ml.Dice(data_obj, model_obj, method="random")

        cf = exp.generate_counterfactuals(
            row,
            total_CFs=n,
            desired_class=target_class,
            verbose=False,
        )
        cfs_df = cf.cf_examples_list[0].final_cfs_df

        results = []
        for _, cf_row in cfs_df.iterrows():
            cf_input = cf_row[self.feature_names].to_dict()
            cf_arr   = pd.DataFrame([cf_input])
            cf_pred  = int(self.clf.predict(cf_arr)[0])
            cf_prob  = float(self.clf.predict_proba(cf_arr)[0][cf_pred])
            orig_vals = row.iloc[0].to_dict()

            changes = [
                {
                    "feature":       feat,
                    "original":      round(float(orig_vals[feat]), 4),
                    "counterfactual": round(float(cf_input[feat]), 4),
                    "delta":          round(float(cf_input[feat]) - float(orig_vals[feat]), 4),
                }
                for feat in self.feature_names
                if abs(float(cf_input[feat]) - float(orig_vals[feat])) > 1e-4
            ]

            results.append({
                "new_input":        {k: round(float(v), 4) for k, v in cf_input.items()},
                "new_prediction":   cf_pred,
                "new_probability":  round(cf_prob, 4),
                "features_changed": len(changes),
                "changes":          changes,
            })

        return {
            "original_prediction":  orig_pred,
            "original_probability": round(orig_prob, 4),
            "target_class":         target_class,
            "counterfactuals":      results,
            "method":               "dice",
        }

    # ── Greedy fallback ───────────────────────────────────────────────────────

    def _greedy_counterfactuals(
        self, row, X_train,
        orig_pred, orig_prob, target_class, n,
    ) -> Dict[str, Any]:
        """
        For each feature, try values from training-data percentiles.
        Keep changes that move the prediction toward the target class.
        Return top-n combinations sorted by fewest changes.
        """
        orig_vals = row.iloc[0].to_dict()
        results   = []

        # Single-feature perturbations
        for feat in self.feature_names:
            percentiles = np.percentile(X_train[feat].dropna(), [10, 25, 50, 75, 90])
            for pct_val in percentiles:
                if abs(pct_val - orig_vals[feat]) < 1e-4:
                    continue
                new_input = orig_vals.copy()
                new_input[feat] = float(pct_val)
                cf_arr   = pd.DataFrame([new_input])
                cf_pred  = int(self.clf.predict(cf_arr)[0])
                cf_prob  = float(self.clf.predict_proba(cf_arr)[0][target_class])

                if cf_pred == target_class:
                    results.append({
                        "new_input":       {k: round(float(v), 4) for k, v in new_input.items()},
                        "new_prediction":  cf_pred,
                        "new_probability": round(cf_prob, 4),
                        "features_changed": 1,
                        "changes": [{
                            "feature":        feat,
                            "original":       round(float(orig_vals[feat]), 4),
                            "counterfactual": round(float(pct_val), 4),
                            "delta":          round(float(pct_val) - float(orig_vals[feat]), 4),
                        }],
                    })

        # Two-feature perturbations if not enough single-feature results
        if len(results) < n:
            top_features = self._most_important_features(row, X_train)[:6]
            for i, f1 in enumerate(top_features):
                for f2 in top_features[i+1:]:
                    med1 = float(X_train[f1].median())
                    med2 = float(X_train[f2].median())
                    new_input = orig_vals.copy()
                    new_input[f1] = med1
                    new_input[f2] = med2
                    cf_arr  = pd.DataFrame([new_input])
                    cf_pred = int(self.clf.predict(cf_arr)[0])
                    cf_prob = float(self.clf.predict_proba(cf_arr)[0][target_class])
                    if cf_pred == target_class:
                        changes = []
                        for f, v in [(f1, med1), (f2, med2)]:
                            changes.append({
                                "feature":        f,
                                "original":       round(float(orig_vals[f]), 4),
                                "counterfactual": round(float(v), 4),
                                "delta":          round(float(v) - float(orig_vals[f]), 4),
                            })
                        results.append({
                            "new_input":       {k: round(float(v), 4) for k, v in new_input.items()},
                            "new_prediction":  cf_pred,
                            "new_probability": round(cf_prob, 4),
                            "features_changed": 2,
                            "changes": changes,
                        })
                        if len(results) >= n * 3:
                            break
                if len(results) >= n * 3:
                    break

        # Sort by fewest changes then highest probability for target class
        results.sort(key=lambda x: (x["features_changed"], -x["new_probability"]))

        return {
            "original_prediction":  orig_pred,
            "original_probability": round(orig_prob, 4),
            "target_class":         target_class,
            "counterfactuals":      results[:n],
            "method":               "greedy",
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _align(self, input_dict: Dict[str, Any]) -> pd.DataFrame:
        norm = {k.lower().replace("-", "_"): v for k, v in input_dict.items()}
        row  = {f: float(norm.get(f.lower().replace("-", "_"), 0.0)) for f in self.feature_names}
        return pd.DataFrame([row])

    def _most_important_features(self, row, X_train) -> List[str]:
        """Return features sorted by importance (uses model if available)."""
        clf_inner = getattr(self.clf, "named_steps", {}).get("clf") or self.clf
        if hasattr(clf_inner, "feature_importances_"):
            imp = clf_inner.feature_importances_
            return [self.feature_names[i] for i in np.argsort(imp)[::-1]]
        if hasattr(clf_inner, "coef_"):
            imp = np.abs(clf_inner.coef_[0])
            return [self.feature_names[i] for i in np.argsort(imp)[::-1]]
        return self.feature_names
