"""
Minimal Feature Analysis — adapted from src/minimal_feature_analysis.py

Finds the smallest feature subset that maintains a target performance,
and calculates economic / healthcare impact of that reduction.
"""

import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, Any, List, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, accuracy_score, f1_score
from loguru import logger

from app.core.config import settings


class MinimalFeatureAnalyzer:
    """
    Analyse model performance as features are progressively removed.

    Parameters
    ----------
    X_train, y_train : training data (already scaled)
    X_test,  y_test  : held-out test data
    """

    def __init__(self, X_train, y_train, X_test, y_test):
        self.X_train = X_train
        self.y_train = y_train
        self.X_test  = X_test
        self.y_test  = y_test

        cols = getattr(X_train, "columns", None)
        self.feature_names = list(cols) if cols is not None else [
            f"feature_{i}" for i in range(X_train.shape[1])
        ]

        # Train full RF for importance ranking
        self.full_model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
        self.full_model.fit(X_train, y_train)
        self.feature_importance = self.full_model.feature_importances_
        self.feature_ranking    = np.argsort(self.feature_importance)[::-1]

    # ── Core analysis ─────────────────────────────────────────────────────────

    def progressive_feature_reduction(self, step_size: int = 1) -> pd.DataFrame:
        """Test model performance as features are progressively removed."""
        results = []
        n_total = len(self.feature_names)

        for n in range(n_total, 0, -step_size):
            top_idx  = self.feature_ranking[:n]
            sel_feat = [self.feature_names[i] for i in top_idx]

            Xtr = self._select(self.X_train, top_idx)
            Xte = self._select(self.X_test,  top_idx)

            clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
            clf.fit(Xtr, self.y_train)

            yp  = clf.predict(Xte)
            ypr = clf.predict_proba(Xte)[:, 1]

            results.append({
                "n_features":            n,
                "features":              sel_feat,
                "accuracy":              float(accuracy_score(self.y_test, yp)),
                "auc":                   float(roc_auc_score(self.y_test, ypr)),
                "f1":                    float(f1_score(self.y_test, yp)),
                "feature_reduction_pct": float((1 - n / n_total) * 100),
            })

        return pd.DataFrame(results)

    def find_minimal_feature_set(
        self,
        target_accuracy: float = 0.85,
        target_metric: str = "accuracy",
    ) -> Optional[Dict[str, Any]]:
        """Return smallest feature set that meets the target metric value."""
        results_df = self.progressive_feature_reduction(step_size=1)

        viable = results_df[results_df[target_metric] >= target_accuracy]
        if viable.empty:
            best = float(results_df[target_metric].max())
            logger.warning(
                f"Cannot reach {target_accuracy:.2%} {target_metric}. "
                f"Best achievable: {best:.4f}"
            )
            return None

        row = viable.nsmallest(1, "n_features").iloc[0]
        baseline_row = results_df[
            results_df["n_features"] == len(self.feature_names)
        ].iloc[0]

        config = {
            "n_features":        int(row["n_features"]),
            "features":          list(row["features"]),
            "accuracy":          float(row["accuracy"]),
            "auc":               float(row["auc"]),
            "f1":                float(row["f1"]),
            "reduction_pct":     float(row["feature_reduction_pct"]),
            "baseline_accuracy": float(baseline_row["accuracy"]),
            "baseline_auc":      float(baseline_row["auc"]),
            "feature_importances": {
                feat: float(self.feature_importance[self.feature_names.index(feat)])
                for feat in row["features"]
            },
        }
        logger.info(
            f"Minimal feature set: {config['n_features']} features "
            f"({config['reduction_pct']:.1f}% reduction)  "
            f"ACC={config['accuracy']:.4f}  AUC={config['auc']:.4f}"
        )
        return config

    # ── Impact metrics ────────────────────────────────────────────────────────

    def calculate_impact_metrics(
        self,
        minimal_config: Dict[str, Any],
        cost_per_test_usd: float = 10.0,
    ) -> List[Dict[str, Any]]:
        """Project cost/accessibility savings at different deployment scales."""
        tests_saved        = len(self.feature_names) - minimal_config["n_features"]
        cost_saved_patient = tests_saved * cost_per_test_usd

        scenarios = [
            ("Small Clinic",       500),
            ("District Hospital",  5_000),
            ("Regional Program",   50_000),
            ("National Program",   500_000),
        ]

        rows = []
        for scale, n_patients in scenarios:
            extra = int(n_patients * 0.30 * minimal_config["reduction_pct"] / 50)
            rows.append({
                "scale":                scale,
                "patients_per_year":    n_patients,
                "total_cost_savings_usd": round(cost_saved_patient * n_patients, 2),
                "tests_eliminated":     tests_saved * n_patients,
                "additional_screenings": extra,
                "accuracy_maintained":  round(minimal_config["accuracy"], 4),
            })
        return rows

    def generate_deployment_protocol(
        self,
        minimal_config: Dict[str, Any],
        output_path: Optional[str] = None,
    ) -> str:
        """Write a Markdown deployment protocol. Returns file path."""
        out_dir = Path(settings.REPORT_SAVE_PATH) / "protocols"
        out_dir.mkdir(parents=True, exist_ok=True)
        if output_path is None:
            output_path = str(out_dir / "deployment_protocol.md")

        lines = [
            "# Clinical Deployment Protocol: Minimal Feature Disease Prediction\n",
            f"## Model Performance\n",
            f"- **Accuracy**: {minimal_config['accuracy']:.2%}",
            f"- **AUC-ROC**: {minimal_config['auc']:.2%}",
            f"- **F1-Score**: {minimal_config['f1']:.2%}",
            f"- **Feature Reduction**: {minimal_config['reduction_pct']:.1f}% fewer tests\n",
            f"## Required Diagnostic Tests ({minimal_config['n_features']})\n",
        ]
        for i, feat in enumerate(minimal_config["features"], 1):
            imp = minimal_config["feature_importances"].get(feat, 0)
            lines.append(f"{i}. **{feat}** (importance: {imp:.4f})")

        lines += [
            "\n## Implementation Notes",
            "- Collect only the listed measurements before running the model.",
            "- High Risk (>75%): immediate referral",
            "- Moderate Risk (40–75%): follow-up in 3 months",
            "- Low Risk (<40%): annual screening",
            "\n*Approved for use only under clinical supervision.*",
        ]

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        logger.info(f"Deployment protocol saved → {output_path}")
        return output_path

    # ── Visualisation ─────────────────────────────────────────────────────────

    def plot_feature_reduction_analysis(
        self, save_path: Optional[str] = None
    ) -> str:
        out_dir = Path(settings.REPORT_SAVE_PATH) / "feature_reduction"
        out_dir.mkdir(parents=True, exist_ok=True)
        if save_path is None:
            save_path = str(out_dir / "feature_reduction_analysis.png")

        df = self.progressive_feature_reduction(step_size=1)
        base_acc = float(df[df["n_features"] == len(self.feature_names)]["accuracy"].iloc[0])

        fig, axes = plt.subplots(2, 2, figsize=(15, 11))

        # 1. Accuracy vs feature count
        ax = axes[0, 0]
        ax.plot(df["n_features"], df["accuracy"], marker="o", linewidth=2.5,
                markersize=5, color="#3498db")
        ax.axhline(0.85, color="red",    linestyle="--", label="85% target", alpha=0.7)
        ax.axhline(0.90, color="orange", linestyle="--", label="90% target", alpha=0.7)
        ax.fill_between(df["n_features"], 0.85, df["accuracy"],
                        where=(df["accuracy"] >= 0.85), alpha=0.15, color="green")
        ax.set_xlabel("Number of Features"); ax.set_ylabel("Accuracy")
        ax.set_title("Accuracy vs Feature Count")
        ax.legend(fontsize=9); ax.grid(True, alpha=0.3)

        # 2. AUC vs feature count
        ax = axes[0, 1]
        ax.plot(df["n_features"], df["auc"], marker="s", linewidth=2.5,
                markersize=5, color="#2ecc71")
        ax.axhline(0.85, color="red", linestyle="--", alpha=0.7)
        ax.set_xlabel("Number of Features"); ax.set_ylabel("AUC-ROC")
        ax.set_title("AUC-ROC vs Feature Count")
        ax.grid(True, alpha=0.3)

        # 3. Accuracy drop vs reduction %
        ax = axes[1, 0]
        drop = (base_acc - df["accuracy"]) * 100
        sc = ax.scatter(df["feature_reduction_pct"], drop,
                        c=df["n_features"], cmap="RdYlGn_r",
                        s=60, alpha=0.7, edgecolors="black", linewidth=0.3)
        ax.axhline(5, color="orange", linestyle="--", label="5 pp drop", alpha=0.7)
        ax.set_xlabel("Feature Reduction (%)"); ax.set_ylabel("Accuracy Drop (pp)")
        ax.set_title("Accuracy Trade-off")
        ax.legend(fontsize=9); ax.grid(True, alpha=0.3)
        plt.colorbar(sc, ax=ax, label="# Features")

        # 4. Feature importance bar
        ax = axes[1, 1]
        top_n  = min(15, len(self.feature_names))
        top_i  = self.feature_ranking[:top_n]
        top_f  = [self.feature_names[i] for i in top_i]
        top_v  = [float(self.feature_importance[i]) for i in top_i]
        colors = plt.cm.viridis(np.linspace(0, 1, top_n))
        ax.barh(range(top_n), top_v, color=colors, alpha=0.85, edgecolor="black")
        ax.set_yticks(range(top_n)); ax.set_yticklabels(top_f, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("Feature Importance")
        ax.set_title(f"Top {top_n} Features")
        ax.grid(axis="x", alpha=0.3)

        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Feature reduction plot saved → {save_path}")
        return save_path

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _select(X, indices):
        if hasattr(X, "iloc"):
            return X.iloc[:, indices]
        return X[:, indices]
