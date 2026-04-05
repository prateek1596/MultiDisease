"""
Longitudinal Patient Tracking Service — tracks patient risk over time.

Provides patient history management, risk trend analysis,
and temporal visualization data for tracking disease progression.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from uuid import uuid4
from loguru import logger

from app.core.config import settings


class LongitudinalTrackingService:
    """
    Manages patient visit history and risk trend analysis.
    
    Stores patient visits with predictions and provides
    trend analysis and change detection.
    """
    
    DISEASES = ['heart', 'diabetes', 'kidney']
    
    def __init__(self):
        self.data_path = Path(settings.MODEL_SAVE_PATH) / "patient_data"
        self.data_path.mkdir(parents=True, exist_ok=True)
        
    def record_visit(
        self,
        patient_id: str,
        predictions: Dict[str, Any],
        patient_data: Dict[str, Any],
        visit_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a patient visit with predictions.
        
        Args:
            patient_id: Unique patient identifier
            predictions: Dict with disease predictions and probabilities
            patient_data: Patient features at time of visit
            visit_notes: Optional clinical notes
            
        Returns:
            Created visit record
        """
        visit = {
            'visit_id': str(uuid4()),
            'patient_id': patient_id,
            'timestamp': datetime.utcnow().isoformat(),
            'predictions': predictions,
            'patient_data': patient_data,
            'notes': visit_notes
        }
        
        # Load existing patient data
        patient_file = self.data_path / f"{patient_id}.json"
        
        if patient_file.exists():
            try:
                data = json.loads(patient_file.read_text())
            except Exception:
                data = {'patient_id': patient_id, 'visits': []}
        else:
            data = {'patient_id': patient_id, 'visits': [], 'created_at': visit['timestamp']}
        
        # Append new visit
        data['visits'].append(visit)
        data['last_visit'] = visit['timestamp']
        
        # Save
        patient_file.write_text(json.dumps(data, indent=2, default=str))
        
        logger.info(f"Recorded visit {visit['visit_id']} for patient {patient_id}")
        
        return visit
    
    def get_patient_history(
        self,
        patient_id: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get complete visit history for a patient.
        
        Args:
            patient_id: Patient identifier
            limit: Optional limit on number of visits returned
            
        Returns:
            Patient data with visit history
        """
        patient_file = self.data_path / f"{patient_id}.json"
        
        if not patient_file.exists():
            return {'patient_id': patient_id, 'visits': [], 'message': 'No history found'}
        
        try:
            data = json.loads(patient_file.read_text())
            
            if limit:
                data['visits'] = data['visits'][-limit:]
            
            # Add computed fields
            data['total_visits'] = len(data['visits'])
            data['trend_analysis'] = self.analyze_trends(patient_id)
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to load patient history: {e}")
            return {'patient_id': patient_id, 'visits': [], 'error': str(e)}
    
    def analyze_trends(
        self,
        patient_id: str,
        window_size: int = 5
    ) -> Dict[str, Any]:
        """
        Analyze risk trends for a patient across visits.
        
        Args:
            patient_id: Patient identifier
            window_size: Number of recent visits to consider for trend
            
        Returns:
            Trend analysis with direction and alerts
        """
        patient_file = self.data_path / f"{patient_id}.json"
        
        if not patient_file.exists():
            return {'status': 'no_data'}
        
        try:
            data = json.loads(patient_file.read_text())
            visits = data.get('visits', [])
            
            if len(visits) < 2:
                return {
                    'status': 'insufficient_data',
                    'message': 'Need at least 2 visits for trend analysis'
                }
            
            # Get recent visits
            recent_visits = visits[-window_size:]
            
            analysis = {
                'period': {
                    'start': recent_visits[0]['timestamp'],
                    'end': recent_visits[-1]['timestamp'],
                    'visits_analyzed': len(recent_visits)
                },
                'trends': {},
                'alerts': [],
                'summary': ''
            }
            
            # Analyze each disease
            for disease in self.DISEASES:
                probs = []
                for visit in recent_visits:
                    pred = visit.get('predictions', {})
                    prob = pred.get('probabilities', {}).get(disease)
                    if prob is not None:
                        probs.append(prob)
                
                if len(probs) >= 2:
                    # Calculate trend
                    trend = self._calculate_trend(probs)
                    analysis['trends'][disease] = trend
                    
                    # Check for alerts
                    alert = self._check_alerts(disease, probs, trend)
                    if alert:
                        analysis['alerts'].append(alert)
            
            # Generate summary
            analysis['summary'] = self._generate_trend_summary(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend direction and magnitude."""
        if len(values) < 2:
            return {'direction': 'stable', 'change': 0}
        
        # Simple linear regression
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # Determine direction
        if abs(slope) < 0.01:
            direction = 'stable'
        elif slope > 0:
            direction = 'increasing'
        else:
            direction = 'decreasing'
        
        # Change from first to last
        total_change = values[-1] - values[0]
        percent_change = (total_change / values[0] * 100) if values[0] != 0 else 0
        
        return {
            'direction': direction,
            'slope': round(slope, 4),
            'first_value': round(values[0], 4),
            'last_value': round(values[-1], 4),
            'total_change': round(total_change, 4),
            'percent_change': round(percent_change, 1),
            'values': [round(v, 4) for v in values]
        }
    
    def _check_alerts(
        self,
        disease: str,
        probs: List[float],
        trend: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check for significant changes that warrant alerts."""
        alerts = []
        
        # Alert if crossed threshold
        threshold = 0.5
        if probs[-1] >= threshold and probs[0] < threshold:
            return {
                'type': 'threshold_crossed',
                'disease': disease,
                'severity': 'high',
                'message': f'⚠️ {disease.title()} risk has crossed critical threshold ({probs[0]:.0%} → {probs[-1]:.0%})'
            }
        
        # Alert if rapid increase
        if trend['direction'] == 'increasing' and trend['percent_change'] > 20:
            return {
                'type': 'rapid_increase',
                'disease': disease,
                'severity': 'moderate',
                'message': f'📈 {disease.title()} risk increasing rapidly (+{trend["percent_change"]:.0f}%)'
            }
        
        # Alert if now high risk
        if probs[-1] >= 0.7:
            return {
                'type': 'high_risk',
                'disease': disease,
                'severity': 'high',
                'message': f'🔴 {disease.title()} risk is now HIGH ({probs[-1]:.0%})'
            }
        
        return None
    
    def _generate_trend_summary(self, analysis: Dict[str, Any]) -> str:
        """Generate human-readable trend summary."""
        trends = analysis.get('trends', {})
        alerts = analysis.get('alerts', [])
        
        if not trends:
            return "No trend data available."
        
        # Count directions
        increasing = sum(1 for t in trends.values() if t.get('direction') == 'increasing')
        decreasing = sum(1 for t in trends.values() if t.get('direction') == 'decreasing')
        
        if alerts:
            severity = max(a.get('severity', 'low') for a in alerts)
            if severity == 'high':
                return f"⚠️ ATTENTION: {len(alerts)} significant change(s) detected. Review recommended."
        
        if increasing > decreasing:
            return f"Overall risk profile trending upward. {increasing} disease(s) showing increased risk."
        elif decreasing > increasing:
            return f"✅ Positive trend: {decreasing} disease(s) showing decreased risk."
        else:
            return "Risk levels relatively stable across all tracked diseases."
    
    def get_timeline_data(
        self,
        patient_id: str
    ) -> Dict[str, Any]:
        """
        Get formatted data for timeline visualization.
        
        Returns data structured for charting libraries.
        """
        history = self.get_patient_history(patient_id)
        visits = history.get('visits', [])
        
        if not visits:
            return {'data': [], 'message': 'No visits recorded'}
        
        timeline = []
        
        for visit in visits:
            timestamp = visit.get('timestamp', '')
            predictions = visit.get('predictions', {})
            probs = predictions.get('probabilities', {})
            
            point = {
                'date': timestamp[:10] if timestamp else '',
                'timestamp': timestamp,
                'visit_id': visit.get('visit_id', '')
            }
            
            for disease in self.DISEASES:
                point[disease] = probs.get(disease)
                point[f'{disease}_prediction'] = predictions.get('predictions', {}).get(disease)
            
            timeline.append(point)
        
        return {
            'patient_id': patient_id,
            'data': timeline,
            'diseases': self.DISEASES,
            'total_points': len(timeline)
        }
    
    def compare_visits(
        self,
        patient_id: str,
        visit_id_1: str,
        visit_id_2: str
    ) -> Dict[str, Any]:
        """Compare two specific visits for a patient."""
        history = self.get_patient_history(patient_id)
        visits = {v['visit_id']: v for v in history.get('visits', [])}
        
        if visit_id_1 not in visits or visit_id_2 not in visits:
            return {'error': 'One or both visits not found'}
        
        v1 = visits[visit_id_1]
        v2 = visits[visit_id_2]
        
        comparison = {
            'visit_1': {
                'id': visit_id_1,
                'timestamp': v1['timestamp'],
                'predictions': v1.get('predictions', {})
            },
            'visit_2': {
                'id': visit_id_2,
                'timestamp': v2['timestamp'],
                'predictions': v2.get('predictions', {})
            },
            'changes': {}
        }
        
        # Compare predictions
        probs1 = v1.get('predictions', {}).get('probabilities', {})
        probs2 = v2.get('predictions', {}).get('probabilities', {})
        
        for disease in self.DISEASES:
            p1 = probs1.get(disease)
            p2 = probs2.get(disease)
            
            if p1 is not None and p2 is not None:
                change = p2 - p1
                comparison['changes'][disease] = {
                    'before': round(p1, 4),
                    'after': round(p2, 4),
                    'change': round(change, 4),
                    'direction': 'increased' if change > 0.01 else ('decreased' if change < -0.01 else 'stable')
                }
        
        return comparison
    
    def list_patients(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all tracked patients with summary info."""
        patients = []
        
        for patient_file in self.data_path.glob("*.json"):
            try:
                data = json.loads(patient_file.read_text())
                patients.append({
                    'patient_id': data.get('patient_id'),
                    'total_visits': len(data.get('visits', [])),
                    'first_visit': data.get('created_at'),
                    'last_visit': data.get('last_visit')
                })
            except Exception:
                continue
        
        # Sort by last visit
        patients.sort(key=lambda x: x.get('last_visit', ''), reverse=True)
        
        return patients[:limit]
    
    def delete_patient(self, patient_id: str) -> bool:
        """Delete all data for a patient."""
        patient_file = self.data_path / f"{patient_id}.json"
        
        if patient_file.exists():
            patient_file.unlink()
            logger.info(f"Deleted patient data: {patient_id}")
            return True
        
        return False


# Demo data generator for testing
def generate_demo_patient(patient_id: str = "demo-patient-001") -> Dict[str, Any]:
    """Generate demo patient with historical visits for testing."""
    import random
    
    service = longitudinal_service
    
    # Generate 6 visits over 6 months
    base_date = datetime.utcnow() - timedelta(days=180)
    
    base_risks = {
        'heart': 0.35,
        'diabetes': 0.45,
        'kidney': 0.25
    }
    
    for i in range(6):
        visit_date = base_date + timedelta(days=30 * i)
        
        # Simulate gradual changes
        predictions = {
            'predictions': {},
            'probabilities': {}
        }
        
        for disease, base in base_risks.items():
            # Add some trend + noise
            trend = 0.02 * i  # Slight increase over time
            noise = random.uniform(-0.05, 0.05)
            prob = max(0, min(1, base + trend + noise))
            
            predictions['probabilities'][disease] = prob
            predictions['predictions'][disease] = prob > 0.5
        
        patient_data = {
            'age': 55 + i * 0.5,
            'bmi': 28 + random.uniform(-1, 1),
            'blood_pressure': 135 + random.randint(-10, 10),
            'cholesterol': 220 + random.randint(-20, 20)
        }
        
        visit = {
            'visit_id': str(uuid4()),
            'patient_id': patient_id,
            'timestamp': visit_date.isoformat(),
            'predictions': predictions,
            'patient_data': patient_data,
            'notes': f'Visit {i + 1}'
        }
        
        # Direct write to avoid service timestamp override
        patient_file = service.data_path / f"{patient_id}.json"
        
        if patient_file.exists():
            data = json.loads(patient_file.read_text())
        else:
            data = {'patient_id': patient_id, 'visits': [], 'created_at': visit['timestamp']}
        
        data['visits'].append(visit)
        data['last_visit'] = visit['timestamp']
        patient_file.write_text(json.dumps(data, indent=2))
    
    return service.get_patient_history(patient_id)


# Singleton instance
longitudinal_service = LongitudinalTrackingService()
