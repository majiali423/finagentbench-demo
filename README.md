# FinAgentBench Demo

Replay-first reliability checks for financial AI agent runs.

This demo evaluates exported financial-agent run artifacts. It does not run an
LLM and does not depend on any specific agent framework.

## What It Checks

- Entity coverage: expected companies are present.
- Numeric correctness: reported financial ratios match formulas and inputs.
- Evidence coverage: entities and important dimensions have cited evidence.
- Market data disclosure: failed market data is disclosed in the final output.
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

## Adapter Demo

The core benchmark expects a normalized `FinRun` shape, but raw agent traces can
come from different systems. Adapters keep that boundary explicit.

```powershell
python -m finagentbench evaluate fixtures\lumenfin_state_sample.json --adapter lumenfin --case fixtures\case_compare_rd.json --out outputs\lumenfin
```

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
