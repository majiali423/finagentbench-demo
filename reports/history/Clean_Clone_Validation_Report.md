# Clean Clone Validation Report

Date: 2026-07-26
Method: detached git worktrees from final local HEADs

## Candidate HEADs

| Repository | HEAD |
|------------|------|
| FinAgentBench | `f58e47978af1badf431221bb1911c0c952b982f1` |
| LumenFin (sibling) | `0f895f85fdd3c39446900c639caaa616d9e7a756` |

## Results

| Gate | Result |
|------|--------|
| unittest discover | 78 OK (1 skip) |
| `tests.test_rc_runner_import` | 3/3 OK |
| mutation suite | 4/4 |
| offline demo | PASS |
| validate_cross_repo | PASS (dirty=false both trees) |
| run_rc_validation --dry-run | PASS |

Sibling LumenFin clean worktree: 271 OK (1 skip), including env-conflict regression tests.

## Judgment

Final-HEAD offline clean-clone gates: **PASS**. No push/tag performed.
