"""
Batch prediction routes — CSV upload and bulk predictions.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Optional
from loguru import logger
import io

from app.core.security import get_current_user
from app.services.batch_prediction_service import batch_prediction_service

router = APIRouter()


@router.post("/predict/batch/{disease}")
async def batch_predict(
    disease: str,
    file: UploadFile = File(...),
    model_name: str = Form(default="best"),
    include_outliers: bool = Form(default=True),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a CSV file and get batch predictions.
    
    - disease: heart | diabetes | kidney
    - file: CSV file with patient records
    - model_name: Model to use for predictions
    - include_outliers: Whether to include outlier detection
    
    Returns predictions for each row with summary statistics.
    """
    if disease not in ("heart", "diabetes", "kidney"):
        raise HTTPException(status_code=400, detail=f"Unknown disease: {disease}")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Read file content
    content = await file.read()
    
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum 10MB allowed.")
    
    # Validate CSV
    is_valid, error, df = batch_prediction_service.validate_csv(content, disease)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    try:
        # Run predictions
        predictions = batch_prediction_service.predict_batch(
            df=df,
            disease=disease,
            model_name=model_name,
            include_outliers=include_outliers,
        )
        
        # Generate summary
        summary = batch_prediction_service.get_batch_summary(predictions)
        
        return {
            "status": "success",
            "disease": disease,
            "model_used": model_name,
            "summary": summary,
            "predictions": predictions,
        }
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Batch prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")


@router.post("/predict/batch/{disease}/download")
async def batch_predict_download(
    disease: str,
    file: UploadFile = File(...),
    model_name: str = Form(default="best"),
    include_outliers: bool = Form(default=True),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a CSV file and get predictions as a downloadable CSV.
    
    Returns a CSV file with original data plus prediction columns.
    """
    if disease not in ("heart", "diabetes", "kidney"):
        raise HTTPException(status_code=400, detail=f"Unknown disease: {disease}")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    content = await file.read()
    
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 10MB allowed.")
    
    is_valid, error, df = batch_prediction_service.validate_csv(content, disease)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    try:
        predictions = batch_prediction_service.predict_batch(
            df=df,
            disease=disease,
            model_name=model_name,
            include_outliers=include_outliers,
        )
        
        csv_content = batch_prediction_service.create_results_csv(df, predictions)
        
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={disease}_predictions.csv"
            }
        )
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Batch prediction download failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")


@router.get("/predict/batch/template/{disease}")
async def get_batch_template(
    disease: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get a CSV template with the required columns for batch prediction.
    """
    if disease not in ("heart", "diabetes", "kidney"):
        raise HTTPException(status_code=400, detail=f"Unknown disease: {disease}")
    
    try:
        from app.services.outlier_service import outlier_service
        
        stats = outlier_service.get_feature_stats(disease)
        headers = list(stats.keys())
        
        # Create template with headers and example values
        lines = [",".join(headers)]
        
        # Add example row with typical values
        example = []
        for feature in headers:
            if feature in stats:
                example.append(str(round(stats[feature]["mean"], 2)))
            else:
                example.append("0")
        lines.append(",".join(example))
        
        csv_content = "\n".join(lines)
        
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={disease}_template.csv"
            }
        )
        
    except Exception as e:
        logger.error(f"Template generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
