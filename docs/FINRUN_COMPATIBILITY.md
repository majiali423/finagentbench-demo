# FinRun Compatibility

Current schema version: **1.0**.

| Producer | FinRun schema | Supported |
|----------|---------------|:---------:|
| LumenFin `0.1.0rc2` (`v0.1.0-rc.2`) | `1.0` | YES |
| FinAgentBench reference runtime `0.1.0rc2` | `1.0` | YES |
| Legacy unversioned fixtures | `legacy-0` | YES (transition only) |
| Unknown future schema | other | NO (fail closed) |

## Required fields

- `run_id` (string)
- `final_output` (string)
- `entities` (list)
- `steps` (list)
- `metrics` (list)
- `evidence` (list)
- `market_data` (list)

Release producers must also emit `schema_version: "1.0"`.

## Optional fields

- `query`
- `metadata` (agent/model/version, workflow status, provenance)
- `claims`
- entity symbols and source/provider metadata

## Fields needed for fail-closed checks

When a case has `require_checkable_metrics: true`:

- Numeric correctness needs metric `formula` + `inputs`
- Unit/currency consistency needs input `unit` + `currency`
- Temporal consistency needs periods/as-of fields
- Evidence coverage needs cited evidence for expected entities
- Evidence consistency needs numeric evidence aligned with metric inputs

No checkable item means **not passed**, not 100.

## Backward compatibility policy

1. `1.x` may add optional fields and metrics without changing required field
   meaning.
2. Removing/renaming required fields requires a new major schema version.
3. Unknown schema versions fail before scoring.
4. Legacy unversioned inputs are accepted during the `0.1.x` transition; new
   release producers must emit `1.0`.
5. Thresholds are case policy and are never reduced to preserve compatibility.
