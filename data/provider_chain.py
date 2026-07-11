from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple, Optional
import logging

@dataclass
class ChainResult:
    """Result from a ProviderChain.fetch() call."""
    value: Any                  # the fetched value, or None if all sources failed
    source: str                 # name of the source that succeeded, or "none"
    attempted: List[str]        # all source names tried in order
    errors: Dict[str, str] = field(default_factory=dict) # source_name → error string for each failure


class ProviderChain:
    """
    Tries a sequence of (name, callable) pairs in order, returning the
    first non-empty result. Logs the outcome at the appropriate level.

    Parameters
    ----------
    logger : logging.Logger
        Passed in from the caller (DataAggregator).
    empty_sentinel : callable, optional
        A function that takes a value and returns True if it should be
        treated as "empty" (triggering the next source). Default: checks
        for None, empty list, and empty dict.
    """

    def __init__(self, logger: logging.Logger, empty_sentinel: Optional[Callable[[Any], bool]] = None):
        self.logger = logger
        if empty_sentinel is None:
            self.empty_sentinel = lambda v: v is None or (isinstance(v, (list, dict)) and len(v) == 0)
        else:
            self.empty_sentinel = empty_sentinel

    def fetch(self, label: str, sources: List[Tuple[str, Callable[[], Any]]]) -> ChainResult:
        """
        Try each (name, fn) in sources until one returns a non-empty value.

        Parameters
        ----------
        label : str
            Human-readable label for this fetch (e.g. "company_info",
            "consensus_estimates"). Used in log messages.
        sources : List[Tuple[str, Callable]]
            Ordered list of (source_name, zero-argument callable) pairs.
            Each callable should perform the actual API call and return
            the result or None.

        Returns
        -------
        ChainResult
            .value is None only if every source failed or returned empty.
        """
        attempted = []
        errors = {}

        for i, (name, fn) in enumerate(sources):
            attempted.append(name)
            try:
                val = fn()
                if not self.empty_sentinel(val):
                    if i == 0:
                        self.logger.debug(f"{label}: used {name}")
                    else:
                        self.logger.warning(f"{label}: primary failed, used {name}")
                    return ChainResult(value=val, source=name, attempted=attempted, errors=errors)
                else:
                    self.logger.debug(f"{label}: {name} returned empty — trying next")
            except Exception as e:
                errors[name] = str(e)
                self.logger.warning(f"{label}: {name} raised {e} — trying next")

        self.logger.warning(f"{label}: all sources failed ({attempted})")
        return ChainResult(value=None, source="none", attempted=attempted, errors=errors)
