"""Report routes: GET /report/download"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pathlib import Path
from loguru import logger

from app.core.security import require_admin, get_current_user
from app.services.report_service import report_generator
from app.core.config import settings

router = APIRouter()


@router.get("/report/download")
async def download_report(current_user: dict = Depends(get_current_user)):
    """Generate and download a PDF report of all model evaluations."""
    try:
        filepath = report_generator.generate()
        if not Path(filepath).exists():
            raise HTTPException(status_code=500, detail="Report generation failed")
        return FileResponse(
            path=filepath,
            media_type="application/pdf",
            filename=Path(filepath).name,
            headers={"Content-Disposition": f"attachment; filename={Path(filepath).name}"},
        )
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/report/list")
async def list_reports(current_user: dict = Depends(get_current_user)):
    """List all generated reports."""
    report_dir = Path(settings.REPORT_SAVE_PATH)
    if not report_dir.exists():
        return {"reports": []}
    reports = sorted(report_dir.glob("mdps_report_*.pdf"), reverse=True)
    return {
        "reports": [
            {"filename": r.name, "size_kb": round(r.stat().st_size / 1024, 1)}
            for r in reports
        ]
    }
