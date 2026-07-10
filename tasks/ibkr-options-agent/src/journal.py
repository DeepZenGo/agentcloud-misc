"""Append-only trade / decision journal + daily summary helper."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Journal:
    def __init__(self, path: Path, daily_summary_path: Path) -> None:
        self.path = path
        self.daily_summary_path = daily_summary_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.daily_summary_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: str, payload: dict[str, Any]) -> None:
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def write_daily_summary(
        self,
        *,
        equity_before: float,
        equity_after: float,
        notes: str,
        trades: list[dict[str, Any]],
    ) -> Path:
        pnl = equity_after - equity_before
        pct = (pnl / equity_before * 100.0) if equity_before else 0.0
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        lines = [
            f"# Daily Summary — {day}",
            "",
            f"- Equity: `{equity_before:.2f}` → `{equity_after:.2f}`",
            f"- Day P/L: `{pnl:+.2f}` ({pct:+.2f}%)",
            f"- Notes: {notes}",
            "",
            "## Trades",
            "",
        ]
        if not trades:
            lines.append("_No trades._")
        else:
            for t in trades:
                lines.append(f"- `{json.dumps(t, ensure_ascii=False)}`")
        lines.append("")
        text = "\n".join(lines)
        # Append to rolling file
        with self.daily_summary_path.open("a", encoding="utf-8") as f:
            f.write(text + "\n---\n\n")
        # Also write dated snapshot
        dated = self.daily_summary_path.parent / f"daily_{day}.md"
        dated.write_text(text + "\n", encoding="utf-8")
        return dated
