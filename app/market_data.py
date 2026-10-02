from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import settings


BINANCE_PUBLIC_URL = "https://api.binance.com"
USER_AGENT = "crypto-trading-assistant-paper/1.0"


class MarketDataError(RuntimeError):
    pass


class DataQuality(StrEnum):
    OK = "OK"
    STALE = "STALE"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    INVALID_CANDLES = "INVALID_CANDLES"
    API_ERROR = "API_ERROR"
    INVALID_QUOTE = "INVALID_QUOTE"


@dataclass(frozen=True)
class Candle:
    opened_at: datetime
    closed_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    timeframe: str
    bid: float
    ask: float
    mid: float
    spread_bps: float
    last_closed_price: float
    last_closed_candle_at: datetime
    candles: tuple[Candle, ...]
    market_fresh: bool
    data_quality: DataQuality
    retrieved_at: datetime


def utc_now():
    return datetime.now(timezone.utc)


def normalize_symbol(symbol: str) -> str:
    normalized = str(symbol).upper().strip().replace("-", "/").replace("_", "/")

    if normalized not in settings.supported_symbols:
        supported = ", ".join(settings.supported_symbols)
        raise MarketDataError(f"Unsupported symbol. Use: {supported}.")

    return normalized


def exchange_symbol(symbol: str) -> str:
    return normalize_symbol(symbol).replace("/", "")


def timeframe_seconds(timeframe: str) -> int:
    values = {
        "1m": 60,
        "3m": 180,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "2h": 7200,
        "4h": 14400,
        "1d": 86400,
    }

    if timeframe not in values:
        raise MarketDataError("Unsupported timeframe.")

    return values[timeframe]


def public_request(path: str, params: dict[str, object]):
    query = urlencode(params)
    url = f"{BINANCE_PUBLIC_URL}{path}?{query}"
    request = Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        raise MarketDataError("Public market-data request failed.") from error


def validate_candles(
    rows,
    timeframe: str,
    retrieved_at: datetime | None = None,
) -> tuple[Candle, ...]:
    if not isinstance(rows, list) or not rows:
        raise MarketDataError("No candle data received.")

    retrieved_at = retrieved_at or utc_now()
    interval_ms = timeframe_seconds(timeframe) * 1000
    candles = []
    previous_open_ms = None

    for row in rows:
        if not isinstance(row, list) or len(row) < 6:
            raise MarketDataError("Invalid candle format.")

        try:
            open_ms = int(row[0])
            open_price = float(row[1])
            high = float(row[2])
            low = float(row[3])
            close = float(row[4])
            volume = float(row[5])
            close_ms = int(row[6])
        except (TypeError, ValueError, IndexError) as error:
            raise MarketDataError("Invalid OHLCV candle values.") from error

        if previous_open_ms is not None:
            if open_ms <= previous_open_ms:
                raise MarketDataError("Duplicate or out-of-order candles.")
            if open_ms - previous_open_ms != interval_ms:
                raise MarketDataError("Missing candles detected.")

        if (
            open_price <= 0
            or high <= 0
            or low <= 0
            or close <= 0
            or volume <= 0
            or high < max(open_price, close)
            or low > min(open_price, close)
            or close_ms <= open_ms
        ):
            raise MarketDataError("Invalid OHLCV candle values.")

        previous_open_ms = open_ms

        close_time = datetime.fromtimestamp(close_ms / 1000, timezone.utc)

        if close_time >= retrieved_at:
            continue

        candles.append(
            Candle(
                opened_at=datetime.fromtimestamp(open_ms / 1000, timezone.utc),
                closed_at=close_time,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )

    if not candles:
        raise MarketDataError("No closed candles available.")

    return tuple(candles)


def quote(symbol: str) -> dict[str, float | str]:
    normalized = normalize_symbol(symbol)
    data = public_request(
        "/api/v3/ticker/bookTicker",
        {"symbol": exchange_symbol(normalized)},
    )

    try:
        bid = float(data["bidPrice"])
        ask = float(data["askPrice"])
    except (KeyError, TypeError, ValueError) as error:
        raise MarketDataError("Invalid quote response.") from error

    if bid <= 0 or ask <= 0 or ask < bid:
        raise MarketDataError("Invalid bid/ask quote.")

    mid = (bid + ask) / 2
    spread_bps = ((ask - bid) / mid) * 10000

    if spread_bps > settings.max_spread_bps:
        raise MarketDataError("Spread exceeds the configured maximum.")

    return {
        "symbol": normalized,
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "spread_bps": spread_bps,
    }


def market_snapshot(
    symbol: str,
    timeframe: str = settings.primary_timeframe,
    limit: int = 200,
) -> MarketSnapshot:
    retrieved_at = utc_now()
    normalized = normalize_symbol(symbol)

    try:
        quote_data = quote(normalized)
        raw_candles = public_request(
            "/api/v3/klines",
            {
                "symbol": exchange_symbol(normalized),
                "interval": timeframe,
                "limit": max(limit + 1, 30),
            },
        )
        candles = validate_candles(raw_candles, timeframe, retrieved_at)
    except MarketDataError:
        raise

    if len(candles) < 60:
        return MarketSnapshot(
            symbol=normalized,
            timeframe=timeframe,
            bid=float(quote_data["bid"]),
            ask=float(quote_data["ask"]),
            mid=float(quote_data["mid"]),
            spread_bps=float(quote_data["spread_bps"]),
            last_closed_price=candles[-1].close,
            last_closed_candle_at=candles[-1].closed_at,
            candles=candles,
            market_fresh=False,
            data_quality=DataQuality.INSUFFICIENT_HISTORY,
            retrieved_at=retrieved_at,
        )

    age_seconds = (retrieved_at - candles[-1].closed_at).total_seconds()
    fresh = age_seconds <= timeframe_seconds(timeframe) + settings.stale_seconds

    return MarketSnapshot(
        symbol=normalized,
        timeframe=timeframe,
        bid=float(quote_data["bid"]),
        ask=float(quote_data["ask"]),
        mid=float(quote_data["mid"]),
        spread_bps=float(quote_data["spread_bps"]),
        last_closed_price=candles[-1].close,
        last_closed_candle_at=candles[-1].closed_at,
        candles=candles,
        market_fresh=fresh,
        data_quality=DataQuality.OK if fresh else DataQuality.STALE,
        retrieved_at=retrieved_at,
    )