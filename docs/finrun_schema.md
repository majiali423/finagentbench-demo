# FinRun Schema

`FinRun` is the neutral artifact that FinAgentBench evaluates. Agent frameworks
can produce their own native traces, but an adapter should normalize them into
this shape before scoring.

## Required Fields

| Field | Type | Description |
| --- | --- | --- |
| `run_id` | string | Stable identifier for the evaluated run. |
| `final_output` | string | Final answer shown to the user. |
| `entities` | array | Companies, symbols, or instruments analyzed by the agent. |
| `steps` | array | Intermediate agent steps such as retrieval, quant, and synthesis. |
| `metrics` | array | Deterministic financial calculations emitted by the agent. |
| `evidence` | array | Retrieved evidence snippets and citations. |
| `market_data` | array | Market data snapshots or provider failures. |

## Optional Fields

| Field | Type | Description |
| --- | --- | --- |
| `query` | string | User request that triggered the run. |
| `metadata` | object | Agent version, prompt version, model, dataset, or timestamp. |

## Entity Shape

Entities can be simple strings or objects.

```json
["NVIDIA", "AMD"]
```

```json
[
  {"name": "NVIDIA", "symbol": "NVDA"},
  {"name": "AMD", "symbol": "AMD"}
]
```

## Step Shape

```json
{"name": "retrieval", "status": "ok"}
```

Required step names are defined by each benchmark case. This keeps the core
evaluator independent from a specific agent architecture.

## Metric Shape

```json
{
  "entity": "NVIDIA",
  "name": "free_cash_flow_margin",
  "value": 0.35,
  "formula": "free_cash_flow / revenue",
  "inputs": {
    "free_cash_flow": 45.3,
    "revenue": 130.5
  }
}
```

FinAgentBench uses the formula and inputs to recompute deterministic values. If
a metric has no formula, it can still be preserved for reporting, but the numeric
correctness check will skip it.

## Evidence Shape

```json
{
  "entity": "NVIDIA",
  "citation": "nvidia_10k_2025.pdf#p42",
  "text": "Free cash flow and revenue values used by the agent."
}
```

## Market Data Shape

```json
{
  "entity": "AAPL",
  "status": "failed",
  "provider": "marketstack",
  "error": "rate_limit"
}
```

If market data fails, the final output should disclose the limitation. Silent
failures are treated as reliability issues.
