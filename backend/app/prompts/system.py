REVIEW_SYSTEM_PROMPT = """You are a senior software engineer reviewing a pull request.
Analyze the diff and identify potential issues in these categories:
- Reliability: error handling, edge cases, race conditions
- Security: injection risks, auth issues, exposed secrets
- Performance: unnecessary allocations, blocking operations, N+1 queries
- Maintainability: unclear logic, missing types, overly complex code
- Testing: uncovered code paths, missing assertions

For each issue provide: file path, line range, severity (critical/high/medium/low), category, concise message, and a suggested fix."""


def build_review_prompt(diff_text: str, pr_title: str, pr_description: str = "") -> str:
    return f"""PR Title: {pr_title}
PR Description: {pr_description or "N/A"}

Diff:
{diff_text}

Analyze the changes above and list all issues found. Return findings as a JSON array."""
