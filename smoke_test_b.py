from datetime import date

# Test fiscal quarter derivation logic directly
def derive_fq(report_date):
    m = report_date.month
    if m <= 3:   return 'Q4', report_date.year - 1
    elif m <= 6: return 'Q1', report_date.year
    elif m <= 9: return 'Q2', report_date.year
    else:        return 'Q3', report_date.year

tests = [
    (date(2025, 2, 5),  'Q4', 2024),
    (date(2025, 4, 25), 'Q1', 2025),
    (date(2025, 7, 30), 'Q2', 2025),
    (date(2025, 11, 1), 'Q3', 2025),
]
for d, exp_q, exp_y in tests:
    q, y = derive_fq(d)
    assert q == exp_q and y == exp_y, f'{d}: expected {exp_q}/{exp_y}, got {q}/{y}'
    print(f'{d} -> {q} {y} OK')

# Verify imports are intact
from data.yahoo_finance import YahooFinanceDataSource
assert hasattr(YahooFinanceDataSource, 'get_single_ticker_calendar'), 'Method missing'
print('get_single_ticker_calendar present: OK')

from data.data_aggregator import DataAggregator
import inspect
src = inspect.getsource(DataAggregator.get_company_data)
assert 'get_single_ticker_calendar' in src, 'calendar call missing from get_company_data'
assert 'fiscal_quarter' in src, 'fiscal_quarter not assigned in CompanyData'
assert 'report_time' in src, 'report_time not assigned in CompanyData'
print('data_aggregator.get_company_data wiring: OK')
print()
print('All Sub-task A checks passed')
