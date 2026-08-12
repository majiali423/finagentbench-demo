# Changelog

## 0.1.0rc4 — 2026-08-12

License closure and producer-pin update for LumenFin `v0.1.0-rc.3`.
Evaluator thresholds, mutation suite, and FinRun schema `1.0` are unchanged.

### Added

- MIT `LICENSE` for project-owned source, copyright 2026 Jiali Ma
- `THIRD_PARTY_NOTICES.md` for build/CI/integration and external FinRun inputs

### Changed

- CI and local cross-repo producer pin: LumenFin `v0.1.0-rc.2` → `v0.1.0-rc.3`
- Package metadata declares MIT license classifiers

### Compatibility

- FinRun schema remains `1.0`
- No metric thresholds or scoring weights were changed
- Published tag: `v0.1.0-rc.4`

## 0.1.0rc3 — 2026-08-06

Hardens FinRun / Case validation and scoring fail-closed behavior before
release consumers (including LumenFin) pin this candidate.

### Added

- Nested FinRun validation for entities, steps, metrics, formula inputs,
  evidence, market data, and claims before metric execution
- Explicit rejection of Python `bool` values used as numbers
- `case_mode: quality | compatibility` with derived-entity boundary
- EvalReport / Markdown / HTML provenance fields for `case_mode` and
  `derived_expectations`
- Metamorphic anti-gaming tests (ordering, evidence removal, numeric error
  monotonicity, forbidden entities, citation/risk spam, number stuffing)
- Score-invariant fail-closed path for non-finite or out-of-range metric scores

### Changed

- `derive_entities_from_run=true` requires `case_mode=compatibility` (or
  `allow_derived_expectations=true`)
- `compare_runs()` freezes baseline-derived expectations so entity regressions
  cannot be masked
- Generic LumenFin fixture marked as compatibility smoke, not quality proof

### Compatibility

- FinRun schema remains `1.0`
- Existing legal fixtures and release Cases remain valid
- Invalid Cases / malformed FinRuns now fail earlier with field-path
  `ValidationError` (intentional contract tightening)

### Security / release

- No secrets required for offline gates
- No thresholds or metric weights were lowered for Agent score matching
- Recommended tag: `v0.1.0-rc.3`

### Known limitations

- Semantic live judge remains optional and non-deterministic
- Claim–Evidence binding is not a registered independent metric in this RC
- Evidence consistency still primarily matches entity + numeric support text;
  richer period/unit binding remains future work

## 0.1.0rc2 — 2026-08-05

Replay-first reliability release candidate aligned with LumenFin `v0.1.0-rc.2`.

### Added

- Visible output integrity metric (scoring v2 opt-in) with adversarial false-positive corpus
- Case-driven input value plausibility with finite bounds validation (rejects NaN/Infinity)
- Period provenance validation and extended provenance/period mutations
- Cross-period, source-record/citation, and metric-period-drift negative controls
- Side-effect-free LumenFin exporter loader for offline cross-repo validation
- Python 3.12 CI matrix lane plus pinned public-tag LumenFin compatibility gate

### Changed

- LumenFin adapter accepts canonical and period-suffixed fundamentals without hard-requiring `revenue_2025`
- Mutation reports separate core reliability (4) from extended provenance/period controls (7)
- Release docs, README positioning, and validation commands aligned to current gates
- Report path portability checks keep machine-absolute paths out of release evidence

### Compatibility

- FinRun schema remains `1.0`
- Validated against LumenFin `v0.1.0-rc.2` (`d075b6851739be82ec2fb71fea7ad08d92d76511`)
- Claim fields may appear in FinRun exports; they do not break schema/runner when unused by metrics

### Security / release

- No secrets required for offline gates
- No thresholds or metric weights were lowered for Agent score matching
- Recommended tag (not created in this closure): `v0.1.0-rc.2`

### Known limitations

- Semantic live judge remains optional and non-deterministic
- Claim–Evidence binding is not a registered independent metric in this RC
- FinRun `1.0` performs shallow structural validation; richer JSON Schema remains future work

## 0.1.0rc1 — 2026-07-25

First release-candidate contract for replay-first financial Agent evaluation.

### Added

- FinRun schema contract `1.0` with legacy unversioned input compatibility
- Deterministic entity, numeric, evidence, temporal, unit and compliance gates
- Fail-closed empty-check behavior for required reliability metrics
- Four-mutation CI suite: wrong number/entity and missing citation/risk
- Portable LumenFin cross-repository validation with commit/schema provenance
- Key-free offline demo and report artifacts

### Changed

- LumenFin issuer/compare cases cover entity leakage explicitly
- CI uploads benchmark and mutation reports

### Security / release

- `.env` and generated outputs are ignored
- No thresholds were lowered for this release

### Known limitations

- Semantic live judge remains optional and non-deterministic
- FinRun `1.0` performs shallow structural validation; richer JSON Schema is
  planned for a later compatible release
