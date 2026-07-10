#!/usr/bin/env python3
"""CLI for the scientific A-share research lab."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from lab.checks import gate_bundle, lint_strategy  # noqa: E402
from lab.data import load_config, load_panel  # noqa: E402
from lab.engine import run_backtest  # noqa: E402
from lab.report import write_report  # noqa: E402
from lab.splits import filter_panel, time_splits  # noqa: E402
from strategies import REGISTRY  # noqa: E402


def load_hypothesis(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_strategy(hyp: dict):
    name = hyp["strategy"]
    if name not in REGISTRY:
        raise KeyError(f"unknown strategy {name}; known={list(REGISTRY)}")
    cls = REGISTRY[name]
    return cls(**(hyp.get("params") or {}))


def cmd_list(_args) -> None:
    print("Strategies:")
    for k in REGISTRY:
        print(f"  - {k}")
    print("\nHypotheses:")
    for p in sorted((ROOT / "hypotheses").glob("*.yaml")):
        h = load_hypothesis(p)
        print(f"  - {p.name}: {h.get('id')} [{h.get('strategy')}]")


def cmd_lint(args) -> None:
    hyp = load_hypothesis(Path(args.hypothesis))
    strat = build_strategy(hyp)
    decision = hyp.get("decision_time", "open")
    res = lint_strategy(strat, decision=decision)
    print(json.dumps({"ok": res.ok, "errors": res.errors, "warnings": res.warnings}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if res.ok else 2)


def cmd_run(args) -> None:
    cfg = load_config()
    hyp = load_hypothesis(Path(args.hypothesis))
    strat = build_strategy(hyp)
    decision = hyp.get("decision_time", "open")
    lint = lint_strategy(strat, decision=decision)

    print(f"hypothesis={hyp.get('id')} strategy={strat.name} decision={decision}")
    print(f"lint ok={lint.ok} errors={lint.errors} warnings={lint.warnings}")

    if not lint.ok and not args.force:
        print("ABORT: lookahead lint failed (pass --force to run anyway)")
        out = ROOT / "results" / str(hyp.get("id", "run"))
        write_report(out, hyp, lint, {}, type("G", (), {"ok": False, "errors": ["lint_failed"], "warnings": []})(), {})
        raise SystemExit(2)

    print("loading panel ...")
    panel = load_panel(cfg)
    dates = sorted(panel["date"].unique())
    splits = time_splits(
        dates,
        test_ratio=cfg["splits"]["test_ratio"],
        val_ratio=cfg["splits"]["val_ratio"],
        purge_days=cfg["splits"]["purge_days"],
    )
    print(
        f"panel codes={panel['code'].nunique()} days={len(dates)} "
        f"train={splits.train.start.date()}..{splits.train.end.date()} "
        f"val={splits.val.start.date()}..{splits.val.end.date()} "
        f"test={splits.test.start.date()}..{splits.test.end.date()}"
    )

    fill_model = hyp.get("fill_model", cfg["fills"]["default"])
    cost = cfg["costs"]["roundtrip"]
    results = {}
    trades = {}
    for split in (splits.train, splits.val, splits.test):
        # Need lookback rows for features (ret_5d etc.) — use full panel for generate,
        # but only keep trades whose date is in split.
        sigs = strat.generate(panel)
        sigs = [s for s in sigs if pd_ts(s.date) in set(split.dates)]
        # For fill we need next_open which may be outside split — keep full panel for engine
        tdf, perf = run_backtest(
            panel,
            sigs,
            fill_model=fill_model,
            cost_roundtrip=cost,
            max_names_per_day=int((hyp.get("params") or {}).get("top_n", 3) or 3),
        )
        # Drop trades whose sell relies on missing data already handled; filter to split dates
        if not tdf.empty:
            tdf = tdf[tdf["date"].isin(split.dates)].copy()
            # recompute equity path within split only
            tdf, perf = _recompute_equity(tdf, cost)
        results[split.name] = perf
        trades[split.name] = tdf
        print(f"  {split.name}: trades={perf['n_trades']} exp={perf.get('expectancy')} dd={perf.get('max_drawdown')}")

    gates = gate_bundle(results, cfg["gates"])
    print(f"gates ok={gates.ok} errors={gates.errors} warnings={gates.warnings}")

    out = ROOT / "results" / str(hyp.get("id", strat.name))
    path = write_report(out, hyp, lint, results, gates, trades)
    print(f"report -> {path}")
    raise SystemExit(0 if (lint.ok and gates.ok) else 3)


def pd_ts(x):
    import pandas as pd

    return pd.Timestamp(x)


def _recompute_equity(tdf, cost, initial_cash=1_000_000.0):
    """Rebuild equity after filtering to a split (equal-weight by day)."""
    import pandas as pd
    from lab.metrics import performance

    if tdf.empty:
        return tdf, performance(tdf, initial_cash)
    rows = []
    cash = initial_cash
    for d, g in tdf.groupby("date", sort=True):
        w = 1.0 / len(g)
        day_cash = cash
        day_pnl = 0.0
        for _, r in g.iterrows():
            day_pnl += day_cash * w * float(r["ret"])
            rec = r.to_dict()
            rec["equity_after"] = day_cash + day_pnl
            rows.append(rec)
        cash = day_cash + day_pnl
    out = pd.DataFrame(rows)
    return out, performance(out, initial_cash)


def cmd_run_all(args) -> None:
    hyps = sorted((ROOT / "hypotheses").glob("*.yaml"))
    if args.only:
        hyps = [p for p in hyps if args.only in p.name or args.only in p.read_text(encoding="utf-8")]
    codes = []
    for p in hyps:
        print("=" * 60, p.name)
        ns = argparse.Namespace(hypothesis=str(p), force=args.force)
        try:
            cmd_run(ns)
            codes.append(0)
        except SystemExit as e:
            codes.append(int(e.code or 0))
    # summary index
    index = []
    for d in sorted((ROOT / "results").glob("H*")):
        rep = d / "report.md"
        met = d / "metrics.json"
        if met.exists():
            data = json.loads(met.read_text(encoding="utf-8"))
            test = data.get("test", {})
            index.append(
                {
                    "id": d.name,
                    "test_n": test.get("n_trades"),
                    "test_exp": test.get("expectancy"),
                    "test_dd": test.get("max_drawdown"),
                    "report": str(rep) if rep.exists() else "",
                }
            )
    out = ROOT / "results" / "index.json"
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print("index ->", out)
    # exit 0 if any candidate else 3
    raise SystemExit(0 if any(c == 0 for c in codes) else 3)


def main() -> None:
    ap = argparse.ArgumentParser(description="A-share scientific research lab")
    sp = ap.add_subparsers(dest="cmd", required=True)

    sp.add_parser("list", help="list strategies and hypotheses")

    p_lint = sp.add_parser("lint", help="lookahead lint only")
    p_lint.add_argument("hypothesis")

    p_run = sp.add_parser("run", help="run one hypothesis through train/val/test + gates")
    p_run.add_argument("hypothesis")
    p_run.add_argument("--force", action="store_true", help="run even if lint fails")

    p_all = sp.add_parser("run-all", help="run all hypotheses")
    p_all.add_argument("--force", action="store_true")
    p_all.add_argument("--only", default="", help="substring filter on hypothesis file/content")

    args = ap.parse_args()
    if args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "lint":
        cmd_lint(args)
    elif args.cmd == "run":
        cmd_run(args)
    elif args.cmd == "run-all":
        cmd_run_all(args)


if __name__ == "__main__":
    main()
