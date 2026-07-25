# Archived FinAgentBench Audits

Historical scripts in this directory are preserved for engineering provenance.
They are unsupported, excluded from CI, and not part of the release validation
interface.

| Script | Historical purpose | Current replacement |
|--------|--------------------|---------------------|
| `evaluate_lumenfin_e2e_regression.py` | Early LumenFin state regression evaluation | `scripts/validate_cross_repo.py` |
| `run_final_reliability_baseline.py` | Pre-RC baseline report | Current release report and CI |
| `run_production_hardening.py` | Production-hardening phase orchestration | `scripts/run_rc_validation.py` |
| `validate_claim_binding.py` | Focused claim/evidence audit | Current tests and RC cases |
| `validate_financial_grounding_nvda.py` | Focused NVIDIA grounding audit | Issuer cases and RC NVIDIA scenario |

Do not run these scripts against production fixtures. They may assume historical
artifact names or report layouts.
