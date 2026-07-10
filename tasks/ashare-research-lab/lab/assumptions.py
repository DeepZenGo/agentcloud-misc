"""Hypothesis assumption audit — metrics alone must not mint a CANDIDATE."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Proxies that look like the claim but are not the claim
DANGEROUS_PROXIES = {
    "amount_as_net_inflow": "成交额 ≠ 资金净流入",
    "daily_vol_as_open_liangbi": "日线量比 ≠ 09:30 分时量比",
    "watchlist_as_discretionary": "规则化自选 ≠ 主观自选（方向相反：更宽/更窄都可能）",
}

# Fill models that systematically overstate edge for board-hitting
OPTIMISTIC_FILLS = {
    "limit_up_optimistic",
    "limit_up_conservative",  # still assumes you got the limit-up price
}


@dataclass
class AssumptionAudit:
    ok_for_candidate: bool
    ok_for_weak: bool
    errors: list[str]
    warnings: list[str]
    grade: str  # "honest" | "weak" | "reject"


def audit_assumptions(hyp: dict[str, Any], cfg: dict | None = None) -> AssumptionAudit:
    cfg = cfg or {}
    errors: list[str] = []
    warnings: list[str] = []
    ass = hyp.get("assumptions") or {}

    if not ass:
        errors.append("missing assumptions{} — refuse to grade without declared fidelity")
        return AssumptionAudit(False, False, errors, warnings, "reject")

    for key in ("signal_fidelity", "fill_realism"):
        val = ass.get(key)
        if val not in {"high", "medium", "low"}:
            errors.append(f"assumptions.{key} must be high|medium|low, got {val!r}")

    proxies = list(ass.get("proxies") or [])
    for p in proxies:
        if p in DANGEROUS_PROXIES:
            warnings.append(f"proxy {p}: {DANGEROUS_PROXIES[p]}")

    fill = hyp.get("fill_model", "")
    if fill in OPTIMISTIC_FILLS:
        warnings.append(
            f"fill_model={fill} still assumes limit-up price fill; "
            "EOD-decidable alternative is next_open chase"
        )

    # Hard reject: claim says 净流入 but only amount proxy without admitting it
    claim = (hyp.get("claim") or "") + (hyp.get("notes") or "")
    if ("净流入" in claim or "资金" in claim) and "amount_as_net_inflow" in proxies:
        # admitted — weak at best
        pass
    elif "净流入" in claim and "amount_as_net_inflow" not in proxies:
        errors.append("claim mentions 净流入 but assumptions.proxies missing amount_as_net_inflow")

    signal_f = ass.get("signal_fidelity")
    fill_r = ass.get("fill_realism")

    # Candidate requires honest-enough assumptions
    reject_dangerous = cfg.get("reject_dangerous_proxies", True)
    has_dangerous = any(p in DANGEROUS_PROXIES for p in proxies)
    low_fidelity = signal_f == "low" or fill_r == "low"

    if errors:
        return AssumptionAudit(False, False, errors, warnings, "reject")

    if reject_dangerous and has_dangerous:
        errors.append(
            "dangerous proxy present — cannot be CANDIDATE "
            f"({', '.join(p for p in proxies if p in DANGEROUS_PROXIES)})"
        )
        # still allow WEAK if metrics pass and user wants to study it
        return AssumptionAudit(False, True, errors, warnings, "weak")

    if low_fidelity:
        warnings.append("signal_fidelity or fill_realism is low")
        return AssumptionAudit(False, True, errors, warnings, "weak")

    if fill in OPTIMISTIC_FILLS and not ass.get("accept_limit_up_fill_risk"):
        errors.append(
            "limit-up fill without assumptions.accept_limit_up_fill_risk=true "
            "— run fill stress (next_open chase) or mark weak"
        )
        return AssumptionAudit(False, True, errors, warnings, "weak")

    return AssumptionAudit(True, True, errors, warnings, "honest")


def verdict(lint_ok: bool, gates_ok: bool, ass: AssumptionAudit, stress_ok: bool | None) -> str:
    if not lint_ok:
        return "REJECT"
    if ass.grade == "reject" and not ass.ok_for_weak:
        return "REJECT"
    if not gates_ok:
        return "REJECT"
    if stress_ok is False:
        return "REJECT"
    if ass.ok_for_candidate and (stress_ok is not False):
        return "CANDIDATE"
    if ass.ok_for_weak and gates_ok:
        return "WEAK_CANDIDATE"
    return "REJECT"
