# FinAgentBench

Replay-first reliability checks for financial AI agent runs.

Financial agents can produce convincing final answers while silently missing an
entity, using unsupported evidence, computing a ratio incorrectly, hiding market
data failures, or making unsafe investment claims. FinAgentBench evaluates the
exported trace of an agent run so those failures are visible before the output
reaches a user.

FinAgentBench does not run an LLM and does not depend on a specific agent
framework. Agents export a small `FinRun` JSON artifact, adapters normalize raw
runtime traces into that shape, and deterministic metrics score the run.

This repository is intended to stand alone as a benchmark and reliability
harness. A financial agent project can use it as a downstream quality gate, but
FinAgentBench does not import or require any specific agent codebase.

## What It Checks

- Entity coverage: expected companies are present.
- Numeric correctness: reported financial ratios match formulas and inputs.
- Evidence coverage: entities and important dimensions have cited evidence.
- Market data disclosure: failed market data is disclosed in the final output.
- Temporal consistency: financial periods and market-data dates are explicit.
- Unit/currency consistency: calculations do not mix units or currencies.
- Risk disclosure: outputs include limitations and research/advice boundaries.
- Compliance language: unsafe financial claims are flagged.
- Required steps: expected agent steps are present.

## Quick Start

```powershell
python -m pip install -e .

python -m finagentbench evaluate fixtures\pass_finrun.json --case fixtures\case_compare_rd.json --out outputs\pass
python -m finagentbench evaluate fixtures\fail_finrun.json --case fixtures\case_compare_rd.json --out outputs\fail
python -m finagentbench compare fixtures\pass_finrun.json fixtures\fail_finrun.json --case fixtures\case_compare_rd.json --out outputs\compare
python -m finagentbench gate fixtures\pass_finrun.json fixtures\fail_finrun.json --case fixtures\case_compare_rd.json --out outputs\gate
```

Reports are written as JSON, Markdown, and HTML.

## Realistic Scenario

The fixtures include a larger multi-company case that checks free cash flow
margin, valuation-risk evidence, market-data failure disclosure, and compliance
wording.

```powershell
python -m finagentbench evaluate fixtures\pass_bigtech_finrun.json --case fixtures\case_bigtech_fcf.json --out outputs\bigtech
```

## Adapter Demo

The core benchmark expects a normalized `FinRun` shape, but raw agent traces can
come from different systems. Adapters keep that boundary explicit.

```powershell
python -m finagentbench evaluate fixtures\agent_state_sample.json --adapter agent-state --case fixtures\case_compare_rd.json --out outputs\agent-state
```

See `docs/adapter_guide.md` for the adapter contract.

## Metric Subsets

Cases can enable a subset of metrics when a team wants to gate only one layer.

```powershell
python -m finagentbench evaluate fixtures\pass_finrun.json --case fixtures\case_numeric_only.json --out outputs\numeric-only
```

## Positioning

FinAgentBench is not a financial report generator. It is a small reliability
harness for checking whether a financial agent run is auditable, grounded, and
safe enough to trust.

The important design choice is replay-first evaluation: production agents export
their intermediate artifacts, and FinAgentBench checks each layer without being
coupled to the agent runtime or prompt implementation.

## Project Shape

- `finagentbench.adapters`: converts external traces into the neutral `FinRun` shape.
- `finagentbench.metrics`: independent checks that can be enabled per case.
- `finagentbench.runner`: validates inputs and aggregates metric results.
- `finagentbench.report`: writes machine-readable and human-readable reports.
- `fixtures`: small pass/fail traces and benchmark cases.

## CI Gate

The GitHub Actions workflow runs unit tests and then executes a benchmark gate.
This lets a team block regressions after changing prompts, tools, retrieval
pipelines, or agent orchestration code.
