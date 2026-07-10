#!/usr/bin/env python3
"""
Backtest three Xiaohongshu retail strategies on daily bars.

Approximations (documented because true 09:30 量比 / 主力净流入 need intraday feeds):
  A) Volume-ratio proxy: day volume / MA5(volume) in [20, 60], open in hot industry,
     buy at open, sell next open (default).
  B) Limit-down bounce: each day build a 5-name watchlist (worst 5d return, industry-
     diversified); if open == limit-down, buy open; sell when +R% from cost or next open.
  C) Limit-up board: close at limit-up AND amount >= 2e9 (proxy for "净流入>20亿"),
     buy at limit-up (optimistic fill), sell next open.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from utils import add_limit_flags, performance_from_trades

DATA_DIR = Path(__file__).resolve().parent / "data"
OUT_DIR = Path(__file__).resolve().parent / "results"

FEE_ROUNDTRIP = 0.0015  # commission + stamp approx


def load_panel(path: Path | None = None) -> pd.DataFrame:
    path = path or (DATA_DIR / "panel_daily.parquet")
    uni_path = DATA_DIR / "meta" / "universe.parquet"
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["tradestatus"] == "1"].copy()
    df = df[(df["volume"] > 0) & (df["preclose"] > 0)]
    # drop Beijing / B-shares if any slipped in
    df = df[df["code"].str.startswith(("sh.60", "sh.68", "sz.00", "sz.30"))]
    if uni_path.exists():
        uni = pd.read_parquet(uni_path)[["code", "industry", "code_name", "ipoDate"]]
        df = df.merge(uni, on="code", how="left")
    df = add_limit_flags(df)
    df = df.sort_values(["code", "date"]).reset_index(drop=True)
    # features
    df["ma5_vol"] = df.groupby("code")["volume"].transform(
        lambda s: s.shift(1).rolling(5, min_periods=5).mean()
    )
    df["vol_ratio"] = df["volume"] / df["ma5_vol"]
    df["ret_5d"] = df.groupby("code")["close"].transform(lambda s: s.shift(1) / s.shift(6) - 1.0)
    df["next_open"] = df.groupby("code")["open"].shift(-1)
    df["next_high"] = df.groupby("code")["high"].shift(-1)
    df["next_low"] = df.groupby("code")["low"].shift(-1)
    df["next_close"] = df.groupby("code")["close"].shift(-1)
    # IPO filter: listed >= 60 calendar days before bar
    if "ipoDate" in df.columns:
        ipo = pd.to_datetime(df["ipoDate"], errors="coerce")
        df = df[(df["date"] - ipo).dt.days >= 60]
    # ST filter
    df = df[df["isST"].astype(str) != "1"]
    return df


def hot_industries(day_df: pd.DataFrame, top_k: int = 3) -> set[str]:
    """Hot = top-K industries by mean open return that morning."""
    g = (
        day_df.dropna(subset=["industry", "open_ret"])
        .groupby("industry")["open_ret"]
        .mean()
        .sort_values(ascending=False)
    )
    return set(g.head(top_k).index.tolist())


def run_strategy_a(
    panel: pd.DataFrame,
    vol_lo: float = 20.0,
    vol_hi: float = 60.0,
    open_lo: float = 0.02,
    open_hi: float = 0.07,
    top_n: int = 3,
    hot_k: int = 3,
    initial_cash: float = 1_000_000.0,
) -> tuple[pd.DataFrame, dict]:
    """量比+热点：用全日量比代理 09:30 量比（有前视偏差，结果偏乐观）。"""
    trades = []
    cash = initial_cash
    dates = sorted(panel["date"].unique())
    by_date = {d: g for d, g in panel.groupby("date")}

    for d in dates:
        day = by_date[d]
        # NOTE: vol_ratio uses same-day volume → look-ahead vs true 09:30 signal.
        hot = hot_industries(day, top_k=hot_k)
        if not hot:
            continue
        cand = day[
            (day["vol_ratio"] >= vol_lo)
            & (day["vol_ratio"] <= vol_hi)
            & (day["open_ret"] >= open_lo)
            & (day["open_ret"] <= open_hi)
            & (day["industry"].isin(hot))
            & (~day["is_limit_up_open"])
            & (day["next_open"].notna())
        ].copy()
        if cand.empty:
            continue
        cand = cand.sort_values("vol_ratio", ascending=False).head(top_n)
        w = 1.0 / len(cand)
        day_cash = cash
        day_pnl = 0.0
        for _, r in cand.iterrows():
            buy = float(r["open"])
            sell = float(r["next_open"])
            ret = sell / buy - 1.0 - FEE_ROUNDTRIP
            pnl = day_cash * w * ret
            day_pnl += pnl
            trades.append(
                {
                    "strategy": "A_vol_ratio_hot",
                    "date": d,
                    "code": r["code"],
                    "name": r.get("code_name", ""),
                    "industry": r.get("industry", ""),
                    "vol_ratio": float(r["vol_ratio"]),
                    "buy": buy,
                    "sell": sell,
                    "ret": ret,
                    "equity_after": day_cash + day_pnl,
                }
            )
        cash = day_cash + day_pnl
    tdf = pd.DataFrame(trades)
    return tdf, performance_from_trades(tdf, initial_cash)


def run_strategy_a_no_lookahead(
    panel: pd.DataFrame,
    open_lo: float = 0.02,
    open_hi: float = 0.07,
    top_n: int = 3,
    hot_k: int = 3,
    prev_vol_lo: float = 1.5,
    initial_cash: float = 1_000_000.0,
) -> tuple[pd.DataFrame, dict]:
    """
    无前视版本：开盘可知的只有开盘价/昨量。
    用 昨量比(=昨量/MA5) + 开盘涨幅 + 热点行业 近似原策略意图。
    """
    df = panel.copy()
    df["prev_vol_ratio"] = df.groupby("code")["vol_ratio"].shift(1)
    trades = []
    cash = initial_cash
    by_date = {d: g for d, g in df.groupby("date")}
    for d in sorted(df["date"].unique()):
        day = by_date[d]
        hot = hot_industries(day, top_k=hot_k)
        cand = day[
            (day["prev_vol_ratio"] >= prev_vol_lo)
            & (day["open_ret"] >= open_lo)
            & (day["open_ret"] <= open_hi)
            & (day["industry"].isin(hot))
            & (~day["is_limit_up_open"])
            & (day["next_open"].notna())
        ].copy()
        if cand.empty:
            continue
        cand = cand.sort_values(["open_ret", "prev_vol_ratio"], ascending=False).head(top_n)
        w = 1.0 / len(cand)
        day_cash = cash
        day_pnl = 0.0
        for _, r in cand.iterrows():
            buy = float(r["open"])
            sell = float(r["next_open"])
            ret = sell / buy - 1.0 - FEE_ROUNDTRIP
            day_pnl += day_cash * w * ret
            trades.append(
                {
                    "strategy": "A_no_lookahead",
                    "date": d,
                    "code": r["code"],
                    "name": r.get("code_name", ""),
                    "industry": r.get("industry", ""),
                    "prev_vol_ratio": float(r["prev_vol_ratio"]),
                    "buy": buy,
                    "sell": sell,
                    "ret": ret,
                    "equity_after": day_cash + day_pnl,
                }
            )
        cash = day_cash + day_pnl
    tdf = pd.DataFrame(trades)
    return tdf, performance_from_trades(tdf, initial_cash)


def build_watchlist(prev_day_panel: pd.DataFrame, n: int = 5) -> list[str]:
    """Worst 5d return, one per industry."""
    x = prev_day_panel.dropna(subset=["ret_5d", "industry"]).copy()
    x = x.sort_values("ret_5d")
    picked = []
    seen_ind = set()
    for _, r in x.iterrows():
        ind = r["industry"]
        if ind in seen_ind:
            continue
        seen_ind.add(ind)
        picked.append(r["code"])
        if len(picked) >= n:
            break
    return picked


def run_strategy_b(
    panel: pd.DataFrame,
    rebound: float = 0.03,
    initial_cash: float = 1_000_000.0,
) -> tuple[pd.DataFrame, dict]:
    """开盘跌停抄底：规则化 5 只自选，开盘跌停买入，反弹 R% 或次日开盘卖。"""
    trades = []
    cash = initial_cash
    dates = sorted(panel["date"].unique())
    by_date = {d: g for d, g in panel.groupby("date")}

    for i, d in enumerate(dates):
        if i == 0:
            continue
        prev = by_date[dates[i - 1]]
        day = by_date[d]
        watch = set(build_watchlist(prev, n=5))
        if not watch:
            continue
        hits = day[
            (day["code"].isin(watch))
            & (day["is_limit_down_open"])
            & (day["next_open"].notna())
        ]
        if hits.empty:
            continue
        w = min(0.2, 1.0 / len(hits))
        day_cash = cash
        day_pnl = 0.0
        for _, r in hits.iterrows():
            buy = float(r["open"])
            # same-day rebound using high; if high >= buy*(1+R) assume fill at target
            target = buy * (1.0 + rebound)
            if float(r["high"]) >= target - 1e-9:
                sell = target
                hold = "intraday_rebound"
            else:
                sell = float(r["next_open"])
                hold = "next_open"
                # if still limit-down next open and couldn't sell — still mark next_open
            ret = sell / buy - 1.0 - FEE_ROUNDTRIP
            day_pnl += day_cash * w * ret
            trades.append(
                {
                    "strategy": "B_limit_down_bounce",
                    "date": d,
                    "code": r["code"],
                    "name": r.get("code_name", ""),
                    "industry": r.get("industry", ""),
                    "buy": buy,
                    "sell": sell,
                    "hold": hold,
                    "ret": ret,
                    "equity_after": day_cash + day_pnl,
                }
            )
        cash = day_cash + day_pnl
    tdf = pd.DataFrame(trades)
    return tdf, performance_from_trades(tdf, initial_cash)


def run_strategy_c(
    panel: pd.DataFrame,
    min_amount: float = 2e9,
    fill_mode: str = "optimistic",
    initial_cash: float = 1_000_000.0,
) -> tuple[pd.DataFrame, dict]:
    """
    打板：涨停收盘 + 成交额>=20亿 代理「净流入>20亿」。
    fill_mode:
      optimistic — 假设涨停价买到
      conservative — 仅当当日曾打开（low < limit_up）才算买到
    """
    trades = []
    cash = initial_cash
    by_date = {d: g for d, g in panel.groupby("date")}
    for d in sorted(panel["date"].unique()):
        day = by_date[d]
        cand = day[
            (day["is_limit_up_close"])
            & (day["amount"] >= min_amount)
            & (day["next_open"].notna())
            & (~day["is_limit_up_open"])  # exclude one-word boards from open
        ].copy()
        if fill_mode == "conservative":
            cand = cand[cand["low"] < cand["limit_up"] - 1e-6]
        if cand.empty:
            continue
        # take all that qualify, equal weight capped
        cand = cand.sort_values("amount", ascending=False).head(3)
        w = 1.0 / len(cand)
        day_cash = cash
        day_pnl = 0.0
        for _, r in cand.iterrows():
            buy = float(r["limit_up"])
            sell = float(r["next_open"])
            ret = sell / buy - 1.0 - FEE_ROUNDTRIP
            day_pnl += day_cash * w * ret
            trades.append(
                {
                    "strategy": f"C_limit_up_{fill_mode}",
                    "date": d,
                    "code": r["code"],
                    "name": r.get("code_name", ""),
                    "industry": r.get("industry", ""),
                    "amount": float(r["amount"]),
                    "buy": buy,
                    "sell": sell,
                    "ret": ret,
                    "equity_after": day_cash + day_pnl,
                }
            )
        cash = day_cash + day_pnl
    tdf = pd.DataFrame(trades)
    return tdf, performance_from_trades(tdf, initial_cash)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", type=str, default="")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    panel_path = Path(args.panel) if args.panel else DATA_DIR / "panel_daily.parquet"
    print(f"loading {panel_path}")
    panel = load_panel(panel_path)
    print(f"panel rows={len(panel):,} codes={panel['code'].nunique()} "
          f"dates={panel['date'].nunique()} "
          f"{panel['date'].min().date()} -> {panel['date'].max().date()}")

    results = {}
    all_trades = []

    for name, fn in [
        ("A_vol_ratio_hot_lookahead", lambda: run_strategy_a(panel)),
        ("A_no_lookahead", lambda: run_strategy_a_no_lookahead(panel)),
        ("B_limit_down_bounce", lambda: run_strategy_b(panel)),
        ("C_limit_up_optimistic", lambda: run_strategy_c(panel, fill_mode="optimistic")),
        ("C_limit_up_conservative", lambda: run_strategy_c(panel, fill_mode="conservative")),
    ]:
        print(f"running {name} ...")
        trades, perf = fn()
        results[name] = perf
        if not trades.empty:
            trades.to_csv(OUT_DIR / f"trades_{name}.csv", index=False)
            all_trades.append(trades)
        print(f"  {perf}")

    summary = pd.DataFrame(results).T
    summary.to_csv(OUT_DIR / "summary.csv")
    summary.to_json(OUT_DIR / "summary.json", orient="index", indent=2)
    if all_trades:
        pd.concat(all_trades, ignore_index=True).to_csv(OUT_DIR / "trades_all.csv", index=False)

    # also dump human-readable
    lines = ["# Backtest Summary", ""]
    for k, v in results.items():
        lines.append(f"## {k}")
        for kk, vv in v.items():
            if isinstance(vv, float):
                lines.append(f"- {kk}: {vv:.4f}" if abs(vv) < 10 else f"- {kk}: {vv:.2f}")
            else:
                lines.append(f"- {kk}: {vv}")
        lines.append("")
    (OUT_DIR / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("wrote", OUT_DIR)


if __name__ == "__main__":
    main()
