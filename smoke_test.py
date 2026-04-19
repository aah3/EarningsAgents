from datetime import date, datetime, timedelta
from scoring_service import PredictionScorer

# Mock a HistoricalEarning-like object
from dataclasses import dataclass
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
            date=date(2025, 1, 29),
            actual_eps=2.40,
            estimate_eps=2.10,
            surprise_pct=14.3,
            beat=True
        )]

scorer = PredictionScorer(FakeYahoo())

# Test fetch_actual_direction with a date 2 days off (within 7-day window)
result = scorer.fetch_actual_direction('FAKE', date(2025, 1, 27))
assert result is not None, 'Should find entry within 7-day window'
assert result['actual_direction'] == 'beat', f'Expected beat, got {result["actual_direction"]}'
assert result['actual_eps'] == 2.40
print('fetch_actual_direction: OK', result)

# Test score_prediction with a mock Prediction
@dataclass
class FakePrediction:
    ticker: str = 'FAKE'
    report_date: datetime = datetime(2025, 1, 27)
    direction: str = 'beat'
    confidence: float = 75.0

pred = FakePrediction()
score_result = scorer.score_prediction(pred)
assert score_result['scored'] == True
assert score_result['actual_direction'] == 'beat'
assert 'accuracy_score' in score_result
print('score_prediction: OK', score_result)
print()
print('Full integration smoke test PASSED')
