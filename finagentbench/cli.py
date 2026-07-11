from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters import load_run_file
from .benchmark import (
    run_benchmark_suite,
    run_live_semantic_benchmark_suite,
    run_semantic_benchmark_suite,
)
from .profiles import apply_profile
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
    eval_parser.add_argument("--profile", choices=["default", "ci", "audit"], default="default")

    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("baseline_json")
    compare_parser.add_argument("current_json")
    compare_parser.add_argument("--case", required=True)
    compare_parser.add_argument("--out", default="outputs")
    compare_parser.add_argument("--adapter", default="auto")
    compare_parser.add_argument("--profile", choices=["default", "ci", "audit"], default="default")

    gate_parser = sub.add_parser("gate")
    gate_parser.add_argument("run_json", nargs="+")
    gate_parser.add_argument("--case", required=True)
    gate_parser.add_argument("--out", default="outputs/gate")
    gate_parser.add_argument("--adapter", default="auto")
    gate_parser.add_argument("--profile", choices=["default", "ci", "audit"], default="default")

    runtime_parser = sub.add_parser("run-reference")
    runtime_parser.add_argument("--out", default="outputs/reference-agent-run.json")
    runtime_parser.add_argument("--query", default=None)

    suggest_parser = sub.add_parser("suggest")
    suggest_parser.add_argument("run_json")
    suggest_parser.add_argument("--case", required=True)
    suggest_parser.add_argument("--out", default="outputs/suggest.json")
    suggest_parser.add_argument("--adapter", default="auto")
    suggest_parser.add_argument("--profile", choices=["default", "ci", "audit"], default="default")

    benchmark_parser = sub.add_parser("benchmark")
    benchmark_parser.add_argument("suite_json")
    benchmark_parser.add_argument("--out", default="outputs/benchmark_report.json")

    semantic_benchmark_parser = sub.add_parser("semantic-benchmark")
    semantic_benchmark_parser.add_argument("suite_json")
    semantic_benchmark_parser.add_argument("--out", default="outputs/semantic_benchmark_report.json")

    live_semantic_parser = sub.add_parser("live-semantic-benchmark")
    live_semantic_parser.add_argument("suite_json")
    live_semantic_parser.add_argument("--out", default="outputs/live_semantic_benchmark_report.json")
    live_semantic_parser.add_argument("--limit", type=int, default=10)
    live_semantic_parser.add_argument("--endpoint", default=None)
    live_semantic_parser.add_argument("--model", default=None)
    live_semantic_parser.add_argument("--api-key-env", default="FINAGENTBENCH_LLM_API_KEY")
    live_semantic_parser.add_argument("--cache-path", default="outputs/live_semantic_judge_cache.json")
    live_semantic_parser.add_argument("--prompt-version", default="financial_audit_v1")
    live_semantic_parser.add_argument("--retry-count", type=int, default=2)
    live_semantic_parser.add_argument("--backoff-seconds", type=float, default=1.0)
    live_semantic_parser.add_argument("--timeout-seconds", type=float, default=20.0)

    args = parser.parse_args()
    if args.command == "evaluate":
        run = load_run_file(args.run_json, args.adapter)
        case = apply_profile(_load_json(args.case), args.profile)
        report = evaluate_run(run, case)
        paths = write_eval_report(report, Path(args.out))
        print(f"{'PASS' if report.passed else 'FAIL'} {report.run_id} score={report.score}")
        print(json.dumps(paths, ensure_ascii=False, indent=2))
        return 0 if report.passed else 1

    if args.command == "gate":
        case = apply_profile(_load_json(args.case), args.profile)
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
        case = apply_profile(_load_json(args.case), args.profile)
        report = evaluate_run(run, case)
        payload = build_suggestions(report)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "benchmark":
        payload = run_benchmark_suite(args.suite_json)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["passed"] else 1

    if args.command == "semantic-benchmark":
        payload = run_semantic_benchmark_suite(args.suite_json)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["passed"] else 1

    if args.command == "live-semantic-benchmark":
        judge_config = {
            "provider": "openai-compatible",
            "endpoint": args.endpoint,
            "model": args.model,
            "api_key_env": args.api_key_env,
            "cache_path": args.cache_path,
            "prompt_version": args.prompt_version,
            "retry_count": args.retry_count,
            "backoff_seconds": args.backoff_seconds,
            "timeout_seconds": args.timeout_seconds,
        }
        payload = run_live_semantic_benchmark_suite(
            args.suite_json,
            judge_config,
            limit=args.limit,
        )
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["passed"] else 1

    baseline = load_run_file(args.baseline_json, args.adapter)
    current = load_run_file(args.current_json, args.adapter)
    case = apply_profile(_load_json(args.case), args.profile)
    payload = compare_runs(baseline, current, case)
    paths = write_compare_report(payload, Path(args.out))
    print(f"{'PASS' if payload['passed'] else 'FAIL'} delta={payload['score_delta']}")
    print(json.dumps(paths, ensure_ascii=False, indent=2))
    return 0 if payload["passed"] else 1


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
