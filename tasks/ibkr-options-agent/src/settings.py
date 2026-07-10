"""Shared settings loaded from env + config.yaml."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), extra="ignore")

    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_base_url: str = Field(default="https://api.openai.com/v1", alias="LLM_BASE_URL")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")

    ibkr_host: str = Field(default="127.0.0.1", alias="IBKR_HOST")
    ibkr_port: int = Field(default=7497, alias="IBKR_PORT")
    ibkr_client_id: int = Field(default=17, alias="IBKR_CLIENT_ID")

    dry_run: bool = Field(default=True, alias="DRY_RUN")


class RiskConfig(BaseModel):
    max_position_pct: float = 0.15
    max_total_options_pct: float = 0.40
    max_contracts_per_order: int = 5
    max_orders_per_day: int = 8
    min_account_equity: float = 200
    allow_live: bool = False


class AppConfig(BaseModel):
    raw: dict[str, Any]
    risk: RiskConfig
    underlyings: list[str]
    confirmations: list[str]
    options: dict[str, Any]
    loop: dict[str, Any]
    journal: dict[str, Any]
    agent: dict[str, Any]
    account_id: str = ""
    currency: str = "USD"


def load_config(path: Path | None = None) -> tuple[EnvSettings, AppConfig]:
    load_dotenv(ROOT / ".env")
    env = EnvSettings()
    cfg_path = path or (ROOT / "config.yaml")
    with cfg_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    account = raw.get("account") or {}
    universe = raw.get("universe") or {}
    app = AppConfig(
        raw=raw,
        risk=RiskConfig(**(raw.get("risk") or {})),
        underlyings=list(universe.get("underlyings") or []),
        confirmations=list(universe.get("confirmations") or []),
        options=dict(raw.get("options") or {}),
        loop=dict(raw.get("loop") or {}),
        journal=dict(raw.get("journal") or {}),
        agent=dict(raw.get("agent") or {}),
        account_id=str(account.get("account_id") or ""),
        currency=str(account.get("currency") or "USD"),
    )
    # Allow env override for dry-run clarity
    if os.getenv("DRY_RUN", "").lower() in {"0", "false", "no"}:
        env.dry_run = False
    return env, app
