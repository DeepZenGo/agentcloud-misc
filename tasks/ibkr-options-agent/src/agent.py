"""LLM decision layer — structured trade / hold / close actions."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

log = logging.getLogger(__name__)
PROMPTS = Path(__file__).resolve().parents[1] / "prompts"


class TradeAction(BaseModel):
    type: Literal["hold", "buy_to_open", "sell_to_close", "sell_to_open", "buy_to_close"]
    underlying: str | None = None
    right: Literal["C", "P"] | None = None
    expiry: str | None = Field(default=None, description="YYYYMMDD")
    strike: float | None = None
    quantity: int | None = None
    limit_price: float | None = None
    rationale: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class AgentDecision(BaseModel):
    market_view: str
    confirmation: str
    action: TradeAction


class TradingAgent:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 1200,
    ) -> None:
        if not api_key:
            raise RuntimeError("LLM_API_KEY is required")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = (PROMPTS / "system.md").read_text(encoding="utf-8")

    def decide(self, context: dict[str, Any]) -> AgentDecision:
        user = (
            "Given the market snapshot and account state, return ONE JSON object "
            "matching the schema. Prefer hold when edge is unclear.\n\n"
            f"CONTEXT:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
        )
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user},
            ],
        )
        raw = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
            return AgentDecision.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            log.error("Invalid agent JSON: %s | raw=%s", exc, raw[:500])
            return AgentDecision(
                market_view="parse_error",
                confirmation="n/a",
                action=TradeAction(type="hold", rationale=f"parse_error: {exc}"),
            )
