"""How LumenFin and FinAgentBench treat data coverage and case selection."""

## Case modes

| `case_mode` | Purpose | `derive_entities_from_run` |
| --- | --- | --- |
| `compatibility` | Schema / adapter / smoke gates | Allowed — entities come from the FinRun under test |
| `quality` (default) | Correctness / regression / entity quality | **Forbidden** — `expected_entities` must be fixed |

`derive_entities_from_run=true` makes `entity_coverage` near-tautological (entities ⊆
entities). It must not be treated as proof of entity correctness. Use it only for
compatibility smoke. Regression and entity-leakage claims need fixed
`expected_entities` / `forbidden_entities` under `case_mode=quality`.

`compare_runs()` freezes derived expectations from the **baseline** FinRun so
baseline and current cannot each invent a different expected set and hide
entity regressions.

## Real-trace gate (any companies) — compatibility only

Use `fixtures/case_lumenfin_generic.json` with
`case_mode: compatibility` and `derive_entities_from_run: true`.
Entities are taken from the exported FinRun — do **not** hand-edit Apple/Microsoft.

```powershell
python -m finagentbench evaluate path\to\finrun.json `
  --case fixtures\case_lumenfin_generic.json --profile ci --out outputs\live-gate
```

## Regression only (fixed sample) — quality

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
