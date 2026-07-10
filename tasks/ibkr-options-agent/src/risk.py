"""Hard risk gates before any order is sent."""

from __future__ import annotations

from dataclasses import dataclass

from settings import RiskConfig


@dataclass
class AccountSnapshot:
    equity: float
    open_option_premium: float  # sum of |premium * 100 * qty| for open option positions
    orders_today: int


@dataclass
class ProposedTrade:
    symbol: str
    action: str  # BUY / SELL
    quantity: int
    limit_price: float  # option premium per share
    right: str
    strike: float
    expiry: str  # YYYYMMDD


@dataclass
class RiskDecision:
    ok: bool
    reason: str
    capped_qty: int = 0


def estimate_premium_notional(qty: int, premium: float) -> float:
    """US equity options: 100 shares per contract."""
    return abs(qty) * abs(premium) * 100.0


def check_trade(
    trade: ProposedTrade,
    account: AccountSnapshot,
    risk: RiskConfig,
    *,
    dry_run: bool,
) -> RiskDecision:
    if not dry_run and not risk.allow_live:
        return RiskDecision(False, "live trading blocked: risk.allow_live=false")

    if account.equity < risk.min_account_equity:
        return RiskDecision(
            False,
            f"equity {account.equity:.2f} below min {risk.min_account_equity}",
        )

    if account.orders_today >= risk.max_orders_per_day:
        return RiskDecision(False, f"daily order cap reached ({risk.max_orders_per_day})")

    if trade.quantity <= 0:
        return RiskDecision(False, "quantity must be positive")

    if trade.quantity > risk.max_contracts_per_order:
        return RiskDecision(
            False,
            f"qty {trade.quantity} > max_contracts_per_order {risk.max_contracts_per_order}",
            capped_qty=risk.max_contracts_per_order,
        )

    if trade.limit_price <= 0:
        return RiskDecision(False, "limit_price must be > 0")

    notional = estimate_premium_notional(trade.quantity, trade.limit_price)
    if account.equity <= 0:
        return RiskDecision(False, "non-positive equity")

    pos_pct = notional / account.equity
    if trade.action.upper() == "BUY" and pos_pct > risk.max_position_pct:
        # Suggest a capped size that fits the budget
        max_notional = account.equity * risk.max_position_pct
        capped = int(max_notional // (trade.limit_price * 100))
        return RiskDecision(
            False,
            f"position {pos_pct:.1%} > max_position_pct {risk.max_position_pct:.0%}",
            capped_qty=max(0, capped),
        )

    if trade.action.upper() == "BUY":
        total = account.open_option_premium + notional
        total_pct = total / account.equity
        if total_pct > risk.max_total_options_pct:
            return RiskDecision(
                False,
                f"total options {total_pct:.1%} > max_total_options_pct "
                f"{risk.max_total_options_pct:.0%}",
            )

    return RiskDecision(True, "ok", capped_qty=trade.quantity)
