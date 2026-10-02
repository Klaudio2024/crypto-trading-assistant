"""Service that returns safe AI analysis for Paper Trading."""

from __future__ import annotations

from typing import Any

from ai_analyst import AIMarketAnalyst, unavailable_analysis
from ai_market_data import build_ai_market_data
from market_data import MarketDataError, normalize_symbol


def ai_status() -> dict[str, object]:
    """Return AI status without exposing any API key."""
    return AIMarketAnalyst().status()


def analyze_symbol(
    symbol: str,
    analyst: AIMarketAnalyst | None = None,
) -> dict[str, Any]:
    """Analyze one symbol.

    This function never creates a paper trade.
    Every market-data or AI failure returns HOLD.
    """
    try:
        market_data = build_ai_market_data(symbol)
    except MarketDataError:
        return unavailable_analysis(
            normalize_symbol(symbol),
            None,
            "Market data is unavailable or stale.",
        )

    active_analyst = analyst or AIMarketAnalyst()
    return active_analyst.analyze(market_data)