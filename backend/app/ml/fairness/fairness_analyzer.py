"""
Fairness Analysis Module — adapted from src/fairness_analysis.py

Computes:
  • Demographic Parity Difference
  • Equal Opportunity Difference
  • Disparate Impact Ratio
  • Predictive Parity Difference
  • Calibration by group

Can be called after training or on any predictions array.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.metrics import confusion_matrix
from typing import Dict, Any, List, Optional
from loguru import logger

from app.core.config import settings


class FairnessAnalyzer:
    """
    Comprehensive fairness analysis for healthcare ML models.

    Parameters
    ----------
    y_true         : true binary labels (0/1)
    y_pred         : predicted binary labels (0/1)
    y_prob         : predicted probabilities for class 1
    sensitive_attr : group labels (e.g. ['Male','Female',...])
    attr_name      : human-readable attribute name for reports
    """

    FAIR_DPD_THRESHOLD  = 0.10   # Demographic Parity Difference
    FAIR_EOD_THRESHOLD  = 0.10   # Equal Opportunity Difference
    FAIR_DIR_LOW        = 0.80   # Disparate Impact lower bound
    FAIR_DIR_HIGH       = 1.25   # Disparate Impact upper bound
    FAIR_PPD_THRESHOLD  = 0.10   # Predictive Parity Difference

    def __init__(
        self,
        y_true,
        y_pred,
        y_prob,
        sensitive_attr,
        attr_name: str = "Group",
    ):
        self.y_true         = np.array(y_true)
        self.y_pred         = np.array(y_pred)
        self.y_prob         = np.array(y_prob)
        self.sensitive_attr = np.array(sensitive_attr)
        self.attr_name      = attr_name
        self.groups         = np.unique(sensitive_attr)

        if len(self.groups) < 2:
            raise ValueError("Need at least 2 groups for fairness analysis")

    # ── Core metrics ──────────────────────────────────────────────────────────

    def demographic_parity_difference(self) -> Dict[str, Any]:
        """P(Ŷ=1) should be equal across groups."""
        rates = {g: float(np.mean(self.y_pred[self.sensitive_attr == g]))
                 for g in self.groups}
        dpd = max(rates.values()) - min(rates.values())
        return {
            "metric":          "Demographic Parity Difference",
            "value":           float(dpd),
            "group_rates":     rates,
            "is_fair":         dpd < self.FAIR_DPD_THRESHOLD,
            "threshold":       self.FAIR_DPD_THRESHOLD,
            "interpretation":  "Lower is better. <0.10 indicates fair predictions.",
        }

    def equal_opportunity_difference(self) -> Dict[str, Any]:
        """TPR should be equal across groups."""
        tpr = {}
        for g in self.groups:
            mask = self.sensitive_attr == g
            yt, yp = self.y_true[mask], self.y_pred[mask]
            if yt.sum() == 0:
                tpr[g] = 0.0
                continue
            cm = confusion_matrix(yt, yp, labels=[0, 1])
            tn, fp, fn, tp = cm.ravel()
            tpr[g] = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0

        eod = max(tpr.values()) - min(tpr.values())
        return {
            "metric":         "Equal Opportunity Difference",
            "value":          float(eod),
            "TPR_by_group":   tpr,
            "is_fair":        eod < self.FAIR_EOD_THRESHOLD,
            "threshold":      self.FAIR_EOD_THRESHOLD,
            "interpretation": "True positive rates should be equal. <0.10 is fair.",
        }

    def disparate_impact_ratio(self) -> Dict[str, Any]:
        """Ratio of positive prediction rates (min/max)."""
        rates = {g: float(np.mean(self.y_pred[self.sensitive_attr == g]))
                 for g in self.groups}
        vals = list(rates.values())
        ratio = min(vals) / max(vals) if max(vals) > 0 else 0.0
        return {
            "metric":         "Disparate Impact Ratio",
            "value":          float(ratio),
            "group_rates":    rates,
            "is_fair":        self.FAIR_DIR_LOW <= ratio <= self.FAIR_DIR_HIGH,
            "threshold":      f"{self.FAIR_DIR_LOW}–{self.FAIR_DIR_HIGH}",
            "interpretation": "Ratio should be between 0.80 and 1.25 for fairness.",
        }

    def predictive_parity_difference(self) -> Dict[str, Any]:
        """PPV (precision) should be equal across groups."""
        ppv = {}
        for g in self.groups:
            mask = self.sensitive_attr == g
            yt, yp = self.y_true[mask], self.y_pred[mask]
            if yp.sum() == 0:
                ppv[g] = 0.0
                continue
            cm = confusion_matrix(yt, yp, labels=[0, 1])
            tn, fp, fn, tp = cm.ravel()
            ppv[g] = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0

        ppd = max(ppv.values()) - min(ppv.values())
        return {
            "metric":         "Predictive Parity Difference",
            "value":          float(ppd),
            "PPV_by_group":   ppv,
            "is_fair":        ppd < self.FAIR_PPD_THRESHOLD,
            "threshold":      self.FAIR_PPD_THRESHOLD,
            "interpretation": "Positive predictive values should be similar.",
        }

    def calibration_by_group(self, n_bins: int = 10) -> Dict[str, Any]:
        """Binned calibration analysis per group."""
        result = {}
        bins = np.linspace(0, 1, n_bins + 1)
        for g in self.groups:
            mask = self.sensitive_attr == g
            yt, yp_prob = self.y_true[mask], self.y_prob[mask]
            bin_idx = np.digitize(yp_prob, bins) - 1
            true_r, pred_r, counts = [], [], []
            for i in range(n_bins):
                b = bin_idx == i
                if b.sum() > 0:
                    true_r.append(float(np.mean(yt[b])))
                    pred_r.append(float(np.mean(yp_prob[b])))
                    counts.append(int(b.sum()))
                else:
                    true_r.append(None)
                    pred_r.append(None)
                    counts.append(0)

            valid = [(true_r[i], pred_r[i]) for i in range(n_bins) if true_r[i] is not None]
            cal_err = float(np.mean([abs(t - p) for t, p in valid])) if valid else None
            result[str(g)] = {
                "true_rates":        true_r,
                "pred_rates":        pred_r,
                "counts":            counts,
                "calibration_error": cal_err,
            }
        return result

    # ── Full report ───────────────────────────────────────────────────────────

    def generate_fairness_report(self) -> Dict[str, Any]:
        """Return structured fairness report dict (also prints summary)."""
        dpd  = self.demographic_parity_difference()
        eod  = self.equal_opportunity_difference()
        dir_ = self.disparate_impact_ratio()
        ppd  = self.predictive_parity_difference()
        cal  = self.calibration_by_group()

        metrics = {"demographic_parity": dpd, "equal_opportunity": eod,
                   "disparate_impact": dir_, "predictive_parity": ppd}

        issues = [v["metric"] for v in metrics.values() if not v["is_fair"]]
        overall_acc = float(np.mean(self.y_true == self.y_pred))

        # Group sizes
        group_sizes = {
            str(g): int(np.sum(self.sensitive_attr == g))
            for g in self.groups
        }

        logger.info(f"Fairness report — {self.attr_name} | issues={issues or 'none'}")

        return {
            "attr_name":       self.attr_name,
            "sample_size":     int(len(self.y_true)),
            "groups":          [str(g) for g in self.groups],
            "group_sizes":     group_sizes,
            "overall_accuracy": overall_acc,
            "metrics":          metrics,
            "calibration":      cal,
            "fairness_issues":  issues,
            "is_fair_overall":  len(issues) == 0,
        }

    # ── Visualisation ─────────────────────────────────────────────────────────

    def plot_fairness_dashboard(
        self,
        save_path: Optional[str] = None,
    ) -> str:
        """Generate and save the fairness dashboard PNG. Returns file path."""
        out_dir = Path(settings.REPORT_SAVE_PATH) / "fairness"
        out_dir.mkdir(parents=True, exist_ok=True)
        if save_path is None:
            save_path = str(out_dir / f"fairness_{self.attr_name.lower()}.png")

        dpd  = self.demographic_parity_difference()
        eod  = self.equal_opportunity_difference()
        dir_ = self.disparate_impact_ratio()
        cal  = self.calibration_by_group()

        fig = plt.figure(figsize=(18, 12))
        gs  = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.35)

        # ── 1. Demographic Parity ────────────────────────────────────────────
        ax1 = fig.add_subplot(gs[0, 0])
        grps  = list(dpd["group_rates"].keys())
        rates = list(dpd["group_rates"].values())
        color = "#2ecc71" if dpd["is_fair"] else "#e74c3c"
        ax1.bar(grps, rates, color=color, alpha=0.75)
        ax1.axhline(np.mean(rates), color="black", linestyle="--", alpha=0.5, label="Mean")
        ax1.set_title(f"Demographic Parity\nDPD = {dpd['value']:.3f}")
        ax1.set_ylabel("Positive Prediction Rate")
        ax1.legend(fontsize=8)
        ax1.grid(axis="y", alpha=0.3)

        # ── 2. Equal Opportunity ─────────────────────────────────────────────
        ax2 = fig.add_subplot(gs[0, 1])
        tpr_grps = list(eod["TPR_by_group"].keys())
        tpr_vals = list(eod["TPR_by_group"].values())
        color2 = "#2ecc71" if eod["is_fair"] else "#e74c3c"
        ax2.bar(tpr_grps, tpr_vals, color=color2, alpha=0.75)
        ax2.set_title(f"Equal Opportunity\nEOD = {eod['value']:.3f}")
        ax2.set_ylabel("True Positive Rate")
        ax2.set_ylim([0, 1])
        ax2.grid(axis="y", alpha=0.3)

        # ── 3. Disparate Impact Ratio ────────────────────────────────────────
        ax3 = fig.add_subplot(gs[0, 2])
        dir_v = dir_["value"]
        ax3.barh([0], [dir_v], color="#2ecc71" if dir_["is_fair"] else "#e74c3c",
                 alpha=0.75, height=0.5)
        ax3.axvline(0.80, color="orange", linestyle="--", label="Lower (0.80)")
        ax3.axvline(1.25, color="orange", linestyle="--", label="Upper (1.25)")
        ax3.axvline(1.00, color="green",  linestyle="-",  alpha=0.4, label="Perfect")
        ax3.set_xlim([0, 2])
        ax3.set_yticks([])
        ax3.set_title(f"Disparate Impact\nDIR = {dir_v:.3f}")
        ax3.legend(fontsize=8)
        ax3.grid(axis="x", alpha=0.3)

        # ── 4–5. Confusion matrices ──────────────────────────────────────────
        for idx, g in enumerate(list(self.groups)[:2]):
            ax = fig.add_subplot(gs[1, idx])
            mask = self.sensitive_attr == g
            cm = confusion_matrix(self.y_true[mask], self.y_pred[mask], labels=[0, 1])
            sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax,
                        xticklabels=["Neg", "Pos"], yticklabels=["Neg", "Pos"])
            ax.set_title(f"Confusion Matrix: {g}")
            ax.set_xlabel("Predicted")
            ax.set_ylabel("True")

        # ── 6. Calibration ───────────────────────────────────────────────────
        ax6 = fig.add_subplot(gs[1, 2])
        for g, data in cal.items():
            tr = [v for v in data["true_rates"] if v is not None]
            pr = [v for v in data["pred_rates"] if v is not None]
            if tr:
                ax6.plot(pr, tr, marker="o", label=str(g), linewidth=2)
        ax6.plot([0, 1], [0, 1], "k--", alpha=0.3, label="Perfect")
        ax6.set_xlabel("Predicted Probability")
        ax6.set_ylabel("True Probability")
        ax6.set_title("Calibration by Group")
        ax6.legend(fontsize=8)
        ax6.grid(True, alpha=0.3)
        ax6.set_xlim([0, 1]); ax6.set_ylim([0, 1])

        # ── 7. Per-group performance metrics ─────────────────────────────────
        ax7 = fig.add_subplot(gs[2, :])
        rows = []
        for g in self.groups:
            mask = self.sensitive_attr == g
            yt, yp = self.y_true[mask], self.y_pred[mask]
            acc = float(np.mean(yt == yp))
            cm  = confusion_matrix(yt, yp, labels=[0, 1])
            tn, fp, fn, tp = cm.ravel()
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
            rows.append({"Group": str(g), "Accuracy": acc,
                         "Precision": prec, "Recall": rec, "F1-Score": f1})

        df_m = pd.DataFrame(rows)
        x    = np.arange(len(self.groups))
        w    = 0.2
        ax7.bar(x - 1.5*w, df_m["Accuracy"],  w, label="Accuracy",  alpha=0.8)
        ax7.bar(x - 0.5*w, df_m["Precision"], w, label="Precision", alpha=0.8)
        ax7.bar(x + 0.5*w, df_m["Recall"],    w, label="Recall",    alpha=0.8)
        ax7.bar(x + 1.5*w, df_m["F1-Score"],  w, label="F1-Score",  alpha=0.8)
        ax7.set_xticks(x)
        ax7.set_xticklabels([str(g) for g in self.groups])
        ax7.set_title(f"Performance Metrics by {self.attr_name}")
        ax7.set_ylabel("Score")
        ax7.set_ylim([0, 1.05])
        ax7.legend(loc="lower right")
        ax7.grid(axis="y", alpha=0.3)

        fig.suptitle(
            f"Fairness Analysis Dashboard — {self.attr_name}",
            fontsize=15, fontweight="bold", y=0.995,
        )
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Fairness dashboard saved → {save_path}")
        return save_path
