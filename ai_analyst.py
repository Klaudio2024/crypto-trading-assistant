"""AI Market Analyst for Paper Trading only.

This module never opens, closes, or sends exchange orders.
It only returns a structured market-analysis result.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError


load_dotenv()


class AIAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    market_regime: str
    directional_bias: str
    action: str
    confidence: int = Field(ge=0, le=100)
    supporting_factors: list[str]
    conflicting_factors: list[str]
    invalidation_conditions: list[str]
    data_timestamp: str
    data_quality: str
    summary: str


ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "symbol": {"type": "string"},
        "market_regime": {
            "type": "string",
            "enum": [
                "TRENDING_UP",
                "TRENDING_DOWN",
                "SIDEWAYS",
                "HIGH_VOLATILITY",
                "UNKNOWN",
            ],
        },
        "directional_bias": {
            "type": "string",
            "enum": ["BULLISH", "BEARISH", "NEUTRAL"],
        },
        "action": {
            "type": "string",
            "enum": ["BUY_CANDIDATE", "SELL_CANDIDATE", "HOLD"],
        },
        "confidence": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
        },
        "supporting_factors": {
            "type": "array",
            "items": {"type": "string"},
        },
        "conflicting_factors": {
            "type": "array",
            "items": {"type": "string"},
        },
        "invalidation_conditions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "data_timestamp": {"type": "string"},
        "data_quality": {
            "type": "string",
            "enum": ["VALID", "INVALID"],
        },
        "summary": {"type": "string"},
    },
    "required": [
        "symbol",
        "market_regime",
        "directional_bias",
        "action",
        "confidence",
        "supporting_factors",
        "conflicting_factors",
        "invalidation_conditions",
        "data_timestamp",
        "data_quality",
        "summary",
    ],
}


def unavailable_analysis(
    symbol: str,
    data_timestamp: str | None,
    reason: str,
) -> dict[str, Any]:
    """Return the safe result used for missing, stale, or invalid AI data."""
    return {
        "symbol": symbol,
        "market_regime": "UNKNOWN",
        "directional_bias": "NEUTRAL",
        "action": "HOLD",
        "confidence": 0,
        "supporting_factors": [],
        "conflicting_factors": [reason],
        "invalidation_conditions": [reason],
        "data_timestamp": data_timestamp or "",
        "data_quality": "INVALID",
        "summary": "AI analysis is unavailable. No paper trade may be opened.",
    }


class AIMarketAnalyst:
    """OpenAI Responses API client with safe Paper Trading fallback."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 15.0,
        min_call_interval_seconds: float = 5.0,
        client: Any | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL")
        self.timeout_seconds = timeout_seconds
        self.min_call_interval_seconds = min_call_interval_seconds
        self._last_call_at = 0.0
        self._client = client

    def status(self) -> dict[str, object]:
        """Return status without exposing keys or secret values."""
        if not self.api_key:
            return {
                "available": False,
                "status": "unavailable",
                "reason": "OPENAI_API_KEY is not configured.",
            }

        if not self.model:
            return {
                "available": False,
                "status": "unavailable",
                "reason": "OPENAI_MODEL is not configured.",
            }

        return {
            "available": True,
            "status": "available",
            "reason": None,
        }

    def analyze(self, market_data: dict[str, Any]) -> dict[str, Any]:
        """Ask AI for analysis. Any failure returns HOLD, never BUY."""
        symbol = str(market_data.get("symbol", "UNKNOWN"))
        data_timestamp = market_data.get("data_timestamp")

        if not bool(market_data.get("market_fresh")):
            return unavailable_analysis(
                symbol,
                data_timestamp,
                "Market data is stale or unavailable.",
            )

        if not data_timestamp:
            return unavailable_analysis(
                symbol,
                None,
                "Market data timestamp is missing.",
            )

        current_status = self.status()

        if not current_status["available"]:
            return unavailable_analysis(
                symbol,
                data_timestamp,
                str(current_status["reason"]),
            )

        now = time.monotonic()

        if now - self._last_call_at < self.min_call_interval_seconds:
            return unavailable_analysis(
                symbol,
                data_timestamp,
                "AI call rate limit is active.",
            )

        try:
            client = self._client or OpenAI(
                api_key=self.api_key,
                timeout=self.timeout_seconds,
            )

            response = client.responses.create(
                model=self.model,
                store=False,
                instructions=(
                    "You are a professional crypto market analyst. "
                    "Use only the supplied market data. "
                    "Never invent prices, indicators, news, or timestamps. "
                    "Return HOLD when data is incomplete, stale, conflicting, "
                    "or insufficient. You cannot choose position size, "
                    "change risk limits, open trades, or call tools."
                ),
                input=json.dumps(market_data, separators=(",", ":")),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "paper_market_analysis",
                        "strict": True,
                        "schema": ANALYSIS_SCHEMA,
                    }
                },
            )

            self._last_call_at = time.monotonic()

            parsed = json.loads(response.output_text)
            analysis = AIAnalysis.model_validate(parsed)

            if analysis.symbol != symbol:
                return unavailable_analysis(
                    symbol,
                    data_timestamp,
                    "AI returned a different symbol.",
                )

            if analysis.data_timestamp != data_timestamp:
                return unavailable_analysis(
                    symbol,
                    data_timestamp,
                    "AI returned a different data timestamp.",
                )

            if analysis.data_quality != "VALID":
                return unavailable_analysis(
                    symbol,
                    data_timestamp,
                    "AI marked market data as invalid.",
                )

            return analysis.model_dump()

        except (
            json.JSONDecodeError,
            ValidationError,
            KeyError,
            TypeError,
            ValueError,
        ):
            return unavailable_analysis(
                symbol,
                data_timestamp,
                "AI returned an invalid structured response.",
            )

        except Exception:
            return unavailable_analysis(
                symbol,
                data_timestamp,
                "AI request failed or timed out.",
            )