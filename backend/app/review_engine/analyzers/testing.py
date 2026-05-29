from app.review_engine.analyzers.base import BaseAnalyzer
from app.review_engine.diff_parser import parse_diff


class TestingAnalyzer(BaseAnalyzer):
    name = "testing"

    async def analyze(self, pr) -> list:
        findings = []
        diff_text = getattr(pr, "diff_text", "") or ""

        if not diff_text:
            return findings

        parsed = parse_diff(diff_text)
        has_test_files = any(
            "test" in f.file_path.lower() or "spec" in f.file_path.lower() or ".test." in f.file_path
            for f in parsed
        )
        total_lines = sum(len(h.content.split("\n")) for f in parsed for h in f.hunks)
        has_source_changes = any(
            not ("test" in f.file_path.lower() or "spec" in f.file_path.lower()) for f in parsed
        )

        if total_lines > 200 and has_source_changes and not has_test_files:
            findings.append({
                "severity": "high",
                "category": "testing",
                "file_path": "",
                "line_start": None,
                "message": f"Large diff ({total_lines}+ lines) with zero test file changes.",
                "suggestion": "Add or update tests for the changed functionality.",
                "confidence": 0.65,
            })

        for f in parsed:
            if f.file_path and ("test" in f.file_path.lower() or "spec" in f.file_path.lower()):
                continue

            if not f.hunks:
                continue

            for hunk in f.hunks:
                added_lines = [l[1:] for l in hunk.content.split("\n") if l.startswith("+")]
                func_names = [l.split("def ")[1].split("(")[0].strip() for l in added_lines if "def " in l]
                func_names += [l.split("function ")[1].split("(")[0].strip() for l in added_lines if "function " in l]

                if func_names and not has_test_files:
                    findings.append({
                        "severity": "medium",
                        "category": "testing",
                        "file_path": f.file_path,
                        "line_start": None,
                        "message": f"Functions changed without test coverage: {', '.join(func_names[:5])}",
                        "suggestion": "Add unit tests for modified functions.",
                        "confidence": 0.5,
                    })

                for line in added_lines:
                    if "fixme" in line.lower() or "hack" in line.lower() or "workaround" in line.lower():
                        findings.append({
                            "severity": "low",
                            "category": "maintainability",
                            "file_path": f.file_path,
                            "line_start": None,
                            "message": f"Code marked as temporary/hack: {line.strip()[:80]}",
                            "suggestion": "Replace with a proper solution or add a tracking issue.",
                            "confidence": 0.7,
                        })

        return findings
