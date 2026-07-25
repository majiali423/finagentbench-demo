# FinAgentBench Worktree Audit

Date: 2026-07-25
Branch: `master`
HEAD before release commits: `a2042e6a493af1d5e464590eeb082bec7c20fa70`
Local tags: none
Remote tags: none

Audit commands: `git status --short`, `git diff --stat`,
`git diff --name-status`, `git ls-files --others --exclude-standard`.

At audit start: 19 modified tracked files and 18 untracked path groups. The
tracked diff contained 467 insertions and 58 deletions.

## Classification

| File/directory | Git status | Category | Recommended action | Reason |
|----------------|------------|----------|--------------------|--------|
| `finagentbench/adapters/lumenfin.py` | modified | production source | stage | Canonical LumenFin state normalization and period-agnostic fundamentals |
| `finagentbench/case_binding.py` | modified | production source | stage | Case/run entity binding used by evaluator |
| `finagentbench/schema.py` | modified | production source | stage | FinRun schema `1.0` compatibility rejection |
| `finagentbench/reference_runtime/agent.py` | modified | production source | stage | Emits schema-versioned reference FinRun |
| `finagentbench/metrics/{__init__,entity,evidence,sections,temporal,unit_currency}.py` | modified | production source | stage | Entity checks and fail-closed reliability behavior |
| `fixtures/case_lumenfin_{diligence,generic}.json` | modified | evaluation configuration | stage | Required checkability/entity policy; no threshold reduction |
| `fixtures/case_lumenfin_{issuer_*,compare_*}.json` | untracked | evaluation configuration | stage | RC issuer/compare coverage |
| `benchmarks/mutations/suite.json` | untracked | evaluation fixture | stage | Four required release mutations |
| `tests/test_fail_closed_and_provenance.py` | modified | tests | stage | Empty-check/provenance regression |
| `tests/test_schema_and_registry.py` | modified | tests | stage | Schema version compatibility regression |
| `tests/test_{correctness_alignment,mutation_suite}.py` | untracked | tests | stage | Correctness and mutation enforcement |
| `.github/workflows/test.yml` | modified | CI/configuration | stage | Mutation gate and report retention |
| `.env.example` | untracked | safe configuration template | stage | Empty placeholders only; `.env` remains ignored |
| `scripts/repo_paths.py` | untracked | release tooling | stage | Portable sibling/env discovery |
| `scripts/{run_mutation_suite,run_offline_demo,validate_cross_repo,run_rc_validation}.py` | untracked | release tooling | stage | Required reproducible release gates |
| `scripts/{evaluate_lumenfin_e2e_regression,run_correctness_validation,run_final_reliability_baseline,run_production_hardening,validate_claim_binding,validate_financial_grounding_nvda}.py` | untracked | validation tooling | stage after review | Reproduces historical RC evidence; no generated output |
| `scripts/rerun_hardening_failures.py` | untracked, now ignored | obsolete temporary | ignore; do not delete | One-off local rerun helper |
| `scripts/rerun_tesla_baseline_after.py` | untracked, now ignored | obsolete temporary | ignore; do not delete | One-off local rerun helper |
| `examples/offline_demo/**` | untracked | documentation/example | stage | Synthetic, key-free example artifacts |
| `README.md`, `docs/lumenfin_regression_case.md` | modified | documentation | stage | Portable paths and release positioning |
| `docs/{CI_GATE,FINRUN_COMPATIBILITY,METRICS,MUTATION_TESTING}.md` | untracked | documentation | stage | Required RC contract documentation |
| `CHANGELOG.md` | untracked | documentation/version | stage | RC change history |
| `reports/FinAgentBench_Final_Release_Report.md` | untracked | formal release report | stage after final refresh | Canonical release evidence |
| `reports/FinAgentBench_Worktree_Audit.md` | untracked | formal release report | stage | This audit |
| `pyproject.toml` | modified | version/configuration | stage last | Package version `0.1.0rc1` |
| `.gitignore` | modified | CI/configuration | stage | Excludes outputs, secrets and retained one-off helpers |
| `outputs/`, caches, logs, DBs | ignored/not listed | generated/local state | keep ignored | No release source |
| `.env` | ignored/not listed | secrets | prohibit commit | Local credentials |

## Binary and large-file review

- No untracked binary fixture is present in FinAgentBench.
- Example and mutation artifacts are small JSON/Markdown files.
- Generated benchmark outputs remain ignored.

## Secret and path review

- No literal API key/token pattern was found.
- `.env.example` contains blank placeholders.
- Published README/regression commands use sibling-relative paths.

## Uncertain items

The six historical validation scripts listed as “stage after review” are useful
for evidence reproduction but are not needed by the minimal package runtime.
They must not be deleted. The commit plan keeps them in a separate tooling
commit so reviewers can omit that commit without affecting the evaluator.

## Release conclusion

The tree is classifiable without staging generated data. It is not yet clean,
and no tag should be created until reviewed commits, license decision and
post-commit validation are complete.
