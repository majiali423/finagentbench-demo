from __future__ import annotations

from .compliance import compliance_language
from .entity import entity_coverage
from .evidence import evidence_coverage
from .market import market_data_disclosure
from .numeric import numeric_correctness
from .steps import step_presence


BUILTIN_METRICS = (
    entity_coverage,
    step_presence,
    numeric_correctness,
    evidence_coverage,
    market_data_disclosure,
    compliance_language,
)
