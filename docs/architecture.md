# FinAgentBench Architecture

FinAgentBench is a replay-first reliability harness for financial AI agents.
It evaluates exported traces instead of calling an LLM directly.

It is designed as a standalone second project: the benchmark defines its own
schema, fixtures, metrics, reports, and CI gate. Agent projects integrate by
exporting traces or writing adapters; the benchmark does not depend on their
runtime code.

## Core Idea

Financial agents fail in different places: entity extraction, retrieval,
calculation, market-data handling, synthesis, and compliance wording. A single
final-answer score hides those failures. FinAgentBench asks agents to export a
small normalized `FinRun` artifact, then runs deterministic checks on each part.

## Boundaries

- Agent runtime: any framework that produces a trace or state file.
- Adapter layer: converts raw traces into the neutral `FinRun` shape.
- Metric layer: small independent checks for reliability risks.
- Runner layer: combines metric results into pass/fail reports.
- CLI layer: supports local evaluation, regression comparison, and CI gates.

## Why This Is Not Coupled To One Agent

The core evaluator knows nothing about LangGraph, AutoGen, internal company
agents, or another runtime. Runtime-specific details stay in
`finagentbench.adapters`. Adding a new agent only requires a new adapter, not a
rewrite of the scoring logic.

## Why This Is More Useful Than Pure E2E Evaluation

End-to-end evaluation can tell whether the final answer looks acceptable.
FinAgentBench also tells where the run became unreliable:

- missing expected entities
- missing required intermediate steps
- wrong deterministic financial formulas
- mixed reporting periods, units, or currencies
- unsupported claims without evidence
- silent market-data failures
- missing risk and limitation disclosure
- unsafe investment language

That makes the output actionable for debugging and for CI regression gates.

## Extension Points

Adapters are selected with `--adapter`. The default `auto` mode can parse native
`FinRun` JSON and a generic agent-state trace format.

Metrics are resolved through a registry. A benchmark case can set
`enabled_metrics` to run a subset, which is useful when a team wants to gate only
retrieval, only numeric correctness, or only compliance language.

Reports are emitted as JSON for automation, Markdown for code review, and HTML
for quick human inspection.

## Production Extensions

- Plugin registry for metric packages.
- Historical baselines by dataset and agent version.
- Severity-weighted scoring instead of a simple average.
- Sensitive-data scrubber before reports are persisted.
