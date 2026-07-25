# Offline Demo Fixtures

All data is synthetic and contains no credentials or customer information.

| Artifact | Path |
|----------|------|
| Sample FinRun | `../../fixtures/pass_due_diligence_finrun.json` |
| Sample evaluation case | `../../fixtures/case_due_diligence.json` |
| Sample EvalReport | `sample_eval_report.json` |
| Four mutation definitions | `../../benchmarks/mutations/suite.json` |

Run:

```bash
python scripts/run_offline_demo.py
```

Expected result: the baseline passes and `wrong_number`, `wrong_entity`,
`missing_citation`, and `missing_risk` are all detected. The command reads
fixtures but never modifies them.
