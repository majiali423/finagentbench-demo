# Changelog

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
