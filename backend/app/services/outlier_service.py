"""
Outlier Detection Service — detects out-of-distribution inputs.

Computes feature statistics (min, max, mean, std) from training data
and flags input values that fall outside the expected range.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger

from app.core.config import settings
from app.ml.data_loader import DISEASE_LOADERS, DISEASE_TARGET_COLS


class OutlierService:
    """Detects inputs outside training data distribution."""

    def __init__(self):
        self.stats_path = Path(settings.MODEL_SAVE_PATH)
        self.stats_path.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict] = {}

    def compute_feature_stats(self, disease: str) -> Dict[str, Dict[str, float]]:
        """Compute and save feature statistics from training data."""
        df = DISEASE_LOADERS[disease]()
        target_col = DISEASE_TARGET_COLS[disease]
        
        # Get feature columns only
        X = df.drop(columns=[target_col], errors='ignore')
        
        stats = {}
        for col in X.columns:
            values = pd.to_numeric(X[col], errors='coerce').dropna()
            if len(values) > 0:
                stats[col] = {
                    "min": float(values.min()),
                    "max": float(values.max()),
                    "mean": float(values.mean()),
                    "std": float(values.std()) if len(values) > 1 else 0.0,
                    "q1": float(values.quantile(0.25)),
                    "q3": float(values.quantile(0.75)),
                    "median": float(values.median()),
                }
        
        # Save stats
        stats_file = self.stats_path / f"{disease}_feature_stats.json"
        stats_file.write_text(json.dumps(stats, indent=2))
        logger.info(f"Saved feature stats for {disease}: {len(stats)} features")
        
        self._cache[disease] = stats
        return stats

    def get_feature_stats(self, disease: str) -> Dict[str, Dict[str, float]]:
        """Load feature statistics, computing if necessary."""
        if disease in self._cache:
            return self._cache[disease]
        
        stats_file = self.stats_path / f"{disease}_feature_stats.json"
        if stats_file.exists():
            stats = json.loads(stats_file.read_text())
            self._cache[disease] = stats
            return stats
        
        # Compute on-the-fly
        return self.compute_feature_stats(disease)

    def detect_outliers(
        self,
        disease: str,
        input_data: Dict[str, Any],
        z_threshold: float = 3.0,
    ) -> List[Dict[str, Any]]:
        """
        Detect outlier values in input data.
        
        Args:
            disease: Disease type (heart, diabetes, kidney)
            input_data: Dict of feature name -> value
            z_threshold: Number of standard deviations for outlier detection
            
        Returns:
            List of outlier alerts with feature name, value, and reason
        """
        stats = self.get_feature_stats(disease)
        alerts = []
        
        # Normalize input keys
        normalized_input = {
            k.lower().replace("-", "_").replace(" ", "_"): v
            for k, v in input_data.items()
        }
        
        for feature, feature_stats in stats.items():
            key = feature.lower().replace("-", "_").replace(" ", "_")
            value = normalized_input.get(key)
            
            if value is None:
                continue
            
            try:
                value = float(value)
            except (ValueError, TypeError):
                continue
            
            alert = self._check_value(feature, value, feature_stats, z_threshold)
            if alert:
                alerts.append(alert)
        
        return alerts

    def _check_value(
        self,
        feature: str,
        value: float,
        stats: Dict[str, float],
        z_threshold: float,
    ) -> Optional[Dict[str, Any]]:
        """Check if a single value is an outlier."""
        min_val = stats["min"]
        max_val = stats["max"]
        mean = stats["mean"]
        std = stats["std"]
        
        # Check if outside absolute range
        if value < min_val:
            return {
                "feature": feature,
                "value": value,
                "severity": "high",
                "reason": f"Below minimum in training data",
                "expected_range": f"{min_val:.2f} - {max_val:.2f}",
                "training_min": min_val,
                "training_max": max_val,
            }
        
        if value > max_val:
            return {
                "feature": feature,
                "value": value,
                "severity": "high",
                "reason": f"Above maximum in training data",
                "expected_range": f"{min_val:.2f} - {max_val:.2f}",
                "training_min": min_val,
                "training_max": max_val,
            }
        
        # Check z-score (if std > 0)
        if std > 0:
            z_score = abs(value - mean) / std
            if z_score > z_threshold:
                return {
                    "feature": feature,
                    "value": value,
                    "severity": "medium",
                    "reason": f"Unusual value ({z_score:.1f} std from mean)",
                    "expected_range": f"{mean - z_threshold*std:.2f} - {mean + z_threshold*std:.2f}",
                    "z_score": z_score,
                    "training_mean": mean,
                    "training_std": std,
                }
        
        return None

    def get_all_feature_bounds(self, disease: str) -> Dict[str, Dict[str, float]]:
        """Get feature bounds for frontend validation."""
        stats = self.get_feature_stats(disease)
        bounds = {}
        
        for feature, feature_stats in stats.items():
            bounds[feature] = {
                "min": feature_stats["min"],
                "max": feature_stats["max"],
                "mean": feature_stats["mean"],
                "typical_low": feature_stats["q1"],
                "typical_high": feature_stats["q3"],
            }
        
        return bounds


# Singleton
outlier_service = OutlierService()
