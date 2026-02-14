#!/usr/bin/env python3
"""
Earnings Prediction POC - Main Entry Point

Usage:
    # Weekly predictions
    python main.py weekly --week 2024-01-15
    
    # Single company
    python main.py single --ticker AAPL --report-date 2024-01-25
    
    # With custom settings
    python main.py weekly --week 2024-01-15 --benchmark NDX --output csv
"""

import argparse
import logging
from datetime import date, datetime
from pathlib import Path

from config.settings import PipelineConfig, AgentConfig, DataSourceConfig
from pipeline import EarningsPipeline


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def parse_date(date_str: str) -> date:
    """Parse date string."""
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"]:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str}")


def cmd_weekly(args, pipeline: EarningsPipeline):
    """Run weekly predictions."""
    week_start = parse_date(args.week)
    
    print(f"\n{'='*60}")
    print(f"Weekly Earnings Predictions")
    print(f"Week Starting: {week_start}")
    print(f"Benchmark: {args.benchmark}")
    print(f"{'='*60}\n")
    
    predictions = pipeline.run_weekly(week_start, args.output)
    return predictions


def cmd_single(args, pipeline: EarningsPipeline):
    """Run single company prediction."""
    ticker = args.ticker.upper()
    report_date = parse_date(args.report_date)
    
    print(f"\n{'='*60}")
    print(f"Single Company Prediction")
    print(f"Ticker: {ticker}")
    print(f"Report Date: {report_date}")
    print(f"{'='*60}\n")
    
    prediction = pipeline.predict_single(ticker, report_date)
    
    # Print results
    print(f"\n{'='*60}")
    print(f"PREDICTION RESULTS")
    print(f"{'='*60}")
    print(f"Company: {prediction.company_name}")
    print(f"Prediction: {prediction.direction.value.upper()}")
    print(f"Confidence: {prediction.confidence:.0%}")
    print(f"\nReasoning: {prediction.reasoning_summary}")
    
    if prediction.agent_votes:
        print(f"\nAgent Votes:")
        for agent, vote in prediction.agent_votes.items():
            print(f"  {agent.title()}: {vote.upper()}")
    
    if prediction.bull_factors:
        print(f"\nBull Factors:")
        for f in prediction.bull_factors[:3]:
            print(f"  + {f}")
    
    if prediction.bear_factors:
        print(f"\nBear Factors:")
        for f in prediction.bear_factors[:3]:
            print(f"  - {f}")
    
    print("="*60)
    return prediction


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Earnings Prediction POC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # Global arguments
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--benchmark', default='SPX', help='Index benchmark')
    parser.add_argument('--model', default='gemini-1.5-flash-002',
                       help='Model name')
    parser.add_argument('--local', action='store_true',
                       help='Use local model instead of API')
    parser.add_argument('--output', default='parquet',
                       choices=['parquet', 'csv', 'json'],
                       help='Output format')
    parser.add_argument('--output-dir', default='./output',
                       help='Output directory')
    
    # Data source API keys
    parser.add_argument('--newsapi-key', help='NewsAPI.org API key')
    parser.add_argument('--av-key', help='Alpha Vantage API key')
    parser.add_argument('--enable-sec', action='store_true', help='Enable SEC EDGAR (slow)')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command')
    
    # Weekly command
    weekly_parser = subparsers.add_parser('weekly', help='Weekly predictions')
    weekly_parser.add_argument('--week', required=True, help='Week start (Monday)')
    
    # Single command
    single_parser = subparsers.add_parser('single', help='Single prediction')
    single_parser.add_argument('--ticker', required=True, help='Ticker symbol')
    single_parser.add_argument('--report-date', required=True, help='Report date')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    setup_logging(args.verbose)
    
    # Build config
    config = PipelineConfig(
        benchmark=args.benchmark,
        yahoo=DataSourceConfig(enabled=True, rate_limit_calls=2000),
        newsapi=DataSourceConfig(
            api_key=args.newsapi_key, 
            enabled=args.newsapi_key is not None
        ),
        alphavantage=DataSourceConfig(
            api_key=args.av_key, 
            enabled=args.av_key is not None
        ),
        sec=DataSourceConfig(enabled=args.enable_sec),
        agent=AgentConfig(
            model_name=args.model,
            use_local=args.local,
        ),
        enable_debate=True,
        output_dir=Path(args.output_dir),
    )
    
    # Create and run pipeline
    pipeline = EarningsPipeline(config)
    
    try:
        pipeline.initialize()
        
        if args.command == 'weekly':
            cmd_weekly(args, pipeline)
        elif args.command == 'single':
            cmd_single(args, pipeline)
        
    finally:
        pipeline.shutdown()
    
    return 0


if __name__ == "__main__":
    exit(main())
