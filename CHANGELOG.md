# Changelog

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
