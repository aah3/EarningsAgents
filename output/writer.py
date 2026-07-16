"""
Output Writers for Earnings Prediction POC.

Supports Parquet (default) and CSV output formats.
"""

from datetime import date
from pathlib import Path
from typing import List, Dict, Any
import json
import logging

from config.settings import EarningsPrediction


class OutputWriter:
    """
    Simple output writer for predictions.
    
    Supports Parquet and CSV formats.
    
    Usage:
        writer = OutputWriter(output_dir="./output")
        writer.write_predictions(predictions, "weekly_predictions")
    """
    
    def __init__(self, output_dir: str = "./output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _prediction_to_dict(self, pred: EarningsPrediction) -> Dict[str, Any]:
        """Convert prediction to dictionary."""
        return {
            "ticker": pred.ticker,
            "company_name": pred.company_name,
            "report_date": pred.report_date.isoformat() if pred.report_date else None,
            "prediction_date": pred.prediction_date.isoformat() if pred.prediction_date else None,
            "direction": pred.direction.value,
            "confidence": pred.confidence,
            "reasoning_summary": pred.reasoning_summary,
            "bull_factors": json.dumps(pred.bull_factors),
            "bear_factors": json.dumps(pred.bear_factors),
            "agent_votes": json.dumps(pred.agent_votes) if pred.agent_votes else None,
            "debate_summary": pred.debate_summary,
        }
    
    def write_parquet(
        self,
        predictions: List[EarningsPrediction],
        filename: str
    ) -> Path:
        """
        Write predictions to Parquet file.
        
        Args:
            predictions: List of predictions
            filename: Output filename (without extension)
            
        Returns:
            Path to output file
        """
        import pandas as pd
        
        records = [self._prediction_to_dict(p) for p in predictions]
        df = pd.DataFrame(records)
        
        output_path = self.output_dir / f"{filename}.parquet"
        df.to_parquet(output_path, index=False)
        
        self.logger.info(f"Wrote {len(predictions)} predictions to {output_path}")
        return output_path
    
    def write_csv(
        self,
        predictions: List[EarningsPrediction],
        filename: str
    ) -> Path:
        """
        Write predictions to CSV file.
        
        Args:
            predictions: List of predictions
            filename: Output filename (without extension)
            
        Returns:
            Path to output file
        """
        import pandas as pd
        
        records = [self._prediction_to_dict(p) for p in predictions]
        df = pd.DataFrame(records)
        
        output_path = self.output_dir / f"{filename}.csv"
        df.to_csv(output_path, index=False)
        
        self.logger.info(f"Wrote {len(predictions)} predictions to {output_path}")
        return output_path
    
    def write_json(
        self,
        predictions: List[EarningsPrediction],
        filename: str
    ) -> Path:
        """
        Write predictions to JSON file.
        
        Args:
            predictions: List of predictions
            filename: Output filename (without extension)
            
        Returns:
            Path to output file
        """
        records = [self._prediction_to_dict(p) for p in predictions]
        
        output_path = self.output_dir / f"{filename}.json"
        with open(output_path, 'w') as f:
            json.dump(records, f, indent=2, default=str)
        
        self.logger.info(f"Wrote {len(predictions)} predictions to {output_path}")
        return output_path
    
    def write(
        self,
        predictions: List[EarningsPrediction],
        filename: str,
        format: str = "parquet"
    ) -> Path:
        """
        Write predictions to file.
        
        Args:
            predictions: List of predictions
            filename: Output filename (without extension)
            format: Output format (parquet, csv, json)
            
        Returns:
            Path to output file
        """
        if format == "parquet":
            return self.write_parquet(predictions, filename)
        elif format == "csv":
            return self.write_csv(predictions, filename)
        elif format == "json":
            return self.write_json(predictions, filename)
        else:
            raise ValueError(f"Unsupported format: {format}")
