"""
Report generation service: produces a comprehensive PDF report
with model metrics, confusion matrices, and visualizations.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from loguru import logger

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.core.config import settings
from app.ml.evaluation.evaluator import get_all_metrics


class ReportGenerator:
    """Generates a professional PDF report of all model evaluations."""

    def __init__(self):
        self.report_path = Path(settings.REPORT_SAVE_PATH)
        self.report_path.mkdir(parents=True, exist_ok=True)
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        self.title_style = ParagraphStyle(
            "CustomTitle",
            parent=self.styles["Title"],
            fontSize=24,
            textColor=colors.HexColor("#1E3A5F"),
            spaceAfter=12,
            alignment=TA_CENTER,
        )
        self.h2_style = ParagraphStyle(
            "CustomH2",
            parent=self.styles["Heading2"],
            fontSize=16,
            textColor=colors.HexColor("#2563EB"),
            spaceBefore=16,
            spaceAfter=8,
        )
        self.h3_style = ParagraphStyle(
            "CustomH3",
            parent=self.styles["Heading3"],
            fontSize=13,
            textColor=colors.HexColor("#374151"),
            spaceBefore=10,
            spaceAfter=6,
        )
        self.body_style = ParagraphStyle(
            "CustomBody",
            parent=self.styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#4B5563"),
            spaceAfter=6,
        )

    def generate(self) -> str:
        """Generate PDF report and return its file path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mdps_report_{timestamp}.pdf"
        filepath = self.report_path / filename

        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        story = []
        story += self._build_cover()
        story.append(PageBreak())
        story += self._build_summary()

        all_metrics = get_all_metrics()
        for disease, metrics in all_metrics.items():
            story.append(PageBreak())
            story += self._build_disease_section(disease, metrics)

        doc.build(story)
        logger.info(f"PDF report generated: {filepath}")
        return str(filepath)

    def _build_cover(self):
        elements = []
        elements.append(Spacer(1, 2 * inch))
        elements.append(Paragraph("Multi-Disease Prediction System", self.title_style))
        elements.append(Paragraph("Comprehensive Model Evaluation Report", self.h2_style))
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(HRFlowable(width="100%", color=colors.HexColor("#2563EB")))
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}",
            self.body_style
        ))
        elements.append(Paragraph(
            "Diseases Covered: Heart Disease • Diabetes • Chronic Kidney Disease",
            self.body_style
        ))
        elements.append(Paragraph(
            "Models: Logistic Regression • Random Forest • SVM • XGBoost • LightGBM • Stacking Ensemble",
            self.body_style
        ))
        return elements

    def _build_summary(self):
        elements = []
        elements.append(Paragraph("Executive Summary", self.h2_style))
        elements.append(Paragraph(
            "This report presents a comprehensive evaluation of six machine learning models "
            "applied to three disease prediction tasks. Models were trained using stratified "
            "train-test splits with SMOTE oversampling to address class imbalance. "
            "5-fold cross-validation was used to assess generalizability.",
            self.body_style
        ))

        all_metrics = get_all_metrics()
        if not all_metrics:
            elements.append(Paragraph("No trained models found. Please run training first.", self.body_style))
            return elements

        # Best models table
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph("Best Models by Disease", self.h3_style))

        table_data = [["Disease", "Best Model", "Accuracy", "ROC-AUC", "F1-Score"]]
        for disease, metrics in all_metrics.items():
            best = max(metrics.items(), key=lambda x: x[1].get("roc_auc", 0))
            m = best[1]
            table_data.append([
                disease.capitalize(),
                best[0].replace("_", " ").title(),
                f"{m.get('accuracy', 0):.4f}",
                f"{m.get('roc_auc', 0):.4f}",
                f"{m.get('f1_score', 0):.4f}",
            ])

        t = Table(table_data, colWidths=[1.5 * inch, 2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch])
        t.setStyle(self._table_style())
        elements.append(t)
        return elements

    def _build_disease_section(self, disease: str, metrics: Dict[str, Any]):
        elements = []
        elements.append(Paragraph(f"{disease.capitalize()} Disease — Model Comparison", self.h2_style))
        elements.append(HRFlowable(width="100%", color=colors.HexColor("#E5E7EB")))
        elements.append(Spacer(1, 0.1 * inch))

        # Metrics comparison table
        elements.append(Paragraph("Performance Metrics Comparison", self.h3_style))
        header = ["Model", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC", "Best?"]
        rows = [header]
        for model_name, m in metrics.items():
            if "error" in m:
                continue
            rows.append([
                model_name.replace("_", " ").title(),
                f"{m.get('accuracy', 0):.4f}",
                f"{m.get('precision', 0):.4f}",
                f"{m.get('recall', 0):.4f}",
                f"{m.get('f1_score', 0):.4f}",
                f"{m.get('roc_auc', 0):.4f}",
                "✓" if m.get("is_best") else "",
            ])
        t = Table(rows, colWidths=[1.6*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.6*inch])
        t.setStyle(self._table_style())
        elements.append(t)
        elements.append(Spacer(1, 0.2 * inch))

        # Confusion matrix images
        cm_dir = Path(settings.REPORT_SAVE_PATH) / "confusion_matrices"
        for model_name in metrics:
            cm_path = cm_dir / f"{disease}_{model_name}_cm.png"
            if cm_path.exists():
                elements.append(Paragraph(
                    f"{model_name.replace('_', ' ').title()} — Confusion Matrix",
                    self.h3_style
                ))
                elements.append(Image(str(cm_path), width=3.5 * inch, height=2.8 * inch))
                elements.append(Spacer(1, 0.1 * inch))

        return elements

    def _table_style(self):
        return TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A5F")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
            ("PADDING", (0, 0), (-1, -1), 6),
        ])


report_generator = ReportGenerator()
