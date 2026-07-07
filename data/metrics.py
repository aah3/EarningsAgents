from typing import Optional

def dollar_surprise(actual: Optional[float], estimate: Optional[float]) -> Optional[float]:
    if actual is None or estimate is None:
        return None
    return actual - estimate

def safe_surprise_pct(actual: Optional[float], estimate: Optional[float],
                      cap: float = 100.0, min_base: float = 0.05) -> Optional[float]:
    """Percentage surprise, guarded. Returns None when the estimate base is too small
    for a % to be meaningful (report the dollar figure instead). Magnitude capped at ±cap."""
    if actual is None or estimate is None:
        return None
    if abs(estimate) < min_base:
        return None            # near-zero base → % is noise; caller shows dollar_surprise
    pct = (actual - estimate) / abs(estimate) * 100.0
    return max(-cap, min(cap, pct))
