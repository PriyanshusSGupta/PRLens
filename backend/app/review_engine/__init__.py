from app.review_engine.diff_parser import parse_diff, BINARY_EXTENSIONS
from app.review_engine.analyzers.security import SecurityAnalyzer
from app.review_engine.analyzers.reliability import ReliabilityAnalyzer
from app.review_engine.analyzers.performance import PerformanceAnalyzer
from app.review_engine.analyzers.testing import TestingAnalyzer
from app.review_engine.analyzers.llm import LLMAnalyzer
from app.core.config import settings
from app.integrations.llm_client import LLMClient


class _PrContext:
    __slots__ = ("diff_text", "title")
    def __init__(self, diff_text: str, title: str):
        self.diff_text = diff_text
        self.title = title


async def run_review_on_diff(diff_text: str, pr_title: str, pr_description: str = "", llm_client: LLMClient | None = None) -> list:
    findings: list[dict] = []

    if not diff_text.strip():
        return [{"severity": "low", "category": "maintainability", "file_path": "", "line_start": None,
                 "message": "No issues detected in this diff.", "suggestion": None, "confidence": 0.3}]

    if len(diff_text) > settings.max_diff_size:
        return [{"severity": "high", "category": "maintainability", "file_path": "", "line_start": None,
                 "message": f"Diff size ({len(diff_text)} chars) exceeds limit ({settings.max_diff_size}).",
                 "suggestion": "Split this PR into smaller changes.", "confidence": 0.95}]

    pr = _PrContext(diff_text, pr_title)

    if settings.enable_security:
        findings.extend(await SecurityAnalyzer().analyze(pr))
    if settings.enable_reliability:
        findings.extend(await ReliabilityAnalyzer().analyze(pr))
    if settings.enable_performance:
        findings.extend(await PerformanceAnalyzer().analyze(pr))
    if settings.enable_testing:
        findings.extend(await TestingAnalyzer().analyze(pr))

    if settings.enable_llm and llm_client and llm_client.api_key:
        findings.extend(await LLMAnalyzer(llm_client=llm_client).analyze(pr))

    if not findings:
        findings.append({"severity": "low", "category": "maintainability", "file_path": "", "line_start": None,
                        "message": "No issues detected in this diff.", "suggestion": None, "confidence": 0.3})

    return _apply_policy(findings)


def _apply_policy(findings: list[dict]) -> list[dict]:
    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    threshold_rank = severity_rank.get(settings.severity_threshold_block, 1)
    filtered = [f for f in findings if severity_rank.get(f.get("severity", "low"), 0) >= threshold_rank]
    filtered = [f for f in filtered if f.get("confidence", 0) >= settings.min_confidence]
    return filtered
