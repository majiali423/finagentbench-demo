# FinAgentBench Final Release Report

Candidate: `0.1.0rc1`
Suggested tag: `v0.1.0-rc.1`
FinRun schema: `1.0`
Assessment date: 2026-07-25

## Positioning

FinAgentBench is a **Replay-first Financial Agent Reliability Evaluation
Framework**. It evaluates exported traces independently from an Agent runtime.

## Release contract

- Deterministic CI profile
- FinRun `1.0`; legacy unversioned input accepted during `0.1.x`
- Unknown schema versions rejected before scoring
- Required empty checks fail closed
- Four mutations enforced in CI
- Cross-repository reports include both commits, schema, profile and mutation
  results

## Validation

| Gate | Result |
|------|--------|
| Unit tests | 75 PASS |
| Mutation suite | 4/4 detected |
| Correctness validation | PASS |
| LumenFin cross-repository gate | PASS |
| Key-free offline demo | PASS |
| Linter | No new diagnostics |
| Clean-tree validation commit | `cab5f810a9bef9cc1c29f1ed4c35f4240e792f2c` |
| Worktree after validation | CLEAN |

## Mutation evidence

| Mutation | Detected by |
|----------|-------------|
| wrong number | numeric correctness |
| wrong entity | entity coverage |
| missing citation | evidence coverage/consistency |
| missing risk | risk disclosure/section presence |

No `min_score`, severity block or metric threshold was lowered.

## Open release blocker

The local release commits and clean-tree validation are complete. The release
tag does not yet exist, no remote operation has been performed, and no LICENSE
has been selected. After the owner chooses a license, push the branch, wait for
CI, and only then create `v0.1.0-rc.1`.
