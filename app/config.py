import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_text(name: str, default: str) -> str:
    return os.getenv(name, default).strip() or default


@dataclass(frozen=True)
class Settings:
    initial_capital: float
    risk_per_trade: float
    daily_loss_limit: float
    max_drawdown: float
    max_open_positions: int
    max_total_exposure: float
    fee_rate: float
    slippage_rate: float
    min_notional: float
    max_spread_bps: float
    stale_seconds: int
    supported_symbols: tuple[str, ...]
    primary_timeframe: str
    trend_timeframe: str
    min_confidence: int
    min_risk_reward: float
    atr_stop_multiplier: float
    atr_target_multiplier: float
    monitor_interval_seconds: int
    openai_model: str
    paper_trading: bool = True
    live_execution: bool = False


def load_settings() -> Settings:
    symbols = tuple(
        symbol.strip().upper()
        for symbol in env_text(
            "SUPPORTED_SYMBOLS",
            "BTC/USDT,ETH/USDT",
        ).split(",")
        if symbol.strip()
    )

    return Settings(
        initial_capital=env_float("INITIAL_CAPITAL", 1000.0),
        risk_per_trade=env_float("RISK_PER_TRADE", 0.005),
        daily_loss_limit=env_float("DAILY_LOSS_LIMIT", 0.015),
        max_drawdown=env_float("MAX_DRAWDOWN", 0.10),
        max_open_positions=env_int("MAX_OPEN_POSITIONS", 3),
        max_total_exposure=env_float("MAX_TOTAL_EXPOSURE", 0.50),
        fee_rate=env_float("FEE_RATE", 0.001),
        slippage_rate=env_float("SLIPPAGE_RATE", 0.0005),
        min_notional=env_float("MIN_NOTIONAL", 10.0),
        max_spread_bps=env_float("MAX_SPREAD_BPS", 15.0),
        stale_seconds=env_int("STALE_SECONDS", 90),
        supported_symbols=symbols,
        primary_timeframe=env_text("PRIMARY_TIMEFRAME", "15m"),
        trend_timeframe=env_text("TREND_TIMEFRAME", "1h"),
        min_confidence=env_int("MIN_CONFIDENCE", 60),
        min_risk_reward=env_float("MIN_RISK_REWARD", 2.0),
        atr_stop_multiplier=env_float("ATR_STOP_MULTIPLIER", 1.5),
        atr_target_multiplier=env_float("ATR_TARGET_MULTIPLIER", 3.2),
        monitor_interval_seconds=env_int(
            "MONITOR_INTERVAL_SECONDS",
            15,
        ),
        openai_model=env_text("OPENAI_MODEL", "gpt-4.1-mini"),
    )


settings = load_settings()
