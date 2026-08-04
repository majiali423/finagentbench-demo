# FinAgentBench Final Release Report

Candidate: `0.1.0rc2`
Recommended tag: `v0.1.0-rc.2` (not created in this closure)
FinRun schema: `1.0`
Scoring versions: `1` (default), `2` (opt-in visible output integrity)
Python: `3.11`, `3.12`
Assessment date: 2026-08-05

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
  → adapter / schema validation
  → deterministic metrics (+ optional semantic judge)
  → Findings + EvalReport
  → CI pass / fail
```

Case contracts decide checkable requirements. Scores depend on trace
observability. Deterministic-first; semantic judges optional.

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
| Unit tests | 127 PASS |
| Offline demo | PASS |
| Correctness validation | PASS |
| Core reliability mutations | 4/4 |
| Extended provenance/period mutations | 7/7 |
| Total negative controls | 11/11 |
| Known-fail fixture blocked | PASS |
| Unsupported FinRun schema rejected | PASS |
| Unsupported scoring version rejected | PASS |
| Visible-output valid corpus | no high-severity false positives |
| Invalid output corpus | detected |
| Case-driven bounds reject NaN/Infinity | PASS |
| LumenFin `v0.1.0-rc.2` cross-repo | PASS |
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
| LumenFin tag | `v0.1.0-rc.2` |
| LumenFin commit | `d075b6851739be82ec2fb71fea7ad08d92d76511` |
| FinRun schema | `1.0` |
| Profile | `ci` |
| Adapter dependency on `revenue_2025` | no (canonical + period-suffixed accepted) |
| Claims field in export | present; does not break schema/runner |
| LumenFin files modified | none |

Local command (set sibling checkout paths via environment variables):

```bash
export LUMENFIN_ROOT=/path/to/lumenfin-agent
export FINAGENTBENCH_DIR=/path/to/finagentbench-demo
python scripts/validate_cross_repo.py --profile ci
```

CI pins the public tag `majiali423/lumenfin-agent@v0.1.0-rc.2` and does not
read sibling workstation paths.

## Case / scoring governance

- Existing release cases keep `min_score` at prior values (no threshold lowering).
- Diligence case added `require_factual_period_provenance: true` (stricter).
- Scoring v2 is opt-in for visible output integrity cases.
- Metric weights were not retuned to improve LumenFin scores.

## Threshold-change audit (since `v0.1.0-rc.1`)

| Change | Direction |
|--------|-----------|
| `min_score` on existing release cases | unchanged |
| `require_factual_period_provenance` | added / stricter |
| New output-integrity cases | new opt-in scoring v2 contracts |
| Plausibility bounds | case-owned; finite-only validation |

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
- No public LICENSE grant; not marketed as open source.

## Worktree / hygiene

- Generated `outputs/` is gitignored.
- Release report uses repository-relative paths or GitHub URLs.
- Cross-repo local commands use `LUMENFIN_ROOT` / `FINAGENTBENCH_DIR`.
- No `.env` / API keys committed.

## Recommended tag command (manual)

Do **not** create the tag until human review of this closure commit and CI green.

```powershell
git tag -a v0.1.0-rc.2 -m "FinAgentBench replay-first reliability release candidate v0.1.0-rc.2"
git push origin v0.1.0-rc.2
```

## Historical note

`0.1.0rc1` evidence (including older unit-test counts such as 75 PASS and the
pre-push license blocker narrative) lives under `reports/history/` and earlier
commits. This file describes the current `0.1.0rc2` candidate only.
