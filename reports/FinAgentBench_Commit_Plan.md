# FinAgentBench Commit Plan (Internal RC Candidate)

Status: staging plan only — **do not auto-commit**.
HEAD baseline before curation commits: `3de1267` (verify with `git rev-parse HEAD`).

## Rules

- No `git add .` / `git add -A`
- Explicit paths only
- No secrets, outputs, databases, or absolute machine paths
- Do not lower mutation / case thresholds

## Commit groups

| Commit | Purpose | Exact files | Validation before commit |
|--------|---------|-------------|--------------------------|
| 1. `feat(core): align FinRun adapter and fail-closed metrics` | Schema/adapter/metrics | `finagentbench/adapters/lumenfin.py`, `finagentbench/schema.py`, `finagentbench/reference_runtime/agent.py`, `finagentbench/case_binding.py`, `finagentbench/metrics/**`, related fixture JSON already on HEAD if dirty | `python -m unittest tests.test_schema_and_registry tests.test_fail_closed_and_provenance -v` |
| 2. `test(reliability): enforce mutation and correctness coverage` | Mutation/correctness | `tests/test_mutation_suite.py`, `tests/test_correctness_alignment.py`, `benchmarks/mutations/suite.json`, `scripts/run_mutation_suite.py`, `scripts/run_correctness_validation.py` | `python scripts/run_mutation_suite.py` → 4/4 |
| 3. `refactor(validation): isolate RC runtime from import side effects` | Side-effect-free RC | `scripts/rc_runtime.py`, `scripts/run_rc_validation.py`, `tests/test_rc_runner_import.py`, `fixtures/case_lumenfin_diligence.json` | `python -m unittest tests.test_rc_runner_import -v`; `python scripts/run_rc_validation.py --help`; `--dry-run` |
| 4. `ci: add cross-repository reliability gate` | CI | `.github/workflows/test.yml`, `scripts/validate_cross_repo.py`, `scripts/repo_paths.py` | workflow YAML syntax + unittest discover |
| 5. `docs: curate benchmark and validation documentation` | Docs | `README.md`, `docs/**`, `CHANGELOG.md`, `.env.example`, `examples/offline_demo/**` | link check for moved paths; exit-code docs present |
| 6. `chore(repo): archive historical audits and clean generated files` | Archive | `tools/archived_audits/**`, `reports/history/**`, `reports/current/**`, `.gitignore` | `git grep run_production_hardening -- scripts tests` empty for active imports |
| 7. `chore(release): prepare internal v0.1.0rc1 candidate` | Release notes | `reports/current/FinAgentBench_Final_Release_Report.md`, `pyproject.toml` version if needed | offline suite green; no LICENSE file created |

## Currently staged snapshot (curation execution)

See `git diff --cached --name-status` after Phase 2. Includes archive renames,
`rc_runtime`, import probes, docs index, diligence `claim_binder` fixture.

Inventory / cleanup process docs remain **untracked** until owner decides:

- `reports/FinAgentBench_Cleanup_Plan.md`
- `reports/FinAgentBench_Repository_Inventory.md`

Recommended: leave untracked or move under `reports/history/` in commit 6.

## Post-stage checks (every group)

```bash
git diff --cached --check
git diff --cached --stat
git diff --cached --name-status
```
