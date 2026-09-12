# FinAgentBench
**Replay financial Agent outputs and explain which assertions fail verification.**

**English** | [中文](README.zh-CN.md)

FinAgentBench is the evaluation component of
[LumenFin](https://github.com/majiali423/lumenfin-agent). It consumes a
**FinRun 1.0** export, checks it against an explicit case, and emits metric-level
findings plus JSON, Markdown and HTML reports. Replaying an export does not
invoke the original Agent.

[![test](https://github.com/majiali423/finagentbench-demo/actions/workflows/test.yml/badge.svg)](https://github.com/majiali423/finagentbench-demo/actions/workflows/test.yml)

[Run an example](#run-an-example) · [Scoring logic](#how-a-run-is-evaluated) ·
[Integrate an Agent](docs/agent_integration_guide.md) · [Documentation](docs/README.md)

## What the evaluator adds

A report can have correct internal metrics and still put a wrong percentage,
company or fiscal year in its visible answer. FinAgentBench checks both sides:

| Layer | Inputs | What is checked |
|---|---|---|
| Contract | FinRun + case | Schema, supported scoring version and case requirements |
| Structured evidence | Formula inputs, metrics, entities, citations | Recomputability, identity and required evidence |
| Visible output — opt-in v3 | Prose, tables and claim ledgers | Supported financial values, units, periods, comparisons and citations |
| Gate | Metric results + severity rules | Weighted score and blocking findings |

An unknown evidence period cannot justify a specific fiscal year. A high
aggregate score also cannot override a finding whose severity blocks the case.
FinAgentBench does not replace LumenFin's document-task catalog. That 24-task
set is candidate gold for a development diagnostic (derived excerpts, lexical
retrieval). If internals and the visible answer share the same wrong number,
export checks can still pass while the catalog fails. Layer A is not formal
source accuracy. LumenFin's adapter policy `lumenfin_eval_contract.v1` runs
applicable metrics through `evaluate_run` (not a single direct metric call)
and does not treat missing Bench dependencies as a pass.

## How a run is evaluated

```text
Agent state / FinRun
  → adapter and schema validation
  → bind the case's expected entities and requirements
  → execute enabled metrics
  → combine scores and inspect blocking findings
  → EvalReport + diagnostic findings + CI outcome
```

### A versioned input boundary

The [schema](finagentbench/schema.py) defines the run, evidence, metric and
finding structures. [Adapters](finagentbench/adapters/) normalize producer
exports, so metric code does not need to import the Agent's graph or API.

The case owns the expected behavior. In a quality case, expected entities must
come from the test specification, not from whatever entities the Agent happened
to return. [Case binding](finagentbench/case_binding.py) keeps that distinction
explicit; compatibility smoke cases have a separate purpose.

### Deterministic checks with inspectable failure reasons

The [runner](finagentbench/runner.py) validates inputs, resolves enabled metrics,
calculates a weighted result and applies `block_on_severity`.
[Numeric correctness](finagentbench/metrics/numeric.py) checks
structured formula results.

[Visible supported claims](finagentbench/metrics/visible_supported_claims.py)
parses supported financial assertions and compares them with exported evidence.
It covers a defined financial vocabulary and grammar; unsupported prose needs
separate review. A score from this parser is not a universal factuality score.

This [product case](fixtures/case_lumenfin_product_quality_v1.json) explicitly enables v3:

```json
{
  "scoring_version": "3",
  "enabled_metrics": ["visible_supported_claims", "numeric_correctness", "entity_coverage"],
  "require_checkable_metrics": true,
  "require_visible_claim_citations": true,
  "block_on_severity": ["high", "critical"]
}
```

This is an excerpt; use the linked full case with the commands below.

### Test the evaluator with deliberately wrong outputs

[Mutation testing](docs/MUTATION_TESTING.md) alters a known-good trace and checks
that the expected failure is detected. The
[mutation suite](benchmarks/mutations/suite.json) includes numerical, entity,
citation and provenance/period controls.

CI checks both positive examples and negative examples. A negative example must
produce a fresh report with the matching run ID and `passed=false`, alongside
the expected exit status. A CLI crash cannot count as successful detection.
See the [workflow](.github/workflows/test.yml).

## Run an example

Use Python **3.11+**:

```bash
git clone https://github.com/majiali423/finagentbench-demo.git
cd finagentbench-demo
python -m venv .venv
```

Activate with `source .venv/bin/activate` on POSIX, or
`.\.venv\Scripts\Activate.ps1` in PowerShell.

```bash
python -m pip install -e .
python scripts/run_offline_demo.py
python -m finagentbench evaluate fixtures/product_quality_visible_baseline_finrun.json --case fixtures/case_lumenfin_product_quality_v1.json --profile ci --out outputs/visible
```

Open the emitted report and inspect its individual metrics and findings.
The offline examples need no API keys or model calls. To inspect the negative
controls and run the test suite:

```bash
python scripts/run_mutation_suite.py
python -m unittest discover -s tests -v
```

[Validation commands](docs/VALIDATION_COMMANDS.md) cover cross-repository checks
and optional live runs. [Recorded passing CI](https://github.com/majiali423/finagentbench-demo/actions/runs/34340092459)
covers the Python 3.11 and 3.12 lanes.

## From an evaluator to a product evaluation

FinAgentBench verifies the supplied run and case. Product evaluation additionally
needs gold answers and source evidence established independently of the
producer's exported metrics.

The [LumenFin evaluation proposal](https://github.com/majiali423/lumenfin-agent/blob/main/docs/evaluation_strategy.md)
separates task success, evidence support, abstention, retrieval diagnostics,
evaluator mutation detection and execution cost. Its new document task set and
baseline runner are planned; fixture gate scores are not presented as measured
product accuracy.

Both repositories are maintained by the same author. The FinRun boundary makes
the evaluator reviewable and reusable; it does not establish third-party
independence.

## Code and compatibility

| Entry | Responsibility |
|---|---|
| [Schema](docs/finrun_schema.md) | Export contract |
| [Adapter guide](docs/adapter_guide.md) | Connect another producer |
| [Metric semantics](docs/METRICS.md) | Scope, tolerances and finding rules |
| [Runner](finagentbench/runner.py) | Evaluation and baseline comparison |
| [CI gate](docs/CI_GATE.md) | Positive cases, negative controls and release checks |

FinRun schema is `1.0`; default scoring remains v1, with v3 enabled per case.
Package metadata `0.1.0rc4` and frozen tag `v0.1.0-rc.4` are separate from
scoring versions: the tag predates v3. LumenFin's product gate pins the published
v3 evaluator source, while its rc.3/rc.4 lanes test frozen compatibility.
See the [compatibility policy](docs/FINRUN_COMPATIBILITY.md).

[MIT license](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md).
Evaluation findings support human review of financial research outputs.
