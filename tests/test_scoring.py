from datetime import date, datetime
import pytest
from database.scoring_service import PredictionScorer
from data.yahoo_finance import YahooFinanceDataSource, DataSourceConfig
from dataclasses import dataclass

@dataclass
class FakePrediction:
    ticker: str
    report_date: date
    direction: str
    confidence: float
    report_timing: str

def test_fetch_price_move_fallback_bmo():
    config = DataSourceConfig(rate_limit_calls=100, rate_limit_period=60)
    yahoo = YahooFinanceDataSource(config)
    yahoo.connect()
    scorer = PredictionScorer(yahoo)
    
    # JPM reported BMO on 2026-07-14.
    # Daily data for 2026-07-14 is missing/None in yfinance API, triggering hourly fallback.
    # Prior close (2026-07-13): ~334.59
    # Report close (2026-07-14): ~343.04
    # Return: ~2.53%
    move = scorer.fetch_price_move("JPM", date(2026, 7, 14), "BMO")
    assert move is not None
    assert abs(move - 0.025255) < 0.005
    yahoo.disconnect()

def test_fetch_price_move_fallback_amc():
    config = DataSourceConfig(rate_limit_calls=100, rate_limit_period=60)
    yahoo = YahooFinanceDataSource(config)
    yahoo.connect()
    scorer = PredictionScorer(yahoo)
    
    # JPM AMC on 2026-07-14.
    # Report close (2026-07-14): ~343.04
    # Next close (2026-07-15): ~346.06
    # Return: (346.059998 - 343.040009) / 343.040009 = ~0.88%
    move = scorer.fetch_price_move("JPM", date(2026, 7, 14), "AMC")
    assert move is not None
    assert abs(move - 0.008803) < 0.005
    yahoo.disconnect()

def test_score_prediction_with_mock():
    # Verify that the scorer works correctly when scoring a prediction
    @dataclass
    class FakeEarning:
        date: date
        actual_eps: float
        estimate_eps: float
        surprise_pct: float
        beat: bool

    class FakeYahoo:
        def get_historical_earnings(self, ticker, num_quarters=8):
            return [FakeEarning(
                date=date(2026, 7, 14),
                actual_eps=6.14,
                estimate_eps=5.8,
                surprise_pct=5.86,
                beat=True
            )]

    scorer = PredictionScorer(FakeYahoo())
    
    # Monkeypatch fetch_price_move to avoid hitting network in this mock test
    scorer.fetch_price_move = lambda t, rd, rt: 0.025255
    
    pred = FakePrediction(
        ticker="JPM",
        report_date=date(2026, 7, 14),
        direction="BEAT",
        confidence=75.0,
        report_timing="BMO"
    )
    
    result = scorer.score_prediction(pred)
    assert result["scored"] is True
    assert result["actual_direction"] == "beat"
    assert result["actual_eps"] == 6.14
    assert result["actual_price_move_pct"] == 0.025255
    assert result["accuracy_score"] == (0.75 - 1.0) ** 2
