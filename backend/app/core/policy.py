from dataclasses import dataclass
from app.core.config import settings


@dataclass
class Policy:
    severity_block: str
    severity_warn: str
    min_confidence: float
    max_diff_size: int
    enable_security: bool
    enable_reliability: bool
    enable_performance: bool
    enable_testing: bool
    enable_llm: bool


def get_policy() -> Policy:
    return Policy(
        severity_block=settings.severity_threshold_block,
        severity_warn=settings.severity_threshold_warn,
        min_confidence=settings.min_confidence,
        max_diff_size=settings.max_diff_size,
        enable_security=settings.enable_security,
        enable_reliability=settings.enable_reliability,
        enable_performance=settings.enable_performance,
        enable_testing=settings.enable_testing,
        enable_llm=settings.enable_llm,
    )
