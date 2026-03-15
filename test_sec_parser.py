import logging
from config.settings import DataSourceConfig
from data.sec_edgar import SECEdgarDataSource
import re

logging.basicConfig(level=logging.INFO)
config = DataSourceConfig(rate_limit_calls=10, rate_limit_period=1)
sec = SECEdgarDataSource(config, user_agent="EarningsPredictor/1.0 (test@example.com)")
sec.connect()

print("Testing transcript fetch...")
transcripts = sec.get_earnings_transcripts("AAPL", year=2025)
print(f"Found {len(transcripts)} potential transcripts")
for t in transcripts[:3]:
    print(f"Transcript: {t.title} Date: {t.date} Quarter: {t.fiscal_quarter}")

sec.disconnect()
