from __future__ import annotations

import numpy as np
import pandas as pd


def performance(trades: pd.DataFrame, initial_cash: float = 1_000_000.0) -> dict:
    if trades is None or trades.empty:
        return {
            "n_signals": 0,
            "n_trades": 0,
            "fill_rate": np.nan,
            "win_rate": np.nan,
            "avg_return": np.nan,
            "expectancy": np.nan,
            "avg_win": np.nan,
            "avg_loss": np.nan,
            "profit_factor": np.nan,
            "total_return": 0.0,
            "max_drawdown": 0.0,
        }

    rets = trades["ret"].astype(float)
    wins = rets[rets > 0]
    losses = rets[rets <= 0]
    equity = trades["equity_after"].astype(float)
    total_return = float(equity.iloc[-1] / initial_cash - 1.0) if len(equity) else 0.0
    peak = equity.cummax()
    max_dd = float((equity / peak - 1.0).min()) if len(equity) else 0.0
    gp = float(wins.sum()) if len(wins) else 0.0
    gl = float(-losses.sum()) if len(losses) else 0.0
    n_signals = int(trades.attrs.get("n_signals", len(trades)))
    return {
        "n_signals": n_signals,
        "n_trades": int(len(trades)),
        "fill_rate": float(len(trades) / n_signals) if n_signals else np.nan,
        "win_rate": float((rets > 0).mean()),
        "avg_return": float(rets.mean()),
        "expectancy": float(rets.mean()),
        "avg_win": float(wins.mean()) if len(wins) else np.nan,
        "avg_loss": float(losses.mean()) if len(losses) else np.nan,
        "profit_factor": (gp / gl) if gl > 1e-12 else np.nan,
        "total_return": total_return,
        "max_drawdown": max_dd,
    }


def by_year(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    t = trades.copy()
    t["year"] = pd.to_datetime(t["date"]).dt.year
    return t.groupby("year")["ret"].agg(n="count", mean="mean", win_rate=lambda s: (s > 0).mean())
