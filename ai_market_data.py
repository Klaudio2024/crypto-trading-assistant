"""Prepare verified market data for the AI Market Analyst."""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean

from market_data import Candle, MarketDataError, closed_candles, normalize_symbol, quote
from strategy import atr, ema, rsi, volume_ratio


TIMEFRAMES = ("15m", "1h", "4h")

TIMEFRAME_SECONDS = {
    "15m": 15 * 60,
    "1h": 60 * 60,
    "4h": 4 * 60 * 60,
}


def adx(candles: list[Candle], period: int = 14) -> float:
    """Calculate ADX14 using Wilder smoothing."""
    if len(candles) < (period * 2) + 1:
        raise ValueError("ADX requires at least 29 closed candles.")

    true_ranges: list[float] = []
    positive_dm: list[float] = []
    negative_dm: list[float] = []

    for index in range(1, len(candles)):
        current = candles[index]
        previous = candles[index - 1]

        up_move = current.high - previous.high
        down_move = previous.low - current.low

        true_ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
        positive_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        negative_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)

    smoothed_tr = sum(true_ranges[:period])
    smoothed_plus_dm = sum(positive_dm[:period])
    smoothed_minus_dm = sum(negative_dm[:period])
    dx_values: list[float] = []

    for index in range(period, len(true_ranges)):
        if smoothed_tr <= 0:
            raise ValueError("ADX cannot be calculated with zero true range.")

        plus_di = 100 * smoothed_plus_dm / smoothed_tr
        minus_di = 100 * smoothed_minus_dm / smoothed_tr
        di_sum = plus_di + minus_di

        dx_values.append(
            0.0 if di_sum == 0 else 100 * abs(plus_di - minus_di) / di_sum
        )

        smoothed_tr = smoothed_tr - (smoothed_tr / period) + true_ranges[index]
        smoothed_plus_dm = (
            smoothed_plus_dm - (smoothed_plus_dm / period) + positive_dm[index]
        )
        smoothed_minus_dm = (
            smoothed_minus_dm - (smoothed_minus_dm / period) + negative_dm[index]
        )

    if len(dx_values) < period:
        raise ValueError("ADX requires more closed candles.")

    adx_value = mean(dx_values[:period])

    for dx_value in dx_values[period:]:
        adx_value = ((adx_value * (period - 1)) + dx_value) / period

    return adx_value


def timeframe_indicators(candles: list[Candle]) -> dict[str, float]:
    closes = [candle.close for candle in candles]

    return {
        "last_close": round(closes[-1], 8),
        "ema20": round(ema(closes, 20), 8),
        "ema50": round(ema(closes, 50), 8),
        "ema200": round(ema(closes, 200), 8),
        "rsi14": round(rsi(closes, 14), 4),
        "atr14": round(atr(candles, 14), 8),
        "adx14": round(adx(candles, 14), 4),
        "volume": round(candles[-1].volume, 8),
        "volume_ratio": round(volume_ratio(candles, 20), 4),
    }


def build_ai_market_data(symbol: str) -> dict[str, object]:
    """Build one verified data packet for AI analysis.

    Only closed candles are used. If data is unavailable or stale,
    MarketDataError is raised and the caller must return HOLD.
    """
    normalized_symbol = normalize_symbol(symbol)
    candles_by_timeframe: dict[str, list[Candle]] = {}

    for timeframe in TIMEFRAMES:
        candles_by_timeframe[timeframe] = closed_candles(
            normalized_symbol,
            interval=timeframe,
            limit=250,
        )

    latest_15m_candle = candles_by_timeframe["15m"][-1]
    now = datetime.now(timezone.utc)
    candle_closed_at = datetime.fromtimestamp(
        latest_15m_candle.close_time / 1000,
        tz=timezone.utc,
    )
    candle_age_seconds = max(0.0, (now - candle_closed_at).total_seconds())
    max_age_seconds = TIMEFRAME_SECONDS["15m"] + 90

    if candle_age_seconds > max_age_seconds:
        raise MarketDataError("Latest closed 15m candle is stale.")

    current_quote = quote(normalized_symbol)
    bid = float(current_quote["bid"])
    ask = float(current_quote["ask"])

    if bid <= 0 or ask <= 0 or ask < bid:
        raise MarketDataError("Current bid/ask quote is invalid.")

    return {
        "symbol": normalized_symbol,
        "data_timestamp": candle_closed_at.isoformat(),
        "market_fresh": True,
        "candle_age_seconds": round(candle_age_seconds, 2),
        "quote": {
            "bid": bid,
            "ask": ask,
            "spread_bps": round(float(current_quote["spread_bps"]), 4),
            "retrieved_at": str(current_quote["retrieved_at"]),
        },
        "timeframes": {
            timeframe: timeframe_indicators(candles)
            for timeframe, candles in candles_by_timeframe.items()
        },
    }