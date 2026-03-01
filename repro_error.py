
import sys
import os
from datetime import date

# Add project root to path
sys.path.append(os.getcwd())

from config.settings import DataSourceConfig
from data.news_sources import AlphaVantageNewsDataSource

def test_repro():
    config = DataSourceConfig(api_key="test_key")
    print(f"Config type: {type(config)}")
    print(f"Config timeout attr: {hasattr(config, 'timeout')}")
    if hasattr(config, 'timeout'):
        print(f"Config timeout value: {config.timeout}")
    else:
        print("Config timeout is MISSING")
    
    av = AlphaVantageNewsDataSource(config)
    # Don't actually connect, just test the method logic
    av._connected = True
    import requests
    av.session = requests.Session()
    
    try:
        print("Trying to call get_news_sentiment...")
        av.get_news_sentiment("COST")
    except Exception as e:
        print(f"Caught error in get_news_sentiment: {e}")
    finally:
        av.session.close()


if __name__ == "__main__":
    test_repro()
