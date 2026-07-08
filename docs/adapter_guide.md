# Adapter Guide

Adapters let FinAgentBench evaluate different agent runtimes without coupling
the scoring logic to LangGraph, AutoGen, LumenFin, or another framework.

## Responsibility

An adapter does only one thing: convert a raw trace into `FinRun`.

It should not:

- call an LLM
- change the final answer
- recompute financial metrics
- decide whether the run passes
- hide missing fields or failed tool calls

## Interface

Adapters implement two methods:

```python
class TraceAdapter:
    name: str

    def can_parse(self, payload: dict) -> bool:
        ...

    def normalize(self, payload: dict) -> dict:
        ...
```

`can_parse` is used by `--adapter auto`. `normalize` maps the raw payload to the
neutral schema documented in `docs/finrun_schema.md`.

## Adding A New Adapter

1. Create a file under `finagentbench/adapters`.
2. Implement `can_parse` and `normalize`.
3. Register the adapter in `finagentbench/adapters/registry.py`.
4. Add a fixture that represents the native trace format.
5. Add a test that checks the normalized `FinRun` fields.

## Example Mapping

A LangGraph-style state might contain:

```json
{
  "thread_id": "run-123",
  "messages": [],
  "companies": ["AAPL", "MSFT"],
  "tool_events": [],
  "final_report": "..."
}
```

The adapter should produce:

```json
{
  "run_id": "run-123",
  "entities": ["AAPL", "MSFT"],
  "steps": [],
  "metrics": [],
  "evidence": [],
  "market_data": [],
  "final_output": "..."
}
```

The important engineering boundary is that metrics remain reusable. Adding a new
agent should require adapter code, not metric rewrites.
