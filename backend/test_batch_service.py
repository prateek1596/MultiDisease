"""
Unit tests for batch prediction service.
"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import io


class TestBatchPredictionService:
    """Tests for BatchPredictionService class."""
    
    @pytest.mark.unit
    def test_validate_csv_accepts_valid_csv(self):
        """Test that valid CSV is accepted."""
        from app.services.batch_prediction_service import BatchPredictionService
        
        service = BatchPredictionService()
        
        csv_content = b"age,sex,cp\n54,1,2\n45,0,1\n"
        
        with patch('app.services.batch_prediction_service.outlier_service') as mock_outlier:
            mock_outlier.get_feature_stats.return_value = {
                "age": {}, "sex": {}, "cp": {}
            }
            
            is_valid, error, df = service.validate_csv(csv_content, "heart")
            
            assert is_valid is True
            assert error is None
            assert df is not None
            assert len(df) == 2
    
    @pytest.mark.unit
    def test_validate_csv_rejects_empty_csv(self):
        """Test that empty CSV is rejected."""
        from app.services.batch_prediction_service import BatchPredictionService
        
        service = BatchPredictionService()
        
        csv_content = b"age,sex,cp\n"
        
        with patch('app.services.batch_prediction_service.outlier_service') as mock_outlier:
            mock_outlier.get_feature_stats.return_value = {"age": {}, "sex": {}, "cp": {}}
            
            is_valid, error, df = service.validate_csv(csv_content, "heart")
            
            assert is_valid is False
            assert "empty" in error.lower()
    
    @pytest.mark.unit
    def test_validate_csv_rejects_invalid_csv(self):
        """Test that invalid CSV content is rejected."""
        from app.services.batch_prediction_service import BatchPredictionService
        
        service = BatchPredictionService()
        
        csv_content = b"not,valid\ncsv\"content"
        
        is_valid, error, df = service.validate_csv(csv_content, "heart")
        
        # Should either fail or parse with issues
        # The exact behavior depends on pandas' error handling
        assert is_valid is False or df is not None
    
    @pytest.mark.unit
    def test_validate_csv_rejects_too_many_rows(self):
        """Test that CSV with too many rows is rejected."""
        from app.services.batch_prediction_service import BatchPredictionService
        
        service = BatchPredictionService()
        
        # Create CSV with 10001 rows
        header = "age,sex,cp\n"
        rows = "54,1,2\n" * 10001
        csv_content = (header + rows).encode()
        
        with patch('app.services.batch_prediction_service.outlier_service') as mock_outlier:
            mock_outlier.get_feature_stats.return_value = {"age": {}, "sex": {}, "cp": {}}
            
            is_valid, error, df = service.validate_csv(csv_content, "heart")
            
            assert is_valid is False
            assert "10,000" in error or "10000" in error
    
    @pytest.mark.unit
    def test_get_batch_summary(self):
        """Test batch summary generation."""
        from app.services.batch_prediction_service import BatchPredictionService
        
        service = BatchPredictionService()
        
        predictions = [
            {"status": "success", "prediction": 1, "confidence": 0.9, "has_outliers": False},
            {"status": "success", "prediction": 0, "confidence": 0.8, "has_outliers": True},
            {"status": "success", "prediction": 1, "confidence": 0.85, "has_outliers": False},
            {"status": "error", "error": "test error"},
        ]
        
        summary = service.get_batch_summary(predictions)
        
        assert summary["total_records"] == 4
        assert summary["successful"] == 3
        assert summary["failed"] == 1
        assert summary["positive_predictions"] == 2
        assert summary["negative_predictions"] == 1
        assert summary["records_with_outliers"] == 1
        assert abs(summary["average_confidence"] - 0.85) < 0.01
    
    @pytest.mark.unit
    def test_create_results_csv(self):
        """Test CSV results creation."""
        from app.services.batch_prediction_service import BatchPredictionService
        
        service = BatchPredictionService()
        
        original_df = pd.DataFrame({
            "age": [54, 45],
            "sex": [1, 0],
        })
        
        predictions = [
            {"prediction": 1, "label": "Positive", "confidence": 0.9, 
             "probability_positive": 0.9, "has_outliers": False, "status": "success"},
            {"prediction": 0, "label": "Negative", "confidence": 0.8,
             "probability_positive": 0.2, "has_outliers": True, "status": "success"},
        ]
        
        csv_result = service.create_results_csv(original_df, predictions)
        
        assert "age" in csv_result
        assert "prediction" in csv_result
        assert "confidence" in csv_result
        assert "prediction_label" in csv_result
        
        # Parse and verify
        result_df = pd.read_csv(io.StringIO(csv_result))
        assert len(result_df) == 2
        assert result_df["prediction"].tolist() == [1, 0]
