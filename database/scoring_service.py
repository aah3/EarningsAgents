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
                
            ticker = ticker.strip().upper()
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
                        if hasattr(val, 'get') and val.get(ticker) is not None:
                            val = val.get(ticker)
                        elif hasattr(val, 'get') and val.get(ticker.upper()) is not None:
                            val = val.get(ticker.upper())
                        elif hasattr(val, 'iloc') and len(val) > 0:
                            val = val.iloc[0]
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
            if not report_day_actual:
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

    def evaluate_vol_stance(self, prediction, actual_move_pct: Optional[float]) -> Optional[bool]:
        if actual_move_pct is None:
            return None
            
        move_vs_implied = (getattr(prediction, "move_vs_implied", "") or "").lower()
        options_features = getattr(prediction, "options_features", None) or {}
        
        implied_move_pct = None
        if isinstance(options_features, dict):
            implied_move_pct = options_features.get("implied_move_pct") or options_features.get("implied_move")
            if implied_move_pct is not None:
                try:
                    implied_move_pct = float(implied_move_pct)
                    if implied_move_pct > 1.0:
                        implied_move_pct = implied_move_pct / 100.0
                except (ValueError, TypeError):
                    implied_move_pct = None
                    
        if implied_move_pct is None and move_vs_implied:
            import re
            match = re.search(r'(\d+(?:\.\d+)?)\s*%', move_vs_implied)
            if match:
                implied_move_pct = float(match.group(1)) / 100.0

        abs_actual_move = abs(actual_move_pct)
        
        if any(kw in move_vs_implied for kw in ["over", "above", "exceed", "larger"]):
            if implied_move_pct is not None:
                return abs_actual_move > implied_move_pct
            return abs_actual_move > 0.04
        elif any(kw in move_vs_implied for kw in ["under", "below", "compress", "smaller"]):
            if implied_move_pct is not None:
                return abs_actual_move <= implied_move_pct
            return abs_actual_move <= 0.04
        elif any(kw in move_vs_implied for kw in ["in-line", "inline", "near", "flat"]):
            if implied_move_pct is not None:
                return abs(abs_actual_move - implied_move_pct) <= 0.015
            return abs_actual_move <= 0.03
            
        if implied_move_pct is not None:
            return abs(abs_actual_move - implied_move_pct) <= 0.02
        return None

    def evaluate_price_direction(self, prediction, actual_move_pct: Optional[float], noise_buffer: float = 0.005) -> Optional[bool]:
        if actual_move_pct is None:
            return None
            
        expected_move_str = (getattr(prediction, "expected_price_move", "") or "").lower()
        predicted_dir = (getattr(prediction, "direction", "") or "").lower()
        
        expected_sign = None
        if any(kw in expected_move_str for kw in ["positive", "+", "up", "bull"]):
            expected_sign = 1
        elif any(kw in expected_move_str for kw in ["negative", "-", "down", "bear"]):
            expected_sign = -1
        elif any(kw in expected_move_str for kw in ["flat", "neutral"]):
            expected_sign = 0
            
        if expected_sign is None:
            if predicted_dir == "beat":
                expected_sign = 1
            elif predicted_dir == "miss":
                expected_sign = -1
            else:
                expected_sign = 0
                
        if abs(actual_move_pct) < noise_buffer:
            actual_sign = 0
        else:
            actual_sign = 1 if actual_move_pct > 0 else -1
            
        return expected_sign == actual_sign

    def evaluate_guidance_stance(self, prediction, actual_guidance_stance: Optional[str] = None) -> tuple[Optional[str], Optional[bool]]:
        guidance_exp = (getattr(prediction, "guidance_expectation", "") or getattr(prediction, "likely_guidance", "") or "").lower()
        
        expected_stance = None
        if any(kw in guidance_exp for kw in ["raise", "upward", "bull", "positive", "beat", "strong"]):
            expected_stance = "RAISED"
        elif any(kw in guidance_exp for kw in ["lower", "downward", "bear", "subdued", "cut", "weak"]):
            expected_stance = "LOWERED"
        elif any(kw in guidance_exp for kw in ["reaffirm", "inline", "in-line", "maintain", "flat"]):
            expected_stance = "REAFFIRMED"

        if actual_guidance_stance:
            norm_actual = actual_guidance_stance.upper()
        else:
            actual_dir = getattr(prediction, "actual_direction", None)
            if actual_dir == "beat":
                norm_actual = "RAISED"
            elif actual_dir == "miss":
                norm_actual = "LOWERED"
            else:
                norm_actual = "REAFFIRMED"

        if expected_stance is None:
            return norm_actual, None
            
        return norm_actual, (expected_stance == norm_actual)

    def compute_composite_score(self, brier: float, vol_hit: Optional[bool], dir_hit: Optional[bool], guidance_hit: Optional[bool]) -> float:
        components = []
        brier_pts = max(0.0, min(100.0, (1.0 - brier) * 100.0))
        components.append((brier_pts, 0.30))

        if vol_hit is not None:
            components.append((100.0 if vol_hit else 0.0, 0.30))
            
        if dir_hit is not None:
            components.append((100.0 if dir_hit else 0.0, 0.20))

        if guidance_hit is not None:
            components.append((100.0 if guidance_hit else 0.0, 0.20))

        total_weight = sum(w for _, w in components)
        if total_weight == 0:
            return round(brier_pts, 2)
            
        weighted_score = sum(pts * w for pts, w in components) / total_weight
        return round(weighted_score, 2)

    def score_prediction(self, prediction) -> dict:
        actual_data = self.fetch_actual_direction(prediction.ticker, prediction.report_date)
        if actual_data is None:
            if getattr(prediction, "actual_direction", None) is not None:
                actual_data = {
                    "actual_direction": prediction.actual_direction,
                    "actual_eps": getattr(prediction, "actual_eps", None),
                }
            else:
                return {"scored": False, "reason": "Actual EPS not yet available"}
        
        report_timing = getattr(prediction, "report_timing", "UNKNOWN")
        price_move = self.fetch_price_move(prediction.ticker, prediction.report_date, report_timing)
        accuracy = self.compute_brier_score(prediction.direction, prediction.confidence, actual_data["actual_direction"])
        
        vol_hit = self.evaluate_vol_stance(prediction, price_move)
        dir_hit = self.evaluate_price_direction(prediction, price_move)
        act_guidance, guidance_hit = self.evaluate_guidance_stance(prediction)
        
        # Calculate magnitude error if expected_price_move has numeric %
        mag_error = None
        if price_move is not None:
            expected_str = getattr(prediction, "expected_price_move", "") or ""
            import re
            m = re.search(r'(\d+(?:\.\d+)?)\s*%', expected_str)
            if m:
                expected_val = float(m.group(1)) / 100.0
                mag_error = round(abs(abs(price_move) - expected_val), 4)

        composite_score = self.compute_composite_score(accuracy, vol_hit, dir_hit, guidance_hit)
        
        return {
            "scored": True,
            "actual_direction": actual_data["actual_direction"],
            "actual_eps": actual_data["actual_eps"],
            "actual_price_move_pct": price_move,
            "accuracy_score": accuracy,
            "vol_stance_hit": vol_hit,
            "price_dir_hit": dir_hit,
            "guidance_stance_hit": guidance_hit,
            "magnitude_error_pct": mag_error,
            "actual_guidance_stance": act_guidance,
            "composite_accuracy_score": composite_score,
            "scored_at": datetime.utcnow()
        }
