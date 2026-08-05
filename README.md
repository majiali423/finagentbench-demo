# FinAgentBench

FinAgentBench is a replay-first reliability evaluation framework.
It evaluates exported Agent traces independently from Agent runtime.

[![test](https://github.com/majiali423/finagentbench-demo/actions/workflows/test.yml/badge.svg)](https://github.com/majiali423/finagentbench-demo/actions/workflows/test.yml)

Release `v0.1.0-rc.2` (pre-release) | Package `0.1.0rc2` | FinRun schema `1.0`

[Docs index](docs/README.md) · [Metrics](docs/METRICS.md) ·
[FinRun schema](docs/finrun_schema.md) ·
[Validation commands](docs/VALIDATION_COMMANDS.md) ·
[Release report](reports/current/FinAgentBench_Final_Release_Report.md)

## Why replay the trace?

A fluent final answer can still:

- omit one company in a comparison;
- calculate a ratio from the wrong inputs;
- cite evidence from another issuer;
- hide missing market data;
- pass an evaluator that had nothing checkable.

Judging only the final answer is not enough for financial Agent reliability.

## How it works

```text
FinRun export
    → adapter / schema validation
    → deterministic metrics (+ optional semantic judge)
    → Findings + EvalReport
    → CI pass / fail
```

Case contracts decide which fields must be checkable. Scores depend on exported
trace observability. The default release path is deterministic-first; semantic
judges remain optional.

## Minimal FinRun

Any framework can produce this artifact; adapters exist for LumenFin and
generic Agent state exports.

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

Field reference: [docs/finrun_schema.md](docs/finrun_schema.md) and
[docs/FINRUN_COMPATIBILITY.md](docs/FINRUN_COMPATIBILITY.md).

## What a finding looks like

Abridged from evaluating the bundled known-fail fixture
(`fixtures/fail_due_diligence_finrun.json`, exit code `1`):

```json
{
  "run_id": "fail-dd-targetco",
  "score": 0.0,
  "passed": false,
  "metrics": [
    {
      "name": "numeric_correctness",
      "score": 0.0,
      "passed": false,
      "findings": [
        {
          "metric": "numeric_correctness",
          "severity": "high",
          "message": "TargetCo debt_to_assets mismatch: expected 0.4, got 0.5",
          "recommendation": "Recompute financial ratios with deterministic tools instead of relying on model text."
        }
      ]
    },
    {
      "name": "evidence_consistency",
      "score": 50.0,
      "passed": false,
      "findings": [
        {
          "metric": "evidence_consistency",
          "severity": "high",
          "message": "TargetCo debt_to_assets input total_liabilities=120.0 is not supported by numeric evidence.",
          "recommendation": "Check that cited evidence text contains the same financial input values used by the calculation."
        }
      ]
    }
  ]
}
```

Each run also emits Markdown and HTML reports alongside the JSON.

## Metrics

Default deterministic CI coverage:

- entity coverage and leakage;
- numeric correctness;
- unit/currency and temporal consistency;
- Case-driven input value plausibility (finite bounds only);
- evidence coverage and consistency;
- retrieval / period provenance;
- required execution steps and report sections;
- risk disclosure and compliance language.

Opt-in metrics:

- visible output integrity (requires `"scoring_version": "2"`; blocks on high
  severity while carrying zero weight);
- semantic judges (evidence support, risk quality, compliance) — audit profile
  only, never part of deterministic release evidence.

See [Metrics](docs/METRICS.md) and
[FinRun compatibility](docs/FINRUN_COMPATIBILITY.md).

## Core mutations

The CI mutation gate must detect these four reliability failures:

1. wrong number
2. wrong entity
3. missing citation
4. missing risk

The suite reports them as **Core reliability mutations: 4/4**.

## Extended mutations

Extended provenance/period negative controls are enforced and counted
separately from the core four:

- missing metric period provenance
- query-period source
- assumed period alignment
- missing source record / citation
- formula cross-period inputs
- missing period alignment
- metric-period drift

Details: [docs/MUTATION_TESTING.md](docs/MUTATION_TESTING.md).

## LumenFin integration

Clone `lumenfin-agent` next to this repository, or set environment variables:

```bash
export LUMENFIN_ROOT=/path/to/lumenfin-agent
export FINAGENTBENCH_DIR=/path/to/finagentbench-demo
python scripts/validate_cross_repo.py --profile ci
```

Validated against frozen LumenFin `v0.1.0-rc.2`
(`d075b6851739be82ec2fb71fea7ad08d92d76511`), FinRun schema `1.0`.

The summary records both repository commits, worktree state, FinRun schema,
benchmark profile, core mutations, and extended mutations.

Release-candidate orchestration across both repositories:

```bash
python scripts/run_rc_validation.py --help
python scripts/run_rc_validation.py --dry-run      # paths, fixtures, schema only
python scripts/run_rc_validation.py --offline-only # deterministic gates, no live Agent calls
```

Running it without `--offline-only` requires configured LumenFin providers.
Infrastructure failures are non-pass and must not be reported as Agent-quality
success.

## Quick start

Requires Python 3.11+ (CI validates 3.11 and 3.12). Every command in this
section is deterministic and offline: no API key and no network access.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
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
| other non-zero | CLI / IO / argument error |

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

## Validated results (`v0.1.0-rc.2`)

| Gate | Result |
|------|--------|
| Unit tests | 127 PASS |
| Offline demo | PASS |
| Correctness validation | PASS |
| Core reliability mutations | 4/4 |
| Extended provenance/period mutations | 7/7 |
| Total negative controls | 11/11 |
| LumenFin `v0.1.0-rc.2` cross-repo | PASS |

Every gate above is reproducible offline and also runs in GitHub Actions
(Python 3.11 smoke lane, Python 3.12 full lane including the mutation suite and
a cross-repo check pinned to the public LumenFin tag).

Evidence:
[reports/current/FinAgentBench_Final_Release_Report.md](reports/current/FinAgentBench_Final_Release_Report.md).

## Benchmark integrity

- No metric threshold is changed to match a tested Agent.
- Required empty checks fail with diagnostic findings.
- Unsupported FinRun schema versions and unsupported scoring versions are rejected.
- Case hashes and enabled metrics are recorded in EvalReports.
- Passing does not prove investment quality; human review remains required.

## Limitations

FinAgentBench is **not**:

- an academic leaderboard;
- a universal factual-correctness proof;
- an investment-performance evaluator;
- a production certification.

Scope boundaries:

- Case contracts decide evaluation requirements, so scores are only as strong as
  the case and the exported trace.
- Claim–Evidence binding is **not** a dedicated independent metric in this
  release; citation checks are covered indirectly by evidence and provenance
  metrics.
- Optional semantic judges introduce provider variability and are excluded from
  release evidence.
- Human financial review remains required.

## Repository layout

```text
finagentbench/    evaluator, adapters, metrics and report model
benchmarks/       deterministic suites, mutations and semantic gold data
fixtures/         synthetic FinRuns and case contracts
tests/            unit and cross-project regression tests
scripts/          supported release and validation entrypoints
docs/             schema, metrics, integration and CI guides
reports/current/  current release evidence
reports/history/  superseded engineering evidence
examples/         sanitized demo artifacts
tools/            archived, unsupported audit scripts
```

## Documentation map

| Doc | Purpose |
|-----|---------|
| [docs/README.md](docs/README.md) | Doc index |
| [docs/architecture.md](docs/architecture.md) | Evaluator architecture |
| [docs/finrun_schema.md](docs/finrun_schema.md) | FinRun field reference |
| [docs/FINRUN_COMPATIBILITY.md](docs/FINRUN_COMPATIBILITY.md) | Producer/schema support matrix |
| [docs/METRICS.md](docs/METRICS.md) | Metric definitions and thresholds policy |
| [docs/MUTATION_TESTING.md](docs/MUTATION_TESTING.md) | Core and extended negative controls |
| [docs/CI_GATE.md](docs/CI_GATE.md) | CI lanes and failure interpretation |
| [docs/agent_integration_guide.md](docs/agent_integration_guide.md) | Integrating a new Agent |
| [docs/adapter_guide.md](docs/adapter_guide.md) | Writing an adapter |
| [docs/VALIDATION_COMMANDS.md](docs/VALIDATION_COMMANDS.md) | Supported commands and exit codes |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

## License status

No open-source license has been selected: the repository is source-available for
review and evaluation, and no redistribution or production-use rights are
granted. Evaluation output is for engineering assessment only and is not
investment advice.
