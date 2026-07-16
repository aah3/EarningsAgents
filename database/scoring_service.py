import yfinance as yf
from datetime import timedelta, date, datetime
import logging
from typing import Optional
import math

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

    def fetch_price_move(self, ticker: str, report_date: date, report_timing: Optional[str] = "UNKNOWN") -> Optional[float]:
        try:
            report_d = report_date
            if isinstance(report_d, datetime):
                report_d = report_d.date()
                
            timing = (report_timing or "UNKNOWN").upper()
            
            # Fetch a wider range of daily prices to calculate yesterday-close-to-close or close-to-tomorrow-close
            start_date = report_d - timedelta(days=7)
            end_date = report_d + timedelta(days=7)
            
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if df is None or df.empty:
                df = yf.Ticker(ticker).history(start=start_date, end=end_date, interval="1d")
                
            closes = {}
            if df is not None and not df.empty:
                for idx, row in df.iterrows():
                    d = idx.date() if hasattr(idx, 'date') else idx
                    val = row['Close']
                    if isinstance(val, (dict, list, tuple)) or hasattr(val, 'keys'):
                        val = val[ticker]
                    if val is not None and not math.isnan(val):
                        closes[d] = float(val)
                        
            # Find the actual trading day on or after report_d
            all_dates = sorted(list(closes.keys()))
            report_day_actual = None
            for d in all_dates:
                if d >= report_d:
                    report_day_actual = d
                    break
                    
            prior_day_actual = None
            if report_day_actual and report_day_actual in all_dates:
                idx = all_dates.index(report_day_actual)
                if idx - 1 >= 0:
                    prior_day_actual = all_dates[idx - 1]
                    
            next_day_actual = None
            if report_day_actual and report_day_actual in all_dates:
                idx = all_dates.index(report_day_actual)
                if idx + 1 < len(all_dates):
                    next_day_actual = all_dates[idx + 1]
                    
            # Check if any required date close price is missing
            need_hourly = False
            if report_d not in closes:
                need_hourly = True
            elif timing == "AMC" and (not next_day_actual or next_day_actual not in closes):
                need_hourly = True
            elif timing != "AMC" and (not prior_day_actual or prior_day_actual not in closes):
                need_hourly = True
                
            if need_hourly:
                self.logger.info(f"Required close price is missing in daily data for {ticker}. Fetching hourly data fallback...")
                ticker_obj = yf.Ticker(ticker)
                h_df = ticker_obj.history(start=start_date, end=end_date + timedelta(days=2), interval="1h")
                if not h_df.empty:
                    h_df['DateOnly'] = h_df.index.map(lambda x: x.date())
                    for d, group in h_df.groupby('DateOnly'):
                        last_row = group.iloc[-1]
                        closes[d] = float(last_row['Close'])
                        
            # Recalculate trading days with updated closes
            all_dates = sorted(list(closes.keys()))
            report_day_actual = None
            for d in all_dates:
                if d >= report_d:
                    report_day_actual = d
                    break
                    
            if not report_day_actual:
                self.logger.warning(f"Could not find trading day on or after {report_d} for {ticker}")
                return None
                
            if timing == "AMC":
                # AMC (After Market Close) reaction: report close to next close
                idx = all_dates.index(report_day_actual)
                if idx + 1 >= len(all_dates):
                    self.logger.warning(f"Next trading day after {report_day_actual} not available yet for {ticker}")
                    return None
                day0_close = closes[report_day_actual]
                day1_close = closes[all_dates[idx + 1]]
            else:
                # BMO (Before Market Open) or UNKNOWN: prior close to report close
                idx = all_dates.index(report_day_actual)
                if idx - 1 < 0:
                    self.logger.warning(f"Prior trading day before {report_day_actual} not found for {ticker}")
                    return None
                day0_close = closes[all_dates[idx - 1]]
                day1_close = closes[report_day_actual]
                
            if day0_close == 0:
                return 0.0
            return (day1_close - day0_close) / day0_close
        except Exception as e:
            self.logger.error(f"Error fetching price move for {ticker}: {e}")
            return None

    def compute_brier_score(self, predicted_direction: str, confidence: float, actual_direction: str) -> float:
        correct = 1.0 if predicted_direction.lower() == actual_direction.lower() else 0.0
        # DB stores confidence as fraction 0.0-1.0 (e.g. 0.78). If > 1.0, convert from 0-100 scale.
        c = float(confidence)
        if c > 1.0:
            c /= 100.0
        return round((c - correct) ** 2, 6)

    def score_prediction(self, prediction) -> dict:
        actual_data = self.fetch_actual_direction(prediction.ticker, prediction.report_date)
        if actual_data is None:
            return {"scored": False, "reason": "Actual EPS not yet available"}
        
        report_timing = getattr(prediction, "report_timing", "UNKNOWN")
        price_move = self.fetch_price_move(prediction.ticker, prediction.report_date, report_timing)
        accuracy = self.compute_brier_score(prediction.direction, prediction.confidence, actual_data["actual_direction"])
        
        return {
            "scored": True,
            "actual_direction": actual_data["actual_direction"],
            "actual_eps": actual_data["actual_eps"],
            "actual_price_move_pct": price_move,
            "accuracy_score": accuracy,
            "scored_at": datetime.utcnow()
        }
