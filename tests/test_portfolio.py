import pytest

from portfolio import PortfolioError, calculate_portfolio


def sample_position():
    return {
        "id": "paper-position-1",
        "symbol": "BTC/USDT",
        "qty": 1.0,
        "entry": 100.0,
        "entry_fee": 0.10,
        "entry_slippage": 0.05,
    }


def test_equity_uses_current_bid_not_entry_price():
    result = calculate_portfolio(
        cash=800.0,
        realized_pnl=0.0,
        prior_equity_peak=1000.0,
        positions=[sample_position()],
        bid_prices={"BTC/USDT": 120.0},
        fee_rate=0.001,
        slippage_rate=0.0005,
    )

    position = result["positions"][0]

    assert position["entry_price"] == 100.0
    assert position["mark_price"] == 120.0
    assert result["equity"] > 900.0
    assert result["equity"] != 900.0
    assert result["unrealized_pnl"] > 0.0


def test_liquidation_value_includes_fee_and_slippage():
    result = calculate_portfolio(
        cash=800.0,
        realized_pnl=0.0,
        prior_equity_peak=1000.0,
        positions=[sample_position()],
        bid_prices={"BTC/USDT": 100.0},
        fee_rate=0.001,
        slippage_rate=0.0005,
    )

    position = result["positions"][0]

    assert position["gross_market_value"] == 100.0
    assert position["estimated_exit_fee"] == pytest.approx(0.10)
    assert position["estimated_exit_slippage"] == pytest.approx(0.05)
    assert position["liquidation_value"] == pytest.approx(99.85)
    assert position["unrealized_pnl"] == pytest.approx(-0.30)


def test_missing_bid_blocks_portfolio_valuation():
    with pytest.raises(PortfolioError, match="No valid current bid"):
        calculate_portfolio(
            cash=800.0,
            realized_pnl=0.0,
            prior_equity_peak=1000.0,
            positions=[sample_position()],
            bid_prices={},
            fee_rate=0.001,
            slippage_rate=0.0005,
        )


def test_drawdown_uses_current_market_value():
    result = calculate_portfolio(
        cash=800.0,
        realized_pnl=0.0,
        prior_equity_peak=1000.0,
        positions=[sample_position()],
        bid_prices={"BTC/USDT": 80.0},
        fee_rate=0.001,
        slippage_rate=0.0005,
    )

    assert result["equity"] < 1000.0
    assert result["drawdown"] > 0.0
    assert result["equity_peak"] == 1000.0