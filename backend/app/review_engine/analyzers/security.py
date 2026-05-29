import re
from app.review_engine.analyzers.base import BaseAnalyzer
from app.review_engine.diff_parser import parse_diff


class SecurityAnalyzer(BaseAnalyzer):
    name = "security"

    SECRET_KEYWORDS = re.compile(
        r'(?:password|secret|api_key|api_secret|token|private_key|access_key|auth_token|passwd)\s*[:=]',
        re.IGNORECASE,
    )
    DANGEROUS_FUNCTIONS = [
        ("eval(", "Use of eval() can lead to code injection"),
        ("exec(", "Use of exec() can execute arbitrary code"),
        ("subprocess", "Use of subprocess with shell=True is a command injection risk"),
        ("os.system(", "os.system() is vulnerable to command injection"),
        ("shell=True", "Explicit shell=True in subprocess is a security risk"),
    ]

    SQL_INJECTION_PATTERN = re.compile(r'["\']\s*[\+\%]?\s*(?:SELECT|INSERT|UPDATE|DELETE|DROP)\b', re.IGNORECASE)
    OPEN_REDIRECT_PATTERN = re.compile(r'redirect\s*\(\s*(?:request\.|params\.|req\.)', re.IGNORECASE)

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

                for line in added_lines:
                    if self.SECRET_KEYWORDS.search(line) and ('"' in line or "'" in line):
                        findings.append({
                            "severity": "critical",
                            "category": "security",
                            "file_path": f.file_path,
                            "line_start": None,
                            "message": f"Potential hardcoded secret or credential: {line.strip()[:80]}",
                            "suggestion": "Use environment variables or a secrets manager instead.",
                            "confidence": 0.7,
                        })
                        break

                for line in added_lines:
                    for func, msg in self.DANGEROUS_FUNCTIONS:
                        if func in line:
                            findings.append({
                                "severity": "critical",
                                "category": "security",
                                "file_path": f.file_path,
                                "line_start": None,
                                "message": f"{msg}: {line.strip()[:80]}",
                                "suggestion": "Replace with a safer alternative or add input validation.",
                                "confidence": 0.85,
                            })

                    if self.SQL_INJECTION_PATTERN.search(line):
                        findings.append({
                            "severity": "high",
                            "category": "security",
                            "file_path": f.file_path,
                            "line_start": None,
                            "message": "Potential SQL injection via string concatenation.",
                            "suggestion": "Use parameterized queries or an ORM.",
                            "confidence": 0.6,
                        })

                    if self.OPEN_REDIRECT_PATTERN.search(line):
                        findings.append({
                            "severity": "high",
                            "category": "security",
                            "file_path": f.file_path,
                            "line_start": None,
                            "message": "Potential open redirect vulnerability.",
                            "suggestion": "Validate redirect URL against an allowlist.",
                            "confidence": 0.55,
                        })

        return findings
