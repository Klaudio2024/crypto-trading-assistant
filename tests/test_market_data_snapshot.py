import time

import market_data as market_data


def make_candle(close_time: int) -> market_data.Candle:
    return market_data.Candle(
        open_time=close_time - (15 * 60 * 1000) + 1,
        close_time=close_time,
        open=100.0,
        high=102.0,
        low=99.0,
        close=101.0,
        volume=10.0,
    )


def test_market_snapshot_marks_expired_closed_candle_as_stale(monkeypatch):
    stale_close_time = int((time.time() - 1_000) * 1_000)

    monkeypatch.setattr(
        market_data,
        "closed_candles",
        lambda symbol, interval="15m", limit=250: [make_candle(stale_close_time)],
    )
    monkeypatch.setattr(
        market_data,
        "quote",
        lambda symbol: {
            "symbol": "BTC/USDT",
            "bid": 100.0,
            "ask": 100.1,
            "mid": 100.05,
            "spread_bps": 10.0,
            "retrieved_at": "2026-10-02T20:00:00+00:00",
            "age_seconds": 0.0,
        },
    )

    snapshot = market_data.market_snapshot("BTC/USDT", "15m")

    assert snapshot["market_fresh"] is False


def test_market_snapshot_marks_recent_closed_candle_as_fresh(monkeypatch):
    recent_close_time = int((time.time() - 60) * 1_000)

    monkeypatch.setattr(
        market_data,
        "closed_candles",
        lambda symbol, interval="15m", limit=250: [make_candle(recent_close_time)],
    )
    monkeypatch.setattr(
        market_data,
        "quote",
        lambda symbol: {
            "symbol": "BTC/USDT",
            "bid": 100.0,
            "ask": 100.1,
            "mid": 100.05,
            "spread_bps": 10.0,
            "retrieved_at": "2026-10-02T20:00:00+00:00",
            "age_seconds": 0.0,
        },
    )

    snapshot = market_data.market_snapshot("BTC/USDT", "15m")

    assert snapshot["market_fresh"] is True


def test_five_minute_timeframe_is_supported():
    assert "5m" in market_data.ALLOWED_INTERVALS
    assert market_data.INTERVAL_SECONDS["5m"] == 5 * 60
