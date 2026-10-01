from .models import RiskSettings, TradePlan
class RiskError(ValueError): pass
def position_size(settings, equity, cash, entry, stop):
 if entry<=0 or stop<=0 or stop>=entry: raise RiskError('Invalid BUY entry or Stop-Loss.')
 risk=settings.risk_per_trade*equity
 unit_risk=(entry-stop)+(entry*settings.fee_rate)+(entry*settings.slippage_rate)
 qty=risk/unit_risk
 return max(0.0,min(qty,cash/(entry*(1+settings.fee_rate+settings.slippage_rate)),(equity*settings.max_total_exposure)/entry))
def validate(settings, plan, account, positions, market_fresh=True):
 if account['emergency_locked']: return False,'Trade rejected because the emergency risk lock is active.'
 if account['daily_locked']: return False,'Trade rejected because daily loss limit has already been reached.'
 if account['drawdown_locked']: return False,'Trade rejected because maximum drawdown protection is active.'
 if not market_fresh: return False,'Trade rejected because market data is stale or unavailable.'
 if len(positions)>=settings.max_positions: return False,'Trade rejected because maximum open positions has been reached.'
 if any(p['symbol']==plan.symbol for p in positions): return False,'Trade rejected because a position for this symbol is already open.'
 if plan.confidence<60: return False,'Trade rejected because confidence is below 60.'
 if plan.entry<=0 or plan.stop<=0 or plan.stop>=plan.entry: return False,'Trade rejected because Stop-Loss is invalid.'
 if plan.target<=plan.entry or (plan.target-plan.entry)/(plan.entry-plan.stop)<2: return False,'Trade rejected because risk/reward is below 1:2.'
 return True,'Risk checks passed.'
