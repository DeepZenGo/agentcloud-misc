"""Fill models — never silently assume limit-up fills."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class FillResult:
    filled: bool
    buy: float
    sell: float
    reason: str


def fill_next_open(row: pd.Series, cost_roundtrip: float) -> FillResult:
    """Signal at T (open or close), buy T open or already in, sell next open.
    For open signals: buy=open, sell=next_open.
    """
    if pd.isna(row.get("next_open")) or pd.isna(row.get("open")):
        return FillResult(False, 0.0, 0.0, "missing_price")
    if bool(row.get("is_limit_up_open", False)):
        return FillResult(False, 0.0, 0.0, "open_limit_up_unfillable")
    buy = float(row["open"])
    sell = float(row["next_open"])
    return FillResult(True, buy, sell, "next_open")


def fill_limit_up_optimistic(row: pd.Series, cost_roundtrip: float) -> FillResult:
    if pd.isna(row.get("next_open")) or pd.isna(row.get("limit_up")):
        return FillResult(False, 0.0, 0.0, "missing_price")
    buy = float(row["limit_up"])
    sell = float(row["next_open"])
    return FillResult(True, buy, sell, "limit_up_optimistic")


def fill_limit_up_conservative(row: pd.Series, cost_roundtrip: float) -> FillResult:
    """Only count fill if board opened at least once (low < limit_up)."""
    if pd.isna(row.get("next_open")) or pd.isna(row.get("limit_up")):
        return FillResult(False, 0.0, 0.0, "missing_price")
    if float(row["low"]) >= float(row["limit_up"]) - 1e-6:
        return FillResult(False, 0.0, 0.0, "one_word_board")
    buy = float(row["limit_up"])
    sell = float(row["next_open"])
    return FillResult(True, buy, sell, "limit_up_conservative")


def fill_limit_down_bounce(row: pd.Series, rebound: float = 0.03) -> FillResult:
    if not bool(row.get("is_limit_down_open", False)):
        return FillResult(False, 0.0, 0.0, "not_limit_down_open")
    if pd.isna(row.get("open")):
        return FillResult(False, 0.0, 0.0, "missing_price")
    buy = float(row["open"])
    target = buy * (1.0 + rebound)
    if float(row["high"]) >= target - 1e-9:
        return FillResult(True, buy, target, "intraday_rebound")
    if pd.isna(row.get("next_open")):
        return FillResult(False, 0.0, 0.0, "missing_next_open")
    return FillResult(True, buy, float(row["next_open"]), "next_open_after_ld")


FILLERS = {
    "next_open": fill_next_open,
    "limit_up_optimistic": fill_limit_up_optimistic,
    "limit_up_conservative": fill_limit_up_conservative,
    "limit_down_bounce": fill_limit_down_bounce,
}
