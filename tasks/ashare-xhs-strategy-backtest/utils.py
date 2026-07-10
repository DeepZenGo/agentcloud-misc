#!/usr/bin/env python3
"""Shared helpers for A-share limit prices and metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def limit_pct(code: str, is_st: bool | str) -> float:
    st = str(is_st) in {"1", "True", "true"}
    if st:
        return 0.05
    # ChiNext / STAR
    if code.startswith("sz.30") or code.startswith("sh.68"):
        return 0.20
    # Beijing / other boards excluded upstream; main board default
    return 0.10


def limit_prices(preclose: float, code: str, is_st) -> tuple[float, float]:
    pct = limit_pct(code, is_st)
    up = round(preclose * (1.0 + pct), 2)
    down = round(preclose * (1.0 - pct), 2)
    return up, down


def add_limit_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    ups, downs = [], []
    for code, pre, st in zip(out["code"], out["preclose"], out["isST"]):
        if pd.isna(pre) or pre <= 0:
            ups.append(np.nan)
            downs.append(np.nan)
        else:
            u, d = limit_prices(float(pre), code, st)
            ups.append(u)
            downs.append(d)
    out["limit_up"] = ups
    out["limit_down"] = downs
    # tolerate 1 fen float noise
    out["is_limit_up_close"] = out["close"] >= out["limit_up"] - 1e-6
    out["is_limit_down_close"] = out["close"] <= out["limit_down"] + 1e-6
    out["is_limit_up_open"] = out["open"] >= out["limit_up"] - 1e-6
    out["is_limit_down_open"] = out["open"] <= out["limit_down"] + 1e-6
    out["open_ret"] = out["open"] / out["preclose"] - 1.0
    out["close_ret"] = out["close"] / out["preclose"] - 1.0
    return out


def performance_from_trades(trades: pd.DataFrame, initial_cash: float = 1_000_000.0) -> dict:
    if trades.empty:
        return {
            "n_trades": 0,
            "win_rate": np.nan,
            "avg_return": np.nan,
            "expectancy": np.nan,
            "total_return": 0.0,
            "max_drawdown": 0.0,
            "profit_factor": np.nan,
            "avg_win": np.nan,
            "avg_loss": np.nan,
        }

    rets = trades["ret"].astype(float)
    wins = rets[rets > 0]
    losses = rets[rets <= 0]
    # equity curve assuming equal-weight sequential / overlapping handled by engine
    equity = trades["equity_after"].astype(float) if "equity_after" in trades.columns else None
    if equity is not None and len(equity):
        total_return = float(equity.iloc[-1] / initial_cash - 1.0)
        peak = equity.cummax()
        dd = equity / peak - 1.0
        max_dd = float(dd.min())
    else:
        total_return = float((1 + rets).prod() - 1)
        max_dd = np.nan

    gross_profit = float(wins.sum()) if len(wins) else 0.0
    gross_loss = float(-losses.sum()) if len(losses) else 0.0
    pf = gross_profit / gross_loss if gross_loss > 1e-12 else np.nan

    return {
        "n_trades": int(len(trades)),
        "win_rate": float((rets > 0).mean()),
        "avg_return": float(rets.mean()),
        "expectancy": float(rets.mean()),
        "avg_win": float(wins.mean()) if len(wins) else np.nan,
        "avg_loss": float(losses.mean()) if len(losses) else np.nan,
        "profit_factor": pf,
        "total_return": total_return,
        "max_drawdown": max_dd,
    }
