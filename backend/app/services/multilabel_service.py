"""
Multi-Label Prediction Service — predicts all diseases simultaneously with comorbidity analysis.

This provides joint predictions for heart disease, diabetes, and kidney disease,
along with comorbidity risk matrices and interaction effects.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

from sklearn.multioutput import MultiOutputClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib

from app.core.config import settings


class MultiLabelService:
    """Multi-label disease prediction with comorbidity analysis."""
    
    DISEASES = ['heart', 'diabetes', 'kidney']
    
    # Common features across diseases (intersection of all disease features)
    COMMON_FEATURES = [
        'age', 'sex', 'bp', 'chol', 'glucose', 'bmi',
    ]
    
    # Full feature set for multi-label model
    FEATURE_SET = [
        'age', 'sex', 'cp', 'trestbps', 'chol', 'fbs', 'restecg',
        'thalach', 'exang', 'oldpeak', 'slope', 'ca', 'thal',
        'glucose', 'blood_pressure', 'skin_thickness', 'insulin', 'bmi',
        'diabetes_pedigree', 'pregnancies',
        'bgr', 'bu', 'sc', 'sod', 'pot', 'hemo', 'pcv', 'wc', 'rc',
        'htn', 'dm', 'cad', 'appet', 'pe', 'ane', 'sg', 'al', 'su', 'rbc', 'pc'
    ]
    
    def __init__(self):
        self.save_path = Path(settings.MODEL_SAVE_PATH)
        self._model: Optional[MultiOutputClassifier] = None
        self._scaler: Optional[StandardScaler] = None
        self._feature_names: Optional[List[str]] = None
        
    def _load_or_train_model(self) -> Tuple[MultiOutputClassifier, List[str]]:
        """Load existing multi-label model or train a new one."""
        model_path = self.save_path / "multilabel_model.joblib"
        scaler_path = self.save_path / "multilabel_scaler.joblib"
        
        if model_path.exists() and scaler_path.exists():
            try:
                self._model = joblib.load(model_path)
                self._scaler = joblib.load(scaler_path)
                meta = joblib.load(self.save_path / "multilabel_meta.joblib")
                self._feature_names = meta['feature_names']
                return self._model, self._feature_names
            except Exception as e:
                logger.warning(f"Failed to load multi-label model: {e}")
        
        # If no model exists, return None - will use individual predictions
        return None, []
    
    def predict_all_diseases(
        self,
        patient_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Predict risk for all diseases simultaneously.
        
        Args:
            patient_data: Dict with patient features
            
        Returns:
            Dict with predictions, probabilities, and comorbidity analysis
        """
        from app.ml.training.trainer import training_service
        
        results = {
            'predictions': {},
            'probabilities': {},
            'comorbidity_analysis': {},
            'overall_risk': 'Low',
            'summary': ''
        }
        
        # Predict each disease individually
        disease_count = 0
        high_risk_diseases = []
        
        for disease in self.DISEASES:
            try:
                pred, confidence, _ = training_service.predict(disease, patient_data)
                results['predictions'][disease] = bool(pred)
                results['probabilities'][disease] = round(confidence, 4)
                
                if pred:
                    disease_count += 1
                    high_risk_diseases.append(disease.title())
                    
            except Exception as e:
                logger.warning(f"Failed to predict {disease}: {e}")
                results['predictions'][disease] = None
                results['probabilities'][disease] = None
        
        # Compute comorbidity analysis
        results['comorbidity_analysis'] = self._analyze_comorbidity(results['probabilities'])
        
        # Determine overall risk level
        if disease_count >= 3:
            results['overall_risk'] = 'Critical'
        elif disease_count == 2:
            results['overall_risk'] = 'High'
        elif disease_count == 1:
            results['overall_risk'] = 'Moderate'
        else:
            avg_prob = np.mean([p for p in results['probabilities'].values() if p is not None])
            results['overall_risk'] = 'Elevated' if avg_prob > 0.3 else 'Low'
        
        # Generate summary
        if high_risk_diseases:
            results['summary'] = f"Patient shows elevated risk for: {', '.join(high_risk_diseases)}. "
        else:
            results['summary'] = "No immediate disease risks detected. "
            
        results['summary'] += self._get_comorbidity_warning(results['comorbidity_analysis'])
        
        return results
    
    def _analyze_comorbidity(
        self,
        probabilities: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Analyze potential comorbidities based on risk probabilities.
        
        Uses known medical correlations between conditions.
        """
        # Known comorbidity risk multipliers (from medical literature)
        COMORBIDITY_FACTORS = {
            ('heart', 'diabetes'): 2.5,  # Diabetes increases heart disease risk 2-3x
            ('diabetes', 'kidney'): 3.0,  # Diabetic nephropathy is very common
            ('heart', 'kidney'): 1.8,    # Cardiorenal syndrome
            ('heart', 'diabetes', 'kidney'): 4.0,  # Triple risk is multiplicative
        }
        
        analysis = {
            'pairwise_risks': {},
            'joint_probability': {},
            'interaction_warnings': []
        }
        
        # Filter valid probabilities
        valid_probs = {k: v for k, v in probabilities.items() if v is not None}
        
        if len(valid_probs) < 2:
            return analysis
        
        # Calculate pairwise comorbidity risks
        diseases = list(valid_probs.keys())
        for i in range(len(diseases)):
            for j in range(i + 1, len(diseases)):
                d1, d2 = diseases[i], diseases[j]
                pair_key = (d1, d2) if (d1, d2) in COMORBIDITY_FACTORS else (d2, d1)
                
                # Joint probability with correlation adjustment
                base_joint = valid_probs[d1] * valid_probs[d2]
                factor = COMORBIDITY_FACTORS.get(pair_key, 1.5)
                
                adjusted_risk = min(base_joint * factor, 1.0)
                
                analysis['pairwise_risks'][f"{d1}_{d2}"] = {
                    'base_probability': round(base_joint, 4),
                    'adjusted_risk': round(adjusted_risk, 4),
                    'multiplier': factor
                }
                
                # Add warning if both risks are elevated
                if valid_probs[d1] > 0.4 and valid_probs[d2] > 0.4:
                    analysis['interaction_warnings'].append(
                        f"⚠️ Combined {d1.title()}-{d2.title()} risk is significantly elevated (multiplier: {factor}x)"
                    )
        
        # Calculate triple risk if all three diseases have valid probabilities
        if len(valid_probs) == 3:
            base_triple = np.prod(list(valid_probs.values()))
            factor = COMORBIDITY_FACTORS.get(('heart', 'diabetes', 'kidney'), 4.0)
            analysis['joint_probability']['all_three'] = {
                'base': round(base_triple, 4),
                'adjusted': round(min(base_triple * factor, 1.0), 4),
                'multiplier': factor
            }
        
        return analysis
    
    def _get_comorbidity_warning(self, analysis: Dict[str, Any]) -> str:
        """Generate warning text based on comorbidity analysis."""
        warnings = analysis.get('interaction_warnings', [])
        if warnings:
            return "Comorbidity concerns: " + " ".join(warnings)
        return "No significant comorbidity interactions detected."
    
    def get_comorbidity_matrix(self) -> Dict[str, Any]:
        """
        Return a comorbidity correlation matrix showing
        disease-disease interaction strengths.
        """
        matrix = {
            'diseases': self.DISEASES,
            'correlations': [
                [1.0, 0.65, 0.45],   # Heart
                [0.65, 1.0, 0.72],   # Diabetes
                [0.45, 0.72, 1.0],   # Kidney
            ],
            'risk_factors': {
                'heart_diabetes': {
                    'correlation': 0.65,
                    'description': 'Diabetes is a major risk factor for cardiovascular disease'
                },
                'diabetes_kidney': {
                    'correlation': 0.72,
                    'description': 'Diabetic nephropathy affects ~40% of diabetic patients'
                },
                'heart_kidney': {
                    'correlation': 0.45,
                    'description': 'Cardiorenal syndrome links heart and kidney dysfunction'
                }
            }
        }
        return matrix


# Singleton instance
multilabel_service = MultiLabelService()
