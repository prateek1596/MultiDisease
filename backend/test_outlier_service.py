"""
Unit tests for outlier detection service.
"""

import pytest
from unittest.mock import patch, MagicMock
import json


class TestOutlierService:
    """Tests for OutlierService class."""
    
    @pytest.mark.unit
    def test_detect_outliers_flags_out_of_range_values(self):
        """Test that values outside training range are flagged."""
        from app.services.outlier_service import OutlierService
        
        service = OutlierService()
        
        # Mock feature stats
        mock_stats = {
            "age": {
                "min": 20,
                "max": 80,
                "mean": 50,
                "std": 10,
                "q1": 40,
                "q3": 60,
                "median": 50,
            }
        }
        
        with patch.object(service, 'get_feature_stats', return_value=mock_stats):
            # Test value below min
            alerts = service.detect_outliers("heart", {"age": 10})
            assert len(alerts) == 1
            assert alerts[0]["severity"] == "high"
            assert "Below minimum" in alerts[0]["reason"]
            
            # Test value above max
            alerts = service.detect_outliers("heart", {"age": 100})
            assert len(alerts) == 1
            assert alerts[0]["severity"] == "high"
            assert "Above maximum" in alerts[0]["reason"]
    
    @pytest.mark.unit
    def test_detect_outliers_flags_high_z_score(self):
        """Test that values with high z-score are flagged."""
        from app.services.outlier_service import OutlierService
        
        service = OutlierService()
        
        mock_stats = {
            "glucose": {
                "min": 50,
                "max": 200,
                "mean": 100,
                "std": 20,
                "q1": 85,
                "q3": 115,
                "median": 100,
            }
        }
        
        with patch.object(service, 'get_feature_stats', return_value=mock_stats):
            # Test value with high z-score (within range but unusual)
            # z = (180 - 100) / 20 = 4, which is > 3
            alerts = service.detect_outliers("diabetes", {"glucose": 180}, z_threshold=3.0)
            assert len(alerts) == 1
            assert alerts[0]["severity"] == "medium"
            assert "std from mean" in alerts[0]["reason"]
    
    @pytest.mark.unit
    def test_detect_outliers_ignores_normal_values(self):
        """Test that normal values are not flagged."""
        from app.services.outlier_service import OutlierService
        
        service = OutlierService()
        
        mock_stats = {
            "age": {
                "min": 20,
                "max": 80,
                "mean": 50,
                "std": 10,
                "q1": 40,
                "q3": 60,
                "median": 50,
            }
        }
        
        with patch.object(service, 'get_feature_stats', return_value=mock_stats):
            alerts = service.detect_outliers("heart", {"age": 55})
            assert len(alerts) == 0
    
    @pytest.mark.unit
    def test_normalize_input_keys(self):
        """Test that input keys are normalized for matching."""
        from app.services.outlier_service import OutlierService
        
        service = OutlierService()
        
        mock_stats = {
            "blood_pressure": {
                "min": 50,
                "max": 200,
                "mean": 100,
                "std": 20,
                "q1": 85,
                "q3": 115,
                "median": 100,
            }
        }
        
        with patch.object(service, 'get_feature_stats', return_value=mock_stats):
            # Test with different key formats
            alerts = service.detect_outliers("heart", {"Blood-Pressure": 250})
            assert len(alerts) == 1
            
            alerts = service.detect_outliers("heart", {"BLOOD_PRESSURE": 250})
            assert len(alerts) == 1
    
    @pytest.mark.unit
    def test_get_all_feature_bounds(self):
        """Test feature bounds extraction."""
        from app.services.outlier_service import OutlierService
        
        service = OutlierService()
        
        mock_stats = {
            "age": {
                "min": 20,
                "max": 80,
                "mean": 50,
                "std": 10,
                "q1": 40,
                "q3": 60,
                "median": 50,
            }
        }
        
        with patch.object(service, 'get_feature_stats', return_value=mock_stats):
            bounds = service.get_all_feature_bounds("heart")
            
            assert "age" in bounds
            assert bounds["age"]["min"] == 20
            assert bounds["age"]["max"] == 80
            assert bounds["age"]["mean"] == 50
            assert bounds["age"]["typical_low"] == 40
            assert bounds["age"]["typical_high"] == 60
