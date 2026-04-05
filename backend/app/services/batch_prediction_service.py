"""
Batch Prediction Service — handles CSV upload and bulk predictions.
"""

import io
import csv
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from loguru import logger

from app.services.prediction_service import prediction_service
from app.services.outlier_service import outlier_service


class BatchPredictionService:
    """Handles batch predictions from CSV files."""

    def validate_csv(
        self,
        file_content: bytes,
        disease: str,
    ) -> Tuple[bool, Optional[str], Optional[pd.DataFrame]]:
        """
        Validate CSV file structure and content.
        
        Returns:
            Tuple of (is_valid, error_message, dataframe)
        """
        try:
            # Try to parse CSV
            df = pd.read_csv(io.BytesIO(file_content))
            
            if df.empty:
                return False, "CSV file is empty", None
            
            if len(df) > 10000:
                return False, "Maximum 10,000 rows allowed per batch", None
            
            # Get expected features
            stats = outlier_service.get_feature_stats(disease)
            expected_features = set(stats.keys())
            
            # Normalize column names
            df.columns = [c.lower().replace("-", "_").replace(" ", "_") for c in df.columns]
            actual_features = set(df.columns)
            
            # Check for required features
            expected_normalized = {f.lower().replace("-", "_").replace(" ", "_") for f in expected_features}
            missing = expected_normalized - actual_features
            
            if missing and len(missing) > len(expected_normalized) * 0.3:
                return False, f"Missing too many required features: {', '.join(list(missing)[:5])}...", None
            
            return True, None, df
            
        except Exception as e:
            return False, f"Failed to parse CSV: {str(e)}", None

    def predict_batch(
        self,
        df: pd.DataFrame,
        disease: str,
        model_name: str = "best",
        include_outliers: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Run predictions on a batch of records.
        
        Args:
            df: DataFrame with patient records
            disease: Disease type
            model_name: Model to use
            include_outliers: Whether to check for outliers
            
        Returns:
            List of prediction results
        """
        results = []
        total = len(df)
        
        for idx, row in df.iterrows():
            try:
                input_data = row.to_dict()
                
                # Run prediction
                pred_result = prediction_service.predict(
                    disease=disease,
                    input_data=input_data,
                    model_name=model_name,
                    explain=False,  # Skip explanations for batch
                )
                
                result = {
                    "row_index": idx,
                    "prediction": pred_result.prediction,
                    "label": pred_result.label,
                    "confidence": pred_result.confidence,
                    "probability_positive": pred_result.probability.get(
                        list(pred_result.probability.keys())[1], 0
                    ),
                    "status": "success",
                }
                
                # Check for outliers
                if include_outliers:
                    outliers = outlier_service.detect_outliers(disease, input_data)
                    result["outlier_count"] = len(outliers)
                    result["has_outliers"] = len(outliers) > 0
                
                results.append(result)
                
            except Exception as e:
                logger.warning(f"Batch prediction failed for row {idx}: {e}")
                results.append({
                    "row_index": idx,
                    "status": "error",
                    "error": str(e),
                })
        
        return results

    def create_results_csv(
        self,
        original_df: pd.DataFrame,
        predictions: List[Dict[str, Any]],
    ) -> str:
        """
        Create CSV output with original data plus predictions.
        
        Returns:
            CSV string content
        """
        # Create results DataFrame
        pred_df = pd.DataFrame(predictions)
        
        # Merge with original data
        result_df = original_df.copy()
        result_df['prediction'] = pred_df['prediction']
        result_df['prediction_label'] = pred_df['label']
        result_df['confidence'] = pred_df['confidence']
        result_df['probability_positive'] = pred_df.get('probability_positive', 0)
        result_df['has_outliers'] = pred_df.get('has_outliers', False)
        result_df['prediction_status'] = pred_df['status']
        
        # Convert to CSV
        output = io.StringIO()
        result_df.to_csv(output, index=False)
        return output.getvalue()

    def get_batch_summary(
        self,
        predictions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate summary statistics for batch predictions."""
        successful = [p for p in predictions if p.get("status") == "success"]
        failed = [p for p in predictions if p.get("status") == "error"]
        
        positive = [p for p in successful if p.get("prediction") == 1]
        negative = [p for p in successful if p.get("prediction") == 0]
        with_outliers = [p for p in successful if p.get("has_outliers")]
        
        avg_confidence = (
            sum(p.get("confidence", 0) for p in successful) / len(successful)
            if successful else 0
        )
        
        return {
            "total_records": len(predictions),
            "successful": len(successful),
            "failed": len(failed),
            "positive_predictions": len(positive),
            "negative_predictions": len(negative),
            "positive_rate": len(positive) / len(successful) if successful else 0,
            "average_confidence": avg_confidence,
            "records_with_outliers": len(with_outliers),
            "outlier_rate": len(with_outliers) / len(successful) if successful else 0,
        }


# Singleton
batch_prediction_service = BatchPredictionService()
