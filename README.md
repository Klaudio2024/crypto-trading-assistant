# Crypto Trading Assistant

**PAPER TRADING ONLY.** This project does not implement live trading, leverage,
futures, margin, martingale, exchange order execution, or withdrawal actions.

## Current scope

The application provides a persistent Paper Trading foundation with:

- SQLite account state, audit journal, Paper positions, fees and slippage.
- Risk limits, emergency lock, daily-loss lock and drawdown lock.
- Binance public market data for `BTC/USDT` and `ETH/USDT`.
- Closed-candle deterministic strategy signals using EMA, RSI, ATR, volume and spread checks.
- Paper Stop-Loss and Take-Profit monitoring.
- A FastAPI dashboard and API.
- `live_execution=False` in all execution flows.

The project is under active development. AI analysis, autonomous worker operation,
mark-to-market accounting, historical backtesting and walk-forward validation
are not yet complete in this branch.

## Run locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the canonical application:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The legacy command below remains compatible, but new documentation and tooling
must use `main:app`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Tests

```bash
python -m pytest -q
```

## Security

- Never commit `.env`, `OPENAI_API_KEY`, exchange keys or `trading.db`.
- `.env` is for local configuration only.
- API keys must never be exposed through HTML, JavaScript, logs, API responses
  or Git history.
- This project must remain in `PAPER_TRADING` mode.
