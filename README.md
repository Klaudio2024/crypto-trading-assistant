# Crypto Trading Assistant v0.2

**PAPER TRADING ONLY.** No Binance/Kraken credentials or live order code exists.

This release refactors the existing prototype into a persistent paper-trading risk and accounting core: SQLite account state, risk locks, positions, idempotent signals, fees/slippage, stop/target monitoring, emergency lock, audit events, and calculation tests.

Run: `pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000`
Test: `pytest -q`

Not yet implemented: market-data adapter, closed-candle EMA/RSI/ATR strategy, Binance symbol metadata sync, historical backtesting, walk-forward validation, notifications. These are intentionally not claimed as complete.
