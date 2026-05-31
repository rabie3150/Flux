"""Gemini Flash vocabulary generator."""

from __future__ import annotations

import json
from typing import Any

import httpx

from flux_lang.utils import get_logger

logger = get_logger(__name__)
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

PROMPT = """You are an expert language teacher. Generate exactly {count} vocabulary items for learning {target_lang} from {source_lang}.

Theme: {theme}
Difficulty: {difficulty}
Avoid these previously taught words:
{avoid_words}

For each item, provide:
1. source — word/sentence in {source_lang}
2. target — exact translation in {target_lang}
3. phonetic — pronunciation guide for target
4. difficulty — {difficulty}
5. category — e.g. "greetings", "food", "numbers"
6. example_sentence — a natural sentence in {target_lang} using the target word

Return ONLY a valid JSON array without markdown. Example:
[
  {{"source": "Hello", "target": "Ciao", "phonetic": "CHOW", "difficulty": "beginner", "category": "greetings", "example_sentence": "Ciao, come stai?"}}
]"""


class GeminiGenerator:
    def __init__(self, api_keys: list[str]):
        self.api_keys = [k.strip() for k in api_keys if k.strip()]
        self._idx = 0

    @property
    def current_key(self) -> str:
        if not self.api_keys:
            raise ValueError("No Gemini API keys configured.")
        return self.api_keys[self._idx]

    def rotate(self) -> None:
        if self.api_keys:
            self._idx = (self._idx + 1) % len(self.api_keys)

    async def generate(
        self,
        source_lang: str,
        target_lang: str,
        theme: str,
        count: int = 5,
        difficulty: str = "beginner",
        avoid_words: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        if not self.api_keys:
            logger.error("No Gemini API keys configured. Set them in config.json -> gemini_api_keys")
            return []

        avoid = ", ".join(avoid_words) if avoid_words else "None"
        prompt = PROMPT.format(
            count=count,
            source_lang=source_lang,
            target_lang=target_lang,
            theme=theme,
            difficulty=difficulty,
            avoid_words=avoid,
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "responseMimeType": "application/json"},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(len(self.api_keys)):
                try:
                    url = f"{GEMINI_URL}?key={self.current_key}"
                    resp = await client.post(url, json=payload)
                    if resp.status_code in (429, 401):
                        logger.warning("Gemini %d, rotating key", resp.status_code)
                        self.rotate()
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]

                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0]
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0]

                    result = json.loads(text.strip())
                    if isinstance(result, list):
                        return [
                            {
                                "source_text": str(item["source"]),
                                "target_text": str(item["target"]),
                                "phonetic": str(item.get("phonetic", "")),
                                "difficulty": str(item.get("difficulty", difficulty)),
                                "category": str(item.get("category", theme)),
                                "theme": theme,
                                "example_sentence": str(item.get("example_sentence", "")),
                            }
                            for item in result
                            if "source" in item and "target" in item
                        ]
                    return []
                except httpx.HTTPStatusError as e:
                    logger.error("Gemini HTTP %d: %s", e.response.status_code, e.response.text[:200])
                    self.rotate()
                except json.JSONDecodeError as e:
                    logger.error("Gemini bad JSON: %s", e)
                except Exception as e:
                    logger.error("Gemini error: %s", e)
                    self.rotate()
        return []
