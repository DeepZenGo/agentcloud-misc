from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_config(path: Path | None = None) -> dict:
    path = path or (ROOT / "config" / "default.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _first_existing(candidates: list[str]) -> Path | None:
    for c in candidates:
        p = (ROOT / c).resolve() if not Path(c).is_absolute() else Path(c)
        if p.exists():
            return p
    return None


def limit_pct(code: str, is_st) -> float:
    if str(is_st) in {"1", "True", "true"}:
        return 0.05
    if code.startswith("sz.30") or code.startswith("sh.68"):
        return 0.20
    return 0.10


def add_limits(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    ups, downs = [], []
    for code, pre, st in zip(out["code"], out["preclose"], out["isST"]):
        if pd.isna(pre) or pre <= 0:
            ups.append(np.nan)
            downs.append(np.nan)
            continue
        pct = limit_pct(code, st)
        ups.append(round(float(pre) * (1 + pct), 2))
        downs.append(round(float(pre) * (1 - pct), 2))
    out["limit_up"] = ups
    out["limit_down"] = downs
    out["is_limit_up_close"] = out["close"] >= out["limit_up"] - 1e-6
    out["is_limit_down_close"] = out["close"] <= out["limit_down"] + 1e-6
    out["is_limit_up_open"] = out["open"] >= out["limit_up"] - 1e-6
    out["is_limit_down_open"] = out["open"] <= out["limit_down"] + 1e-6
    out["open_ret"] = out["open"] / out["preclose"] - 1.0
    out["close_ret"] = out["close"] / out["preclose"] - 1.0
    return out


def load_panel(cfg: dict | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    panel_path = _first_existing(cfg["data"]["panel_candidates"])
    if panel_path is None:
        raise FileNotFoundError(
            "No panel_daily.parquet found. Run download in ashare-xhs-strategy-backtest "
            "or place panel under ashare-research-lab/data/."
        )
    uni_path = _first_existing(cfg["data"].get("universe_candidates", []))
    open5_path = _first_existing(cfg["data"].get("open5m_candidates", []))

    df = pd.read_parquet(panel_path)
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["tradestatus"].astype(str) == "1"].copy()
    df = df[(df["volume"] > 0) & (df["preclose"] > 0)]
    df = df[df["code"].str.startswith(("sh.60", "sh.68", "sz.00", "sz.30"))]

    if uni_path is not None:
        uni = pd.read_parquet(uni_path)[["code", "industry", "code_name", "ipoDate"]]
        df = df.merge(uni, on="code", how="left")

    df = add_limits(df)
    df = df.sort_values(["code", "date"]).reset_index(drop=True)

    # Features known only after close / with lag discipline
    df["ma5_vol"] = df.groupby("code")["volume"].transform(
        lambda s: s.shift(1).rolling(5, min_periods=5).mean()
    )
    df["vol_ratio_eod"] = df["volume"] / df["ma5_vol"]  # same-day → lookahead if used at open
    df["prev_vol_ratio"] = df.groupby("code")["vol_ratio_eod"].shift(1)  # open-safe
    df["ret_5d"] = df.groupby("code")["close"].transform(lambda s: s.shift(1) / s.shift(6) - 1.0)
    df["next_open"] = df.groupby("code")["open"].shift(-1)
    df["next_high"] = df.groupby("code")["high"].shift(-1)
    df["next_low"] = df.groupby("code")["low"].shift(-1)
    df["next_close"] = df.groupby("code")["close"].shift(-1)
    df["next2_open"] = df.groupby("code")["open"].shift(-2)

    if open5_path is not None:
        o5 = pd.read_parquet(open5_path)
        o5["date"] = pd.to_datetime(o5["date"])
        cols = [c for c in ["date", "code", "open_vol_ratio"] if c in o5.columns]
        df = df.merge(o5[cols], on=["date", "code"], how="left")

    if "ipoDate" in df.columns:
        ipo = pd.to_datetime(df["ipoDate"], errors="coerce")
        df = df[(df["date"] - ipo).dt.days >= 60]
    df = df[df["isST"].astype(str) != "1"]
    return df
