from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters import load_run_file
from .reference_runtime import run_reference_agent
from .report import write_compare_report, write_eval_report
from .runner import compare_runs, evaluate_run
from .suggest import build_suggestions


def main() -> int:
    parser = argparse.ArgumentParser(prog="finagentbench")
    sub = parser.add_subparsers(dest="command", required=True)

    eval_parser = sub.add_parser("evaluate")
    eval_parser.add_argument("run_json")
    eval_parser.add_argument("--case", required=True)
    eval_parser.add_argument("--out", default="outputs")
    eval_parser.add_argument("--adapter", default="auto")

    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("baseline_json")
    compare_parser.add_argument("current_json")
    compare_parser.add_argument("--case", required=True)
    compare_parser.add_argument("--out", default="outputs")
    compare_parser.add_argument("--adapter", default="auto")

    gate_parser = sub.add_parser("gate")
    gate_parser.add_argument("run_json", nargs="+")
    gate_parser.add_argument("--case", required=True)
    gate_parser.add_argument("--out", default="outputs/gate")
    gate_parser.add_argument("--adapter", default="auto")

    runtime_parser = sub.add_parser("run-reference")
    runtime_parser.add_argument("--out", default="outputs/reference-agent-run.json")
    runtime_parser.add_argument("--query", default=None)

    suggest_parser = sub.add_parser("suggest")
    suggest_parser.add_argument("run_json")
    suggest_parser.add_argument("--case", required=True)
    suggest_parser.add_argument("--out", default="outputs/suggest.json")
    suggest_parser.add_argument("--adapter", default="auto")

    args = parser.parse_args()
    if args.command == "evaluate":
        run = load_run_file(args.run_json, args.adapter)
        case = _load_json(args.case)
        report = evaluate_run(run, case)
        paths = write_eval_report(report, Path(args.out))
        print(f"{'PASS' if report.passed else 'FAIL'} {report.run_id} score={report.score}")
        print(json.dumps(paths, ensure_ascii=False, indent=2))
        return 0 if report.passed else 1

    if args.command == "gate":
        case = _load_json(args.case)
        failed = False
        for run_json in args.run_json:
            run = load_run_file(run_json, args.adapter)
            report = evaluate_run(run, case)
            run_out = Path(args.out) / report.run_id
            paths = write_eval_report(report, run_out)
            failed = failed or not report.passed
            print(f"{'PASS' if report.passed else 'FAIL'} {report.run_id} score={report.score}")
            print(json.dumps(paths, ensure_ascii=False, indent=2))
        return 1 if failed else 0

    if args.command == "run-reference":
        run = run_reference_agent(args.query)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"WROTE {out_path}")
        return 0

    if args.command == "suggest":
        run = load_run_file(args.run_json, args.adapter)
        case = _load_json(args.case)
        report = evaluate_run(run, case)
        payload = build_suggestions(report)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    baseline = load_run_file(args.baseline_json, args.adapter)
    current = load_run_file(args.current_json, args.adapter)
    case = _load_json(args.case)
    payload = compare_runs(baseline, current, case)
    paths = write_compare_report(payload, Path(args.out))
    print(f"{'PASS' if payload['passed'] else 'FAIL'} delta={payload['score_delta']}")
    print(json.dumps(paths, ensure_ascii=False, indent=2))
    return 0 if payload["passed"] else 1


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
