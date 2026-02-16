from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import date
from typing import List, Optional
from pydantic import BaseModel
import sys
import os

# Add the project root to sys.path to import existing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from pipeline import EarningsPipeline
from config.settings import PipelineConfig, load_config

router = APIRouter(
    prefix="/earnings",
    tags=["earnings"],
)

# Initialize pipeline as a singleton-like object for the router
# In a real app, this would be handled via a dependency or lifecycle event
_pipeline_instance = None

def get_pipeline():
    global _pipeline_instance
    if _pipeline_instance is None:
        config = load_config()
        # Ensure output dir is manageable
        config.output_dir = "api_output"
        _pipeline_instance = EarningsPipeline(config)
        _pipeline_instance.initialize()
    return _pipeline_instance

@router.get("/predict/{ticker}")
async def predict_ticker(
    ticker: str, 
    report_date: date,
    pipeline: EarningsPipeline = Depends(get_pipeline),
    user_id: str = Depends(get_current_user)
):
    try:
        # In the future, we will use user_id to associate prediction with the user
        prediction = pipeline.predict_single(ticker, report_date)
        return prediction
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/weekly")
async def get_weekly_predictions(
    week_start: date,
    pipeline: EarningsPipeline = Depends(get_pipeline)
):
    try:
        predictions = pipeline.run_weekly(week_start)
        return predictions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health():
    return {"status": "Earnings router is up"}
