# Clean Clone Validation Report

Date: 2026-07-26  
Method: detached git worktrees from local candidate HEADs

## Candidate HEADs

| Repository | HEAD |
|------------|------|
| FinAgentBench | `e5cffe2e9fca3d7c052b2c5db193d0f6796008f6` |
| LumenFin | `8b944f7d9927bc2a726fc57ec5b12f3c4b7ebd10` |

## Results

| Gate | Result |
|------|--------|
| unittest discover | 77 OK |
| mutation suite | 4/4 |
| offline demo | PASS |
| import side-effect tests | PASS |
| validate_cross_repo --profile ci | PASS |
| run_rc_validation --dry-run | PASS |

Sibling LumenFin clean worktree unit suite: 267 OK (1 intentional live-integration skip).

## Judgment

Offline clean-clone gates: **PASS**. No push/tag performed.
