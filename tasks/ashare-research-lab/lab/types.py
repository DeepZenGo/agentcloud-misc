from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import pandas as pd


@dataclass
class Signal:
    """One actionable signal known at decision_time (no future fields allowed)."""

    date: pd.Timestamp
    code: str
    side: str = "buy"  # buy only for long-only lab v1
    strength: float = 1.0
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Trade:
    date: pd.Timestamp
    code: str
    buy: float
    sell: float
    ret: float
    fill_model: str
    weight: float
    equity_after: float
    meta: dict[str, Any] = field(default_factory=dict)


class Strategy(Protocol):
    """Strategy contract: name + generate signals from a feature panel slice."""

    name: str
    # Columns the strategy reads — used by lookahead linter
    required_columns: list[str]
    # Columns that must be known at decision time (shifted / open-known)
    decision_columns: list[str]

    def generate(self, panel: pd.DataFrame) -> list[Signal]:
        """Return signals. Must not use same-day close-only fields unless decision=close."""
        ...
