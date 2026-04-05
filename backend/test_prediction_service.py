"""
Unit tests for prediction service.
"""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd


class TestPredictionService:
    """Tests for PredictionService class."""
    
    @pytest.mark.unit
    def test_align_input_normalizes_keys(self, heart_input_data):
        """Test that input keys are normalized correctly."""
        from app.services.prediction_service import PredictionService
        
        service = PredictionService()
        
        # Test with different key formats
        input_data = {
            "Age": 54,
            "TRESTBPS": 130,
            "blood-pressure": 120,
        }
        
        feature_names = ["age", "trestbps", "blood_pressure"]
        result = service._align_input(input_data, feature_names)
        
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == feature_names
        assert len(result) == 1
    
    @pytest.mark.unit
    def test_align_input_handles_missing_features(self):
        """Test that missing features default to 0."""
        from app.services.prediction_service import PredictionService
        
        service = PredictionService()
        
        input_data = {"age": 54}
        feature_names = ["age", "missing_feature"]
        
        result = service._align_input(input_data, feature_names)
        
        # Missing feature should be 0.0
        assert result["missing_feature"].iloc[0] == 0.0
    
    @pytest.mark.unit
    def test_disease_labels_exist(self):
        """Test that disease labels are defined for all diseases."""
        from app.services.prediction_service import DISEASE_LABELS
        
        assert "heart" in DISEASE_LABELS
        assert "diabetes" in DISEASE_LABELS
        assert "kidney" in DISEASE_LABELS
        
        for disease, labels in DISEASE_LABELS.items():
            assert 0 in labels
            assert 1 in labels


class TestPredictionServiceIntegration:
    """Integration tests that require model loading."""
    
    @pytest.mark.integration
    def test_predict_with_mock_model(self, heart_input_data, mock_classifier):
        """Test prediction with mocked model."""
        from app.services.prediction_service import PredictionService
        
        service = PredictionService()
        
        with patch.object(service, '_align_input') as mock_align:
            mock_align.return_value = pd.DataFrame([[0] * 13], columns=[f"f{i}" for i in range(13)])
            
            with patch('app.ml.training.trainer.training_service') as mock_trainer:
                mock_trainer.get_best_model_name.return_value = 'random_forest'
                mock_trainer.load_model.return_value = (mock_classifier, [f"f{i}" for i in range(13)])
                
                with patch('app.services.prediction_service.get_shap_explanation') as mock_shap:
                    mock_shap.return_value = {
                        "feature_names": [],
                        "shap_values": [],
                        "base_value": 0.5,
                        "top_features": [],
                    }
                    
                    result = service.predict(
                        disease="heart",
                        input_data=heart_input_data,
                        model_name="best",
                        explain=True,
                    )
        
        assert result.prediction == 0
        assert result.confidence == 0.7
        assert result.label == "No Heart Disease"
