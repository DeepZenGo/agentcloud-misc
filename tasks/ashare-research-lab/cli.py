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

from lab.assumptions import OPTIMISTIC_FILLS, audit_assumptions, verdict as grade_verdict  # noqa: E402
from lab.checks import gate_bundle, lint_strategy  # noqa: E402
from lab.data import load_config, load_panel  # noqa: E402
from lab.engine import run_backtest  # noqa: E402
from lab.report import write_report  # noqa: E402
from lab.splits import time_splits  # noqa: E402
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


def pd_ts(x):
    import pandas as pd

    return pd.Timestamp(x)


def _recompute_equity(tdf, cost, initial_cash=1_000_000.0):
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


def _run_splits(panel, strat, splits, fill_model, cost, top_n):
    results, trades = {}, {}
    for split in (splits.train, splits.val, splits.test):
        sigs = strat.generate(panel)
        sigs = [s for s in sigs if pd_ts(s.date) in set(split.dates)]
        tdf, perf = run_backtest(
            panel,
            sigs,
            fill_model=fill_model,
            cost_roundtrip=cost,
            max_names_per_day=top_n,
        )
        if not tdf.empty:
            tdf = tdf[tdf["date"].isin(split.dates)].copy()
            tdf, perf = _recompute_equity(tdf, cost)
        results[split.name] = perf
        trades[split.name] = tdf
    return results, trades


def _fill_stress(panel, strat, splits, hyp, cfg, cost, top_n):
    """For limit-up fills, also test EOD-executable chase_next_open."""
    fill = hyp.get("fill_model", "")
    if fill not in OPTIMISTIC_FILLS:
        return None
    stress_fill = "chase_next_open"
    results, _ = _run_splits(panel, strat, splits, stress_fill, cost, top_n)
    errors = []
    # Stress must not be a bloodbath on val+test expectancy
    min_exp = cfg.get("gates", {}).get("stress_min_expectancy", -0.002)
    for split in ("val", "test"):
        exp = results.get(split, {}).get("expectancy")
        n = results.get(split, {}).get("n_trades") or 0
        if n < 10:
            errors.append(f"stress {split} n_trades={n} < 10")
            continue
        if exp is not None and exp == exp and exp < min_exp:
            errors.append(f"stress {split} expectancy={exp:.4f} < {min_exp}")
    return {
        "fill_model": stress_fill,
        "results": results,
        "ok": not errors,
        "errors": errors,
    }


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
    ass = audit_assumptions(hyp, load_config().get("assumptions_policy", {}))
    print(
        json.dumps(
            {
                "lint": {"ok": res.ok, "errors": res.errors, "warnings": res.warnings},
                "assumptions": {
                    "grade": ass.grade,
                    "ok_for_candidate": ass.ok_for_candidate,
                    "errors": ass.errors,
                    "warnings": ass.warnings,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(0 if res.ok else 2)


def cmd_run(args) -> None:
    cfg = load_config()
    hyp = load_hypothesis(Path(args.hypothesis))
    strat = build_strategy(hyp)
    decision = hyp.get("decision_time", "open")
    lint = lint_strategy(strat, decision=decision)
    ass = audit_assumptions(hyp, cfg.get("assumptions_policy", {}))

    print(f"hypothesis={hyp.get('id')} strategy={strat.name} decision={decision}")
    print(f"lint ok={lint.ok} errors={lint.errors}")
    print(f"assumptions grade={ass.grade} candidate={ass.ok_for_candidate} errors={ass.errors}")

    empty_gates = type("G", (), {"ok": False, "errors": ["lint_failed"], "warnings": []})()
    if not lint.ok and not args.force:
        print("ABORT: lookahead lint failed (pass --force to run anyway)")
        out = ROOT / "results" / str(hyp.get("id", "run"))
        v = grade_verdict(False, False, ass, None)
        write_report(out, hyp, lint, {}, empty_gates, {}, assumption_audit=ass, final_verdict=v)
        print(f"verdict={v}")
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
    top_n = int((hyp.get("params") or {}).get("top_n", 3) or 3)
    results, trades = _run_splits(panel, strat, splits, fill_model, cost, top_n)
    for name, perf in results.items():
        print(f"  {name}: trades={perf['n_trades']} exp={perf.get('expectancy')} dd={perf.get('max_drawdown')}")

    gates = gate_bundle(results, cfg["gates"])
    print(f"metric gates ok={gates.ok} errors={gates.errors}")

    stress = _fill_stress(panel, strat, splits, hyp, cfg, cost, top_n)
    stress_ok = None if stress is None else stress["ok"]
    if stress is not None:
        print(f"fill stress ok={stress['ok']} errors={stress['errors']}")

    final = grade_verdict(lint.ok or args.force, gates.ok, ass, stress_ok)
    # If assumptions say reject hard
    if ass.grade == "reject" and not ass.ok_for_weak:
        final = "REJECT"

    out = ROOT / "results" / str(hyp.get("id", strat.name))
    path = write_report(
        out,
        hyp,
        lint,
        results,
        gates,
        trades,
        assumption_audit=ass,
        stress=stress,
        final_verdict=final,
    )
    print(f"verdict={final}")
    print(f"report -> {path}")
    # exit: 0 candidate, 4 weak, else fail
    if final == "CANDIDATE":
        raise SystemExit(0)
    if final == "WEAK_CANDIDATE":
        raise SystemExit(4)
    raise SystemExit(3)


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
    index = []
    for d in sorted(p for p in (ROOT / "results").glob("H*") if p.is_dir()):
        met = d / "metrics.json"
        verd = d / "verdict.txt"
        entry = {"id": d.name, "report": str(d / "report.md")}
        if verd.exists():
            entry["verdict"] = verd.read_text(encoding="utf-8").strip()
        if met.exists():
            data = json.loads(met.read_text(encoding="utf-8"))
            # support both old flat and new nested
            metrics = data.get("metrics", data)
            test = metrics.get("test", {})
            entry.update(
                {
                    "verdict": data.get("verdict", entry.get("verdict")),
                    "test_n": test.get("n_trades"),
                    "test_exp": test.get("expectancy"),
                    "test_dd": test.get("max_drawdown"),
                    "assumption_grade": data.get("assumption_grade"),
                }
            )
        index.append(entry)
    out = ROOT / "results" / "index.json"
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print("index ->", out)
    for row in index:
        print(f"  {row.get('id')}: {row.get('verdict')}")
    if any(c == 0 for c in codes):
        raise SystemExit(0)
    if any(c == 4 for c in codes):
        raise SystemExit(4)
    raise SystemExit(3)


def main() -> None:
    ap = argparse.ArgumentParser(description="A-share scientific research lab")
    sp = ap.add_subparsers(dest="cmd", required=True)

    sp.add_parser("list", help="list strategies and hypotheses")

    p_lint = sp.add_parser("lint", help="lookahead + assumption lint")
    p_lint.add_argument("hypothesis")

    p_run = sp.add_parser("run", help="run one hypothesis through full pipeline")
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
