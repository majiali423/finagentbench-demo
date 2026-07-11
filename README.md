# FinAgentBench

Replay-first reliability checks for financial AI agent runs.

Financial agents can produce convincing final answers while silently missing an
entity, using unsupported evidence, computing a ratio incorrectly, hiding market
data failures, or making unsafe investment claims. FinAgentBench evaluates the
exported trace of an agent run so those failures are visible before the output
reaches a user.

FinAgentBench does not require an LLM and does not depend on a specific agent
framework. Agents export a small `FinRun` JSON artifact, adapters normalize raw
runtime traces into that shape, and deterministic metrics score the run. For
release audits, an optional semantic judge can be enabled for checks that are
hard to express with rules, such as whether the final conclusion is actually
supported by cited evidence.

This repository is intended to stand alone as a benchmark and reliability
harness. A financial agent project can use it as a downstream quality gate, but
FinAgentBench does not import or require any specific agent codebase.

## Relationship To The Financial Agent Project

This is my second project, not an extension module inside the first one. The
financial agent project is responsible for generation: LLM calls, RAG, tools, and
report writing. FinAgentBench is responsible for calibration: checking exported
`FinRun` traces with deterministic metrics, regression gates, and repair
suggestions.

The two projects connect only through files or adapters. The agent can export a
JSON trace, and FinAgentBench can evaluate it without importing the agent runtime.
That keeps the benchmark reusable for other financial agents as well.

## What It Checks

- Entity coverage: expected companies are present.
- Numeric correctness: reported financial ratios match formulas and inputs.
- Evidence coverage: entities and important dimensions have cited evidence.
- Evidence consistency: cited evidence contains the numbers used in calculations.
- Evidence support: optional semantic audit for whether cited evidence supports the final answer.
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

## Due Diligence Scenario

The due diligence case checks report sections, weighted scoring, evidence-number
alignment, risk disclosure, and compliance language.

```powershell
python -m finagentbench evaluate fixtures\pass_due_diligence_finrun.json --case fixtures\case_due_diligence.json --out outputs\dd-pass
python -m finagentbench evaluate fixtures\due_diligence_state_sample.json --adapter due-diligence --case fixtures\case_due_diligence.json --out outputs\dd-state
```

## Benchmark Suite

The curated due diligence suite contains 10 traces covering 9 failure scenarios,
including missing entities, missing workflow steps, missing report sections,
wrong numbers, evidence-number mismatch, missing evidence, missing risk
disclosure, compliance violation, and multi-issue regressions.

```powershell
python -m finagentbench benchmark benchmarks\due_diligence\suite.json --out outputs\dd-suite-report.json
```

Current expected result: 9/9 failing traces detected, 0 false positives.

The semantic audit suite contains 20 human-labeled synthetic golden cases for
`evidence_support`, covering supported summaries and unsupported
recommendations, growth claims, valuation claims, stale evidence, wrong-entity
evidence, irrelevant citations, missing citations, and private-company data
gaps.

```powershell
python -m finagentbench semantic-benchmark benchmarks\semantic_audit\evidence_support_golden.json --out outputs\evidence-support-golden.json
```

Current expected replay result: 20/20 labels matched, 0 false positives, 0
false negatives. This is static judge replay for metric plumbing and label
alignment, not a claim of live LLM judge accuracy. Production teams should run
the same suite with a real judge configuration and add real failures observed
from their own agent logs.

## Repair Suggestions

`suggest` converts findings into structured repair actions that an agent or
human review queue can consume.

```powershell
python -m finagentbench suggest fixtures\fail_due_diligence_finrun.json --case fixtures\case_due_diligence.json --out outputs\dd-suggest.json
```

## Optional Semantic Audit

Most metrics are deterministic and should stay in the default CI gate. Semantic
audit is optional and intended for release evaluation or golden-label replay.
Enable semantic metrics in a case file and configure `semantic_audit.judge`.

- `evidence_support`: whether final conclusions are supported by cited evidence.
- `risk_quality`: whether risk disclosure is concrete and tied to the analysis.
- `compliance_semantic`: whether the answer contains implicit advice or overconfident claims.

The built-in `static` judge is useful for tests and labeled benchmark replay.
When no semantic judge is configured, semantic metrics fail conservatively with
`semantic_judge_not_configured`; the fallback is not treated as a real semantic
auditor.
`openai-compatible` reads endpoint, key, and model from
`FINAGENTBENCH_LLM_ENDPOINT`, `FINAGENTBENCH_LLM_API_KEY`, and
`FINAGENTBENCH_LLM_MODEL`. It also supports cache, retry, timeout, and prompt
version tracking through judge config:

```json
{
  "semantic_audit": {
    "judge": {
      "provider": "openai-compatible",
      "prompt_version": "financial_audit_v1",
      "cache_path": "outputs/llm_judge_cache.json",
      "retry_count": 2,
      "backoff_seconds": 1,
      "timeout_seconds": 20
    }
  }
}
```

Semantic findings include judge metadata such as provider, model,
`prompt_version`, cache key, cache hit status, and latency. This makes release
audit results easier to reproduce after changing prompts or models.

This keeps the project provider-neutral: the benchmark schema, reports, and
suggestions do not depend on a specific LLM vendor.

```powershell
python -m finagentbench evaluate fixtures\pass_due_diligence_finrun.json --case fixtures\case_due_diligence_semantic_audit.json --out outputs\dd-semantic-audit
```

## Profiles

`--profile ci` removes semantic metrics and keeps the deterministic gate fast
and reproducible. `--profile audit` adds metrics listed in `audit_metrics`, which
should be used with a configured semantic judge.

```powershell
python -m finagentbench evaluate fixtures\pass_due_diligence_finrun.json --case fixtures\case_due_diligence_semantic_audit.json --profile ci
python -m finagentbench evaluate fixtures\pass_due_diligence_finrun.json --case fixtures\case_due_diligence_semantic_audit.json --profile audit
```

The included semantic audit case uses `static` judge output for demo replay. It
is not evidence that a live LLM provider has been audited.

## Reference Runtime

The repository also includes a small reference financial-agent runtime. It is not
the main product, but it demonstrates orchestration, tool calling, retrieval,
caching, retry, and trace export.

```powershell
python -m finagentbench run-reference --out outputs\reference-agent-run.json
python -m finagentbench evaluate outputs\reference-agent-run.json --case fixtures\case_bigtech_fcf.json --out outputs\reference-agent-eval
```

See `docs/reference_runtime.md` and `docs/regression_log.md`.

## Adapter Demo

The core benchmark expects a normalized `FinRun` shape, but raw agent traces can
come from different systems. Adapters keep that boundary explicit.

```powershell
python -m finagentbench evaluate fixtures\agent_state_sample.json --adapter agent-state --case fixtures\case_compare_rd.json --out outputs\agent-state
```

See `docs/adapter_guide.md` for the adapter contract.

## LumenFin End-To-End Trace

FinAgentBench can evaluate a LumenFin exported state without importing the
LumenFin runtime. LumenFin writes a `*_state.json` artifact; the `lumenfin`
adapter maps that state into the neutral `FinRun` schema.

```powershell
# In C:\a_project\Projects\lumenfin-agent
python run_demo.py --query "Compare Apple and Microsoft FY2025 financial performance, supply chain risk, and market data quality." --thread-id lumenfin-e2e --output-dir outputs
$state = Get-ChildItem outputs\lumenfin-e2e_*_state.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1
python scripts\export_finrun.py $state.FullName --out outputs\lumenfin-e2e-finrun.json

# In C:\a_project\Projects\finagentbench-demo
python -m finagentbench evaluate fixtures\lumenfin_state_sample.json --adapter lumenfin --case fixtures\case_lumenfin_diligence.json --profile ci --out outputs\lumenfin-e2e
python -m finagentbench evaluate C:\a_project\Projects\lumenfin-agent\outputs\lumenfin-e2e-finrun.json --case fixtures\case_lumenfin_diligence.json --profile ci --out outputs\lumenfin-exported-finrun-eval
```

The included fixture is a deterministic LumenFin-shaped trace for CI and demo
purposes. For a live portfolio run, point `evaluate` at the actual exported
`*_state.json` or the `FinRun` generated by `scripts\export_finrun.py`.

See `docs/lumenfin_regression_case.md` for a before/after regression story:
wrong quant and missing risk disclosure are blocked by the gate, and `suggest`
returns concrete `recompute` / `rewrite` actions.

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
- `finagentbench.reference_runtime`: minimal agent runtime that exports `FinRun`.
- `fixtures`: small pass/fail traces and benchmark cases.

## CI Gate

The GitHub Actions workflow runs unit tests and then executes a benchmark gate.
This lets a team block regressions after changing prompts, tools, retrieval
pipelines, or agent orchestration code.
