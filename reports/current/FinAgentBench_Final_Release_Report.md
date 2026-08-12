# FinAgentBench Final Release Report

Candidate: `0.1.0rc4`
Recommended tag: `v0.1.0-rc.4`
Tag target: tip of `master` after CI green for this closure
FinRun schema: `1.0`
Scoring versions: `1` (default), `2` (opt-in visible output integrity)
Python: `3.11`, `3.12`
Assessment date: 2026-08-12

> Builds on the published `0.1.0rc3` / `v0.1.0-rc.3` evaluator. This closure
> adds MIT licensing and updates the CI producer pin to LumenFin
> `v0.1.0-rc.3`. Metric thresholds and FinRun schema `1.0` are unchanged.

## Positioning

FinAgentBench is a replay-first reliability evaluation framework.
It evaluates exported Agent traces independently from Agent runtime.

It is not an academic leaderboard, universal factual-correctness proof,
investment-performance evaluator, or production certification.

## Install

```bash
python -m pip install -e .
```

Requires Python `>=3.11`.

## Architecture summary

```text
FinRun export
  → adapter / nested schema validation
  → deterministic metrics (+ optional semantic judge)
  → Findings + EvalReport (case_mode / derived_expectations)
  → CI pass / fail
```

Case contracts decide checkable requirements. Scores depend on trace
observability. Deterministic-first; semantic judges optional.

## Highlights in `0.1.0rc3`

- Nested FinRun validation before metric execution
- Explicit Case numeric hardening (NaN/Inf/bool/negative weights/penalties)
- `case_mode: quality | compatibility` and derived-expectation boundary
- Score fail-closed for non-finite / out-of-range metric results
- Metamorphic anti-gaming invariants

## Metrics registry

Registered deterministic / audit metrics include:

- entity_coverage, entity_leakage
- step_presence, section_presence
- numeric_correctness, temporal_consistency, unit_currency_consistency
- input_value_plausibility
- evidence_coverage, evidence_consistency, evidence_support
- market_data_disclosure
- risk_disclosure, risk_quality
- compliance_language, compliance_semantic
- input_safety, runtime_compliance
- retrieval_provenance
- visible_output_integrity

Claim–Evidence binding is **not** a registered independent metric in this RC.

## Validation evidence

| Gate | Result |
|------|--------|
| Unit tests | 149 PASS |
| Offline demo | PASS |
| Correctness validation | PASS |
| Core reliability mutations | 4/4 |
| Extended provenance/period mutations | 7/7 |
| Total negative controls | 11/11 |
| Nested FinRun / Case validation hardening | PASS |
| Metamorphic anti-gaming invariants | PASS |
| Known-fail fixture blocked | PASS |
| Unsupported FinRun schema rejected | PASS |
| Unsupported scoring version rejected | PASS |
| LumenFin `v0.1.0-rc.3` producer pin (CI) | PASS |
| Secrets / API keys required | none for offline gates |

### Core reliability mutations

| Mutation | Detected by |
|----------|-------------|
| wrong number | numeric_correctness |
| wrong entity | entity_coverage |
| missing citation | evidence_coverage/consistency |
| missing risk | risk_disclosure/section_presence |

### Extended provenance/period mutations

| Mutation | Detected by |
|----------|-------------|
| missing_metric_period_provenance | retrieval_provenance |
| query_period_source | retrieval_provenance |
| assumed_period_alignment | retrieval_provenance |
| missing_source_record | retrieval_provenance |
| formula_cross_period_inputs | retrieval_provenance |
| missing_period_alignment | retrieval_provenance |
| metric_period_drift | retrieval_provenance |

## LumenFin compatibility

| Field | Value |
|-------|-------|
| Producer pin in FAB CI | LumenFin `v0.1.0-rc.3` |
| FinRun schema | `1.0` |
| Profile | `ci` |
| Claims field in export | present; nested claim validation when present |
| LumenFin files modified | none in this RC |

Local command (set sibling checkout paths via environment variables):

```bash
export LUMENFIN_ROOT=/path/to/lumenfin-agent
export FINAGENTBENCH_DIR=/path/to/finagentbench-demo
python scripts/validate_cross_repo.py --profile ci
```

CI pins the public tag `majiali423/lumenfin-agent@v0.1.0-rc.3` as the
producer under test and does not read sibling workstation paths.

## Case / scoring governance

- Existing release cases keep `min_score` at prior values (no threshold lowering).
- `derive_entities_from_run` is limited to compatibility/smoke Cases.
- Scoring v2 remains opt-in for visible output integrity cases.
- Metric weights were not retuned to improve LumenFin scores.

## Threshold-change audit (since `v0.1.0-rc.2`)

| Change | Direction |
|--------|-----------|
| `min_score` on existing release cases | unchanged |
| Nested FinRun / Case validation | stricter |
| Derived-entity Case contract | stricter (`case_mode` required for derive) |
| Aggregate score NaN / out-of-range path | fail-closed |

## CI

Workflow: `.github/workflows/test.yml`

- Triggers: `push`, `pull_request`
- No secrets
- No live provider calls in ordinary gates
- Python 3.11: unit tests + CLI/schema smoke + known-fail block
- Python 3.12: full unit + benchmark + mutation + static semantic replay + pinned LumenFin cross-repo
- Uploads `outputs/` artifacts

## Known limitations

- Semantic live judge is optional and non-deterministic.
- Claim–Evidence binding is not an independent metric yet.
- Passing does not prove investment quality.
- Human financial review remains required.
- Project-owned source is MIT licensed; external FinRun inputs retain their own
  data rights.

## Worktree / hygiene

- Generated `outputs/` is gitignored.
- Release report uses repository-relative paths or GitHub URLs.
- Cross-repo local commands use `LUMENFIN_ROOT` / `FINAGENTBENCH_DIR`.
- No `.env` / API keys committed.

## License

Project-owned source is licensed under MIT, copyright 2026 Jiali Ma.
FinAgentBench declares no third-party runtime dependencies. Python build tools,
CI actions, LumenFin integration, and external FinRun inputs retain their own
licenses and data terms; see `THIRD_PARTY_NOTICES.md`.

## Recommended tag command (manual)

Do **not** create the tag until human review of this closure commit and CI green.

```powershell
git tag -a v0.1.0-rc.4 -m "FinAgentBench MIT license and LumenFin v0.1.0-rc.3 producer pin"
git push origin v0.1.0-rc.4
```

## Historical note

Earlier release-candidate closures remain in git history and prior report
commits. This file describes the current `0.1.0rc4` candidate only.
