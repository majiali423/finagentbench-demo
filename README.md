# FinAgentBench

**Replay-first reliability evaluation for financial Agents.**

FinAgentBench evaluates an exported Agent trace instead of judging only the
final answer. It turns financial calculations, entities, evidence, citations,
risks and execution steps into deterministic findings that can block CI.

Project status: **Release Candidate / Internal Portfolio Release**
Package: `0.1.0rc1` | FinRun schema: `1.0`

## Why replay the trace?

A fluent report can still:

- omit one company in a comparison;
- calculate a ratio from the wrong inputs;
- cite evidence from another issuer;
- hide missing market data;
- pass an evaluator that had nothing checkable.

FinAgentBench addresses those failure modes with a framework-independent
artifact and fail-closed metrics.

## How it works

```text
Agent state or FinRun
        ?
        ?
 Adapter / schema validation
        ?
        ?
 Deterministic metrics ?? optional semantic judge
        ?
        ?
 Findings + EvalReport
        ?
        ?
 CI pass / fail
```

## Core features

- Framework-independent `FinRun` contract
- Deterministic-first entity, numeric, temporal and unit checks
- Evidence coverage and numeric evidence consistency
- Entity leakage detection for issuer and comparison cases
- Fail-closed behavior when required checks have zero inputs
- Four-mutation evaluator regression suite
- JSON, Markdown and HTML EvalReports
- Optional semantic audit profile
- Portable LumenFin compatibility gate

## Minimal FinRun

```json
{
  "schema_version": "1.0",
  "run_id": "demo-001",
  "query": "Compare Company A and Company B",
  "entities": [{"name": "Company A"}, {"name": "Company B"}],
  "steps": [{"name": "retrieval", "status": "ok"}],
  "metrics": [],
  "evidence": [],
  "market_data": [],
  "final_output": "Research output with disclosed limitations."
}
```

Cases decide which fields must be checkable. An empty list does not receive a
free pass when `require_checkable_metrics` is enabled.

## Quick start

Requires Python 3.11+.

```bash
python -m venv .venv
python -m pip install -e .
python -m unittest discover -s tests -v
```

Evaluate the included synthetic due-diligence run:

```bash
python -m finagentbench evaluate \
  fixtures/pass_due_diligence_finrun.json \
  --case fixtures/case_due_diligence.json \
  --profile ci \
  --out outputs/example
```

Exit codes for `evaluate` / `gate` / `benchmark`:

| Code | Meaning |
|------|---------|
| `0` | evaluation / gate passed |
| `1` | evaluation / gate failed (expected for known-fail fixtures) |
| non-`0` other | CLI / IO / argument error |

When a Quick Start example intentionally evaluates a failing fixture, exit code
`1` is success for the demo narrative, not a broken install.

Key-free release demo:

```bash
python scripts/run_offline_demo.py
```

Mutation and correctness gates:

```bash
python scripts/run_mutation_suite.py
python scripts/run_correctness_validation.py
```

Supported validation commands: [docs/VALIDATION_COMMANDS.md](docs/VALIDATION_COMMANDS.md).

## LumenFin integration

Clone `lumenfin-agent` and `finagentbench-demo` as sibling directories, or set
`LUMENFIN_ROOT` / `FINAGENTBENCH_DIR`.

```bash
python scripts/validate_cross_repo.py --profile ci
```

The summary records both repository commits, worktree state, FinRun schema,
benchmark profile and mutation results.

Full live RC orchestration:

```bash
python scripts/run_rc_validation.py --help
python scripts/run_rc_validation.py --dry-run
python scripts/run_rc_validation.py
```

This command requires the configured LumenFin live providers. Infrastructure
failures are non-pass and must not be reported as Agent-quality success.

## Metrics

The deterministic CI profile covers:

- entity coverage and leakage;
- numeric correctness;
- unit/currency and temporal consistency;
- evidence coverage and consistency;
- required execution steps and report sections;
- risk disclosure and compliance language.

See [Metrics](docs/METRICS.md) and
[FinRun compatibility](docs/FINRUN_COMPATIBILITY.md).

## Benchmark integrity

- No metric threshold is changed to match a tested Agent.
- Required empty checks fail with diagnostic findings.
- The mutation gate must detect wrong number, wrong entity, missing citation
  and missing risk.
- The CI profile removes optional semantic metrics; it does not lower case
  thresholds.
- Case hashes and enabled metrics are recorded in EvalReports.

## Repository structure

```text
finagentbench/       evaluator, adapters, metrics and report model
benchmarks/          deterministic suites, mutations and semantic gold data
fixtures/            small synthetic FinRuns and case contracts
tests/               unit and cross-project regression tests
scripts/             supported release and validation entrypoints
docs/                schema, metrics, integration and CI guides
reports/current/     current release evidence
reports/history/     superseded engineering evidence
tools/archived_audits/ unsupported historical audit scripts
examples/            sanitized demo artifacts
```

## Limitations

- This is a reliability framework, not an academic leaderboard.
- Scores depend on the case contract and exported trace quality.
- Optional semantic judges introduce provider and prompt variability.
- Passing a benchmark does not prove investment performance or universal
  factual correctness.
- Human financial review remains required.

## Documentation

Start with [docs/README.md](docs/README.md). The current release evidence is in
[reports/current/FinAgentBench_Final_Release_Report.md](reports/current/FinAgentBench_Final_Release_Report.md).

## License status

No public license grant has been selected. The current repository is intended
for private/internal portfolio review unless the owner explicitly adds a
license.
