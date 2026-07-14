"""How LumenFin and FinAgentBench treat data coverage and case selection."""

## Real-trace gate (any companies)

Use `fixtures/case_lumenfin_generic.json` with `derive_entities_from_run: true`.
Entities are taken from the exported FinRun — do **not** hand-edit Apple/Microsoft.

```powershell
python -m finagentbench evaluate path\to\finrun.json `
  --case fixtures\case_lumenfin_generic.json --profile ci --out outputs\live-gate
```

## Regression only (fixed sample)

Use `fixtures/case_lumenfin_diligence.json` with the Apple/Microsoft fixture.
That binding is intentional for mutation detection, not for arbitrary queries.

## Fail-loud when fundamentals are missing

If a company has no sample DB row and no PDF-extractable metrics:

1. Retrieval sets `fatal_data_gap=true` and skips the silent replan→quant loop.
2. Graph routes `retrieval → synthesizer`.
3. `workflow_status=incomplete_data` with an explicit report banner.
4. FinAgentBench gate is **expected to fail** (`structured_source=none`, no checkable metrics).

This is correct: the stack refuses to invent numbers.

**User action:** upload a filing PDF, or analyze a demo sample company
(Apple / Microsoft / NVIDIA / AMD / Tesla / …).

Chinese names such as `腾讯控股` resolve to `Tencent` via aliases; Tencent still needs PDF
or sample fundamentals to pass a diligence gate.
