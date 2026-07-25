# FinAgentBench Repository Curation Report

Date: 2026-07-25
Judgment: **NOT READY — MANUAL REVIEW REQUIRED**

## 1. Half-done migration handling

| Old Path | New Path | Git State | Still Referenced | Action |
|----------|----------|-----------|------------------|--------|
| `scripts/run_production_hardening.py` | `tools/archived_audits/run_production_hardening.py` | staged rename | no active import | archive + unsupported header |
| `scripts/run_final_reliability_baseline.py` | `tools/archived_audits/...` | staged rename | no | archive |
| `scripts/evaluate_lumenfin_e2e_regression.py` | `tools/archived_audits/...` | staged rename | no | archive |
| `scripts/validate_claim_binding.py` | `tools/archived_audits/...` | staged rename | no | archive |
| `scripts/validate_financial_grounding_nvda.py` | `tools/archived_audits/...` | staged rename | no | archive |
| n/a | `scripts/rc_runtime.py` | staged add | used by RC runner (lazy) | keep |
| `scripts/run_rc_validation.py` | same | staged modify | README/CI | keep; import side-effect free |
| `docs/regression_log.md` | `reports/history/regression_log.md` | staged rename | docs index updated | history |
| `docs/sample_report.md` | `reports/history/sample_report.md` | staged rename | none critical | history |
| `reports/FinAgentBench_Final_Release_Report.md` | `reports/current/...` | staged rename | README | keep current |

`RM` half-states were resolved by restaging destination working trees. Active RC path no longer imports archived modules.

## 2. Secret risk

| Secret Risk | Repository | Git Tracked/Untracked | Required Action |
|-------------|------------|-----------------------|-----------------|
| No local `.env` | FinAgentBench | ignored / absent | none |
| `.env.example` placeholders only | FinAgentBench | tracked | keep |
| False-positive `sk-synthesize` in reference runtime string | FinAgentBench | tracked | no rotation |

## 3. Deleted files

None deleted in this pass. Obsolete runners were archived, not removed.

## 4. Archived files

- `tools/archived_audits/*.py` (+ README)
- `reports/history/*` (worktree audit, old commit plan, regression log, sample report)

## 5. Ignored

- `outputs/`, `data/`, `.env`, caches, egg-info
- root `LumenFin_*.md`, `FinAgentBench_Correctness_Report.md`
- `scripts/rerun_*.py`

## 6. SEC fixtures

N/A in this repo (JSON cases only). Diligence case now requires `claim_binder`; sample state audit log updated to match.

## 7. README / docs fixes

- Exit-code table for evaluate/gate/benchmark
- `docs/VALIDATION_COMMANDS.md`
- docs index + current/history report layout
- License status: no public grant

## 8. Supported commands

See `docs/VALIDATION_COMMANDS.md`.

## 9. Explicit staging groups

See `reports/FinAgentBench_Commit_Plan.md`. Current index holds curation/archive/RC-runtime docs as one staged candidate set (23 paths). Inventory/cleanup process docs remain untracked.

## 10. Staged audit

- `git diff --cached --check`: PASS
- No high-confidence secrets in staged diff
- No outputs/DB staged
- No `git add .`

## 11. Offline validation

| Gate | Result |
|------|--------|
| unittest discover | 77 PASS |
| mutation suite | 4/4 |
| correctness validation | PASS |
| offline demo | PASS |
| RC import tests | 2/2 PASS |
| RC `--dry-run` | PASS |
| cross-repo gate | PASS (dirty trees noted) |

## 12. Clean-clone

Not completed (no temporary commit / worktree clone run in this pass).

## 13. Live RC

Not re-run (blocked until clean-clone + owner authorization).

## 14. Uncertain

- Whether to commit `reports/FinAgentBench_{Cleanup_Plan,Repository_Inventory}.md`
- Whether `reports/history/sample_report.md` should instead live under `examples/`
- FAB tag `v0.1.0-rc.1` still absent on remote

## 15. Judgment

**NOT READY — MANUAL REVIEW REQUIRED**

Ready for owner-reviewed split commits after clean-clone and explicit commit authorization. Do not push/tag yet.
