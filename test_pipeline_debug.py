import asyncio
import json
from datetime import date
from pipeline import EarningsPipeline
from config.settings import load_config

if __name__ == "__main__":
    try:
        print("Loading config...")
        config = load_config()
        config.output_dir = "worker_output"
        
        print("Initializing pipeline...")
        pipeline = EarningsPipeline(config)
        pipeline.initialize()
        
        print("Running prediction for NVDA...")
        result = pipeline.predict_single("NVDA", date(2026, 3, 3))
        
        print("=== RESULT ===")
        # result is a dictionary based on api/tasks.py it seems.
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
