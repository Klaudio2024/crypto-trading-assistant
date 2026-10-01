from __future__ import annotations

from statistics import mean

from market_data import Candle, MarketDataError, closed_candles, market_snapshot


EMA_FAST_PERIOD = 20
EMA_SLOW_PERIOD = 50
RSI_PERIOD = 14
ATR_PERIOD = 14

MAX_SPREAD_BPS = 15.0
MIN_VOLUME_RATIO = 0.80

STOP_ATR_MULTIPLIER = 1.5
TARGET_ATR_MULTIPLIER = 3.2


def _closes(candles: list[Candle]) -> list[float]:
    return [candle.close for candle in candles]


def ema(values: list[float], period: int) -> float:
    if len(values) < period:
        raise ValueError(
            f"EMA requires at least {period} values."
        )

    multiplier = 2 / (period + 1)
    result = mean(values[:period])

    for value in values[period:]:
        result = (value - result) * multiplier + result

    return result


def rsi(values: list[float], period: int = RSI_PERIOD) -> float:
    if len(values) < period + 1:
        raise ValueError(
            f"RSI requires at least {period + 1} close values."
        )

    changes = [
        values[index] - values[index - 1]
        for index in range(1, len(values))
    ]

    gains = [max(change, 0.0) for change in changes]
    losses = [abs(min(change, 0.0)) for change in changes]

    average_gain = mean(gains[-period:])
    average_loss = mean(losses[-period:])

    if average_loss == 0:
        return 100.0

    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))


def atr(candles: list[Candle], period: int = ATR_PERIOD) -> float:
    if len(candles) < period + 1:
        raise ValueError(
            f"ATR requires at least {period + 1} candles."
        )

    true_ranges: list[float] = []

    for index in range(1, len(candles)):
        current = candles[index]
        previous_close = candles[index - 1].close

        true_range = max(
            current.high - current.low,
            abs(current.high - previous_close),
            abs(current.low - previous_close),
        )

        true_ranges.append(true_range)

    return mean(true_ranges[-period:])


def volume_ratio(candles: list[Candle], period: int = 20) -> float:
    if len(candles) < period + 1:
        raise ValueError(
            f"Volume filter requires at least {period + 1} candles."
        )

    current_volume = candles[-1].volume
    historical_volumes = [
        candle.volume
        for candle in candles[-period - 1:-1]
    ]

    average_volume = mean(historical_volumes)

    if average_volume <= 0:
        return 0.0

    return current_volume / average_volume


def evaluate(
    symbol: str = "BTC/USDT",
    interval: str = "15m",
) -> dict[str, object]:
    try:
        snapshot = market_snapshot(symbol, interval)
        candles = snapshot["candles"]

        if not isinstance(candles, list):
            raise MarketDataError(
                "Market candles are unavailable."
            )

        primary_candles = candles
        primary_closes = _closes(primary_candles)

        trend_candles = closed_candles(
            symbol,
            interval="1h",
            limit=100,
        )
        trend_closes = _closes(trend_candles)

        quote = snapshot["quote"]

        if not isinstance(quote, dict):
            raise MarketDataError(
                "Market quote is unavailable."
            )

        bid = float(quote["bid"])
        ask = float(quote["ask"])
        spread_bps = float(quote["spread_bps"])

        ema_fast = ema(primary_closes, EMA_FAST_PERIOD)
        ema_slow = ema(primary_closes, EMA_SLOW_PERIOD)

        trend_ema_fast = ema(trend_closes, EMA_FAST_PERIOD)
        trend_ema_slow = ema(trend_closes, EMA_SLOW_PERIOD)

        rsi_value = rsi(primary_closes, RSI_PERIOD)
        atr_value = atr(primary_candles, ATR_PERIOD)
        current_volume_ratio = volume_ratio(primary_candles)

        latest_closed_price = primary_closes[-1]

        trend_bullish = trend_ema_fast > trend_ema_slow
        momentum_bullish = ema_fast > ema_slow
        price_confirmed = latest_closed_price > ema_fast
        rsi_confirmed = 52 <= rsi_value <= 68
        volume_confirmed = current_volume_ratio >= MIN_VOLUME_RATIO
        spread_acceptable = spread_bps <= MAX_SPREAD_BPS

        reasons: list[str] = []

        if not spread_acceptable:
            reasons.append(
                f"NO_TRADE: spread is too high at {spread_bps:.2f} bps."
            )

        if not trend_bullish:
            reasons.append(
                "WAIT: 1h EMA20 is below or equal to EMA50."
            )

        if not momentum_bullish:
            reasons.append(
                "EXIT: 15m EMA20 is below or equal to EMA50."
            )

        if not price_confirmed:
            reasons.append(
                "WAIT: latest closed price is below EMA20."
            )

        if not rsi_confirmed:
            reasons.append(
                f"WAIT: RSI14 is {rsi_value:.2f}; required range is 52 to 68."
            )

        if not volume_confirmed:
            reasons.append(
                f"WAIT: volume ratio is {current_volume_ratio:.2f}; minimum is {MIN_VOLUME_RATIO:.2f}."
            )

        entry = ask
        stop = entry - (atr_value * STOP_ATR_MULTIPLIER)
        target = entry + (atr_value * TARGET_ATR_MULTIPLIER)

        risk_per_unit = entry - stop
        reward_per_unit = target - entry
        risk_reward = (
            reward_per_unit / risk_per_unit
            if risk_per_unit > 0
            else 0.0
        )

        action = "WAIT"

        if not spread_acceptable:
            action = "NO_TRADE"

        elif not momentum_bullish:
            action = "EXIT"

        elif (
            trend_bullish
            and momentum_bullish
            and price_confirmed
            and rsi_confirmed
            and volume_confirmed
            and risk_reward >= 2.0
        ):
            action = "BUY"
            reasons.append(
                "BUY: 1h and 15m trend, RSI, volume, spread, and risk/reward filters passed."
            )

        if not reasons:
            reasons.append(
                "WAIT: market conditions are not fully confirmed."
            )

        confidence = 0

        for passed in [
            trend_bullish,
            momentum_bullish,
            price_confirmed,
            rsi_confirmed,
            volume_confirmed,
            spread_acceptable,
        ]:
            if passed:
                confidence += 15

        confidence = min(confidence, 90)

        return {
            "symbol": snapshot["symbol"],
            "timeframe": interval,
            "action": action,
            "reason": " ".join(reasons),
            "confidence": confidence,
            "market_fresh": bool(snapshot["market_fresh"]),
            "entry": round(entry, 4),
            "stop": round(stop, 4),
            "target": round(target, 4),
            "risk_reward": round(risk_reward, 2),
            "indicators": {
                "ema20": round(ema_fast, 4),
                "ema50": round(ema_slow, 4),
                "trend_ema20_1h": round(trend_ema_fast, 4),
                "trend_ema50_1h": round(trend_ema_slow, 4),
                "rsi14": round(rsi_value, 2),
                "atr14": round(atr_value, 4),
                "volume_ratio": round(current_volume_ratio, 2),
                "spread_bps": round(spread_bps, 4),
                "bid": bid,
                "ask": ask,
                "last_closed_price": latest_closed_price,
            },
            "last_closed_candle_at": snapshot[
                "last_closed_candle_at"
            ],
        }

    except (MarketDataError, ValueError) as exc:
        return {
            "symbol": symbol,
            "timeframe": interval,
            "action": "NO_TRADE",
            "reason": f"NO_TRADE: market analysis unavailable: {exc}",
            "confidence": 0,
            "market_fresh": False,
            "entry": None,
            "stop": None,
            "target": None,
            "risk_reward": None,
            "indicators": {},
            "last_closed_candle_at": None,
        }
