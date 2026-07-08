# Sample Evaluation Report

Run: `fail-nvidia-amd`

Score: **34.45**

Status: **FAIL**

## What Failed

- `entity_coverage`: AMD was expected but missing from extracted entities.
- `step_presence`: retrieval was required but absent.
- `numeric_correctness`: NVIDIA R&D intensity did not match the formula inputs.
- `evidence_coverage`: AMD had no cited evidence.
- `market_data_disclosure`: AMD market data failed but the final answer did not disclose that limitation.
- `compliance_language`: the final answer used unsafe language such as guaranteed return and must buy.

## Why This Matters

The final answer can look fluent while the trace reveals reliability problems.
FinAgentBench turns those hidden failures into concrete findings that can be
used in code review, CI gates, and agent regression testing.
