#!/usr/bin/env python3
"""
Download first 5-min bar each day (≈09:30–09:35) to approximate open 量比.

open_vol_ratio_t = vol_0935_t / mean(vol_0935_{t-5..t-1})
"""

from __future__ import annotations

import argparse
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import baostock as bs
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"
OPEN5_DIR = DATA_DIR / "open5m"
META_DIR = DATA_DIR / "meta"


def _one(args: tuple[str, str, str]) -> tuple[str, str]:
    code, start, end = args
    out = OPEN5_DIR / f"{code.replace('.', '_')}.parquet"
    if out.exists():
        return code, "cached"
    lg = bs.login()
    if lg.error_code != "0":
        return code, f"login_fail:{lg.error_msg}"
    try:
        rs = bs.query_history_k_data_plus(
            code,
            "date,time,code,open,high,low,close,volume,amount",
            start_date=start,
            end_date=end,
            frequency="5",
            adjustflag="3",
        )
        rows = []
        while rs.error_code == "0" and rs.next():
            row = rs.get_row_data()
            # first bar of session ends at 09:35
            if str(row[1]).endswith("093500000"):
                rows.append(row)
        fields = list(rs.fields)
        if not rows:
            pd.DataFrame(columns=fields).to_parquet(out, index=False)
            return code, "empty"
        df = pd.DataFrame(rows, columns=fields)
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        df["open_vol_ma5"] = df["volume"].shift(1).rolling(5, min_periods=5).mean()
        df["open_vol_ratio"] = df["volume"] / df["open_vol_ma5"]
        df.to_parquet(out, index=False)
        return code, "ok"
    except Exception as e:
        return code, f"err:{e}"
    finally:
        bs.logout()


def build_open5_panel() -> Path:
    frames = []
    for f in sorted(OPEN5_DIR.glob("*.parquet")):
        df = pd.read_parquet(f)
        if not df.empty:
            frames.append(df[["date", "code", "volume", "amount", "open_vol_ratio"]])
    panel = pd.concat(frames, ignore_index=True)
    out = DATA_DIR / "panel_open5m.parquet"
    panel.to_parquet(out, index=False)
    print(f"open5 panel: {len(panel):,} rows, {panel['code'].nunique()} codes")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-stocks", type=int, default=0)
    ap.add_argument("--only-from-panel", action="store_true",
                    help="only codes present in panel_daily.parquet")
    ap.add_argument("--build-panel-only", action="store_true")
    args = ap.parse_args()

    OPEN5_DIR.mkdir(parents=True, exist_ok=True)
    if args.build_panel_only:
        build_open5_panel()
        return

    if args.only_from_panel:
        daily = pd.read_parquet(DATA_DIR / "panel_daily.parquet")
        codes = sorted(daily["code"].unique().tolist())
    else:
        uni = pd.read_parquet(META_DIR / "universe.parquet")
        codes = uni["code"].tolist()
    if args.max_stocks:
        codes = codes[: args.max_stocks]

    done = {p.stem for p in OPEN5_DIR.glob("*.parquet")}
    todo = [c for c in codes if c.replace(".", "_") not in done]
    print(f"open5 todo={len(todo)} cached={len(done)} workers={args.workers}", flush=True)

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_one, (c, args.start, args.end)) for c in todo]
        for i, fut in enumerate(as_completed(futs), 1):
            code, status = fut.result()
            if status not in {"ok", "cached", "empty"}:
                print("FAIL", code, status, flush=True)
            if i % 50 == 0 or i == len(todo):
                rate = i / max(time.time() - t0, 1e-6)
                eta = (len(todo) - i) / max(rate, 1e-6)
                print(f"[{i}/{len(todo)}] {code} {status} rate={rate:.2f}/s eta={eta/60:.1f}m", flush=True)

    build_open5_panel()


if __name__ == "__main__":
    main()
