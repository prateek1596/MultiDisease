"""
Risk Scoring Module
Maps prediction probability to Low / Medium / High / Critical tiers.
Mirrors your original src/risk_scoring.py with per-disease thresholds.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class RiskBand:
    level: str          # Low | Medium | High | Critical
    color: str          # hex — used by frontend badge
    min_prob: float
    max_prob: float
    action: str         # clinical recommendation


# Per-disease thresholds (can be tuned per clinical guidelines)
DISEASE_THRESHOLDS: Dict[str, list] = {
    "heart": [
        RiskBand("Low",      "#10b981", 0.00, 0.25, "Annual cardiovascular check-up recommended."),
        RiskBand("Medium",   "#f59e0b", 0.25, 0.50, "Lifestyle modification advised. Re-evaluate in 6 months."),
        RiskBand("High",     "#f97316", 0.50, 0.75, "Cardiology referral recommended within 4 weeks."),
        RiskBand("Critical", "#ef4444", 0.75, 1.00, "Urgent cardiology consultation required."),
    ],
    "diabetes": [
        RiskBand("Low",      "#10b981", 0.00, 0.20, "Maintain healthy diet and exercise. Annual HbA1c check."),
        RiskBand("Medium",   "#f59e0b", 0.20, 0.45, "Pre-diabetic range — dietary counselling recommended."),
        RiskBand("High",     "#f97316", 0.45, 0.70, "Endocrinology referral within 2 weeks advised."),
        RiskBand("Critical", "#ef4444", 0.70, 1.00, "Immediate blood glucose testing and specialist consult."),
    ],
    "kidney": [
        RiskBand("Low",      "#10b981", 0.00, 0.20, "Monitor kidney function annually. Stay hydrated."),
        RiskBand("Medium",   "#f59e0b", 0.20, 0.45, "Nephrology review in 3 months. Monitor BP and creatinine."),
        RiskBand("High",     "#f97316", 0.45, 0.70, "Nephrology referral recommended within 2 weeks."),
        RiskBand("Critical", "#ef4444", 0.70, 1.00, "Urgent nephrology consultation. Consider dialysis assessment."),
    ],
}


def risk_category(probability: float, disease: str = "heart") -> dict:
    """
    Classify a prediction probability into a risk band.

    Parameters
    ----------
    probability : float   Predicted probability for positive class (0–1)
    disease     : str     'heart' | 'diabetes' | 'kidney'

    Returns
    -------
    dict with level, color, probability, action, min_prob, max_prob
    """
    bands = DISEASE_THRESHOLDS.get(disease, DISEASE_THRESHOLDS["heart"])
    for band in bands:
        if band.min_prob <= probability < band.max_prob:
            return {
                "level":       band.level,
                "color":       band.color,
                "probability": round(probability, 4),
                "pct":         round(probability * 100, 1),
                "action":      band.action,
                "min_prob":    band.min_prob,
                "max_prob":    band.max_prob,
            }
    # Edge case: probability == 1.0
    last = bands[-1]
    return {
        "level":       last.level,
        "color":       last.color,
        "probability": round(probability, 4),
        "pct":         round(probability * 100, 1),
        "action":      last.action,
        "min_prob":    last.min_prob,
        "max_prob":    last.max_prob,
    }


def get_all_bands(disease: str) -> list:
    """Return all risk bands for a disease (for frontend display)."""
    bands = DISEASE_THRESHOLDS.get(disease, DISEASE_THRESHOLDS["heart"])
    return [
        {
            "level":    b.level,
            "color":    b.color,
            "min_prob": b.min_prob,
            "max_prob": b.max_prob,
            "action":   b.action,
        }
        for b in bands
    ]
