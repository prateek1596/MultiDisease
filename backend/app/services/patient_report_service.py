"""
Per-patient clinical PDF report.
Generates a professional, doctor-ready one-page summary for a single prediction.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable
)

from app.core.config import settings

# Risk level → color
RISK_COLORS = {
    "Low":      colors.HexColor("#10b981"),
    "Medium":   colors.HexColor("#f59e0b"),
    "High":     colors.HexColor("#f97316"),
    "Critical": colors.HexColor("#ef4444"),
}

DISEASE_FULL = {
    "heart":    "Heart Disease",
    "diabetes": "Diabetes Mellitus",
    "kidney":   "Chronic Kidney Disease",
}


class PatientReportGenerator:
    """Generates a per-patient clinical summary PDF."""

    def __init__(self):
        self.out_dir = Path(settings.REPORT_SAVE_PATH) / "patient_reports"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.styles = getSampleStyleSheet()
        self._build_styles()

    def _build_styles(self):
        self.title_style = ParagraphStyle(
            "PTitle", fontSize=20, textColor=colors.HexColor("#1e3a5f"),
            fontName="Helvetica-Bold", alignment=TA_LEFT, spaceAfter=4,
        )
        self.subtitle_style = ParagraphStyle(
            "PSub", fontSize=11, textColor=colors.HexColor("#64748b"),
            fontName="Helvetica", alignment=TA_LEFT,
        )
        self.section_style = ParagraphStyle(
            "PSection", fontSize=12, textColor=colors.HexColor("#1e3a5f"),
            fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6,
        )
        self.body_style = ParagraphStyle(
            "PBody", fontSize=10, textColor=colors.HexColor("#374151"),
            fontName="Helvetica", spaceAfter=4, leading=14,
        )
        self.small_style = ParagraphStyle(
            "PSmall", fontSize=9, textColor=colors.HexColor("#6b7280"),
            fontName="Helvetica", spaceAfter=2,
        )

    def generate(
        self,
        prediction_data: Dict[str, Any],
        patient_name: str = "Anonymous Patient",
        patient_id: Optional[str] = None,
        clinician: Optional[str] = None,
    ) -> str:
        """
        Generate a patient report PDF.

        prediction_data must contain:
          - disease, model_used, prediction, label, confidence, probability
          - explanation (optional SHAP data)
          - risk (optional risk band data)

        Returns the file path of the generated PDF.
        """
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        pid      = (patient_id or "unknown").replace(" ", "_")
        filename = f"patient_{pid}_{prediction_data.get('disease','x')}_{ts}.pdf"
        filepath = self.out_dir / filename

        doc = SimpleDocTemplate(
            str(filepath), pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2.5*cm, bottomMargin=2.5*cm,
        )

        story = []
        story += self._header(patient_name, patient_id, clinician, prediction_data)
        story.append(HRFlowable(width="100%", color=colors.HexColor("#e2e8f0"), thickness=1))
        story.append(Spacer(1, 0.3*cm))
        story += self._result_section(prediction_data)
        story.append(Spacer(1, 0.2*cm))
        if prediction_data.get("explanation"):
            story += self._shap_section(prediction_data["explanation"])
        story.append(Spacer(1, 0.2*cm))
        story += self._input_section(prediction_data)
        story.append(Spacer(1, 0.3*cm))
        story += self._disclaimer()

        doc.build(story)
        logger.info(f"Patient report generated: {filepath}")
        return str(filepath)

    # ── Sections ──────────────────────────────────────────────────────────────

    def _header(self, patient_name, patient_id, clinician, pred):
        disease = pred.get("disease", "")
        now     = datetime.now().strftime("%B %d, %Y  %H:%M")
        elements = [
            Paragraph("MedPredict — Clinical Prediction Report", self.title_style),
            Paragraph(f"AI-assisted {DISEASE_FULL.get(disease, disease)} risk assessment", self.subtitle_style),
            Spacer(1, 0.4*cm),
        ]
        # Info table
        info = [
            ["Patient", patient_name, "Report Date", now],
            ["Patient ID", patient_id or "—", "Disease", DISEASE_FULL.get(disease, disease)],
            ["Clinician", clinician or "—", "Model", pred.get("model_used","—").replace("_"," ").title()],
        ]
        t = Table(info, colWidths=[3*cm, 7*cm, 3*cm, 5*cm])
        t.setStyle(TableStyle([
            ("FONTNAME",  (0,0), (-1,-1), "Helvetica"),
            ("FONTSIZE",  (0,0), (-1,-1), 9),
            ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTNAME",  (2,0), (2,-1), "Helvetica-Bold"),
            ("TEXTCOLOR", (0,0), (-1,-1), colors.HexColor("#374151")),
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0,0), (-1,-1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.4*cm))
        return elements

    def _result_section(self, pred):
        disease    = pred.get("disease","")
        label      = pred.get("label","—")
        confidence = pred.get("confidence", 0)
        result     = pred.get("prediction", 0)
        risk       = pred.get("risk", {})
        risk_level = risk.get("level", "Unknown") if risk else "Unknown"
        risk_color = RISK_COLORS.get(risk_level, colors.HexColor("#64748b"))
        action     = risk.get("action", "") if risk else ""

        # Big result box
        result_color = colors.HexColor("#fef2f2") if result == 1 else colors.HexColor("#f0fdf4")
        text_color   = colors.HexColor("#b91c1c")   if result == 1 else colors.HexColor("#15803d")

        result_style = ParagraphStyle(
            "Res", fontSize=16, fontName="Helvetica-Bold",
            textColor=text_color, alignment=TA_CENTER,
        )
        conf_style = ParagraphStyle(
            "Conf", fontSize=11, fontName="Helvetica",
            textColor=colors.HexColor("#374151"), alignment=TA_CENTER,
        )

        result_table = Table(
            [[
                Paragraph(label, result_style),
            ],
            [
                Paragraph(f"Confidence: {confidence*100:.1f}%   ·   Risk Level: {risk_level}", conf_style),
            ]],
            colWidths=[16*cm],
        )
        result_table.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,-1), result_color),
            ("GRID",        (0,0), (-1,-1), 1, text_color),
            ("PADDING",     (0,0), (-1,-1), 12),
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [result_color]),
        ]))

        elements = [
            Paragraph("Prediction Result", self.section_style),
            result_table,
        ]
        if action:
            elements.append(Spacer(1, 0.2*cm))
            elements.append(Paragraph(f"Recommended action: {action}", self.body_style))

        # Probability breakdown
        prob = pred.get("probability", {})
        if prob:
            elements.append(Spacer(1, 0.2*cm))
            rows = [["Outcome", "Probability"]] + [
                [k, f"{v*100:.1f}%"] for k, v in prob.items()
            ]
            pt = Table(rows, colWidths=[10*cm, 4*cm])
            pt.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
                ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",   (0,0), (-1,-1), 9),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
                ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
                ("PADDING", (0,0), (-1,-1), 6),
            ]))
            elements.append(pt)

        return elements

    def _shap_section(self, explanation):
        top = explanation.get("top_features", [])
        if not top:
            return []

        elements = [Paragraph("Key Driving Factors (SHAP)", self.section_style)]
        rows = [["Feature", "Direction", "Impact Score"]]
        for f in top:
            direction_str = "↑ Increases risk" if f.get("shap_value", 0) > 0 else "↓ Decreases risk"
            rows.append([
                f.get("feature","").replace("_"," ").title(),
                direction_str,
                f"{abs(f.get('abs_impact',0)):.4f}",
            ])
        t = Table(rows, colWidths=[6*cm, 6*cm, 3.5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#1e3a5f")),
            ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
            ("GRID",          (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING",       (0,0), (-1,-1), 6),
        ]))
        elements.append(t)
        return elements

    def _input_section(self, pred):
        input_data = pred.get("input_data", {})
        if not input_data:
            return []
        elements = [Paragraph("Patient Input Values", self.section_style)]
        rows = [["Feature", "Value"]]
        for k, v in input_data.items():
            rows.append([k.replace("_"," ").title(), str(round(float(v), 4) if isinstance(v, (int, float)) else v)])
        t = Table(rows, colWidths=[8*cm, 7.5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#334155")),
            ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 8.5),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
            ("GRID",          (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING",       (0,0), (-1,-1), 5),
        ]))
        elements.append(t)
        return elements

    def _disclaimer(self):
        return [
            HRFlowable(width="100%", color=colors.HexColor("#e2e8f0"), thickness=0.5),
            Spacer(1, 0.2*cm),
            Paragraph(
                "DISCLAIMER: This report is generated by an AI model for clinical decision support "
                "purposes only. It is not a substitute for professional medical judgement. All "
                "predictions must be reviewed and confirmed by a qualified healthcare professional "
                "before any clinical action is taken.",
                self.small_style,
            ),
            Paragraph(
                f"Generated by MedPredict v2.0 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                self.small_style,
            ),
        ]


patient_report_generator = PatientReportGenerator()
