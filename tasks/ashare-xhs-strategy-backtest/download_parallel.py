#!/usr/bin/env python3
"""Parallel baostock downloader — one login per worker, resumable per-code parquet."""

from __future__ import annotations

import argparse
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import baostock as bs
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"
BARS_DIR = DATA_DIR / "bars"
META_DIR = DATA_DIR / "meta"
FIELDS = (
    "date,code,open,high,low,close,preclose,volume,amount,turn,pctChg,isST,tradestatus"
)


def _download_one(args: tuple[str, str, str]) -> tuple[str, str]:
    code, start, end = args
    out = BARS_DIR / f"{code.replace('.', '_')}.parquet"
    if out.exists():
        return code, "cached"
    lg = bs.login()
    if lg.error_code != "0":
        return code, f"login_fail:{lg.error_msg}"
    try:
        rs = bs.query_history_k_data_plus(
            code, FIELDS, start_date=start, end_date=end, frequency="d", adjustflag="3"
        )
        rows = []
        while rs.error_code == "0" and rs.next():
            rows.append(rs.get_row_data())
        fields = list(rs.fields)
        if not rows:
            pd.DataFrame(columns=fields).to_parquet(out, index=False)
            return code, "empty"
        df = pd.DataFrame(rows, columns=fields)
        for col in ["open", "high", "low", "close", "preclose", "volume", "amount", "turn", "pctChg"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["isST"] = df["isST"].astype(str)
        df["tradestatus"] = df["tradestatus"].astype(str)
        df.to_parquet(out, index=False)
        return code, "ok"
    except Exception as e:
        return code, f"err:{e}"
    finally:
        bs.logout()


def build_panel() -> None:
    files = sorted(BARS_DIR.glob("*.parquet"))
    frames = []
    for f in files:
        df = pd.read_parquet(f)
        if not df.empty:
            frames.append(df)
    panel = pd.concat(frames, ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"])
    panel = panel.sort_values(["date", "code"]).reset_index(drop=True)
    out = DATA_DIR / "panel_daily.parquet"
    panel.to_parquet(out, index=False)
    print(f"panel: {len(panel):,} rows, {panel['code'].nunique()} codes")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-stocks", type=int, default=0)
    ap.add_argument("--build-panel-only", action="store_true")
    args = ap.parse_args()

    BARS_DIR.mkdir(parents=True, exist_ok=True)
    if args.build_panel_only:
        build_panel()
        return

    # ensure meta exists
    if not (META_DIR / "universe.parquet").exists():
        from download_data import login, save_universe, save_trade_dates

        login()
        save_universe()
        save_trade_dates(args.start, args.end)
        bs.logout()

    uni = pd.read_parquet(META_DIR / "universe.parquet")
    # diversify: shuffle by board prefix buckets
    uni = uni.copy()
    uni["board"] = uni["code"].str.slice(0, 5)
    uni = uni.sample(frac=1.0, random_state=42).sort_values("board")
    codes = uni["code"].tolist()
    if args.max_stocks:
        # take round-robin across boards for diversity
        buckets = {b: g["code"].tolist() for b, g in uni.groupby("board")}
        codes = []
        while len(codes) < args.max_stocks and any(buckets.values()):
            for b in list(buckets.keys()):
                if buckets[b]:
                    codes.append(buckets[b].pop(0))
                if len(codes) >= args.max_stocks:
                    break

    done = {p.stem for p in BARS_DIR.glob("*.parquet")}
    todo = [c for c in codes if c.replace(".", "_") not in done]
    print(f"todo={len(todo)} cached={len(done)} workers={args.workers}")

    t0 = time.time()
    ok = fail = 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_download_one, (c, args.start, args.end)): c for c in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            code, status = fut.result()
            if status in {"ok", "cached", "empty"}:
                ok += 1
            else:
                fail += 1
                print("FAIL", code, status)
            if i % 100 == 0 or i == len(todo):
                rate = i / max(time.time() - t0, 1e-6)
                eta = (len(todo) - i) / max(rate, 1e-6)
                print(f"[{i}/{len(todo)}] ok={ok} fail={fail} rate={rate:.2f}/s eta={eta/60:.1f}m")

    build_panel()


if __name__ == "__main__":
    main()
