from __future__ import annotations

from .compliance import compliance_language
from .compliance_semantic import compliance_semantic
from .entity import entity_coverage
from .evidence import evidence_coverage
from .evidence_consistency import evidence_consistency
from .evidence_support import evidence_support
from .market import market_data_disclosure
from .numeric import numeric_correctness
from .risk import risk_disclosure
from .risk_quality import risk_quality
from .sections import section_presence
from .steps import step_presence
from .temporal import temporal_consistency
from .unit_currency import unit_currency_consistency


BUILTIN_METRICS = (
    entity_coverage,
    step_presence,
    section_presence,
    numeric_correctness,
    temporal_consistency,
    unit_currency_consistency,
    evidence_coverage,
    evidence_consistency,
    evidence_support,
    market_data_disclosure,
    risk_disclosure,
    risk_quality,
    compliance_language,
    compliance_semantic,
)
