import json
import logging
logging.basicConfig(level=logging.ERROR)
from data.sec_edgar import SECEdgarDataSource
from config.settings import DataSourceConfig

sec = SECEdgarDataSource(DataSourceConfig(rate_limit_calls=10, rate_limit_period=1), 'Test/1.0 (test@example.com)')
sec.connect()
facts = sec.get_company_facts('AAPL')
if facts:
    gaap = facts.get('facts', {}).get('us-gaap', {})
    keys = ['Assets', 'Liabilities', 'Revenues', 'SalesRevenueNet', 'NetIncomeLoss', 'OperatingIncomeLoss']
    results = {}
    for k in keys:
        if k in gaap:
            val = gaap[k].get('units', {}).get('USD', [])
            if val:
                results[k] = val[-1]
    print(json.dumps(results, indent=2))
