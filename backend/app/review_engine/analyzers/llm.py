from app.review_engine.analyzers.base import BaseAnalyzer
from app.review_engine.diff_parser import parse_diff
from app.integrations.llm_client import LLMClient
from app.prompts.system import REVIEW_SYSTEM_PROMPT, build_review_prompt


class LLMAnalyzer(BaseAnalyzer):
    name = "llm"

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client or LLMClient()

    async def analyze(self, pr) -> list:
        if not self.llm_client.api_key:
            return []

        diff_text = getattr(pr, "diff_text", "") or ""
        if not diff_text:
            return []

        parsed = parse_diff(diff_text)
        all_findings = []
        chunk_max = 8000

        for f in parsed:
            if not f.hunks:
                continue
            content = "\n".join(h.content for h in f.hunks)
            for i in range(0, len(content), chunk_max):
                chunk = content[i : i + chunk_max]
                user_prompt = build_review_prompt(chunk, getattr(pr, "title", ""))
                chunk_findings = await self.llm_client.generate_structured(REVIEW_SYSTEM_PROMPT, user_prompt)
                all_findings.extend(chunk_findings)

        seen = set()
        deduped = []
        for f in all_findings:
            key = (f.get("file_path", ""), f.get("message", ""), f.get("line_start"))
            if key not in seen:
                seen.add(key)
                deduped.append(f)

        return deduped
