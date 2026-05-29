from app.review_engine.analyzers.base import BaseAnalyzer
from app.review_engine.diff_parser import parse_diff


class ReliabilityAnalyzer(BaseAnalyzer):
    name = "reliability"

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
                lines = hunk.content.split("\n")
                added_lines = [l[1:] for l in lines if l.startswith("+")]
                removed_lines = [l[1:] for l in lines if l.startswith("-")]
                all_changed = added_lines + removed_lines

                bare_except_found = False
                for i, line in enumerate(added_lines):
                    stripped = line.strip()
                    if stripped == "except:" or stripped.startswith("except:"):
                        bare_except_found = True
                        findings.append({
                            "severity": "high",
                            "category": "reliability",
                            "file_path": f.file_path,
                            "line_start": None,
                            "message": "Bare except clause catches all exceptions, including SystemExit and KeyboardInterrupt.",
                            "suggestion": "Catch specific exception types, e.g., except ValueError.",
                            "confidence": 0.9,
                        })

                if not bare_except_found:
                    for i, line in enumerate(added_lines):
                        if "try:" in line and not any("except" in l for l in added_lines[i + 1 : i + 10]):
                            findings.append({
                                "severity": "medium",
                                "category": "reliability",
                                "file_path": f.file_path,
                                "line_start": None,
                                "message": "try block without visible except handler nearby.",
                                "suggestion": "Add error handling or confirm the try is intentionally bare.",
                                "confidence": 0.35,
                            })
                            break

                removed_checks = [
                    l for l in removed_lines
                    if "if" in l and ("is None" in l or "== None" in l or "is not None" in l or "!= None" in l)
                ]
                if removed_checks and not any("null" in l.lower() or "none" in l.lower() for l in added_lines):
                    findings.append({
                        "severity": "medium",
                        "category": "reliability",
                        "file_path": f.file_path,
                        "line_start": None,
                        "message": "Null/None guard removed without replacement.",
                        "suggestion": "Ensure all code paths handle None values correctly.",
                        "confidence": 0.5,
                    })

                shared_state_patterns = [".shared", ".global", "threading.", "multiprocessing."]
                for line in added_lines:
                    if any(p in line for p in shared_state_patterns):
                        findings.append({
                            "severity": "medium",
                            "category": "reliability",
                            "file_path": f.file_path,
                            "line_start": None,
                            "message": "Potential race condition: shared mutable state detected.",
                            "suggestion": "Use locks, queues, or immutable data structures for concurrent access.",
                            "confidence": 0.4,
                        })
                        break

                for line in added_lines:
                    if "Promise" in line and ".catch" not in line and "await" not in line:
                        findings.append({
                            "severity": "medium",
                            "category": "reliability",
                            "file_path": f.file_path,
                            "line_start": None,
                            "message": "Unhandled promise without .catch() or await.",
                            "suggestion": "Add .catch() handler or use async/await with try/catch.",
                            "confidence": 0.5,
                        })
                        break

                for line in removed_lines:
                    if "raise" in line and not any("raise" in l for l in added_lines):
                        findings.append({
                            "severity": "low",
                            "category": "reliability",
                            "file_path": f.file_path,
                            "line_start": None,
                            "message": "Error raising code removed without replacement.",
                            "suggestion": "Ensure errors are still properly surfaced.",
                            "confidence": 0.3,
                        })
                        break

        return findings
