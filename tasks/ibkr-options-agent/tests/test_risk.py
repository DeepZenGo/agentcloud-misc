"""Unit tests that do not require IBKR / LLM connectivity."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from risk import AccountSnapshot, ProposedTrade, check_trade, estimate_premium_notional
from session import in_session
from settings import RiskConfig


def test_estimate_premium_notional():
    # 3 contracts @ 0.73 → 3 * 0.73 * 100 = 219
    assert estimate_premium_notional(3, 0.73) == pytest.approx(219.0)


def test_blocks_oversized_day6_style_position():
    """Day-6 style ~41% of a ~$530 account on one RIVN call should be blocked."""
    risk = RiskConfig(max_position_pct=0.15, allow_live=False)
    account = AccountSnapshot(equity=529.02, open_option_premium=0.0, orders_today=0)
    trade = ProposedTrade(
        symbol="RIVN",
        action="BUY",
        quantity=3,
        limit_price=0.73,
        right="C",
        strike=17.5,
        expiry="20240719",
    )
    decision = check_trade(trade, account, risk, dry_run=True)
    assert decision.ok is False
    assert "max_position_pct" in decision.reason
    assert decision.capped_qty >= 0
    # 15% of 529.02 ≈ 79.35 → at most 1 contract @ 0.73 (73)
    assert decision.capped_qty <= 1


def test_allows_small_position():
    risk = RiskConfig(max_position_pct=0.15, allow_live=False)
    account = AccountSnapshot(equity=1000.0, open_option_premium=0.0, orders_today=0)
    trade = ProposedTrade(
        symbol="RIVN",
        action="BUY",
        quantity=1,
        limit_price=0.50,
        right="C",
        strike=17.5,
        expiry="20260717",
    )
    decision = check_trade(trade, account, risk, dry_run=True)
    assert decision.ok is True


def test_live_blocked_without_allow_live():
    risk = RiskConfig(allow_live=False)
    account = AccountSnapshot(equity=1000.0, open_option_premium=0.0, orders_today=0)
    trade = ProposedTrade(
        symbol="RIVN",
        action="BUY",
        quantity=1,
        limit_price=0.50,
        right="C",
        strike=17.5,
        expiry="20260717",
    )
    decision = check_trade(trade, account, risk, dry_run=False)
    assert decision.ok is False
    assert "allow_live" in decision.reason


def test_session_weekday_rth():
    tz = ZoneInfo("America/New_York")
    # Wednesday 10:00 ET — in session
    wed = datetime(2026, 7, 8, 10, 0, tzinfo=tz)
    assert in_session(wed) is True
    # Wednesday 09:00 ET — before window
    early = datetime(2026, 7, 8, 9, 0, tzinfo=tz)
    assert in_session(early) is False
    # Saturday — closed
    sat = datetime(2026, 7, 11, 12, 0, tzinfo=tz)
    assert in_session(sat) is False
