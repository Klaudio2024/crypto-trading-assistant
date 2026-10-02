import main


def test_ai_status_endpoint_is_paper_only(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_ai_status",
        lambda: {
            "available": False,
            "status": "unavailable",
            "reason": "OPENAI_API_KEY is not configured.",
        },
    )

    result = main.ai_status_endpoint()

    assert result["mode"] == "PAPER_TRADING"
    assert result["live_execution"] is False
    assert result["ai"]["status"] == "unavailable"


def test_ai_analyze_endpoint_does_not_open_trade(monkeypatch):
    monkeypatch.setattr(
        main,
        "analyze_symbol",
        lambda symbol: {
            "symbol": symbol,
            "action": "BUY_CANDIDATE",
            "data_quality": "VALID",
            "confidence": 70,
        },
    )

    result = main.ai_analyze_endpoint("BTC/USDT")

    assert result["mode"] == "PAPER_TRADING"
    assert result["live_execution"] is False
    assert result["analysis"]["action"] == "BUY_CANDIDATE"
    assert "opened" not in result
    assert "paper_result" not in result