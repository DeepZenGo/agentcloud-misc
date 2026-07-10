"""Backtest engine: signals → fills → costs → equity."""

from __future__ import annotations

from collections import defaultdict

import pandas as pd

from lab.fills import FILLERS
from lab.metrics import performance
from lab.types import Signal, Trade


def run_backtest(
    panel: pd.DataFrame,
    signals: list[Signal],
    fill_model: str = "next_open",
    cost_roundtrip: float = 0.0015,
    initial_cash: float = 1_000_000.0,
    max_names_per_day: int = 3,
) -> tuple[pd.DataFrame, dict]:
    if fill_model not in FILLERS:
        raise KeyError(f"unknown fill_model={fill_model}, choose from {list(FILLERS)}")
    filler = FILLERS[fill_model]

    indexed = panel.set_index(["date", "code"], drop=False).sort_index()

    by_day: dict[pd.Timestamp, list[Signal]] = defaultdict(list)
    for s in signals:
        by_day[pd.Timestamp(s.date)].append(s)

    trades: list[dict] = []
    n_signals = 0
    unfilled = 0
    cash = initial_cash

    for day in sorted(by_day):
        day_sigs = sorted(by_day[day], key=lambda s: -s.strength)[:max_names_per_day]
        n_signals += len(day_sigs)
        filled_rows = []
        for s in day_sigs:
            key = (pd.Timestamp(s.date), s.code)
            if key not in indexed.index:
                unfilled += 1
                continue
            r = indexed.loc[key]
            if isinstance(r, pd.DataFrame):
                r = r.iloc[0]
            if fill_model == "limit_down_bounce":
                fr = filler(r)
            else:
                fr = filler(r, cost_roundtrip)
            if not fr.filled:
                unfilled += 1
                continue
            filled_rows.append((s, fr, r))

        if not filled_rows:
            continue
        w = 1.0 / len(filled_rows)
        day_cash = cash
        day_pnl = 0.0
        for s, fr, r in filled_rows:
            ret = fr.sell / fr.buy - 1.0 - cost_roundtrip
            day_pnl += day_cash * w * ret
            trades.append(
                {
                    "date": pd.Timestamp(s.date),
                    "code": s.code,
                    "buy": fr.buy,
                    "sell": fr.sell,
                    "ret": ret,
                    "fill_model": fr.reason,
                    "weight": w,
                    "equity_after": day_cash + day_pnl,
                    "name": r.get("code_name", ""),
                    "industry": r.get("industry", ""),
                    **{f"m_{k}": v for k, v in s.meta.items() if isinstance(v, (int, float, str))},
                }
            )
        cash = day_cash + day_pnl

    tdf = pd.DataFrame(trades)
    tdf.attrs["n_signals"] = n_signals
    tdf.attrs["n_unfilled"] = unfilled
    perf = performance(tdf, initial_cash)
    perf["n_signals"] = n_signals
    perf["n_unfilled"] = unfilled
    perf["fill_rate"] = (perf["n_trades"] / n_signals) if n_signals else float("nan")
    return tdf, perf
