import httpx
from app.core.config import settings

GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    def __init__(self, token: str = ""):
        self.token = token or settings.github_private_key or ""

    def _headers(self, extra: dict | None = None) -> dict:
        h = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if extra:
            h.update(extra)
        return h

    async def fetch_pr_and_diff(self, owner: str, repo: str, pr_number: int) -> tuple[dict, str]:
        async with httpx.AsyncClient() as client:
            pr_resp = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=self._headers(),
            )
            if pr_resp.status_code == 404:
                raise ValueError(f"PR #{pr_number} not found in {owner}/{repo}")
            if pr_resp.status_code == 403:
                raise RuntimeError("GitHub rate limit exceeded. Try using a token.")
            if pr_resp.status_code == 401:
                raise RuntimeError("GitHub authentication failed. Token may be invalid or expired.")
            pr_resp.raise_for_status()
            pr_data = pr_resp.json()

        async with httpx.AsyncClient() as client:
            diff_resp = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=self._headers({"Accept": "application/vnd.github.v3.diff"}),
            )
            if diff_resp.status_code == 403:
                diff_text = "[diff unavailable — rate limited]"
            elif diff_resp.status_code == 401:
                diff_text = "[diff unavailable — authentication failed]"
            else:
                diff_resp.raise_for_status()
                diff_text = diff_resp.text

        return pr_data, diff_text

    async def post_pr_comment(self, owner: str, repo: str, pr_number: int, findings: list) -> dict:
        if not self.token:
            return {"status": "skipped_no_token"}

        critical = [f for f in findings if f.get("severity") == "critical"]
        high = [f for f in findings if f.get("severity") == "high"]
        medium = [f for f in findings if f.get("severity") == "medium"]
        low = [f for f in findings if f.get("severity") == "low"]

        lines = [
            "## 🤖 PRLens Review",
            "",
            f"**{len(findings)} findings** — "
            f"🔴 {len(critical)} critical, 🟠 {len(high)} high, 🟡 {len(medium)} medium, 🟢 {len(low)} low",
            "",
        ]

        for f in findings:
            severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(f.get("severity"), "⚪")
            lines.append(f"{severity_icon} **[{f.get('severity', 'low').upper()}] {f.get('category', '')}** — {f.get('message', '')}")
            if f.get("file_path"):
                lines.append(f"  📁 `{f['file_path']}`")
            if f.get("suggestion"):
                lines.append(f"  💡 *{f['suggestion']}*")
            lines.append("")

        if not findings:
            lines.append("✅ No issues detected in this diff.")

        body = "\n".join(lines)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{pr_number}/comments",
                json={"body": body},
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()
