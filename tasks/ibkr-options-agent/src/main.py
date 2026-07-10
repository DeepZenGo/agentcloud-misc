#!/usr/bin/env python3
"""IBKR Options Agent — main loop.

Replicates the "AI agent trades US options" pattern on Interactive Brokers:
  market snapshot → LLM decision → risk gate → (paper/live) order → journal

Default is DRY_RUN=true. Requires local TWS or IB Gateway.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent import TradingAgent  # noqa: E402
from ibkr_client import IbkrClient  # noqa: E402
from journal import Journal  # noqa: E402
from risk import ProposedTrade, check_trade  # noqa: E402
from session import in_session  # noqa: E402
from settings import load_config  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("main")


def build_context(client: IbkrClient, app, account) -> dict[str, Any]:
    symbols = list(dict.fromkeys([*app.underlyings, *app.confirmations]))
    quotes = client.snapshot_universe(symbols)
    opt_cfg = app.options
    candidates = []
    for u in app.underlyings:
        for right in {str(opt_cfg.get("right") or "C").upper(), "P"}:
            try:
                found = client.list_option_candidates(
                    u,
                    right=right,
                    min_dte=int(opt_cfg.get("min_dte_days", 3)),
                    max_dte=int(opt_cfg.get("max_dte_days", 45)),
                    strike_band_pct=float(opt_cfg.get("strike_band_pct", 15)),
                )
                for c in found[:6]:
                    candidates.append(
                        {
                            "underlying": c.symbol,
                            "expiry": c.expiry,
                            "strike": c.strike,
                            "right": c.right,
                            "bid": c.bid,
                            "ask": c.ask,
                            "last": c.last,
                            "mid": c.mid,
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                log.warning("option chain %s %s failed: %s", u, right, exc)

    return {
        "quotes": {
            s: {"last": q.last, "bid": q.bid, "ask": q.ask, "mid": q.mid, "close": q.close}
            for s, q in quotes.items()
        },
        "positions": client.positions_brief(),
        "account": {
            "equity": account.equity,
            "open_option_premium": account.open_option_premium,
            "orders_today": account.orders_today,
        },
        "risk": app.risk.model_dump(),
        "universe": {"underlyings": app.underlyings, "confirmations": app.confirmations},
        "option_candidates": candidates,
        "dry_run": True,  # overwritten by caller
    }


def decision_to_trade(decision) -> ProposedTrade | None:
    a = decision.action
    if a.type == "hold":
        return None
    if not a.underlying or a.quantity is None or a.limit_price is None:
        return None
    if a.strike is None or not a.expiry or not a.right:
        return None

    if a.type in {"buy_to_open", "buy_to_close"}:
        action = "BUY"
    elif a.type in {"sell_to_close", "sell_to_open"}:
        action = "SELL"
    else:
        return None

    return ProposedTrade(
        symbol=a.underlying.upper(),
        action=action,
        quantity=int(a.quantity),
        limit_price=float(a.limit_price),
        right=a.right.upper(),
        strike=float(a.strike),
        expiry=str(a.expiry),
    )


def run_once(client: IbkrClient, agent: TradingAgent, journal: Journal, env, app) -> dict[str, Any]:
    account = client.account_snapshot()
    ctx = build_context(client, app, account)
    ctx["dry_run"] = env.dry_run

    decision = agent.decide(ctx)
    journal.write(
        "decision",
        {
            "market_view": decision.market_view,
            "confirmation": decision.confirmation,
            "action": decision.action.model_dump(),
            "equity": account.equity,
        },
    )
    log.info(
        "Decision: %s | %s | conf=%.2f",
        decision.action.type,
        decision.action.rationale,
        decision.action.confidence,
    )

    trade = decision_to_trade(decision)
    result: dict[str, Any] = {"decision": decision.model_dump(), "order": None}
    if trade is None:
        return result

    gate = check_trade(trade, account, app.risk, dry_run=env.dry_run)
    journal.write("risk_check", {"ok": gate.ok, "reason": gate.reason, "trade": trade.__dict__})
    if not gate.ok:
        log.warning("Risk blocked: %s", gate.reason)
        # Auto-resize once if risk suggested a positive capped qty
        if gate.capped_qty > 0 and trade.action == "BUY":
            trade.quantity = gate.capped_qty
            gate = check_trade(trade, account, app.risk, dry_run=env.dry_run)
            journal.write(
                "risk_check_retry",
                {"ok": gate.ok, "reason": gate.reason, "trade": trade.__dict__},
            )
            if not gate.ok:
                return result
        else:
            return result

    order = client.place_option_limit(trade, dry_run=env.dry_run)
    journal.write("order", order)
    result["order"] = order
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="IBKR Options Agent")
    parser.add_argument("--once", action="store_true", help="Single decision cycle then exit")
    parser.add_argument("--config", type=Path, default=None, help="Path to config.yaml")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Write a daily summary snapshot from current equity and exit",
    )
    args = parser.parse_args()

    env, app = load_config(args.config)
    journal = Journal(
        path=ROOT / app.journal.get("path", "logs/journal.jsonl"),
        daily_summary_path=ROOT / app.journal.get("daily_summary_path", "logs/daily_summary.md"),
    )

    client = IbkrClient(
        host=env.ibkr_host,
        port=env.ibkr_port,
        client_id=env.ibkr_client_id,
        account_id=app.account_id,
    )
    agent = TradingAgent(
        api_key=env.llm_api_key,
        base_url=env.llm_base_url,
        model=env.llm_model,
        temperature=float(app.agent.get("temperature", 0.2)),
        max_tokens=int(app.agent.get("max_tokens", 1200)),
    )

    client.connect()
    try:
        if args.summary:
            snap = client.account_snapshot()
            path = journal.write_daily_summary(
                equity_before=snap.equity,
                equity_after=snap.equity,
                notes="manual --summary snapshot",
                trades=[],
            )
            log.info("Wrote %s (equity=%.2f)", path, snap.equity)
            return 0

        loop_cfg = app.loop
        poll = int(loop_cfg.get("poll_seconds", 60))
        session_kwargs = {
            "tz_name": str(loop_cfg.get("timezone", "America/New_York")),
            "start": str(loop_cfg.get("session_start", "09:35")),
            "end": str(loop_cfg.get("session_end", "15:50")),
            "market_hours_only": bool(loop_cfg.get("market_hours_only", True)),
        }

        log.info(
            "Agent started dry_run=%s account=%s underlyings=%s",
            env.dry_run,
            client.account_id,
            app.underlyings,
        )

        while True:
            if in_session(**session_kwargs):
                try:
                    run_once(client, agent, journal, env, app)
                except Exception:  # noqa: BLE001
                    log.exception("cycle failed")
                    journal.write("error", {"msg": "cycle failed — see logs"})
            else:
                log.info("Outside session window — sleeping")

            if args.once:
                break
            time.sleep(poll)
    finally:
        client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
