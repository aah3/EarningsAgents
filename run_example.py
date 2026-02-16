# run_example.py

from data_aggregator import DataAggregator
from base import DataSourceConfig
from datetime import date

# Initialize (Yahoo is free, no keys needed!)
aggregator = DataAggregator(
    yahoo_config=DataSourceConfig(rate_limit_calls=2000),
    # Optional: add API keys for news
    # newsapi_config=DataSourceConfig(api_key="xxx"),
    # alphavantage_config=DataSourceConfig(api_key="xxx")
)

aggregator.initialize()

# Get comprehensive company data
company = aggregator.get_company_data("AAPL", date(2024, 2, 1))
print(f"Beat Rate: {company.beat_rate_4q:.0%}")
print(f"Consensus EPS: ${company.consensus_eps:.2f}")

# Get news with sentiment
news = aggregator.get_news_with_sentiment("AAPL", "Apple", days_back=30)
for article in news[:5]:
    print(f"{article.headline} [{article.sentiment_score:+.2f}]")

aggregator.shutdown()


# get news
from newsapi import NewsApiClient  
newsapi_key='078eb94468bc44b886fac950b97f5ffe'
newsapi = NewsApiClient(api_key=newsapi_key)
top_headlines = newsapi.get_top_headlines(q='appl') 
top_headlines = newsapi.get_top_headlines(q='appl',
                                          sources='msnbc',
                                          category='business',
                                          language='en',
                                          country='us')
print(top_headlines.get('articles')[0].keys())
print(top_headlines.get('articles')[0].get('description'))
