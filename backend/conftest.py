"""
Pytest configuration and shared fixtures.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import MagicMock, patch, AsyncMock
import numpy as np
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))


# ─── Async Event Loop ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ─── Mock User ───────────────────────────────────────────────────────────────

@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "sub": "1",
        "username": "testuser",
        "email": "test@example.com",
        "role": "user",
    }


@pytest.fixture
def mock_admin():
    """Mock admin user."""
    return {
        "sub": "1",
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
    }


# ─── Sample Input Data ───────────────────────────────────────────────────────

@pytest.fixture
def heart_input_data():
    """Sample heart disease prediction input."""
    return {
        "age": 54,
        "sex": 1,
        "cp": 2,
        "trestbps": 130,
        "chol": 250,
        "fbs": 0,
        "restecg": 0,
        "thalach": 150,
        "exang": 0,
        "oldpeak": 1.5,
        "slope": 1,
        "ca": 0,
        "thal": 2,
    }


@pytest.fixture
def diabetes_input_data():
    """Sample diabetes prediction input."""
    return {
        "pregnancies": 2,
        "glucose": 120,
        "blood_pressure": 70,
        "skin_thickness": 20,
        "insulin": 80,
        "bmi": 28.5,
        "diabetes_pedigree": 0.45,
        "age": 33,
    }


@pytest.fixture
def kidney_input_data():
    """Sample kidney disease prediction input."""
    return {
        "age": 50,
        "blood_pressure": 80,
        "specific_gravity": 1.015,
        "albumin": 1,
        "sugar": 0,
        "red_blood_cells": 1,
        "pus_cell": 1,
        "pus_cell_clumps": 0,
        "bacteria": 0,
        "blood_glucose_random": 120,
        "blood_urea": 40,
        "serum_creatinine": 1.2,
        "sodium": 140,
        "potassium": 4.5,
        "haemoglobin": 14,
        "packed_cell_volume": 44,
        "white_blood_cell_count": 8000,
        "red_blood_cell_count": 5.0,
        "hypertension": 0,
        "diabetes_mellitus": 0,
        "coronary_artery_disease": 0,
        "appetite": 1,
        "pedal_edema": 0,
        "anemia": 0,
    }


# ─── Mock Model ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_classifier():
    """Mock trained classifier."""
    clf = MagicMock()
    clf.predict.return_value = np.array([0])
    clf.predict_proba.return_value = np.array([[0.7, 0.3]])
    clf.feature_importances_ = np.array([0.1, 0.2, 0.15, 0.05, 0.5])
    return clf


# ─── Mock Database ───────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db
