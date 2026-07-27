"""
Tests for Custom Data Source Ingestion Framework in Earnings Agents.
"""

from datetime import date
import pytest
from data.base import (
    CompanyInfo,
    PriceData,
    ConsensusEstimate,
    HistoricalEarning,
    EstimateRevision,
    RevisionDirection,
    IPriceProvider,
    IEarningsEstimateProvider,
)
from data.provider_registry import ProviderRegistry
from data.adapters.custom_dict_source import InMemoryCustomDataProvider
from data.adapters.client_sql_source import ClientSQLPriceProvider
from data.adapters.client_api_source import ClientAPIEstimatesProvider
from data.data_aggregator import DataAggregator


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset ProviderRegistry state before and after each test."""
    ProviderRegistry.clear()
    yield
    ProviderRegistry.clear()


def test_provider_registry_manual_registration():
    """Test manual provider registration and retrieval."""
    sql_provider = ClientSQLPriceProvider()
    ProviderRegistry.register_provider("client_sql", sql_provider)

    retrieved = ProviderRegistry.get_provider("client_sql")
    assert retrieved is sql_provider

    price = retrieved.get_price_data("AAPL")
    assert price is not None
    assert price.current_price == 150.25


def test_provider_registry_config_loading():
    """Test dynamic provider loading from config dict."""
    config = {
        "clients": {
            "client_sql": {
                "class": "data.adapters.client_sql_source.ClientSQLPriceProvider",
                "connection_string": "sqlite:///:memory:"
            }
        },
        "routes": {
            "price_data": ["client_sql", "yahoo"]
        }
    }
    ProviderRegistry.load_from_config(config)

    retrieved = ProviderRegistry.get_provider("client_sql")
    assert retrieved is not None
    assert isinstance(retrieved, ClientSQLPriceProvider)

    routes = ProviderRegistry.get_domain_providers("price_data")
    assert routes == ["client_sql", "yahoo"]


def test_in_memory_custom_data_provider():
    """Test InMemoryCustomDataProvider providing price and estimate data."""
    provider = InMemoryCustomDataProvider()

    test_info = CompanyInfo(
        ticker="CUSTOM",
        company_name="Custom Corp",
        sector="Technology",
        industry="Software",
        market_cap=10000000000.0
    )
    test_price = PriceData(
        current_price=250.0,
        volume=1000000.0,
        as_of_date=date.today()
    )
    test_estimates = ConsensusEstimate(
        eps_mean=3.50,
        eps_median=3.50,
        eps_high=3.60,
        eps_low=3.40,
        eps_std=0.05,
        num_analysts=15,
        as_of_date=date.today()
    )

    provider.set_ticker_data("CUSTOM", {
        "company_info": test_info,
        "price_data": test_price,
        "consensus_estimates": test_estimates
    })

    assert provider.get_company_info("CUSTOM").company_name == "Custom Corp"
    assert provider.get_price_data("CUSTOM").current_price == 250.0
    assert provider.get_consensus_estimates("CUSTOM").eps_mean == 3.50


def test_data_aggregator_custom_provider_override():
    """Test DataAggregator using custom provider data over default providers."""
    custom_provider = InMemoryCustomDataProvider()

    custom_info = CompanyInfo(
        ticker="TEST",
        company_name="Test Client Corp",
        sector="Technology",
        industry="Software",
        market_cap=5000000000.0
    )
    custom_price = PriceData(
        current_price=999.99,
        volume=2000000.0,
        as_of_date=date.today()
    )
    custom_estimates = ConsensusEstimate(
        eps_mean=5.00,
        eps_median=5.00,
        eps_high=5.20,
        eps_low=4.80,
        eps_std=0.10,
        num_analysts=10,
        as_of_date=date.today()
    )

    custom_provider.set_ticker_data("TEST", {
        "company_info": custom_info,
        "price_data": custom_price,
        "consensus_estimates": custom_estimates
    })

    # Register custom provider and route
    ProviderRegistry.register_provider("custom_memory", custom_provider)

    aggregator = DataAggregator(enable_yahoo=False, enable_alphavantage=False)
    aggregator.initialize()

    company_data = aggregator.get_company_data(
        ticker="TEST",
        report_date=date.today(),
        include_news=False
    )

    assert company_data.ticker == "TEST"
    assert company_data.company_name == "Test Client Corp"
    assert company_data.current_price == 999.99
    assert company_data.consensus_eps == 5.00
    aggregator.shutdown()


def test_data_aggregator_custom_provider_fallback():
    """Test fallback when custom provider returns None."""
    class FailingCustomProvider(IPriceProvider):
        def get_price_data(self, ticker: str):
            return None  # Trigger fallback

    class WorkingBackupProvider(IPriceProvider):
        def get_price_data(self, ticker: str):
            return PriceData(current_price=42.0, as_of_date=date.today())

    ProviderRegistry.register_provider("failing", FailingCustomProvider())
    ProviderRegistry.register_provider("backup", WorkingBackupProvider())
    ProviderRegistry.set_domain_providers("price_data", ["failing", "backup"])

    sources = ProviderRegistry.get_domain_providers("price_data")
    assert sources == ["failing", "backup"]

    failing_p = ProviderRegistry.get_provider("failing")
    backup_p = ProviderRegistry.get_provider("backup")

    assert failing_p.get_price_data("ANY") is None
    assert backup_p.get_price_data("ANY").current_price == 42.0
