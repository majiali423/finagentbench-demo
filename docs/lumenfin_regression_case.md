# LumenFin Regression Case

This case shows how FinAgentBench catches regressions from a LumenFin exported
trace. It is not a synthetic score table: the commands below run against the
same LumenFin-shaped trace and case used by the tests.

## Baseline

```powershell
python -m finagentbench evaluate fixtures\lumenfin_state_sample.json --adapter lumenfin --case fixtures\case_lumenfin_diligence.json --profile ci --out outputs\lumenfin-e2e
```

Result:

```text
PASS lumenfin-e2e-apple-microsoft score=100.0
```

The baseline includes the expected LumenFin workflow steps, report sections,
formula-backed metrics, numeric evidence, market-data status, risk disclosure,
and compliance language.

## Live Trace Check

On 2026-07-11, a live LumenFin run was executed with DeepSeek and market data
providers, then exported through `scripts\export_finrun.py` and evaluated by
FinAgentBench.

```powershell
# In C:\a_project\Projects\lumenfin-agent
python run_demo.py --query "Compare Apple and Microsoft FY2025 financial performance, supply chain risk, and market data quality." --thread-id lumenfin-live-20260711 --output-dir outputs
python scripts\export_finrun.py outputs\lumenfin-live-20260711_20260711_204223_state.json --out outputs\lumenfin-live-20260711-finrun.json

# In C:\a_project\Projects\finagentbench-demo
python -m finagentbench evaluate C:\a_project\Projects\lumenfin-agent\outputs\lumenfin-live-20260711-finrun.json --case fixtures\case_lumenfin_diligence.json --profile ci --out outputs\lumenfin-live-20260711-eval
```

Result:

```text
PASS lumenfin-live-20260711 score=100.0
```

This live run is separate from the deterministic fixture used by CI. The fixture
keeps tests reproducible; the live trace proves the integration path works with
a freshly generated LumenFin artifact.

## Mutated Regression Suite

```powershell
python -m finagentbench benchmark benchmarks\lumenfin_regression\suite.json --out outputs\lumenfin-regression-report.json
```

Current result:

```text
baseline: PASS score=100.0
wrong_quant: FAIL score=87.86, finding=numeric_correctness
missing_risk_section: FAIL score=72.37, findings=section_presence,risk_disclosure
detection_rate=1.0, false_positives=0
```

The `wrong_quant` case changes Microsoft `ebitda_margin` from the formula-backed
value to `0.5`. The case still has a score above 85, but the gate fails because
the LumenFin case blocks high-severity findings. This prevents a serious
financial calculation error from slipping through as an average-score pass.

The `missing_risk_section` case removes the `## Risk` section and the concrete
market/data limitation language. FinAgentBench flags both the missing section and
the missing risk disclosure.

## Gate And Suggest

The materialized bad trace combines both regressions so the repair suggestion
payload can be inspected directly.

```powershell
python -m finagentbench gate fixtures\lumenfin_regression_bad_finrun.json --case fixtures\case_lumenfin_diligence.json --profile ci --out outputs\lumenfin-regression-gate
```

Result:

```text
FAIL lumenfin-regression-bad score=55.96
```

```powershell
python -m finagentbench suggest fixtures\lumenfin_regression_bad_finrun.json --case fixtures\case_lumenfin_diligence.json --profile ci --out outputs\lumenfin-regression-suggest.json
```

Key suggested actions:

```json
[
  {
    "action": "rewrite",
    "target": {"section": "## Risk"},
    "metric": "section_presence"
  },
  {
    "action": "recompute",
    "target": {"calculation": "Microsoft ebitda_margin"},
    "metric": "numeric_correctness"
  },
  {
    "action": "rewrite",
    "target": {"section": "final_output"},
    "metric": "risk_disclosure"
  }
]
```

After restoring the correct Microsoft EBITDA margin and the `## Risk` section,
the baseline trace passes again with score `100.0`.
