"""
Integration tests for API routes.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import numpy as np


@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    from app.main import app
    
    # Mock authentication
    with patch('app.core.security.get_current_user') as mock_auth:
        mock_auth.return_value = {
            "sub": "1",
            "username": "testuser",
            "role": "user",
        }
        
        with TestClient(app) as client:
            yield client


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    @pytest.mark.unit
    def test_root_returns_status(self, client):
        """Test root endpoint returns status."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "app" in data
    
    @pytest.mark.unit
    def test_health_returns_healthy(self, client):
        """Test health endpoint returns healthy status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAnalyticsEndpoints:
    """Tests for analytics API endpoints."""
    
    @pytest.mark.integration
    def test_outlier_check_endpoint(self, client, heart_input_data):
        """Test outlier check endpoint."""
        with patch('app.services.outlier_service.outlier_service') as mock_service:
            mock_service.detect_outliers.return_value = []
            mock_service.get_feature_stats.return_value = {"age": {}}
            
            response = client.post(
                "/api/analytics/outliers/check",
                json={
                    "disease": "heart",
                    "input_data": heart_input_data,
                    "z_threshold": 3.0,
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "has_outliers" in data
            assert "alerts" in data
    
    @pytest.mark.integration
    def test_outlier_check_rejects_invalid_disease(self, client, heart_input_data):
        """Test outlier check rejects invalid disease."""
        response = client.post(
            "/api/analytics/outliers/check",
            json={
                "disease": "invalid",
                "input_data": heart_input_data,
            }
        )
        
        assert response.status_code == 400
        assert "Unknown disease" in response.json()["detail"]
    
    @pytest.mark.integration
    def test_feature_bounds_endpoint(self, client):
        """Test feature bounds endpoint."""
        with patch('app.services.outlier_service.outlier_service') as mock_service:
            mock_service.get_all_feature_bounds.return_value = {
                "age": {"min": 20, "max": 80, "mean": 50}
            }
            
            response = client.get("/api/analytics/outliers/bounds/heart")
            
            assert response.status_code == 200
            data = response.json()
            assert data["disease"] == "heart"
            assert "bounds" in data
    
    @pytest.mark.integration
    def test_lime_status_endpoint(self, client):
        """Test LIME status endpoint."""
        response = client.get("/api/analytics/lime/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "available" in data
    
    @pytest.mark.integration
    def test_feature_importance_endpoint(self, client, mock_classifier):
        """Test feature importance endpoint."""
        with patch('app.services.performance_curves_service.performance_curves_service') as mock_service:
            mock_service.get_feature_importance.return_value = {
                "age": 0.3,
                "glucose": 0.25,
                "bmi": 0.2,
            }
            
            response = client.get("/api/analytics/importance/heart")
            
            assert response.status_code == 200
            data = response.json()
            assert "importance" in data
            assert "importance_list" in data


class TestPredictionEndpoints:
    """Tests for prediction API endpoints."""
    
    @pytest.mark.integration
    def test_predict_endpoint_requires_auth(self):
        """Test that predict endpoint requires authentication."""
        from app.main import app
        
        # Without auth mock
        with TestClient(app) as client:
            response = client.post(
                "/api/predict/heart",
                json={
                    "disease": "heart",
                    "model_name": "best",
                    "input_data": {"age": 54},
                }
            )
            
            # Should fail with 401 or 403
            assert response.status_code in [401, 403, 422]
    
    @pytest.mark.integration
    def test_predict_rejects_invalid_disease(self, client):
        """Test that predict rejects invalid disease."""
        response = client.post(
            "/api/predict/invalid",
            json={
                "disease": "invalid",
                "model_name": "best",
                "input_data": {},
            }
        )
        
        assert response.status_code == 400


class TestBatchEndpoints:
    """Tests for batch prediction endpoints."""
    
    @pytest.mark.integration
    def test_batch_template_endpoint(self, client):
        """Test batch template download."""
        with patch('app.services.outlier_service.outlier_service') as mock_service:
            mock_service.get_feature_stats.return_value = {
                "age": {"mean": 50},
                "sex": {"mean": 0.5},
            }
            
            response = client.get("/api/predict/batch/template/heart")
            
            assert response.status_code == 200
            assert "text/csv" in response.headers["content-type"]
    
    @pytest.mark.integration
    def test_batch_upload_rejects_non_csv(self, client):
        """Test that batch upload rejects non-CSV files."""
        response = client.post(
            "/api/predict/batch/heart",
            files={"file": ("test.txt", b"not a csv", "text/plain")},
            data={"model_name": "best"},
        )
        
        assert response.status_code == 400
        assert "CSV" in response.json()["detail"]
