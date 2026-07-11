import os
import sys
from datetime import date

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.earningsapi_source import EarningsAPIDataSource
from config.settings import load_config

def test_resolve_next_earnings():
    config = load_config()
    # Ensure api key is configured
    if not config.earningsapi.api_key:
        print("Skipping test: EARNINGSAPI_API_KEY environment variable not set.")
        return

    src = EarningsAPIDataSource(config.earningsapi)
    assert src.connect() is True
    
    ticker = "AAPL"
    try:
        print(f"Fetching earnings history for {ticker}...")
        earnings = src.get_company_earnings(ticker)
        assert isinstance(earnings, list)
        assert len(earnings) > 0
        
        # Test the upcoming earnings logic
        today = date.today()
        upcoming = []
        for event in earnings:
            event_date_str = event.get("date")
            if not event_date_str:
                continue
            try:
                event_date = date.fromisoformat(event_date_str)
            except ValueError:
                continue
            if event_date >= today:
                upcoming.append((event_date, event))
        
        next_event = None
        if upcoming:
            upcoming.sort(key=lambda x: x[0])
            next_event = upcoming[0][1]
        else:
            next_event = earnings[0]
            
        print(f"Upcoming / fallback event for {ticker}: {next_event}")
        assert next_event is not None
        assert "date" in next_event
        assert "epsEstimate" in next_event
        assert "time" in next_event
        
        print("Test passed successfully!")
    finally:
        src.disconnect()

if __name__ == "__main__":
    test_resolve_next_earnings()
