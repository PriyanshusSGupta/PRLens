import json
import asyncio
import httpx
from app.core.config import settings


class LLMClient:
    def __init__(self, api_key: str = "", model: str = "", base_url: str = ""):
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model or "gpt-4o"
        self.base_url = (base_url or settings.llm_base_url or "https://api.openai.com/v1").rstrip("/")

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            return "[]"

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        url,
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                    )
                    if resp.status_code == 429:
                        retry_after = int(resp.headers.get("Retry-After", "2"))
                        await asyncio.sleep(retry_after * (attempt + 1))
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return content
            except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(2 ** (attempt + 1))
        return "[]"

    async def generate_structured(self, system_prompt: str, user_prompt: str) -> list[dict]:
        raw = await self.generate(system_prompt, user_prompt)
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "findings" in data:
                return data["findings"]
            return []
        except json.JSONDecodeError:
            return []
