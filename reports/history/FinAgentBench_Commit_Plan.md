# FinAgentBench RC Commit Plan

Status: Historical
Superseded by: `../current/FinAgentBench_Final_Release_Report.md`
Purpose: Engineering evolution and release-commit evidence

Base HEAD: `a2042e6a493af1d5e464590eeb082bec7c20fa70`
Target package: `0.1.0rc1`
Suggested tag (not created): `v0.1.0-rc.1`

No `git add .` is permitted. Each commit should stage only the listed paths and
must be inspected with `git diff --cached` before commit.

## 1. `feat(adapter): align LumenFin canonical FinRun export`

- `finagentbench/adapters/lumenfin.py`
- `finagentbench/case_binding.py`
- `finagentbench/schema.py`
- `finagentbench/reference_runtime/agent.py`
- `tests/test_schema_and_registry.py`

Purpose: schema `1.0`, period-agnostic fundamentals and canonical normalization.

## 2. `feat(metrics): fail closed on empty reliability checks`

- `finagentbench/metrics/__init__.py`
- `finagentbench/metrics/entity.py`
- `finagentbench/metrics/evidence.py`
- `finagentbench/metrics/sections.py`
- `finagentbench/metrics/temporal.py`
- `finagentbench/metrics/unit_currency.py`
- `fixtures/case_lumenfin_diligence.json`
- `fixtures/case_lumenfin_generic.json`
- `tests/test_fail_closed_and_provenance.py`

Purpose: required empty checks and issuer leakage fail closed. Thresholds are
unchanged.

## 3. `test(mutations): enforce four failure mutations`

- `benchmarks/mutations/suite.json`
- `fixtures/case_lumenfin_issuer_*.json`
- `fixtures/case_lumenfin_compare_*.json`
- `scripts/run_mutation_suite.py`
- `scripts/run_correctness_validation.py`
- `scripts/run_offline_demo.py`
- `tests/test_correctness_alignment.py`
- `tests/test_mutation_suite.py`
- `examples/offline_demo/**`

Purpose: clean baseline plus wrong number/entity and missing citation/risk.

## 4. `ci: add correctness, mutation and cross-repository gates`

- `.github/workflows/test.yml`
- `scripts/repo_paths.py`
- `scripts/validate_cross_repo.py`
- `scripts/run_rc_validation.py`

Purpose: portable release gate and retained diagnostic artifacts.

## 5. `test(validation): preserve RC evidence tooling`

Reviewable optional commit:

- `scripts/evaluate_lumenfin_e2e_regression.py`
- `scripts/run_final_reliability_baseline.py`
- `scripts/run_production_hardening.py`
- `scripts/validate_claim_binding.py`
- `scripts/validate_financial_grounding_nvda.py`

The package and deterministic CI do not depend on this commit. Omit it if the
public RC should contain only maintained gates.

Excluded and retained locally:

- `scripts/rerun_hardening_failures.py`
- `scripts/rerun_tesla_baseline_after.py`

## 6. `docs: add RC compatibility and release documentation`

- `README.md`
- `docs/lumenfin_regression_case.md`
- `docs/CI_GATE.md`
- `docs/FINRUN_COMPATIBILITY.md`
- `docs/METRICS.md`
- `docs/MUTATION_TESTING.md`
- `CHANGELOG.md`
- `reports/FinAgentBench_Worktree_Audit.md`
- `reports/FinAgentBench_Commit_Plan.md`
- `reports/FinAgentBench_Final_Release_Report.md`

## 7. `chore: prepare v0.1.0-rc.1`

- `.env.example`
- `.gitignore`
- `pyproject.toml`

Purpose: package version and release hygiene. This commit does not create a tag.

## Pre-commit checks

For every group:

```bash
git diff --cached --name-status
git diff --cached --check
```

After all approved commits:

```bash
python -m unittest discover -s tests -v
python scripts/run_mutation_suite.py
python scripts/run_offline_demo.py
git status --short
```

Remote push, tag creation and GitHub Release remain explicitly unauthorized.
