"""Portfolio calculations for Paper Trading only.

Open long positions are valued with the latest valid bid price.
The bid is used because it is the conservative price available when selling.
No trade execution, exchange calls, or database writes happen in this module.
"""

from __future__ import annotations

from math import isfinite


class PortfolioError(ValueError):
    """Raised when portfolio values are missing or invalid."""


def _number(value: object, name: str, *, positive: bool = False) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise PortfolioError(f"{name} must be a number.") from exc

    if not isfinite(result):
        raise PortfolioError(f"{name} must be finite.")

    if positive and result <= 0:
        raise PortfolioError(f"{name} must be greater than zero.")

    if not positive and result < 0:
        raise PortfolioError(f"{name} cannot be negative.")

    return result


def liquidation_value(
    quantity: float,
    bid_price: float,
    fee_rate: float,
    slippage_rate: float,
) -> dict[str, float]:
    """Calculate conservative exit value for an open long position."""
    qty = _number(quantity, "quantity", positive=True)
    bid = _number(bid_price, "bid_price", positive=True)
    fee = _number(fee_rate, "fee_rate")
    slippage = _number(slippage_rate, "slippage_rate")

    gross_value = qty * bid
    estimated_exit_fee = gross_value * fee
    estimated_exit_slippage = gross_value * slippage
    net_value = gross_value - estimated_exit_fee - estimated_exit_slippage

    if net_value < 0:
        raise PortfolioError("liquidation value cannot be negative.")

    return {
        "gross_market_value": gross_value,
        "estimated_exit_fee": estimated_exit_fee,
        "estimated_exit_slippage": estimated_exit_slippage,
        "liquidation_value": net_value,
    }


def value_position(
    position: dict[str, object],
    bid_price: float,
    fee_rate: float,
    slippage_rate: float,
) -> dict[str, object]:
    """Value one open Paper long position using its current bid price."""
    quantity = _number(position["qty"], "position quantity", positive=True)
    entry = _number(position["entry"], "entry price", positive=True)
    entry_fee = _number(position["entry_fee"], "entry fee")
    entry_slippage = _number(position["entry_slippage"], "entry slippage")
    bid = _number(bid_price, "bid price", positive=True)

    exit_values = liquidation_value(
        quantity,
        bid,
        fee_rate,
        slippage_rate,
    )

    entry_cost = (quantity * entry) + entry_fee + entry_slippage
    unrealized_pnl = exit_values["liquidation_value"] - entry_cost

    return {
        "position_id": str(position["id"]),
        "symbol": str(position["symbol"]),
        "quantity": quantity,
        "entry_price": entry,
        "mark_price": bid,
        "entry_cost": entry_cost,
        "unrealized_pnl": unrealized_pnl,
        **exit_values,
    }


def calculate_portfolio(
    *,
    cash: float,
    realized_pnl: float,
    prior_equity_peak: float,
    positions: list[dict[str, object]],
    bid_prices: dict[str, float],
    fee_rate: float,
    slippage_rate: float,
) -> dict[str, object]:
    """Calculate Paper Trading equity with conservative mark-to-market prices."""
    cash_value = _number(cash, "cash")
    peak_before = _number(
        prior_equity_peak,
        "prior_equity_peak",
        positive=True,
    )

    try:
        realized_value = float(realized_pnl)
    except (TypeError, ValueError) as exc:
        raise PortfolioError("realized_pnl must be a number.") from exc

    if not isfinite(realized_value):
        raise PortfolioError("realized_pnl must be finite.")

    valued_positions: list[dict[str, object]] = []

    for position in positions:
        symbol = str(position["symbol"])

        if symbol not in bid_prices:
            raise PortfolioError(
                f"No valid current bid is available for {symbol}."
            )

        valued_positions.append(
            value_position(
                position,
                bid_prices[symbol],
                fee_rate,
                slippage_rate,
            )
        )

    gross_exposure = sum(
        float(item["gross_market_value"])
        for item in valued_positions
    )
    liquidation_total = sum(
        float(item["liquidation_value"])
        for item in valued_positions
    )
    unrealized_total = sum(
        float(item["unrealized_pnl"])
        for item in valued_positions
    )

    equity = cash_value + liquidation_total
    equity_peak = max(peak_before, equity)
    drawdown = max(0.0, (equity_peak - equity) / equity_peak)

    return {
        "cash": cash_value,
        "realized_pnl": realized_value,
        "unrealized_pnl": unrealized_total,
        "equity": equity,
        "equity_peak": equity_peak,
        "drawdown": drawdown,
        "gross_exposure": gross_exposure,
        "net_liquidation_value": liquidation_total,
        "positions": valued_positions,
    }