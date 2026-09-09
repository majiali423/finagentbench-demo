# FinAgentBench

**English** | [中文](README.zh-CN.md)

**Replay an Agent's answer and evidence, then identify unsupported financial claims.**
FinAgentBench consumes **FinRun 1.0** exports and produces findings, reports and
a CI pass/fail result without running the Agent.

[![test](https://github.com/majiali423/finagentbench-demo/actions/workflows/test.yml/badge.svg)](https://github.com/majiali423/finagentbench-demo/actions/workflows/test.yml)

[Quick start](#quick-start) · [Metrics](docs/METRICS.md) ·
[FinRun schema](docs/finrun_schema.md) · [Documentation](docs/README.md)

## What it checks

| Layer | Examples |
|---|---|
| Trace and evidence | Missing companies, inconsistent financial inputs, absent citations, missing required checks |
| Visible assertions — opt-in v3 | Wrong number, unit, currency, fiscal period or source in prose, tables and claim ledgers |
| Negative controls | Intentionally wrong numbers/entities and missing citations/risk must fail |

A known financial period cannot be supported by evidence whose period is
unknown. A correct internal metric also cannot excuse a contradictory sentence
in the final answer.

```text
FinRun → schema / adapter → deterministic checks → findings + reports → CI gate
```

## Quick start

Python **3.11+**; CI covers 3.11 and 3.12. Installation downloads build
dependencies; the following demo needs no API keys or live model calls.

```bash
git clone https://github.com/majiali423/finagentbench-demo.git
cd finagentbench-demo
python -m venv .venv
```

Activate with `.\.venv\Scripts\Activate.ps1` in PowerShell, or
`source .venv/bin/activate` in a POSIX shell.

```bash
python -m pip install -e .
python scripts/run_offline_demo.py
```

Inspect the emitted JSON, Markdown and HTML reports. To run the visible-output
v3 baseline explicitly:

```bash
python -m finagentbench evaluate fixtures/product_quality_visible_baseline_finrun.json --case fixtures/case_lumenfin_product_quality_v1.json --profile ci --out outputs/visible
```

A finding identifies the affected metric and explains the mismatch, for example:

```text
NVIDIA operating_income is stated for FY2025 but verified period is unknown.
```

Exit code **0** means passed, **1** means failed (expected for negative
fixtures), and other non-zero codes indicate CLI or execution errors.

## Why a separate evaluator repository?

[LumenFin](https://github.com/majiali423/lumenfin-agent) produces answers;
FinAgentBench evaluates the exported artifact. The versioned boundary makes
producer changes, evaluator changes and compatibility reviewable independently.
Other Agents can implement the same [FinRun interface](docs/agent_integration_guide.md).

Both repositories are maintained by the same author. These are author-owned
contract gates; neither repository independence nor a passing score establishes
third-party validation or real-world answer accuracy.

## Scoring and release versions

Scoring versions are separate from package versions and the FinRun schema.

| Role | Version / evidence |
|---|---|
| Published source with scoring v3 | [`40f7599`](https://github.com/majiali423/finagentbench-demo/commit/40f7599e408f317515583405cb90249b811179c0) |
| Historical package/tag | `0.1.0rc4` / `v0.1.0-rc.4`; the frozen tag predates v3 |
| FinRun envelope | `1.0` |
| Default scoring | v1; existing case semantics are preserved |
| Opt-in visible scoring | v3 + `visible_supported_claims` in the case's enabled metrics |
| Frozen producer compatibility | LumenFin `v0.1.0-rc.3` in this repository's full CI lane |

The [2026-09-09 baseline CI](https://github.com/majiali423/finagentbench-demo/actions/runs/34329922587)
passed at `40f7599`. LumenFin's separate
[Product quality v3 gate](https://github.com/majiali423/lumenfin-agent/actions/runs/34329999879)
pins that evaluator commit. Its rc.3/rc.4 evaluator lanes remain frozen contract
compatibility checks.

See [metric semantics](docs/METRICS.md) and
[compatibility policy](docs/FINRUN_COMPATIBILITY.md). Historical rc.4 results
remain in the [release report](reports/current/FinAgentBench_Final_Release_Report.md).

## Validation

```bash
python -m unittest discover -s tests -v
python scripts/run_mutation_suite.py
python scripts/run_correctness_validation.py
```

For joint checks, install the current LumenFin source and configure
`LUMENFIN_ROOT` / `FINAGENTBENCH_DIR` explicitly, then run
`python scripts/validate_cross_repo.py --profile ci`.
[Validation commands](docs/VALIDATION_COMMANDS.md) describe environment setup and
the optional live RC path.

## Scope and limitations

- Cases specify required checks and thresholds. Empty required checks fail
  with findings; unrecognized schema/scoring versions are rejected.
- v3 covers a supported financial assertion grammar, not arbitrary prose
  truth. Semantic judges are optional and outside deterministic release evidence.
- Mutation detection rates and frozen contract scores measure those cases;
  they do not measure investment performance or certify production readiness.
- Scores do not replace human review of source quality or financial conclusions.

## Repository guide

| Path | Responsibility |
|---|---|
| `finagentbench/` | Schema, adapters, metrics, reports and CLI |
| `benchmarks/`, `fixtures/` | Cases and negative controls |
| `tests/` | Unit, regression and compatibility checks |
| `scripts/` | Supported demo and validation entrypoints |
| `docs/` | Metrics, integration and operating instructions |
| `reports/` | Versioned release evidence and historical records |

[MIT license](LICENSE) for project-owned code ·
[Third-party notices](THIRD_PARTY_NOTICES.md)
