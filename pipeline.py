"""
Main Pipeline for Earnings Prediction POC.

Orchestrates:
- Bloomberg data fetching
- Three-agent analysis (Bull, Bear, Quant + Consensus)
- Output writing
"""

from datetime import date, timedelta
from typing import List, Dict, Any, Optional
import logging

from config.settings import (
    PipelineConfig,
    CompanyData,
    NewsArticle,
    EarningsPrediction,
    DataSourceConfig,
)
from data.data_aggregator import DataAggregator
from agents.huggingface_agents import ThreeAgentSystem
from output.writer import OutputWriter


class EarningsPipeline:
    """
    Main pipeline for earnings prediction.
    
    Usage:
        config = PipelineConfig(
            benchmark="SPX",
            enable_debate=True,
        )
        
        pipeline = EarningsPipeline(config)
        pipeline.initialize()
        
        # Single prediction
        prediction = pipeline.predict_single("AAPL", date(2024, 1, 25))
        
        # Weekly predictions
        predictions = pipeline.run_weekly(date(2024, 1, 15))
        
        pipeline.shutdown()
    """
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.aggregator: Optional[DataAggregator] = None
        self.agent_system: Optional[ThreeAgentSystem] = None
        self.output_writer: Optional[OutputWriter] = None
        
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize all pipeline components."""
        self.logger.info("Initializing earnings prediction pipeline...")
        
        # Initialize Data Aggregator
        self.logger.info("Connecting to data sources via Aggregator...")
        self.aggregator = DataAggregator(
            yahoo_config=self.config.yahoo,
            newsapi_config=self.config.newsapi,
            alphavantage_config=self.config.alphavantage,
            sec_config=self.config.sec,
            enable_yahoo=self.config.yahoo.enabled,
            enable_newsapi=self.config.newsapi.enabled and self.config.newsapi.api_key is not None,
            enable_alphavantage=self.config.alphavantage.enabled and self.config.alphavantage.api_key is not None,
            enable_sec=self.config.sec.enabled,
        )
        self.aggregator.initialize()
        
        # Initialize agent system
        self.logger.info("Initializing Hugging Face agents...")
        self.agent_system = ThreeAgentSystem(self.config.agent)
        self.agent_system.initialize()
        
        # Initialize output writer
        self.output_writer = OutputWriter(str(self.config.output_dir))
        
        self._initialized = True
        self.logger.info("Pipeline initialized successfully")
    
    def shutdown(self) -> None:
        """Shutdown all components."""
        self.logger.info("Shutting down pipeline...")
        
        if self.aggregator:
            self.aggregator.shutdown()
        
        if self.agent_system:
            self.agent_system.shutdown()
        
        self._initialized = False
        self.logger.info("Pipeline shutdown complete")
    
    def _ensure_initialized(self):
        """Ensure pipeline is initialized."""
        if not self._initialized:
            raise RuntimeError("Pipeline not initialized. Call initialize() first.")
    
    def predict_single(
        self,
        ticker: str,
        report_date: date,
        prediction_date: Optional[date] = None,
        task_id: Optional[str] = None,
        user_analysis: Optional[str] = None,
        options_df: Optional[Any] = None
    ) -> EarningsPrediction:
        """
        Generate prediction for a single company.
        
        Args:
            ticker: Company ticker symbol
            report_date: Earnings report date
            prediction_date: Date prediction is made (default: today)
            task_id: Optional Celery task ID for real-time progress updates
            
        Returns:
            EarningsPrediction
        """
        self._ensure_initialized()
        
        import redis
        import json
        import os
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        
        def publish(msg: str):
            if task_id:
                r.publish(f"task_updates:{task_id}", json.dumps({"status": "RUNNING", "message": msg}))

        prediction_date = prediction_date or date.today()
        
        self.logger.info(f"Generating prediction for {ticker} (reports {report_date})")
        publish(f"Gathering company and consensus data for {ticker}...")
        
        # Fetch company data from Aggregator
        company_data = self.aggregator.get_company_data(
            ticker, report_date, include_news=False, options_df=options_df
        )
        
        publish(f"Fetching recent news and performing sentiment analysis...")
        
        # Fetch news with sentiment
        news = self.aggregator.get_news_with_sentiment(
            ticker, 
            company_data.company_name, 
            days_back=self.config.news_lookback_days,
            max_articles=self.config.max_news_articles
        )
        
        publish(f"Data gathered successfully. Initializing 3-agent debate...")
        
        # Run three-agent prediction
        prediction = self.agent_system.predict(
            company_data, news, prediction_date, task_id=task_id, user_analysis=user_analysis
        )
        
        publish(f"Debate concluded. Finalizing decision...")
        
        return prediction
    
    def predict_batch(
        self,
        companies: List[Dict[str, Any]],
        prediction_date: Optional[date] = None
    ) -> List[EarningsPrediction]:
        """
        Generate predictions for multiple companies.
        
        Args:
            companies: List of dicts with 'ticker' and 'report_date'
            prediction_date: Date prediction is made
            
        Returns:
            List of EarningsPrediction
        """
        self._ensure_initialized()
        
        prediction_date = prediction_date or date.today()
        predictions = []
        
        for i, company in enumerate(companies):
            try:
                self.logger.info(f"Processing {i+1}/{len(companies)}: {company['ticker']}")
                
                prediction = self.predict_single(
                    company["ticker"],
                    company["report_date"],
                    prediction_date,
                    user_analysis=company.get("user_analysis"),
                    options_df=company.get("options_df")
                )
                predictions.append(prediction)
                
            except Exception as e:
                self.logger.error(f"Failed for {company['ticker']}: {e}")
        
        return predictions
    
    def run_weekly(
        self,
        week_start: date,
        output_format: str = "parquet"
    ) -> List[EarningsPrediction]:
        """
        Run predictions for all companies reporting in a given week.
        
        Args:
            week_start: Monday of the target week
            output_format: Output format (parquet, csv, json)
            
        Returns:
            List of predictions
        """
        self._ensure_initialized()
        
        self.logger.info(f"Running weekly predictions for week of {week_start}")
        
        # Get earnings calendar for the week
        week_end = week_start + timedelta(days=6)
        
        # For POC, we'll use a set of default tickers or let the aggregator fetch what it can
        # The aggregator currently takes a list of tickers for the calendar
        # We'll use the benchmark as a proxy if possible, but for now let's assume 
        # we have a list of tickers to check.
        # In a real scenario, we'd get index constituents first.
        default_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"]
        
        calendar = self.aggregator.get_earnings_calendar(
            default_tickers, week_start, week_end
        )
        
        self.logger.info(f"Found {len(calendar)} companies reporting this week")
        
        # Generate predictions
        companies = []
        for e in calendar:
            # Handle both dataclass and dict
            if hasattr(e, 'ticker'):
                companies.append({"ticker": e.ticker, "report_date": e.report_date})
            else:
                companies.append({"ticker": e["ticker"], "report_date": e["report_date"]})
        
        predictions = self.predict_batch(companies, week_start)
        
        # Write output
        filename = f"predictions_week_{week_start.strftime('%Y%m%d')}"
        self.output_writer.write(predictions, filename, output_format)
        
        # Print summary
        self._print_summary(predictions)
        
        return predictions
    
    def _print_summary(self, predictions: List[EarningsPrediction]) -> None:
        """Print prediction summary."""
        if not predictions:
            print("No predictions generated.")
            return
        
        beat_count = sum(1 for p in predictions if p.direction.value == "beat")
        miss_count = sum(1 for p in predictions if p.direction.value == "miss")
        meet_count = sum(1 for p in predictions if p.direction.value == "meet")
        
        print("\n" + "="*60)
        print("PREDICTION SUMMARY")
        print("="*60)
        print(f"Total Predictions: {len(predictions)}")
        print(f"Predicted BEAT: {beat_count}")
        print(f"Predicted MISS: {miss_count}")
        print(f"Predicted MEET: {meet_count}")
        
        # High confidence predictions
        high_conf = [p for p in predictions if p.confidence >= 0.7]
        if high_conf:
            print(f"\nHigh Confidence Predictions (>=70%):")
            for p in sorted(high_conf, key=lambda x: -x.confidence)[:10]:
                print(f"  {p.ticker}: {p.direction.value.upper()} ({p.confidence:.0%})")
        
        print("="*60)
