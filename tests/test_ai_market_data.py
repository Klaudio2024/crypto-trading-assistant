from datetime import datetime, timezone

import pytest

import ai_market_data
from market_data import Candle, MarketDataError


def candles(count=250, last_close_time=None):
    if last_close_time is None:
        last_close_time = int(datetime.now(timezone.utc).timestamp() * 1000)

    result = []

    for index in range(count):
        price = 100.0 + index
        close_time = last_close_time - ((count - index - 1) * 900_000)

        result.append(
            Candle(
                open_time=close_time - 900_000,
                close_time=close_time,
                open=price - 0.5,
                high=price + 1.0,
                low=price - 1.0,
                close=price,
                volume=1000.0 + index,
            )
        )

    return result


def test_adx_requires_enough_closed_candles():
    with pytest.raises(ValueError, match="ADX requires"):
        ai_market_data.adx(candles(count=20))


def test_build_ai_market_data_contains_all_timeframes(monkeypatch):
    market_candles = candles()

    monkeypatch.setattr(
        ai_market_data,
        "closed_candles",
        lambda symbol, interval, limit: market_candles,
    )
    monkeypatch.setattr(
        ai_market_data,
        "quote",
        lambda symbol: {
            "bid": 200.0,
            "ask": 200.1,
            "spread_bps": 5.0,
            "retrieved_at": "2026-10-02T16:00:00+00:00",
        },
    )

    result = ai_market_data.build_ai_market_data("BTC/USDT")

    assert result["symbol"] == "BTC/USDT"
    assert result["market_fresh"] is True
    assert result["quote"]["bid"] == 200.0
    assert set(result["timeframes"]) == {"15m", "1h", "4h"}

    for timeframe in ("15m", "1h", "4h"):
        indicators = result["timeframes"][timeframe]
        assert "ema20" in indicators
        assert "ema50" in indicators
        assert "ema200" in indicators
        assert "rsi14" in indicators
        assert "atr14" in indicators
        assert "adx14" in indicators
        assert "volume_ratio" in indicators


def test_stale_15m_candle_is_rejected(monkeypatch):
    stale_close_time = int(
        datetime.now(timezone.utc).timestamp() * 1000
    ) - (20 * 60 * 1000)

    monkeypatch.setattr(
        ai_market_data,
        "closed_candles",
        lambda symbol, interval, limit: candles(
            last_close_time=stale_close_time
        ),
    )

    with pytest.raises(MarketDataError, match="stale"):
        ai_market_data.build_ai_market_data("BTC/USDT")