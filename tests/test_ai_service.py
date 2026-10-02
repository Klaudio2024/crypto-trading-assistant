from ai_analyst import AIMarketAnalyst
import ai_service
from market_data import MarketDataError


def market_data():
    return {
        "symbol": "BTC/USDT",
        "data_timestamp": "2026-10-02T16:00:00+00:00",
        "market_fresh": True,
        "quote": {
            "bid": 100.0,
            "ask": 100.1,
            "spread_bps": 10.0,
        },
        "timeframes": {},
    }


def test_market_data_error_returns_hold(monkeypatch):
    def raise_market_error(symbol):
        raise MarketDataError("Binance is unavailable")

    monkeypatch.setattr(ai_service, "build_ai_market_data", raise_market_error)

    result = ai_service.analyze_symbol("BTC/USDT")

    assert result["action"] == "HOLD"
    assert result["data_quality"] == "INVALID"


def test_ai_service_uses_injected_analyst(monkeypatch):
    monkeypatch.setattr(
        ai_service,
        "build_ai_market_data",
        lambda symbol: market_data(),
    )

    analyst = AIMarketAnalyst(
        api_key="test-key",
        model="test-model",
    )

    monkeypatch.setattr(
        analyst,
        "analyze",
        lambda data: {
            "symbol": "BTC/USDT",
            "action": "HOLD",
            "data_quality": "VALID",
        },
    )

    result = ai_service.analyze_symbol("BTC/USDT", analyst)

    assert result["symbol"] == "BTC/USDT"
    assert result["action"] == "HOLD"


def test_ai_status_does_not_return_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = ai_service.ai_status()

    assert result["status"] == "unavailable"
    assert "api_key" not in result
    assert "OPENAI_API_KEY" in str(result["reason"])