#!/usr/bin/env python3
"""Download A-share daily bars + industry map via baostock (resumable)."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import baostock as bs
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"
BARS_DIR = DATA_DIR / "bars"
META_DIR = DATA_DIR / "meta"

FIELDS = (
    "date,code,open,high,low,close,preclose,volume,amount,turn,pctChg,isST,tradestatus"
)


def login() -> None:
    lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(f"baostock login failed: {lg.error_msg}")


def fetch_rows(rs) -> tuple[list[str], list[list[str]]]:
    rows: list[list[str]] = []
    while rs.error_code == "0" and rs.next():
        rows.append(rs.get_row_data())
    return list(rs.fields), rows


def save_universe() -> pd.DataFrame:
    META_DIR.mkdir(parents=True, exist_ok=True)
    fields, rows = fetch_rows(bs.query_stock_basic())
    basic = pd.DataFrame(rows, columns=fields)
    basic = basic[(basic["type"] == "1") & (basic["status"] == "1")].copy()

    fields, rows = fetch_rows(bs.query_stock_industry())
    industry = pd.DataFrame(rows, columns=fields)
    industry = industry[industry["industryClassification"] == "证监会行业分类"][
        ["code", "code_name", "industry"]
    ]

    uni = basic.merge(industry, on="code", how="left", suffixes=("", "_ind"))
    if "code_name_ind" in uni.columns:
        uni["code_name"] = uni["code_name"].fillna(uni["code_name_ind"])
        uni = uni.drop(columns=["code_name_ind"])
    uni.to_parquet(META_DIR / "universe.parquet", index=False)
    uni.to_csv(META_DIR / "universe.csv", index=False)
    print(f"universe: {len(uni)} stocks")
    return uni


def save_trade_dates(start: str, end: str) -> pd.DataFrame:
    META_DIR.mkdir(parents=True, exist_ok=True)
    fields, rows = fetch_rows(bs.query_trade_dates(start_date=start, end_date=end))
    df = pd.DataFrame(rows, columns=fields)
    df = df[df["is_trading_day"] == "1"][["calendar_date"]].rename(
        columns={"calendar_date": "date"}
    )
    df.to_parquet(META_DIR / "trade_dates.parquet", index=False)
    print(f"trade dates: {len(df)}")
    return df


def download_bars(codes: list[str], start: str, end: str, sleep_s: float = 0.0) -> None:
    BARS_DIR.mkdir(parents=True, exist_ok=True)
    done = {p.stem for p in BARS_DIR.glob("*.parquet")}
    todo = [c for c in codes if c.replace(".", "_") not in done]
    print(f"bars cached={len(done)} todo={len(todo)}")

    t0 = time.time()
    for i, code in enumerate(todo, 1):
        out = BARS_DIR / f"{code.replace('.', '_')}.parquet"
        try:
            rs = bs.query_history_k_data_plus(
                code,
                FIELDS,
                start_date=start,
                end_date=end,
                frequency="d",
                adjustflag="3",  # unadjusted — needed for limit-up/down
            )
            fields, rows = fetch_rows(rs)
            if not rows:
                # empty marker so we don't retry forever
                pd.DataFrame(columns=fields.split(",") if isinstance(fields, str) else fields).to_parquet(
                    out, index=False
                )
            else:
                df = pd.DataFrame(rows, columns=fields)
                for col in [
                    "open",
                    "high",
                    "low",
                    "close",
                    "preclose",
                    "volume",
                    "amount",
                    "turn",
                    "pctChg",
                ]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df["isST"] = df["isST"].astype(str)
                df["tradestatus"] = df["tradestatus"].astype(str)
                df.to_parquet(out, index=False)
        except Exception as e:
            print(f"FAIL {code}: {e}")
            login()
        if i % 50 == 0 or i == len(todo):
            elapsed = time.time() - t0
            rate = i / max(elapsed, 1e-6)
            eta = (len(todo) - i) / max(rate, 1e-6)
            print(f"[{i}/{len(todo)}] {code} rate={rate:.2f}/s eta={eta/60:.1f}m")
        if sleep_s:
            time.sleep(sleep_s)


def build_panel() -> Path:
    """Concatenate all bars into one panel parquet for fast backtests."""
    files = sorted(BARS_DIR.glob("*.parquet"))
    frames = []
    for f in files:
        df = pd.read_parquet(f)
        if df.empty:
            continue
        frames.append(df)
    if not frames:
        raise RuntimeError("no bar files")
    panel = pd.concat(frames, ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"])
    panel = panel.sort_values(["date", "code"]).reset_index(drop=True)
    out = DATA_DIR / "panel_daily.parquet"
    panel.to_parquet(out, index=False)
    print(f"panel: {len(panel):,} rows, {panel['code'].nunique()} codes -> {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--max-stocks", type=int, default=0, help="0 = all")
    ap.add_argument("--build-panel-only", action="store_true")
    args = ap.parse_args()

    if args.build_panel_only:
        build_panel()
        return

    login()
    try:
        uni = save_universe()
        save_trade_dates(args.start, args.end)
        codes = uni["code"].tolist()
        if args.max_stocks and args.max_stocks > 0:
            codes = codes[: args.max_stocks]
        download_bars(codes, args.start, args.end)
    finally:
        bs.logout()
    build_panel()


if __name__ == "__main__":
    main()
