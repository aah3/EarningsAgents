"""
Provider Registry & Custom Data Source Router.

Allows registering, instantiating, and resolving custom client data sources
for different fields or domain inputs in Earnings Agents AI.
"""

import importlib
import logging
from typing import Dict, Any, List, Optional, Callable, Type, Tuple, Union
from data.base import (
    IPriceProvider,
    IOptionChainProvider,
    IEarningsEstimateProvider,
    IFinancialsProvider,
    INewsTranscriptProvider,
)

logger = logging.getLogger("ProviderRegistry")


class ProviderRegistry:
    """
    Central registry for managing pluggable client data providers.
    
    Supports:
      1. Registering provider instances or callables programmatically.
      2. Dynamic loading from dictionary/YAML configuration.
      3. Building prioritized provider chains for specific data domains.
    """
    
    _registered_providers: Dict[str, Any] = {}
    _domain_routes: Dict[str, List[str]] = {
        "price_data": [],
        "consensus_estimates": [],
        "historical_earnings": [],
        "estimate_revisions": [],
        "company_info": [],
        "options_features": [],
        "news_articles": [],
        "transcripts": [],
    }

    @classmethod
    def register_provider(cls, name: str, provider_instance_or_factory: Any) -> None:
        """
        Register a custom provider instance or zero-arg factory function under a name.
        
        Args:
            name: Identifier (e.g. 'client_sql_db', 'client_rest_api')
            provider_instance_or_factory: Instance implementing domain provider interface(s) or factory returning one.
        """
        cls._registered_providers[name] = provider_instance_or_factory
        logger.info(f"Registered data provider '{name}'")

    @classmethod
    def get_provider(cls, name: str) -> Optional[Any]:
        """Get registered provider instance by name."""
        provider = cls._registered_providers.get(name)
        if callable(provider) and not hasattr(provider, "__self__") and not hasattr(provider, "get_price_data"):
            # If it's a factory function, invoke it
            return provider()
        return provider

    @classmethod
    def set_domain_providers(cls, domain: str, provider_names: List[str]) -> None:
        """
        Set priority order of provider names for a specific data domain.
        
        Args:
            domain: Domain key (e.g. 'price_data', 'consensus_estimates', 'options_features')
            provider_names: Ordered list of provider names to try.
        """
        cls._domain_routes[domain] = list(provider_names)
        logger.info(f"Set domain route for '{domain}': {provider_names}")

    @classmethod
    def get_domain_providers(cls, domain: str) -> List[str]:
        """Get priority list of provider names for a domain."""
        return cls._domain_routes.get(domain, [])

    @classmethod
    def load_from_config(cls, config: Dict[str, Any]) -> None:
        """
        Load custom providers and domain routing from a configuration dictionary.
        
        Example config:
            {
                "clients": {
                    "client_sql": {
                        "class": "data.adapters.client_sql_source.ClientSQLPriceProvider",
                        "connection_string": "sqlite:///:memory:"
                    }
                },
                "routes": {
                    "price_data": ["client_sql", "yahoo_finance"],
                    "consensus_estimates": ["client_api", "yahoo_finance"]
                }
            }
        """
        clients_cfg = config.get("clients", {})
        for name, cfg in clients_cfg.items():
            if isinstance(cfg, dict) and "class" in cfg:
                class_path = cfg["class"]
                module_path, class_name = class_path.rsplit(".", 1)
                try:
                    module = importlib.import_module(module_path)
                    cls_type: Type = getattr(module, class_name)
                    kwargs = {k: v for k, v in cfg.items() if k != "class"}
                    instance = cls_type(**kwargs)
                    cls.register_provider(name, instance)
                except Exception as e:
                    logger.error(f"Failed to instantiate custom provider '{name}' from {class_path}: {e}")
            elif hasattr(cfg, "get_price_data") or hasattr(cfg, "get_consensus_estimates"):
                cls.register_provider(name, cfg)

        routes_cfg = config.get("routes", {})
        for domain, providers in routes_cfg.items():
            if isinstance(providers, list):
                cls.set_domain_providers(domain, providers)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered providers and custom routes (useful for testing)."""
        cls._registered_providers.clear()
        for k in cls._domain_routes:
            cls._domain_routes[k] = []
