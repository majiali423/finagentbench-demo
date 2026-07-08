# Due Diligence Integration

FinAgentBench can evaluate a due diligence agent without importing the agent
runtime. The agent only needs to export its final state as JSON.

## Three Steps

1. Export the agent state at the end of a run.
2. Normalize it with the `due-diligence` adapter.
3. Evaluate it with `fixtures/case_due_diligence.json`.

```powershell
python -m finagentbench evaluate fixtures\due_diligence_state_sample.json --adapter due-diligence --case fixtures\case_due_diligence.json --out outputs\dd-state
```

## Expected State Fields

| Due diligence state | FinRun field |
| --- | --- |
| `company_name` / `target` | `entities[].name` |
| `workflow_events` | `steps[]` |
| `computed_ratios` | `metrics[]` |
| `source_snippets` | `evidence[]` |
| `market_quotes` | `market_data[]` |
| `report_markdown` | `final_output` |
