"""
A/B Shadow Testing Framework.

When enabled for a disease, every prediction secretly runs TWO models.
Both results are logged. After N predictions, admin can request a
paired t-test comparing their probabilities to pick the winner.

Mirrors your original scipy.stats.ttest_rel usage from main.py.
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger
from scipy.stats import ttest_rel, wilcoxon

from app.core.config import settings


class ABTestingService:
    """
    Manages shadow-mode A/B testing across diseases.

    Config is stored in  ml/saved_models/{disease}_ab_config.json
    Results are appended to ml/saved_models/{disease}_ab_log.jsonl
    """

    def __init__(self):
        self.save_path = Path(settings.MODEL_SAVE_PATH)

    # ── Config ────────────────────────────────────────────────────────────────

    def configure(
        self,
        disease: str,
        model_a: str,
        model_b: str,
        enabled: bool = True,
        min_samples: int = 30,
    ) -> dict:
        cfg = {
            "disease":     disease,
            "model_a":     model_a,
            "model_b":     model_b,
            "enabled":     enabled,
            "min_samples": min_samples,
            "created_at":  datetime.utcnow().isoformat(),
        }
        self._config_path(disease).write_text(json.dumps(cfg, indent=2))
        logger.info(f"A/B configured [{disease}]: {model_a} vs {model_b}")
        return cfg

    def get_config(self, disease: str) -> Optional[dict]:
        path = self._config_path(disease)
        if path.exists():
            return json.loads(path.read_text())
        return None

    def is_enabled(self, disease: str) -> bool:
        cfg = self.get_config(disease)
        return bool(cfg and cfg.get("enabled"))

    # ── Logging ───────────────────────────────────────────────────────────────

    def log_result(
        self,
        disease: str,
        model_a: str,
        model_b: str,
        prob_a: float,
        prob_b: float,
        true_label: Optional[int] = None,
    ):
        """Append one shadow comparison to the JSONL log."""
        entry = {
            "ts":         datetime.utcnow().isoformat(),
            "disease":    disease,
            "model_a":    model_a,
            "model_b":    model_b,
            "prob_a":     round(prob_a, 6),
            "prob_b":     round(prob_b, 6),
            "pred_a":     int(prob_a >= 0.5),
            "pred_b":     int(prob_b >= 0.5),
            "agree":      int(prob_a >= 0.5) == int(prob_b >= 0.5),
            "true_label": true_label,
        }
        with open(self._log_path(disease), "a") as f:
            f.write(json.dumps(entry) + "\n")

    # ── Analysis ──────────────────────────────────────────────────────────────

    def analyse(self, disease: str) -> Dict[str, Any]:
        """
        Run paired t-test + Wilcoxon signed-rank test on logged probabilities.
        Returns significance results, agreement rate, and recommendation.
        """
        log = self._read_log(disease)
        cfg = self.get_config(disease) or {}

        if len(log) < 2:
            return {
                "status":  "insufficient_data",
                "message": f"Need at least 2 samples, have {len(log)}.",
                "n":       len(log),
            }

        probs_a = np.array([e["prob_a"] for e in log])
        probs_b = np.array([e["prob_b"] for e in log])
        preds_a = np.array([e["pred_a"] for e in log])
        preds_b = np.array([e["pred_b"] for e in log])

        # Paired t-test (matches your scipy.stats.ttest_rel usage)
        t_stat, p_value = ttest_rel(probs_a, probs_b)

        # Wilcoxon signed-rank (non-parametric alternative)
        try:
            w_stat, w_pval = wilcoxon(probs_a, probs_b)
        except Exception:
            w_stat, w_pval = None, None

        agree_rate  = float(np.mean(preds_a == preds_b))
        mean_diff   = float(np.mean(probs_a - probs_b))
        significant = bool(p_value < 0.05)

        # Recommendation
        if not significant:
            recommendation = f"No significant difference. Keep model A ({cfg.get('model_a','A')})."
        elif mean_diff > 0:
            recommendation = f"Model A ({cfg.get('model_a','A')}) has significantly higher probability scores. Recommend A."
        else:
            recommendation = f"Model B ({cfg.get('model_b','B')}) has significantly higher probability scores. Recommend B."

        return {
            "status":          "completed",
            "disease":         disease,
            "n_samples":       len(log),
            "model_a":         cfg.get("model_a"),
            "model_b":         cfg.get("model_b"),
            "mean_prob_a":     round(float(np.mean(probs_a)), 4),
            "mean_prob_b":     round(float(np.mean(probs_b)), 4),
            "mean_difference": round(mean_diff, 4),
            "agreement_rate":  round(agree_rate, 4),
            "t_statistic":     round(float(t_stat), 4),
            "p_value":         round(float(p_value), 6),
            "wilcoxon_stat":   round(float(w_stat), 4) if w_stat is not None else None,
            "wilcoxon_pvalue": round(float(w_pval), 6) if w_pval is not None else None,
            "significant_005": significant,
            "recommendation":  recommendation,
        }

    def get_log_summary(self, disease: str) -> Dict[str, Any]:
        log  = self._read_log(disease)
        cfg  = self.get_config(disease) or {}
        if not log:
            return {"n": 0, "disease": disease}
        agree = sum(1 for e in log if e["agree"])
        return {
            "n":            len(log),
            "disease":      disease,
            "model_a":      cfg.get("model_a"),
            "model_b":      cfg.get("model_b"),
            "agreement_pct": round(agree / len(log) * 100, 1),
            "latest":       log[-1]["ts"] if log else None,
        }

    def clear_log(self, disease: str):
        path = self._log_path(disease)
        if path.exists():
            path.write_text("")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _read_log(self, disease: str) -> List[dict]:
        path = self._log_path(disease)
        if not path.exists():
            return []
        entries = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
        return entries

    def _config_path(self, disease: str) -> Path:
        return self.save_path / f"{disease}_ab_config.json"

    def _log_path(self, disease: str) -> Path:
        return self.save_path / f"{disease}_ab_log.jsonl"


ab_testing = ABTestingService()
