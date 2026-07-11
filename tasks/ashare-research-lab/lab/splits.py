"""Train / validation / test splits with purge gap (no leakage across folds)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Split:
    name: str
    dates: list[pd.Timestamp]

    @property
    def start(self) -> pd.Timestamp:
        return min(self.dates)

    @property
    def end(self) -> pd.Timestamp:
        return max(self.dates)


@dataclass
class SplitBundle:
    train: Split
    val: Split
    test: Split
    all_dates: list[pd.Timestamp]


def time_splits(
    dates: list[pd.Timestamp],
    test_ratio: float = 0.20,
    val_ratio: float = 0.15,
    purge_days: int = 5,
) -> SplitBundle:
    dates = sorted(pd.to_datetime(dates).unique())
    n = len(dates)
    if n < 50:
        raise ValueError(f"need >=50 trading days, got {n}")

    n_test = max(20, int(n * test_ratio))
    n_val = max(15, int(n * val_ratio))
    test_dates = dates[-n_test:]
    # purge before test
    test_start = test_dates[0]
    purged = [d for d in dates if d < test_start - pd.Timedelta(days=purge_days)]
    val_dates = purged[-n_val:]
    train_dates = purged[:-n_val] if n_val < len(purged) else purged[: max(1, len(purged) // 2)]

    return SplitBundle(
        train=Split("train", list(train_dates)),
        val=Split("val", list(val_dates)),
        test=Split("test", list(test_dates)),
        all_dates=list(dates),
    )


def filter_panel(panel: pd.DataFrame, split: Split) -> pd.DataFrame:
    return panel[panel["date"].isin(split.dates)].copy()
