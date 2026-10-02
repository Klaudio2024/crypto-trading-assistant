from math import isfinite

from .models import RiskSettings, TradePlan


class RiskError(ValueError):
    pass


def valid_number(value):
    return isinstance(value, (int, float)) and isfinite(value)


def risk_reward(entry, stop, target):
    if not all(valid_number(x) for x in (entry, stop, target)):
        return 0.0

    risk = entry - stop
    reward = target - entry

    if risk <= 0 or reward <= 0:
        return 0.0

    return reward / risk


def position_size(settings, equity, cash, entry, stop):
    values = (equity, cash, entry, stop)

    if not all(valid_number(x) for x in values):
        raise RiskError("Position values must be numbers.")

    if equity <= 0 or cash <= 0:
        raise RiskError("Equity and cash must be positive.")

    if entry <= 0 or stop <= 0 or stop >= entry:
        raise RiskError("Invalid BUY entry or Stop-Loss.")

    risk_budget = equity * settings.risk_per_trade
    unit_risk = (
        (entry - stop)
        + (entry * settings.fee_rate)
        + (entry * settings.slippage_rate)
    )

    if unit_risk <= 0:
        raise RiskError("Invalid position risk.")

    risk_quantity = risk_budget / unit_risk
    cash_quantity = cash / (
        entry * (1 + settings.fee_rate + settings.slippage_rate)
    )
    exposure_quantity = (
        equity * settings.max_total_exposure
    ) / entry

    return max(
        0.0,
        min(risk_quantity, cash_quantity, exposure_quantity),
    )


def validate(settings, plan, account, positions, market_fresh=True):
    if account.get("emergency_locked"):
        return False, "Trade rejected: emergency lock is active."

    if account.get("daily_locked"):
        return False, "Trade rejected: daily-loss lock is active."

    if account.get("drawdown_locked"):
        return False, "Trade rejected: drawdown lock is active."

    if not market_fresh:
        return False, "Trade rejected: market data is stale."

    if len(positions) >= settings.max_positions:
        return False, "Trade rejected: maximum open positions reached."

    if any(item.get("symbol") == plan.symbol for item in positions):
        return False, "Trade rejected: duplicate symbol."

    if plan.confidence < settings.min_confidence:
        return False, "Trade rejected: confidence is too low."

    if not all(
        valid_number(x)
        for x in (plan.entry, plan.stop, plan.target)
    ):
        return False, "Trade rejected: invalid price."

    if plan.entry <= 0 or plan.stop <= 0 or plan.stop >= plan.entry:
        return False, "Trade rejected: invalid stop."

    if plan.target <= plan.entry:
        return False, "Trade rejected: invalid target."

    if risk_reward(plan.entry, plan.stop, plan.target) < settings.min_risk_reward:
        return False, "Trade rejected: risk/reward is too low."

    return True, "Risk checks passed."