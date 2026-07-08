# Reference Runtime

FinAgentBench is primarily a benchmark, but the repository includes a small
reference financial-agent runtime to show how a real run can produce a `FinRun`
trace.

The reference runtime implements:

- orchestration: planning, retrieval, quant, risk, synthesis, compliance
- tool calling: financial statement and market data tools
- retrieval: deterministic in-memory filing snippets
- caching: shared cache for retrieval and tool results
- retry: transient market-data failure for NVDA succeeds on the second attempt
- trace export: final run is emitted as normal `FinRun` JSON

Run it with:

```powershell
python -m finagentbench run-reference --out outputs\reference-agent-run.json
python -m finagentbench evaluate outputs\reference-agent-run.json --case fixtures\case_bigtech_fcf.json --out outputs\reference-agent-eval
```

This runtime is intentionally small. Its job is to demonstrate how an agent run
can be made auditable, not to replace production orchestration frameworks.
