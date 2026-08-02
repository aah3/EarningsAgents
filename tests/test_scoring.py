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

def test_fetch_price_move_timing_normalization():
    config = DataSourceConfig(rate_limit_calls=100, rate_limit_period=60)
    yahoo = YahooFinanceDataSource(config)
    yahoo.connect()
    scorer = PredictionScorer(yahoo)
    
    # Test normalized timing strings: "AFTER_MARKET" should evaluate same as "AMC"
    move_amc = scorer.fetch_price_move("JPM", date(2026, 7, 14), "AFTER_MARKET")
    assert move_amc is not None
    assert abs(move_amc - 0.008803) < 0.005

    # "BEFORE_MARKET" should evaluate same as "BMO"
    move_bmo = scorer.fetch_price_move("JPM", date(2026, 7, 14), "BEFORE_MARKET")
    assert move_bmo is not None
    assert abs(move_bmo - 0.025255) < 0.005
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
    assert "vol_stance_hit" in result
    assert "price_dir_hit" in result
    assert "guidance_stance_hit" in result
    assert "composite_accuracy_score" in result

def test_evaluate_multi_factor_metrics():
    @dataclass
    class ExtendedFakePrediction:
        ticker: str
        report_date: date
        direction: str
        confidence: float
        report_timing: str
        expected_price_move: str
        move_vs_implied: str
        guidance_expectation: str
        options_features: dict

    class FakeYahoo:
        pass

    scorer = PredictionScorer(FakeYahoo())

    pred = ExtendedFakePrediction(
        ticker="AAPL",
        report_date=date(2026, 7, 14),
        direction="BEAT",
        confidence=80.0,
        report_timing="AMC",
        expected_price_move="Positive move (+4.5%)",
        move_vs_implied="Over-implied (expect move > 3.0%)",
        guidance_expectation="Raised FY Guidance",
        options_features={"implied_move_pct": 3.0}
    )

    # 1. Vol stance hit: actual move +5.0% (> 3.0% implied) -> True
    vol_hit = scorer.evaluate_vol_stance(pred, 0.05)
    assert vol_hit is True

    # 2. Vol stance miss: actual move +2.0% (<= 3.0% implied when predicting over-implied) -> False
    vol_miss = scorer.evaluate_vol_stance(pred, 0.02)
    assert vol_miss is False

    # 3. Price direction hit: expected positive (+4.5%), actual move +5.0% -> True
    dir_hit = scorer.evaluate_price_direction(pred, 0.05)
    assert dir_hit is True

    # 4. Price direction miss: expected positive, actual move -3.0% -> False
    dir_miss = scorer.evaluate_price_direction(pred, -0.03)
    assert dir_miss is False

    # 5. Price direction noise buffer: actual move +0.1% (< 0.5% default buffer) -> Flat/False against positive call
    dir_noise = scorer.evaluate_price_direction(pred, 0.001)
    assert dir_noise is False

    # 6. Guidance stance hit
    actual_g, guidance_hit = scorer.evaluate_guidance_stance(pred, "RAISED")
    assert actual_g == "RAISED"
    assert guidance_hit is True

    # 7. Composite score calculation
    brier = 0.04 # (0.8 - 1.0)^2 = 0.04
    comp_score = scorer.compute_composite_score(brier, True, True, True)
    assert comp_score > 90.0

