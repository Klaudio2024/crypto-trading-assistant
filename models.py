from dataclasses import dataclass
from enum import Enum

class Mode(str, Enum):
    SIMULATION = "SIMULATION"
    PAPER = "PAPER_TRADING"
    LIVE = "LIVE"

@dataclass(frozen=True)
class RiskSettings:
    capital: float = 1000.0
    risk_per_trade: float = 0.005
    max_positions: int = 3
    daily_loss_limit: float = 0.02
    weekly_loss_limit: float = 0.05
    max_drawdown: float = 0.10
    max_position_exposure: float = 0.25

@dataclass(frozen=True)
class TradePlan:
    symbol: str
    entry: float
    stop: float
    target: float
    confidence: int
    regime: str
    reason: str
