from dataclasses import dataclass

from .config import settings


@dataclass(frozen=True)
class RiskSettings:
    initial_capital: float = settings.initial_capital
    risk_per_trade: float = settings.risk_per_trade
    daily_loss_limit: float = settings.daily_loss_limit
    max_drawdown: float = settings.max_drawdown
    max_positions: int = settings.max_open_positions
    max_total_exposure: float = settings.max_total_exposure
    fee_rate: float = settings.fee_rate
    slippage_rate: float = settings.slippage_rate
    min_notional: float = settings.min_notional
    stale_seconds: int = settings.stale_seconds
    min_confidence: int = settings.min_confidence
    min_risk_reward: float = settings.min_risk_reward


@dataclass(frozen=True)
class TradePlan:
    signal_id: str
    symbol: str
    entry: float
    stop: float
    target: float
    confidence: int
    regime: str
    reason: str
    timeframe: str = "15m"
