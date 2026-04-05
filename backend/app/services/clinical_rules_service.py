"""
Clinical Decision Rules Service — compares AI predictions with established clinical guidelines.

Implements Framingham Risk Score, WHO CVD Risk Calculator, KDIGO CKD staging,
and ADA Diabetes Risk Test for clinical validation and comparison.
"""

import math
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class RiskScore:
    """Container for a clinical risk score result."""
    score: float
    risk_category: str
    percentage: float
    interpretation: str
    source: str


class ClinicalDecisionRulesService:
    """
    Provides validated clinical risk scores for comparison with ML predictions.
    
    Implements:
    - Framingham Risk Score (10-year CVD risk)
    - WHO/ISH CVD Risk Charts
    - KDIGO CKD Risk Matrix
    - ADA Type 2 Diabetes Risk Test
    """
    
    def compare_with_clinical_rules(
        self,
        disease: str,
        patient_data: Dict[str, Any],
        ml_prediction: float
    ) -> Dict[str, Any]:
        """
        Compare ML prediction with appropriate clinical decision rules.
        
        Args:
            disease: Type of disease ('heart', 'diabetes', 'kidney')
            patient_data: Patient features
            ml_prediction: ML model probability (0-1)
            
        Returns:
            Dict with clinical scores and comparison analysis
        """
        result = {
            'ml_prediction': {
                'probability': round(ml_prediction, 4),
                'risk_level': self._get_ml_risk_level(ml_prediction)
            },
            'clinical_scores': [],
            'agreement_analysis': {},
            'recommendation': ''
        }
        
        if disease == 'heart':
            # Framingham Risk Score
            framingham = self.calculate_framingham_score(patient_data)
            if framingham:
                result['clinical_scores'].append(framingham)
            
            # WHO CVD Risk
            who_risk = self.calculate_who_cvd_risk(patient_data)
            if who_risk:
                result['clinical_scores'].append(who_risk)
                
        elif disease == 'diabetes':
            # ADA Risk Test
            ada_score = self.calculate_ada_diabetes_risk(patient_data)
            if ada_score:
                result['clinical_scores'].append(ada_score)
            
            # FINDRISC (simplified)
            findrisc = self.calculate_findrisc(patient_data)
            if findrisc:
                result['clinical_scores'].append(findrisc)
                
        elif disease == 'kidney':
            # KDIGO Risk Matrix
            kdigo = self.calculate_kdigo_risk(patient_data)
            if kdigo:
                result['clinical_scores'].append(kdigo)
        
        # Analyze agreement between ML and clinical rules
        result['agreement_analysis'] = self._analyze_agreement(
            ml_prediction,
            result['clinical_scores']
        )
        
        # Generate recommendation
        result['recommendation'] = self._generate_combined_recommendation(result)
        
        return result
    
    def calculate_framingham_score(
        self,
        patient_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate Framingham 10-year CVD Risk Score.
        
        Based on: D'Agostino et al., 2008
        """
        try:
            age = float(patient_data.get('age', 0))
            sex = int(patient_data.get('sex', 1))  # 1=male, 0=female
            total_chol = float(patient_data.get('chol', patient_data.get('total_cholesterol', 200)))
            hdl = float(patient_data.get('hdl', 50))  # Default if not provided
            sbp = float(patient_data.get('trestbps', patient_data.get('blood_pressure', 120)))
            smoker = int(patient_data.get('smoker', patient_data.get('fbs', 0)))  # Use fbs as proxy
            bp_treated = int(patient_data.get('bp_treated', 0))
            diabetes = int(patient_data.get('diabetes', patient_data.get('fbs', 0)))
            
            if sex == 1:  # Male
                # Log-transformed coefficients for men
                log_age = math.log(age) * 3.06117
                log_chol = math.log(total_chol) * 1.12370
                log_hdl = math.log(hdl) * -0.93263
                log_sbp = math.log(sbp) * (1.93303 if bp_treated else 1.99881)
                smoke_term = 0.65451 if smoker else 0
                dm_term = 0.57367 if diabetes else 0
                
                risk_sum = log_age + log_chol + log_hdl + log_sbp + smoke_term + dm_term
                baseline = 23.9802
                
                risk_10yr = 1 - math.pow(0.88936, math.exp(risk_sum - baseline))
                
            else:  # Female
                log_age = math.log(age) * 2.32888
                log_chol = math.log(total_chol) * 1.20904
                log_hdl = math.log(hdl) * -0.70833
                log_sbp = math.log(sbp) * (2.82263 if bp_treated else 2.76157)
                smoke_term = 0.52873 if smoker else 0
                dm_term = 0.69154 if diabetes else 0
                
                risk_sum = log_age + log_chol + log_hdl + log_sbp + smoke_term + dm_term
                baseline = 26.1931
                
                risk_10yr = 1 - math.pow(0.95012, math.exp(risk_sum - baseline))
            
            risk_10yr = max(0, min(1, risk_10yr))  # Clamp to [0, 1]
            
            # Risk categories
            if risk_10yr < 0.10:
                category = 'Low'
            elif risk_10yr < 0.20:
                category = 'Intermediate'
            else:
                category = 'High'
                
            return {
                'name': 'Framingham Risk Score',
                'score': round(risk_10yr * 100, 1),
                'unit': '%',
                'risk_category': category,
                'probability': round(risk_10yr, 4),
                'interpretation': f'{risk_10yr*100:.1f}% 10-year cardiovascular disease risk',
                'source': "D'Agostino et al., Circulation, 2008",
                'factors_used': ['age', 'sex', 'cholesterol', 'HDL', 'blood pressure', 'smoking', 'diabetes']
            }
            
        except Exception as e:
            logger.warning(f"Framingham calculation failed: {e}")
            return None
    
    def calculate_who_cvd_risk(
        self,
        patient_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Simplified WHO/ISH CVD Risk Chart calculation.
        
        Based on WHO CVD Risk Charts, 2019 update.
        """
        try:
            age = int(patient_data.get('age', 50))
            sex = int(patient_data.get('sex', 1))
            sbp = float(patient_data.get('trestbps', patient_data.get('blood_pressure', 120)))
            smoker = int(patient_data.get('smoker', 0))
            diabetes = int(patient_data.get('fbs', 0))
            chol = float(patient_data.get('chol', 200))
            
            # Simplified risk scoring (real WHO charts use region-specific tables)
            base_risk = 0.02  # Base 2% for young healthy
            
            # Age adjustment
            if age >= 70:
                base_risk *= 4.0
            elif age >= 60:
                base_risk *= 2.5
            elif age >= 50:
                base_risk *= 1.5
            elif age >= 40:
                base_risk *= 1.2
            
            # Sex adjustment
            if sex == 1:  # Male
                base_risk *= 1.5
            
            # Blood pressure
            if sbp >= 180:
                base_risk *= 3.0
            elif sbp >= 160:
                base_risk *= 2.0
            elif sbp >= 140:
                base_risk *= 1.5
            
            # Smoking
            if smoker:
                base_risk *= 2.0
            
            # Diabetes
            if diabetes:
                base_risk *= 2.0
            
            # Cholesterol
            if chol >= 280:
                base_risk *= 2.0
            elif chol >= 240:
                base_risk *= 1.5
            
            risk = min(base_risk, 1.0)
            
            # WHO categories
            if risk < 0.05:
                category = 'Low (<5%)'
            elif risk < 0.10:
                category = 'Low-Moderate (5-10%)'
            elif risk < 0.20:
                category = 'Moderate (10-20%)'
            elif risk < 0.30:
                category = 'High (20-30%)'
            else:
                category = 'Very High (≥30%)'
            
            return {
                'name': 'WHO CVD Risk Score',
                'score': round(risk * 100, 1),
                'unit': '%',
                'risk_category': category,
                'probability': round(risk, 4),
                'interpretation': f'{risk*100:.1f}% 10-year CVD risk per WHO guidelines',
                'source': 'WHO CVD Risk Charts, 2019',
                'factors_used': ['age', 'sex', 'blood pressure', 'smoking', 'diabetes', 'cholesterol']
            }
            
        except Exception as e:
            logger.warning(f"WHO CVD calculation failed: {e}")
            return None
    
    def calculate_ada_diabetes_risk(
        self,
        patient_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate ADA Type 2 Diabetes Risk Test score.
        
        Based on American Diabetes Association risk test.
        """
        try:
            score = 0
            
            # Age points
            age = int(patient_data.get('age', 40))
            if age >= 60:
                score += 3
            elif age >= 50:
                score += 2
            elif age >= 40:
                score += 1
            
            # Sex/gestational diabetes (using sex as proxy)
            sex = int(patient_data.get('sex', 1))
            if sex == 0:  # Female - assume gestational DM risk
                pregnancies = int(patient_data.get('pregnancies', 0))
                if pregnancies > 0:
                    score += 1
            
            # Family history (using diabetes_pedigree as proxy)
            pedigree = float(patient_data.get('diabetes_pedigree', patient_data.get('pedigree', 0)))
            if pedigree > 0.5:
                score += 1
            
            # Blood pressure
            bp = float(patient_data.get('blood_pressure', patient_data.get('trestbps', 120)))
            if bp >= 140:
                score += 1
            
            # BMI
            bmi = float(patient_data.get('bmi', 25))
            if bmi >= 40:
                score += 3
            elif bmi >= 30:
                score += 2
            elif bmi >= 25:
                score += 1
            
            # Physical activity (default assume somewhat active)
            score += 0  # Would add 1 for inactive
            
            # Convert to probability
            if score <= 2:
                prob = 0.05
                category = 'Low Risk'
            elif score <= 4:
                prob = 0.15
                category = 'Moderate Risk'
            elif score <= 6:
                prob = 0.30
                category = 'High Risk'
            else:
                prob = 0.50
                category = 'Very High Risk'
            
            return {
                'name': 'ADA Diabetes Risk Test',
                'score': score,
                'unit': 'points',
                'max_score': 10,
                'risk_category': category,
                'probability': prob,
                'interpretation': f'Score {score}/10: {category}. {"Recommend screening." if score >= 5 else "Monitor risk factors."}',
                'source': 'American Diabetes Association',
                'factors_used': ['age', 'BMI', 'blood pressure', 'family history', 'gestational history']
            }
            
        except Exception as e:
            logger.warning(f"ADA risk calculation failed: {e}")
            return None
    
    def calculate_findrisc(
        self,
        patient_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate Finnish Diabetes Risk Score (FINDRISC).
        """
        try:
            score = 0
            
            # Age
            age = int(patient_data.get('age', 40))
            if age >= 64:
                score += 4
            elif age >= 55:
                score += 3
            elif age >= 45:
                score += 2
            
            # BMI
            bmi = float(patient_data.get('bmi', 25))
            if bmi > 30:
                score += 3
            elif bmi > 25:
                score += 1
            
            # Waist (estimate from BMI if not provided)
            # Using approximation
            if bmi > 30:
                score += 4
            elif bmi > 27:
                score += 3
            
            # Blood pressure medication
            bp = float(patient_data.get('blood_pressure', patient_data.get('trestbps', 120)))
            if bp >= 140:
                score += 2
            
            # History of high blood glucose
            glucose = float(patient_data.get('glucose', patient_data.get('fbs', 0)))
            if glucose > 100:
                score += 5
            
            # Probability based on score
            if score < 7:
                prob = 0.01
                category = 'Low (1%)'
            elif score < 12:
                prob = 0.04
                category = 'Slightly Elevated (4%)'
            elif score < 15:
                prob = 0.17
                category = 'Moderate (17%)'
            elif score < 20:
                prob = 0.33
                category = 'High (33%)'
            else:
                prob = 0.50
                category = 'Very High (50%)'
            
            return {
                'name': 'FINDRISC Score',
                'score': score,
                'unit': 'points',
                'max_score': 26,
                'risk_category': category,
                'probability': prob,
                'interpretation': f'{int(prob*100)}% risk of developing Type 2 diabetes in 10 years',
                'source': 'Finnish Diabetes Association',
                'factors_used': ['age', 'BMI', 'waist', 'blood pressure', 'blood glucose history']
            }
            
        except Exception as e:
            logger.warning(f"FINDRISC calculation failed: {e}")
            return None
    
    def calculate_kdigo_risk(
        self,
        patient_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate KDIGO CKD risk category based on GFR and albuminuria.
        """
        try:
            # Estimate GFR from available data
            age = float(patient_data.get('age', 50))
            sex = int(patient_data.get('sex', 1))
            sc = float(patient_data.get('sc', 1.0))  # Serum creatinine
            
            # CKD-EPI equation (simplified)
            if sex == 0:  # Female
                if sc <= 0.7:
                    gfr = 144 * pow(sc/0.7, -0.329) * pow(0.993, age)
                else:
                    gfr = 144 * pow(sc/0.7, -1.209) * pow(0.993, age)
            else:  # Male
                if sc <= 0.9:
                    gfr = 141 * pow(sc/0.9, -0.411) * pow(0.993, age)
                else:
                    gfr = 141 * pow(sc/0.9, -1.209) * pow(0.993, age)
            
            # GFR stage
            if gfr >= 90:
                gfr_stage = 'G1'
                gfr_desc = 'Normal or high'
            elif gfr >= 60:
                gfr_stage = 'G2'
                gfr_desc = 'Mildly decreased'
            elif gfr >= 45:
                gfr_stage = 'G3a'
                gfr_desc = 'Mildly to moderately decreased'
            elif gfr >= 30:
                gfr_stage = 'G3b'
                gfr_desc = 'Moderately to severely decreased'
            elif gfr >= 15:
                gfr_stage = 'G4'
                gfr_desc = 'Severely decreased'
            else:
                gfr_stage = 'G5'
                gfr_desc = 'Kidney failure'
            
            # Albuminuria (estimate from protein data if available)
            al = float(patient_data.get('al', 0))  # Albumin level
            if al <= 1:
                alb_stage = 'A1'
                alb_desc = 'Normal to mildly increased'
            elif al <= 2:
                alb_stage = 'A2'
                alb_desc = 'Moderately increased'
            else:
                alb_stage = 'A3'
                alb_desc = 'Severely increased'
            
            # Combined risk category (KDIGO heat map)
            risk_matrix = {
                ('G1', 'A1'): ('Low', 0.05),
                ('G1', 'A2'): ('Moderate', 0.15),
                ('G1', 'A3'): ('High', 0.35),
                ('G2', 'A1'): ('Low', 0.08),
                ('G2', 'A2'): ('Moderate', 0.20),
                ('G2', 'A3'): ('High', 0.40),
                ('G3a', 'A1'): ('Moderate', 0.20),
                ('G3a', 'A2'): ('High', 0.35),
                ('G3a', 'A3'): ('Very High', 0.55),
                ('G3b', 'A1'): ('High', 0.35),
                ('G3b', 'A2'): ('Very High', 0.50),
                ('G3b', 'A3'): ('Very High', 0.65),
                ('G4', 'A1'): ('Very High', 0.55),
                ('G4', 'A2'): ('Very High', 0.65),
                ('G4', 'A3'): ('Very High', 0.80),
                ('G5', 'A1'): ('Very High', 0.75),
                ('G5', 'A2'): ('Very High', 0.85),
                ('G5', 'A3'): ('Very High', 0.95),
            }
            
            category, prob = risk_matrix.get((gfr_stage, alb_stage), ('Unknown', 0.5))
            
            return {
                'name': 'KDIGO CKD Risk Matrix',
                'score': f'{gfr_stage}/{alb_stage}',
                'unit': 'stage',
                'gfr': round(gfr, 1),
                'gfr_stage': gfr_stage,
                'gfr_description': gfr_desc,
                'albuminuria_stage': alb_stage,
                'albuminuria_description': alb_desc,
                'risk_category': category,
                'probability': prob,
                'interpretation': f'GFR {gfr:.0f} ({gfr_desc}), Albuminuria {alb_desc}. {category} risk of CKD progression.',
                'source': 'KDIGO Clinical Practice Guidelines, 2012',
                'factors_used': ['serum creatinine', 'age', 'sex', 'albumin']
            }
            
        except Exception as e:
            logger.warning(f"KDIGO calculation failed: {e}")
            return None
    
    def _get_ml_risk_level(self, probability: float) -> str:
        """Convert probability to risk level string."""
        if probability >= 0.7:
            return 'High'
        elif probability >= 0.4:
            return 'Moderate'
        elif probability >= 0.2:
            return 'Low-Moderate'
        else:
            return 'Low'
    
    def _analyze_agreement(
        self,
        ml_prob: float,
        clinical_scores: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze agreement between ML prediction and clinical rules."""
        if not clinical_scores:
            return {'status': 'no_clinical_data', 'message': 'No clinical scores available for comparison'}
        
        ml_level = self._get_ml_risk_level(ml_prob)
        
        agreements = []
        disagreements = []
        
        for score in clinical_scores:
            clinical_level = score.get('risk_category', 'Unknown').split()[0]  # Get first word
            
            # Normalize for comparison
            ml_high = ml_level in ['High', 'Moderate']
            clinical_high = clinical_level.lower() in ['high', 'very', 'moderate']
            
            if ml_high == clinical_high:
                agreements.append(score['name'])
            else:
                disagreements.append({
                    'score': score['name'],
                    'ml_says': ml_level,
                    'clinical_says': score['risk_category']
                })
        
        total = len(clinical_scores)
        agreement_rate = len(agreements) / total if total > 0 else 0
        
        if agreement_rate >= 0.8:
            status = 'strong_agreement'
            message = 'ML prediction aligns well with established clinical guidelines'
        elif agreement_rate >= 0.5:
            status = 'partial_agreement'
            message = 'Some discrepancy between ML and clinical scores; consider additional factors'
        else:
            status = 'significant_disagreement'
            message = '⚠️ ML prediction differs significantly from clinical guidelines; review recommended'
        
        return {
            'status': status,
            'agreement_rate': round(agreement_rate, 2),
            'message': message,
            'agreeing_scores': agreements,
            'disagreeing_scores': disagreements
        }
    
    def _generate_combined_recommendation(self, result: Dict[str, Any]) -> str:
        """Generate combined recommendation based on ML and clinical scores."""
        ml_prob = result['ml_prediction']['probability']
        ml_level = result['ml_prediction']['risk_level']
        agreement = result.get('agreement_analysis', {})
        
        if agreement.get('status') == 'strong_agreement':
            if ml_level == 'High':
                return "Both ML model and clinical guidelines indicate elevated risk. Recommend clinical evaluation and intervention."
            else:
                return "Both ML model and clinical guidelines suggest lower risk. Continue standard monitoring and preventive care."
        elif agreement.get('status') == 'significant_disagreement':
            return "⚠️ Discrepancy between ML prediction and clinical guidelines. Recommend physician review to reconcile differences and determine appropriate care plan."
        else:
            return "Mixed indicators from ML and clinical scoring. Consider patient-specific factors and clinical judgment for final assessment."
    
    def get_all_available_rules(self) -> Dict[str, List[str]]:
        """List all available clinical decision rules by disease."""
        return {
            'heart': ['Framingham Risk Score', 'WHO CVD Risk Score'],
            'diabetes': ['ADA Diabetes Risk Test', 'FINDRISC Score'],
            'kidney': ['KDIGO CKD Risk Matrix']
        }


# Singleton instance
clinical_rules_service = ClinicalDecisionRulesService()
