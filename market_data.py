from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://api.binance.com"

ALLOWED_SYMBOLS = {
    "BTC/USDT": "BTCUSDT",
    "ETH/USDT": "ETHUSDT",
}

ALLOWED_INTERVALS = {
    "15m",
    "1h",
    "4h",
}


class MarketDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class Candle:
    open_time: int
    close_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float


def _request(path: str, params: dict[str, object]) -> object:
    url = f"{BASE_URL}{path}?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "User-Agent": "crypto-trading-assistant-paper/0.3",
        },
    )

    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise MarketDataError(
            f"Binance public market-data request failed: {exc}"
        ) from exc


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.upper().replace("-", "/").replace("_", "/")

    if normalized in ALLOWED_SYMBOLS:
        return normalized

    compact = normalized.replace("/", "")

    for display_symbol, binance_symbol in ALLOWED_SYMBOLS.items():
        if compact == binance_symbol:
            return display_symbol

    raise MarketDataError(
        "Only BTC/USDT and ETH/USDT are enabled in Paper Trading."
    )


def exchange_symbol(symbol: str) -> str:
    return ALLOWED_SYMBOLS[normalize_symbol(symbol)]


def closed_candles(
    symbol: str,
    interval: str = "15m",
    limit: int = 250,
) -> list[Candle]:
    if interval not in ALLOWED_INTERVALS:
        raise MarketDataError(
            "Allowed intervals are 15m, 1h, and 4h."
        )

    rows = _request(
        "/api/v3/klines",
        {
            "symbol": exchange_symbol(symbol),
            "interval": interval,
            "limit": min(max(limit, 60), 500),
        },
    )

    if not isinstance(rows, list) or len(rows) < 60:
        raise MarketDataError(
            "Insufficient candle history returned by Binance."
        )

    current_time_ms = int(time.time() * 1000)

    candles = [
        Candle(
            open_time=int(row[0]),
            close_time=int(row[6]),
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            volume=float(row[5]),
        )
        for row in rows
    ]

    completed = [
        candle
        for candle in candles
        if candle.close_time <= current_time_ms
    ]

    if len(completed) < 60:
        raise MarketDataError(
            "No sufficient closed candles are available yet."
        )

    return completed


def quote(symbol: str) -> dict[str, float | str]:
    data = _request(
        "/api/v3/ticker/bookTicker",
        {
            "symbol": exchange_symbol(symbol),
        },
    )

    bid = float(data["bidPrice"])
    ask = float(data["askPrice"])

    if bid <= 0 or ask <= 0 or ask < bid:
        raise MarketDataError(
            "Invalid bid/ask quote returned by Binance."
        )

    midpoint = (bid + ask) / 2
    spread_bps = ((ask - bid) / midpoint) * 10_000

    return {
        "symbol": normalize_symbol(symbol),
        "bid": bid,
        "ask": ask,
        "mid": midpoint,
        "spread_bps": spread_bps,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "age_seconds": 0.0,
    }


def market_snapshot(
    symbol: str,
    interval: str = "15m",
) -> dict[str, object]:
    candles = closed_candles(symbol, interval)
    current_quote = quote(symbol)
    latest_closed_candle = candles[-1]

    return {
        "symbol": normalize_symbol(symbol),
        "interval": interval,
        "quote": current_quote,
        "closed_candle_count": len(candles),
        "last_closed_candle_at": datetime.fromtimestamp(
            latest_closed_candle.close_time / 1000,
            tz=timezone.utc,
        ).isoformat(),
        "last_close": latest_closed_candle.close,
        "market_fresh": True,
        "candles": candles,
    }
