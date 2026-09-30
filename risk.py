from .models import RiskSettings, TradePlan

class RiskError(ValueError): pass

def size_position(settings: RiskSettings, entry: float, stop: float, available: float) -> float:
    if entry <= 0 or stop <= 0 or stop >= entry: raise RiskError("Invalid long entry or stop")
    risk_amount = settings.capital * settings.risk_per_trade
    quantity = risk_amount / (entry - stop)
    return max(0.0, min(quantity, available / entry, settings.capital * settings.max_position_exposure / entry))

def check_trade(settings: RiskSettings, plan: TradePlan, daily_pnl: float, weekly_pnl: float, drawdown: float, open_positions: int, stale: bool=False, emergency: bool=False):
    if emergency: return False, "Trade rejected because the emergency risk lock is active."
    if stale: return False, "Trade rejected because market data is stale."
    if daily_pnl <= -settings.capital * settings.daily_loss_limit: return False, "Trade rejected because daily loss limit has already been reached."
    if weekly_pnl <= -settings.capital * settings.weekly_loss_limit: return False, "Trade rejected because weekly loss limit has already been reached."
    if drawdown >= settings.max_drawdown: return False, "Trade rejected because maximum drawdown protection is active."
    if open_positions >= settings.max_positions: return False, "Trade rejected because maximum open positions has been reached."
    if plan.confidence < 60: return False, "Trade rejected because confidence is below 60."
    if plan.stop >= plan.entry: return False, "Trade rejected because the stop loss is invalid."
    if (plan.target-plan.entry)/(plan.entry-plan.stop) < 2: return False, "Trade rejected because risk/reward is below 1:2."
    return True, "Risk checks passed."
