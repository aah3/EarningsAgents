import yfinance as yf
from datetime import timedelta, date, datetime
import logging
from typing import Optional

class PredictionScorer:
    def __init__(self, yahoo_source):
        self.yahoo = yahoo_source
        self.logger = logging.getLogger("PredictionScorer")
        
    def fetch_actual_direction(self, ticker: str, report_date: date) -> Optional[dict]:
        try:
            history = self.yahoo.get_historical_earnings(ticker, num_quarters=8)
        except Exception as e:
            self.logger.error(f"Error fetching historical earnings for {ticker}: {e}")
            return None
            
        for entry in history:
            entry_date = entry.date
            if isinstance(entry_date, datetime):
                entry_date = entry_date.date()
                
            report_d = report_date
            if isinstance(report_d, datetime):
                report_d = report_d.date()
                
            # within 7 calendar days
            delta = abs((entry_date - report_d).days)
            if delta <= 7:
                surprise = entry.surprise_pct or 0.0
                if surprise > 2.0:
                    overall_dir = "beat"
                elif surprise < -2.0:
                    overall_dir = "miss"
                else:
                    overall_dir = "meet"
                    
                return {
                    "actual_eps": entry.actual_eps,
                    "estimate_eps": entry.estimate_eps,
                    "surprise_pct": surprise,
                    "beat": surprise > 0,
                    "actual_direction": overall_dir
                }
        return None

    def fetch_price_move(self, ticker: str, report_date: date) -> Optional[float]:
        try:
            report_d = report_date
            if isinstance(report_d, datetime):
                report_d = report_d.date()
                
            end_date = report_d + timedelta(days=5)
            df = yf.download(ticker, start=report_d, end=end_date, progress=False)
            
            if df is None or len(df) < 2:
                return None
                
            day0_close = float(df['Close'].iloc[0].item() if hasattr(df['Close'].iloc[0], 'item') else df['Close'].iloc[0])
            day1_close = float(df['Close'].iloc[1].item() if hasattr(df['Close'].iloc[1], 'item') else df['Close'].iloc[1])
            
            return (day1_close - day0_close) / day0_close
        except Exception as e:
            self.logger.error(f"Error fetching price move for {ticker}: {e}")
            return None

    def compute_brier_score(self, predicted_direction: str, confidence: float, actual_direction: str) -> float:
        correct = 1.0 if predicted_direction.lower() == actual_direction.lower() else 0.0
        return round((float(confidence) / 100.0 - correct) ** 2, 6)

    def score_prediction(self, prediction) -> dict:
        actual_data = self.fetch_actual_direction(prediction.ticker, prediction.report_date)
        if actual_data is None:
            return {"scored": False, "reason": "Actual EPS not yet available"}
        
        price_move = self.fetch_price_move(prediction.ticker, prediction.report_date)
        accuracy = self.compute_brier_score(prediction.direction, prediction.confidence, actual_data["actual_direction"])
        
        return {
            "scored": True,
            "actual_direction": actual_data["actual_direction"],
            "actual_eps": actual_data["actual_eps"],
            "actual_price_move_pct": price_move,
            "accuracy_score": accuracy,
            "scored_at": datetime.utcnow()
        }
