# FinAgentBench Final Stage Manifest

Date: 2026-07-25

## Summary

```text
Files to stage:
  - RC runtime isolation + import tests + diligence/sample fixture alignment
  - archived audit renames under tools/archived_audits/
  - docs/README, VALIDATION_COMMANDS, curated README
  - reports/current + reports/history layout
  - Commit Plan + Repository Curation Report
  - .gitignore updates

Files to archive:
  - scripts/evaluate_lumenfin_e2e_regression.py
  - scripts/run_final_reliability_baseline.py
  - scripts/run_production_hardening.py
  - scripts/validate_claim_binding.py
  - scripts/validate_financial_grounding_nvda.py
  - docs/regression_log.md -> reports/history/
  - docs/sample_report.md -> reports/history/
  - prior reports -> reports/current|history/

Files intentionally ignored:
  - .env, outputs/, data/, caches, egg-info
  - root generated LumenFin_*.md / Correctness_Report.md

Files requiring manual review (NOT staged):
  - reports/FinAgentBench_Cleanup_Plan.md
  - reports/FinAgentBench_Repository_Inventory.md
```

## Notes

- Commit plan groups 1/2/4 (core metrics, mutation suite, CI gate) are already on HEAD `3de1267`.
- Remaining local commits: validation refactor, archive chore, docs/release curation.
