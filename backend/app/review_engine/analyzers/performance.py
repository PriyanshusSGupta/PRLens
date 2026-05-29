from app.review_engine.analyzers.base import BaseAnalyzer
from app.review_engine.diff_parser import parse_diff


class PerformanceAnalyzer(BaseAnalyzer):
    name = "performance"

    async def analyze(self, pr) -> list:
        findings = []
        diff_text = getattr(pr, "diff_text", "") or ""

        if not diff_text:
            return findings

        parsed = parse_diff(diff_text)

        for f in parsed:
            if not f.hunks:
                continue

            for hunk in f.hunks:
                added_lines = [l[1:] for l in hunk.content.split("\n") if l.startswith("+")]
                lines_raw = hunk.content.split("\n")

                for line in added_lines:
                    if ".all()" in line or ".find(" in line or "SELECT *" in line.upper():
                        loop_lines_above = [l for l in lines_raw if l.startswith(" ") and ("for " in l or "while " in l)]
                        if loop_lines_above:
                            findings.append({
                                "severity": "high",
                                "category": "performance",
                                "file_path": f.file_path,
                                "line_start": None,
                                "message": "Potential N+1 query: database call detected inside a loop.",
                                "suggestion": "Use join/prefetch or batch query outside the loop.",
                                "confidence": 0.55,
                            })
                            break

                for line in added_lines:
                    if ("new " in line or "malloc" in line.lower() or "Array(" in line) and any(
                        loop in line.lower() for loop in ["for ", "while ", ".map(", ".forEach(", "loop"]
                    ):
                        pass  # harder to detect — check lines around
                    if ("range(" in line or "list(" in line or "dict(" in line or "['" in line or '["' in line) and any(
                        l.startswith(" ") and ("for " in l or "while " in l) for l in lines_raw
                    ):
                        findings.append({
                            "severity": "medium",
                            "category": "performance",
                            "file_path": f.file_path,
                            "line_start": None,
                            "message": "Large allocation detected inside a loop.",
                            "suggestion": "Move allocation outside the loop if possible.",
                            "confidence": 0.35,
                        })
                        break

                has_async_pattern = any("async def" in l or "await " in l for l in added_lines)
                has_blocking_io = any(
                    pat in l for l in added_lines
                    for pat in ["requests.get", "requests.post", "time.sleep(", "open("]
                )
                if has_async_pattern and has_blocking_io:
                    findings.append({
                        "severity": "high",
                        "category": "performance",
                        "file_path": f.file_path,
                        "line_start": None,
                        "message": "Blocking I/O operation detected in async context.",
                        "suggestion": "Use async-compatible libraries (httpx, aiofiles, asyncio.sleep).",
                        "confidence": 0.7,
                    })

                list_endpoint = any(
                    "/list" in l or "getAll" in l or "fetchAll" in l for l in added_lines
                )
                has_limit = any("limit" in l.lower() or "page" in l.lower() for l in added_lines)
                if list_endpoint and not has_limit:
                    findings.append({
                        "severity": "medium",
                        "category": "performance",
                        "file_path": f.file_path,
                        "line_start": None,
                        "message": "List endpoint detected without pagination/limit parameter.",
                        "suggestion": "Add page/limit query parameters and cursor-based pagination.",
                        "confidence": 0.5,
                    })

        return findings
