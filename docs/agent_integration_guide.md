# Agent Integration Guide

This guide is for teams that want to evaluate a financial agent with
FinAgentBench without adopting a specific runtime, prompt stack, or orchestration
framework.

The integration boundary is a JSON artifact called `FinRun`. Your agent can
either export `FinRun` directly or export its native trace and add an adapter
that normalizes that trace into `FinRun`.

## Integration Principle

FinAgentBench evaluates what the agent produced; it does not run the agent.

Keep this boundary clear:

- Agent runtime: planning, retrieval, tools, calculations, report generation.
- FinAgentBench: replay, scoring, regression gates, reports, suggestions.

The evaluator should not import your agent runtime. Your agent should not need
to import the evaluator unless you choose to call it in a pipeline script.

## FinRun Contract

Minimum required fields:

| Field | Purpose |
| --- | --- |
| `run_id` | Stable ID for the evaluated run. |
| `final_output` | Final answer or report shown to the user. |
| `entities` | Companies, symbols, issuers, assets, or funds analyzed. |
| `steps` | Workflow events such as retrieval, quant, risk, synthesis. |
| `metrics` | Structured financial calculations with formula and inputs. |
| `evidence` | Retrieved snippets, citations, source text, and periods. |
| `market_data` | Market snapshots, provider status, and failures. |

Recommended optional fields:

| Field | Purpose |
| --- | --- |
| `query` | User request that triggered the run. |
| `metadata` | Agent version, model, prompt version, adapter, dataset. |

See `docs/finrun_schema.md` for detailed field shapes.

## L0-L3 Integration Levels

You do not need a perfect trace on day one. Start with the level your agent can
support, then add more structure as reliability needs increase.

| Level | Exported Fields | Useful Checks | Typical Use |
| --- | --- | --- | --- |
| L0 | `run_id`, `final_output` | compliance language, risk disclosure | quick smoke check for existing report generators |
| L1 | L0 + `entities`, `steps` | entity coverage, step presence, section presence | basic agent workflow regression |
| L2 | L1 + `evidence`, `market_data` | evidence coverage, market-data disclosure | RAG and data-provider reliability |
| L3 | L2 + `metrics.formula.inputs` | numeric correctness, unit/currency, evidence consistency | production-grade financial calculation gate |

L0 can catch obvious unsafe language, but it cannot diagnose why a report went
wrong. L3 gives the most useful failure localization because it ties final text
back to tools, formulas, evidence, and market-data status.

## Direct FinRun Export

If you control the agent runtime, direct export is the cleanest path:

```json
{
  "run_id": "my-agent-run-001",
  "query": "Compare AAPL and MSFT FY2025 margins.",
  "entities": [{"name": "AAPL"}, {"name": "MSFT"}],
  "steps": [
    {"name": "retrieval", "status": "ok"},
    {"name": "quant", "status": "ok"},
    {"name": "synthesis", "status": "ok"}
  ],
  "metrics": [
    {
      "entity": "AAPL",
      "name": "ebitda_margin",
      "period": "FY2025",
      "value": 0.34,
      "formula": "ebitda / revenue",
      "inputs": {
        "ebitda": {"value": 141.2, "unit": "billion", "currency": "USD", "period": "FY2025"},
        "revenue": {"value": 412.0, "unit": "billion", "currency": "USD", "period": "FY2025"}
      }
    }
  ],
  "evidence": [
    {
      "entity": "AAPL",
      "citation": "aapl_2025_10k.pdf#p42",
      "period": "FY2025",
      "source_type": "filing",
      "provider": "sec",
      "text": "Revenue was 412.0 billion USD and EBITDA was 141.2 billion USD."
    }
  ],
  "market_data": [
    {"entity": "AAPL", "status": "ok", "provider": "yahoo", "as_of": "2026-07-10"}
  ],
  "final_output": "Final financial analysis..."
}
```

Run:

```powershell
python -m finagentbench evaluate outputs\my-agent-finrun.json --case fixtures\case_lumenfin_diligence.json --profile ci --out outputs\my-agent-eval
```

## Adapter Pattern

If your agent already has a native trace format, add an adapter instead of
changing the runtime.

```python
from __future__ import annotations

from typing import Any


class MyAgentAdapter:
    name = "my-agent"

    def can_parse(self, payload: dict[str, Any]) -> bool:
        return "final_report" in payload and "tool_events" in payload

    def normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": str(payload.get("thread_id") or "my-agent-run"),
            "query": payload.get("query", ""),
            "metadata": {"adapter": self.name, "source_project": "my-agent"},
            "entities": [{"name": name} for name in payload.get("companies", [])],
            "steps": [
                {"name": event["name"], "status": event.get("status", "ok")}
                for event in payload.get("tool_events", [])
            ],
            "metrics": [],
            "evidence": [],
            "market_data": [],
            "final_output": payload.get("final_report", ""),
        }
```

Then:

1. Add the adapter under `finagentbench/adapters/`.
2. Register it in `finagentbench/adapters/registry.py`.
3. Add one native trace fixture.
4. Add a test that asserts the normalized `FinRun` has the expected entities,
   steps, metrics, evidence, and final output.

Adapters should not call an LLM, recompute metrics, hide failed tool calls, or
decide pass/fail. They only preserve and normalize the trace.

## Profiles

Use profiles to separate fast CI gates from slower semantic audit.

```powershell
python -m finagentbench evaluate run.json --case case.json --profile ci
python -m finagentbench evaluate run.json --case case.json --profile audit
```

`--profile ci` removes semantic metrics and keeps deterministic checks
reproducible. It is appropriate for pull requests, prompt changes, tool changes,
and regression gates.

`--profile audit` adds metrics listed in `audit_metrics`. It should be used only
when a semantic judge is configured through `semantic_audit.judge`.

If a case omits `enabled_metrics`, `--profile audit` evaluates only the metrics
listed in `audit_metrics`; include deterministic metrics explicitly when you
want audit mode to be additive.

If no semantic judge is configured, semantic metrics fail conservatively with
`semantic_judge_not_configured`; the fallback is not treated as a real semantic
auditor.

## Example: LumenFin

LumenFin exports a native LangGraph state with fields such as:

- `audit_log`
- `retrieved_docs`
- `financial_metrics`
- `rag_evidence`
- `market_snapshots`
- `final_report`

FinAgentBench supports this in two ways:

1. LumenFin direct export:

```powershell
python scripts\export_finrun.py outputs\lumenfin-e2e_state.json --out outputs\lumenfin-e2e-finrun.json
```

2. FinAgentBench adapter:

```powershell
python -m finagentbench evaluate fixtures\lumenfin_state_sample.json --adapter lumenfin --case fixtures\case_lumenfin_diligence.json --profile ci --out outputs\lumenfin-e2e
```

CI also gates this LumenFin-shaped native trace (not only synthetic FinRun fixtures):

```powershell
python -m finagentbench gate fixtures\lumenfin_state_sample.json --adapter lumenfin --case fixtures\case_lumenfin_diligence.json --profile ci --out outputs\ci-lumenfin-gate
```

Diligence cases set `require_checkable_metrics: true`. If `numeric_correctness`
or `evidence_consistency` is enabled but the export has nothing checkable
(empty metrics / missing formula+inputs), the gate fails closed instead of
scoring 100. Keep that flag off for intentionally non-quantitative L0–L2 scaffolds.

The LumenFin regression suite mutates the same baseline trace to prove that the
gate catches real failures:

```powershell
python -m finagentbench benchmark benchmarks\lumenfin_regression\suite.json --out outputs\lumenfin-regression-report.json
```

Current expected result:

```text
baseline: PASS score=100.0
wrong_quant: FAIL score=87.86, finding=numeric_correctness
missing_risk_section: FAIL score=72.37, findings=section_presence,risk_disclosure
```

## Common Failure Modes

| Symptom | Likely Cause | Useful Metric |
| --- | --- | --- |
| Final answer mentions the wrong company | planner/entity extraction issue | `entity_coverage` |
| Report skipped a required stage | orchestration or trace export issue | `step_presence` |
| Ratio is numerically wrong | formula/tool regression | `numeric_correctness` |
| Citation exists but numbers are absent | retrieval or citation mismatch | `evidence_consistency` |
| Provider failed silently | market-data fallback not disclosed | `market_data_disclosure` |
| Report has generic risk wording | weak synthesis or risk node | `risk_disclosure`, `risk_quality` |
| Output sounds like advice | compliance policy gap | `compliance_language`, `compliance_semantic` |

## Checklist Before Adding A New Agent

- Choose direct FinRun export or adapter normalization.
- Export stable `run_id` and original `query`.
- Preserve all workflow steps, including failed or retried steps.
- Export formulas and inputs for financial calculations.
- Include units, currencies, and periods for metric inputs.
- Attach evidence text, not only citation IDs.
- Represent market-data failures explicitly.
- Add one passing fixture and at least one failing regression fixture.
- Run `--profile ci` before using semantic audit.
- Do not claim live LLM judge accuracy unless you actually ran a configured
  external judge against human-labeled cases.
