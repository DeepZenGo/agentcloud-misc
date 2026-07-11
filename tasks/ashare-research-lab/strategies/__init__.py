"""Example strategies — each declares decision_columns for linting."""

from __future__ import annotations

import pandas as pd

from lab.types import Signal


def _hot_industries(day: pd.DataFrame, top_k: int = 3) -> set[str]:
    if "industry" not in day.columns or day["industry"].isna().all():
        # fallback: board bucket
        day = day.copy()
        day["industry"] = day["code"].str.slice(0, 5)
    g = (
        day.dropna(subset=["industry", "open_ret"])
        .groupby("industry")["open_ret"]
        .mean()
        .sort_values(ascending=False)
    )
    return set(g.head(top_k).index.tolist())


class OpenGapHotNoLookahead:
    """Open gap in band + prev day volume ratio + hot industry. Open decision."""

    name = "open_gap_hot_no_lookahead"
    required_columns = ["open_ret", "prev_vol_ratio", "industry", "is_limit_up_open", "next_open"]
    decision_columns = ["open_ret", "prev_vol_ratio", "industry", "is_limit_up_open"]

    def __init__(self, open_lo=0.02, open_hi=0.07, prev_vol_lo=1.5, top_n=3, hot_k=3):
        self.open_lo = open_lo
        self.open_hi = open_hi
        self.prev_vol_lo = prev_vol_lo
        self.top_n = top_n
        self.hot_k = hot_k

    def generate(self, panel: pd.DataFrame) -> list[Signal]:
        sigs: list[Signal] = []
        for d, day in panel.groupby("date"):
            hot = _hot_industries(day, self.hot_k)
            cand = day[
                (day["prev_vol_ratio"] >= self.prev_vol_lo)
                & (day["open_ret"] >= self.open_lo)
                & (day["open_ret"] <= self.open_hi)
                & (day["industry"].isin(hot))
                & (~day["is_limit_up_open"])
            ]
            cand = cand.sort_values(["open_ret", "prev_vol_ratio"], ascending=False).head(self.top_n)
            for _, r in cand.iterrows():
                sigs.append(
                    Signal(
                        date=pd.Timestamp(d),
                        code=r["code"],
                        strength=float(r["open_ret"]),
                        meta={"prev_vol_ratio": float(r["prev_vol_ratio"])},
                    )
                )
        return sigs


class OpenGapHotLookaheadBad:
    """BAD example: uses same-day EOD vol_ratio at open — lint must fail."""

    name = "open_gap_hot_lookahead_bad"
    required_columns = ["open_ret", "vol_ratio_eod", "industry"]
    decision_columns = ["open_ret", "vol_ratio_eod", "industry"]  # vol_ratio_eod is EOD

    def __init__(self, vol_lo=3.0, vol_hi=8.0, open_lo=0.02, open_hi=0.07, top_n=3, hot_k=3):
        self.vol_lo, self.vol_hi = vol_lo, vol_hi
        self.open_lo, self.open_hi = open_lo, open_hi
        self.top_n, self.hot_k = top_n, hot_k

    def generate(self, panel: pd.DataFrame) -> list[Signal]:
        sigs = []
        for d, day in panel.groupby("date"):
            hot = _hot_industries(day, self.hot_k)
            cand = day[
                (day["vol_ratio_eod"] >= self.vol_lo)
                & (day["vol_ratio_eod"] <= self.vol_hi)
                & (day["open_ret"] >= self.open_lo)
                & (day["open_ret"] <= self.open_hi)
                & (day["industry"].isin(hot))
                & (~day["is_limit_up_open"])
            ].sort_values("vol_ratio_eod", ascending=False).head(self.top_n)
            for _, r in cand.iterrows():
                sigs.append(Signal(date=pd.Timestamp(d), code=r["code"], strength=float(r["vol_ratio_eod"])))
        return sigs


class LimitDownBounceWatchlist:
    name = "limit_down_bounce_watchlist"
    required_columns = ["ret_5d", "industry", "is_limit_down_open", "open", "high", "next_open"]
    decision_columns = ["ret_5d", "industry", "is_limit_down_open", "open"]  # ret_5d is lagged

    def __init__(self, n_watch=5):
        self.n_watch = n_watch

    def _watchlist(self, prev: pd.DataFrame) -> set[str]:
        x = prev.dropna(subset=["ret_5d", "industry"]).sort_values("ret_5d")
        picked, seen = [], set()
        for _, r in x.iterrows():
            if r["industry"] in seen:
                continue
            seen.add(r["industry"])
            picked.append(r["code"])
            if len(picked) >= self.n_watch:
                break
        return set(picked)

    def generate(self, panel: pd.DataFrame) -> list[Signal]:
        dates = sorted(panel["date"].unique())
        by = {d: g for d, g in panel.groupby("date")}
        sigs = []
        for i, d in enumerate(dates):
            if i == 0:
                continue
            watch = self._watchlist(by[dates[i - 1]])
            day = by[d]
            hits = day[(day["code"].isin(watch)) & (day["is_limit_down_open"])]
            for _, r in hits.iterrows():
                sigs.append(Signal(date=pd.Timestamp(d), code=r["code"], strength=1.0))
        return sigs


class LimitUpAmountBoard:
    """Limit-up close + amount threshold. Decision=close (EOD fields OK)."""

    name = "limit_up_amount_board"
    required_columns = ["is_limit_up_close", "amount", "limit_up", "low", "next_open", "is_limit_up_open"]
    decision_columns = ["is_limit_up_close", "amount", "limit_up", "low", "is_limit_up_open"]

    def __init__(self, min_amount=2e9, top_n=3):
        self.min_amount = min_amount
        self.top_n = top_n

    def generate(self, panel: pd.DataFrame) -> list[Signal]:
        sigs = []
        for d, day in panel.groupby("date"):
            cand = day[
                (day["is_limit_up_close"])
                & (day["amount"] >= self.min_amount)
                & (~day["is_limit_up_open"])
            ].sort_values("amount", ascending=False).head(self.top_n)
            for _, r in cand.iterrows():
                sigs.append(
                    Signal(
                        date=pd.Timestamp(d),
                        code=r["code"],
                        strength=float(r["amount"]),
                        meta={"amount": float(r["amount"])},
                    )
                )
        return sigs


class GapDownAfterUpMarket:
    """
    Honest open mean-reversion:
    - Yesterday cross-sectional median close_ret > mkt_lo (known at open)
    - Today open_ret in [gap_lo, gap_hi] (e.g. -5%..-2%), not limit-down
    - Buy open, sell next open; take the most depressed top_n names
    """

    name = "gap_down_after_up_market"
    required_columns = [
        "open_ret",
        "mkt_prev_median",
        "is_limit_down_open",
        "next_open",
    ]
    decision_columns = ["open_ret", "mkt_prev_median", "is_limit_down_open"]

    def __init__(
        self,
        gap_lo: float = -0.05,
        gap_hi: float = -0.02,
        mkt_lo: float = 0.003,
        top_n: int = 3,
        boards: tuple[str, ...] | None = None,
    ):
        self.gap_lo = gap_lo
        self.gap_hi = gap_hi
        self.mkt_lo = mkt_lo
        self.top_n = top_n
        self.boards = boards

    def generate(self, panel: pd.DataFrame) -> list[Signal]:
        sigs: list[Signal] = []
        for d, day in panel.groupby("date"):
            g = day
            if self.boards:
                g = g[g["code"].str.startswith(self.boards)]
            cand = g[
                (g["open_ret"] >= self.gap_lo)
                & (g["open_ret"] <= self.gap_hi)
                & (g["mkt_prev_median"] > self.mkt_lo)
                & (~g["is_limit_down_open"])
            ]
            cand = cand.sort_values("open_ret").head(self.top_n)
            for _, r in cand.iterrows():
                sigs.append(
                    Signal(
                        date=pd.Timestamp(d),
                        code=r["code"],
                        strength=-float(r["open_ret"]),
                        meta={
                            "open_ret": float(r["open_ret"]),
                            "mkt_prev_median": float(r["mkt_prev_median"]),
                        },
                    )
                )
        return sigs


REGISTRY = {
    OpenGapHotNoLookahead.name: OpenGapHotNoLookahead,
    OpenGapHotLookaheadBad.name: OpenGapHotLookaheadBad,
    LimitDownBounceWatchlist.name: LimitDownBounceWatchlist,
    LimitUpAmountBoard.name: LimitUpAmountBoard,
    GapDownAfterUpMarket.name: GapDownAfterUpMarket,
}
