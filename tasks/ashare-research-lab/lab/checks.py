"""Scientific gates: lookahead lint + pass/fail criteria."""

from __future__ import annotations

from dataclasses import dataclass

# Columns that are unsafe at open decision time (same-day EOD knowledge)
OPEN_UNSAFE = {
    "close",
    "high",
    "low",
    "volume",
    "amount",
    "turn",
    "pctChg",
    "vol_ratio_eod",
    "close_ret",
    "is_limit_up_close",
    "is_limit_down_close",
}

# Always future
ALWAYS_FUTURE = {"next_open", "next_high", "next_low", "next_close", "next2_open"}


@dataclass
class CheckResult:
    ok: bool
    errors: list[str]
    warnings: list[str]


def lint_strategy(strategy, decision: str = "open") -> CheckResult:
    errors, warnings = [], []
    cols = set(getattr(strategy, "decision_columns", []) or [])
    req = set(getattr(strategy, "required_columns", []) or [])

    future = cols & ALWAYS_FUTURE
    if future:
        errors.append(f"decision_columns include future fields: {sorted(future)}")

    if decision == "open":
        bad = cols & OPEN_UNSAFE
        if bad:
            errors.append(f"open decision uses same-day EOD fields: {sorted(bad)}")

    if not cols:
        warnings.append("decision_columns empty — cannot lint lookahead")

    unused_req = req - cols
    if unused_req:
        warnings.append(f"required_columns not listed in decision_columns: {sorted(unused_req)}")

    return CheckResult(ok=not errors, errors=errors, warnings=warnings)


def gate_metrics(perf: dict, gates: dict, split_name: str = "test") -> CheckResult:
    errors, warnings = [], []
    n = perf.get("n_trades") or 0
    min_n = gates.get("min_trades_test", 30) if split_name == "test" else gates.get("min_trades_val", 15)
    if split_name in {"test", "val"} and n < min_n:
        errors.append(f"{split_name} n_trades={n} < min={min_n}")
    exp = perf.get("expectancy")
    if exp is not None and exp == exp and exp < gates.get("min_expectancy", 0.0):
        errors.append(f"{split_name} expectancy={exp:.4f} < min_expectancy")
    pf = perf.get("profit_factor")
    if pf is not None and pf == pf and pf < gates.get("min_profit_factor", 1.05):
        errors.append(f"{split_name} profit_factor={pf:.3f} < min_profit_factor")
    dd = perf.get("max_drawdown")
    if dd is not None and dd == dd and dd < gates.get("max_drawdown", -0.35):
        errors.append(f"{split_name} max_drawdown={dd:.3f} worse than gate {gates.get('max_drawdown')}")
    fr = perf.get("fill_rate")
    if fr is not None and fr == fr and fr < 0.5:
        warnings.append(f"{split_name} fill_rate={fr:.2f} low — fills may be unrealistic")
    return CheckResult(ok=not errors, errors=errors, warnings=warnings)


def gate_bundle(results: dict[str, dict], gates: dict) -> CheckResult:
    """Combine test (+ optional val) gates."""
    test = gate_metrics(results.get("test", {}), gates, "test")
    errors = list(test.errors)
    warnings = list(test.warnings)
    if gates.get("require_val_pass", True):
        val = gate_metrics(results.get("val", {}), gates, "val")
        errors.extend(val.errors)
        warnings.extend(val.warnings)
    train = results.get("train", {})
    te = train.get("expectancy")
    if te is not None and te == te and te < 0:
        warnings.append(f"train expectancy={te:.4f} < 0 — unstable / regime-dependent")
    return CheckResult(ok=not errors, errors=errors, warnings=warnings)
