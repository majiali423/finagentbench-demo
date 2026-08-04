# FinAgentBench

FinAgentBench is a replay-first reliability evaluation framework.
It evaluates exported Agent traces independently from Agent runtime.

Package: `0.1.0rc2` | Recommended tag: `v0.1.0-rc.2` | FinRun schema: `1.0`

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

## Core metrics

Deterministic CI coverage includes:

- entity coverage and leakage;
- numeric correctness;
- unit/currency and temporal consistency;
- Case-driven input value plausibility (finite bounds only);
- evidence coverage and consistency;
- retrieval / period provenance;
- visible output integrity (scoring v2 opt-in);
- required execution steps and report sections;
- risk disclosure and compliance language.

See [Metrics](docs/METRICS.md) and
[FinRun compatibility](docs/FINRUN_COMPATIBILITY.md).

## Core mutations

The CI mutation gate must detect these four reliability failures:

1. wrong number
2. wrong entity
3. missing citation
4. missing risk

Report these separately as **Core reliability mutations: 4/4**.

## Extended mutations

Extended provenance/period negative controls are also enforced and reported
separately (not folded into the core 4/4):

- missing metric period provenance
- query-period source
- assumed period alignment
- missing source record / citation
- formula cross-period inputs
- missing period alignment
- metric-period drift

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

Full live RC orchestration (requires configured LumenFin providers):

```bash
python scripts/run_rc_validation.py --help
python scripts/run_rc_validation.py --dry-run
```

Infrastructure failures are non-pass and must not be reported as Agent-quality
success.

## Quick start

Requires Python 3.11+ (CI validates 3.11 and 3.12).

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

## Validated results (local RC2 closure)

| Gate | Result |
|------|--------|
| Unit tests | 127 PASS |
| Offline demo | PASS |
| Correctness validation | PASS |
| Core reliability mutations | 4/4 |
| Extended provenance/period mutations | 7/7 |
| Total negative controls | 11/11 |
| LumenFin `v0.1.0-rc.2` cross-repo | PASS |

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

It is a replay-first reliability framework. Case contracts decide evaluation
requirements; optional semantic judges introduce provider variability; human
financial review remains required.

## License status

No public license grant has been selected. The repository is intended for
private/internal portfolio review unless the owner explicitly adds a license.
