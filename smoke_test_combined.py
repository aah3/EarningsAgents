from config.settings import CompanyData as SettingsCompanyData, ReportTime
from data.base import CompanyData as BaseCompanyData, EarningsEvent
from data.yahoo_finance import YahooFinanceDataSource
from data.data_aggregator import DataAggregator

# CompanyData in both locations has fiscal fields
assert hasattr(SettingsCompanyData, '__dataclass_fields__')
assert 'fiscal_quarter' in SettingsCompanyData.__dataclass_fields__
assert 'fiscal_year'    in SettingsCompanyData.__dataclass_fields__
assert 'report_time'    in SettingsCompanyData.__dataclass_fields__
print('settings.CompanyData fields: OK')

assert 'fiscal_quarter' in BaseCompanyData.model_fields
assert 'fiscal_year'    in BaseCompanyData.model_fields
assert 'report_time'    in BaseCompanyData.model_fields
print('base.CompanyData fields: OK')

# EarningsEvent has fiscal fields
assert 'fiscal_quarter' in EarningsEvent.model_fields
assert 'fiscal_year'    in EarningsEvent.model_fields
print('base.EarningsEvent fields: OK')

# yahoo_finance has the new helper
assert hasattr(YahooFinanceDataSource, 'get_single_ticker_calendar')
print('YahooFinanceDataSource.get_single_ticker_calendar: OK')

# DataAggregator has the chain helper
assert hasattr(DataAggregator, '_chain')
print('DataAggregator._chain: OK')

print()
print('Full smoke test PASSED — ready for live testing')
