import json

from ai_analyst import AIMarketAnalyst


def market_data():
    return {
        "symbol": "BTC/USDT",
        "data_timestamp": "2026-10-02T16:00:00+00:00",
        "market_fresh": True,
        "timeframes": {
            "15m": {
                "ema20": 100.0,
                "ema50": 99.0,
                "ema200": 95.0,
                "rsi14": 58.0,
                "atr14": 2.0,
                "adx14": 25.0,
                "volume_ratio": 1.2,
            }
        },
        "quote": {
            "bid": 100.0,
            "ask": 100.1,
            "spread_bps": 10.0,
        },
    }


class FakeResponse:
    def __init__(self, output_text):
        self.output_text = output_text


class FakeResponses:
    def __init__(self, output_text=None, error=None):
        self.output_text = output_text
        self.error = error

    def create(self, **kwargs):
        if self.error:
            raise self.error
        return FakeResponse(self.output_text)


class FakeClient:
    def __init__(self, output_text=None, error=None):
        self.responses = FakeResponses(output_text, error)


def valid_response():
    return json.dumps(
        {
            "symbol": "BTC/USDT",
            "market_regime": "TRENDING_UP",
            "directional_bias": "BULLISH",
            "action": "BUY_CANDIDATE",
            "confidence": 70,
            "supporting_factors": ["EMA20 is above EMA50."],
            "conflicting_factors": [],
            "invalidation_conditions": ["15m close below EMA50."],
            "data_timestamp": "2026-10-02T16:00:00+00:00",
            "data_quality": "VALID",
            "summary": "Bullish trend with valid market data.",
        }
    )


def test_missing_api_key_returns_safe_hold(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "test-model")

    result = AIMarketAnalyst().analyze(market_data())

    assert result["action"] == "HOLD"
    assert result["data_quality"] == "INVALID"
    assert "OPENAI_API_KEY" in result["conflicting_factors"][0]


def test_stale_market_data_returns_hold_without_ai_call():
    stale_data = market_data()
    stale_data["market_fresh"] = False

    result = AIMarketAnalyst(
        api_key="test-key",
        model="test-model",
        client=FakeClient(error=AssertionError("AI must not be called.")),
    ).analyze(stale_data)

    assert result["action"] == "HOLD"
    assert result["data_quality"] == "INVALID"
    assert "stale" in result["conflicting_factors"][0].lower()


def test_invalid_ai_response_returns_hold():
    result = AIMarketAnalyst(
        api_key="test-key",
        model="test-model",
        client=FakeClient(output_text='{"symbol":"BTC/USDT"}'),
    ).analyze(market_data())

    assert result["action"] == "HOLD"
    assert result["data_quality"] == "INVALID"


def test_ai_timeout_returns_hold():
    result = AIMarketAnalyst(
        api_key="test-key",
        model="test-model",
        client=FakeClient(error=TimeoutError("request timed out")),
    ).analyze(market_data())

    assert result["action"] == "HOLD"
    assert result["data_quality"] == "INVALID"
    assert "failed" in result["conflicting_factors"][0].lower()


def test_valid_structured_response_is_accepted():
    result = AIMarketAnalyst(
        api_key="test-key",
        model="test-model",
        client=FakeClient(output_text=valid_response()),
    ).analyze(market_data())

    assert result["action"] == "BUY_CANDIDATE"
    assert result["data_quality"] == "VALID"
    assert result["symbol"] == "BTC/USDT"
    assert result["confidence"] == 70