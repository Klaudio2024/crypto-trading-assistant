from dataclasses import dataclass
@dataclass(frozen=True)
class RiskSettings:
    initial_capital: float=1000.0
    risk_per_trade: float=0.005
    daily_loss_limit: float=0.02
    max_drawdown: float=0.10
    max_positions: int=3
    max_total_exposure: float=0.30
    fee_rate: float=0.001
    slippage_rate: float=0.0005
    min_notional: float=10.0
    stale_seconds: int=90
@dataclass(frozen=True)
class TradePlan:
    signal_id:str; symbol:str; entry:float; stop:float; target:float; confidence:int; regime:str; reason:str; timeframe:str='15m'
