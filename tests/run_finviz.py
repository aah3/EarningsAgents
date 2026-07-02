import pandas as pd
from finvizfinance.screener.overview import Overview
from datetime import date

class EarningsDataFetch:
    def __init__(self):
        self.screener = Overview()

    def get_upcoming_earnings(self, index_name=None, days_limit=5):
        filters = {}
        if index_name:
            filters['Index'] = index_name
        
        if days_limit <= 1:
            filters['Earnings Date'] = 'Today'
        elif days_limit <= 2:
            filters['Earnings Date'] = 'Tomorrow'
        elif days_limit <= 5:
            filters['Earnings Date'] = 'This Week'
        else:
            filters['Earnings Date'] = 'Next Week'

        try:
            self.screener.set_filter(filters_dict=filters)
            df = self.screener.screener_view()
            if df is None or df.empty:
                return []
            return df.to_dict('records')
        except Exception as e:
            print(f"Error: {e}")
            return []

if __name__ == "__main__":
    fetcher = EarningsDataFetch()
    results = fetcher.get_upcoming_earnings(index_name="S&P 500", days_limit=5)
    print(f"Found {len(results)} companies:")
    if results:
        for k in results[0].keys():
            print(k)
        print(results[0])
