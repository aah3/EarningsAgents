import sys
import logging
from datetime import date
from pipeline import EarningsPipeline
from config.settings import load_config

logging.basicConfig(level=logging.DEBUG)

def main():
    config = load_config()
    pipeline = EarningsPipeline(config)
    pipeline.initialize()
    
    analysis = "Given the high price of oil and lower demand for travel, CCL will have preasures from both lower travelers and higher cost, thus reducing margins."
    
    try:
        res = pipeline.predict_single(
            ticker="CCL",
            report_date=date(2026, 3, 25),
            user_analysis=analysis
        )
        print(res.debate_summary)
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    main()
