"""
Longitudinal Tracking API routes — patient history and trend analysis.

Provides endpoints for:
- Recording patient visits
- Retrieving patient history
- Trend analysis and alerts
- Timeline visualization data
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from loguru import logger

from app.services.longitudinal_service import longitudinal_service, generate_demo_patient


router = APIRouter(prefix="/patients", tags=["Patient Tracking"])


# ==================== SCHEMAS ====================

class RecordVisitRequest(BaseModel):
    """Request to record a patient visit."""
    patient_id: str = Field(..., min_length=1, max_length=50)
    predictions: Dict[str, Any]
    patient_data: Dict[str, Any]
    visit_notes: Optional[str] = None


class CompareVisitsRequest(BaseModel):
    """Request to compare two visits."""
    patient_id: str
    visit_id_1: str
    visit_id_2: str


# ==================== ENDPOINTS ====================

@router.post("/visits")
async def record_visit(request: RecordVisitRequest) -> Dict[str, Any]:
    """
    Record a patient visit with predictions.
    
    Stores visit data for longitudinal tracking.
    """
    try:
        visit = longitudinal_service.record_visit(
            patient_id=request.patient_id,
            predictions=request.predictions,
            patient_data=request.patient_data,
            visit_notes=request.visit_notes
        )
        return {
            "status": "success",
            "data": visit
        }
    except Exception as e:
        logger.error(f"Failed to record visit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{patient_id}/history")
async def get_patient_history(
    patient_id: str,
    limit: Optional[int] = Query(None, ge=1, le=100)
) -> Dict[str, Any]:
    """
    Get complete visit history for a patient.
    
    Returns all visits with trend analysis.
    """
    history = longitudinal_service.get_patient_history(patient_id, limit)
    return {
        "status": "success",
        "data": history
    }


@router.get("/{patient_id}/trends")
async def analyze_trends(
    patient_id: str,
    window_size: int = Query(5, ge=2, le=20)
) -> Dict[str, Any]:
    """
    Analyze risk trends for a patient.
    
    Returns trend direction, alerts, and summary.
    """
    analysis = longitudinal_service.analyze_trends(patient_id, window_size)
    return {
        "status": "success",
        "data": analysis
    }


@router.get("/{patient_id}/timeline")
async def get_timeline_data(patient_id: str) -> Dict[str, Any]:
    """
    Get formatted timeline data for visualization.
    
    Returns data structured for charting libraries.
    """
    timeline = longitudinal_service.get_timeline_data(patient_id)
    return {
        "status": "success",
        "data": timeline
    }


@router.post("/compare-visits")
async def compare_visits(request: CompareVisitsRequest) -> Dict[str, Any]:
    """Compare two specific visits for a patient."""
    comparison = longitudinal_service.compare_visits(
        patient_id=request.patient_id,
        visit_id_1=request.visit_id_1,
        visit_id_2=request.visit_id_2
    )
    
    if "error" in comparison:
        raise HTTPException(status_code=404, detail=comparison["error"])
    
    return {
        "status": "success",
        "data": comparison
    }


@router.get("/")
async def list_patients(
    limit: int = Query(100, ge=1, le=500)
) -> Dict[str, Any]:
    """List all tracked patients with summary info."""
    patients = longitudinal_service.list_patients(limit)
    return {
        "status": "success",
        "data": patients,
        "total": len(patients)
    }


@router.delete("/{patient_id}")
async def delete_patient(patient_id: str) -> Dict[str, Any]:
    """Delete all data for a patient."""
    deleted = longitudinal_service.delete_patient(patient_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return {
        "status": "success",
        "message": f"Patient {patient_id} data deleted"
    }


@router.post("/demo/generate")
async def generate_demo_data(
    patient_id: str = Query("demo-patient-001")
) -> Dict[str, Any]:
    """Generate demo patient with historical visits for testing."""
    try:
        history = generate_demo_patient(patient_id)
        return {
            "status": "success",
            "message": f"Generated demo data for {patient_id}",
            "data": history
        }
    except Exception as e:
        logger.error(f"Failed to generate demo data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
