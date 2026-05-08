"""
Vocabulary Generation via Gemini Flash.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from flux.config import settings
from flux.logger import get_logger

logger = get_logger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

WORD_GENERATION_PROMPT = """
You are an expert language teacher. Generate exactly {count} vocabulary items for learning {target_lang} from {source_lang}.

Theme: {theme}
Difficulty: {difficulty}
Avoid these previously taught words (do not include them):
{avoid_words}

For each item, provide:
1. The word or short sentence in {source_lang} (source text)
2. The exact translation in {target_lang} (target text)
3. A phonetic pronunciation guide for the {target_lang} text
4. The difficulty tag ({difficulty})

Return ONLY a valid JSON array of objects without markdown formatting. Example format:
[
  {{
    "source": "How are you?",
    "target": "Come stai?",
    "phonetic": "KOH-meh STAH-ee",
    "difficulty": "beginner"
  }}
]
"""

class GeminiGenerator:
    """Async client for Gemini API to generate vocabulary."""

    def __init__(self):
        self.api_keys = settings.gemini_api_keys
        self._current_key_idx = 0

    @property
    def current_key(self) -> str:
        if not self.api_keys:
            raise ValueError("No Gemini API keys configured.")
        return self.api_keys[self._current_key_idx]

    def rotate_key(self):
        """Switch to the next available API key."""
        if not self.api_keys:
            return
        self._current_key_idx = (self._current_key_idx + 1) % len(self.api_keys)
        logger.info("Rotated to Gemini API key index %d", self._current_key_idx)

    async def generate_vocabulary(
        self,
        source_lang: str,
        target_lang: str,
        theme: str,
        count: int = 5,
        difficulty: str = "beginner",
        avoid_words: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Generate a batch of vocabulary words."""
        
        if not self.api_keys:
            logger.error("Cannot generate vocabulary: GEMINI_API_KEYS not set")
            return []

        avoid_text = ", ".join(avoid_words) if avoid_words else "None"
        prompt = WORD_GENERATION_PROMPT.format(
            count=count,
            source_lang=source_lang,
            target_lang=target_lang,
            theme=theme,
            difficulty=difficulty,
            avoid_words=avoid_text
        )

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "responseMimeType": "application/json"
            }
        }

        # Try with current key, rotate on failure
        for attempt in range(len(self.api_keys)):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    url = f"{GEMINI_API_URL}?key={self.current_key}"
                    response = await client.post(url, json=payload)
                    
                    if response.status_code == 429: # Rate limit
                        logger.warning("Gemini API rate limit hit (429)")
                        self.rotate_key()
                        continue
                    
                    if response.status_code == 401: # Invalid key
                        logger.warning("Gemini API key invalid (401)")
                        self.rotate_key()
                        continue
                        
                    response.raise_for_status()
                    data = response.json()
                    
                    text_response = data['candidates'][0]['content']['parts'][0]['text']
                    
                    # Clean up response if it's wrapped in markdown
                    if "```json" in text_response:
                        text_response = text_response.split("```json")[1].split("```")[0]
                    elif "```" in text_response:
                        text_response = text_response.split("```")[1].split("```")[0]
                        
                    result = json.loads(text_response.strip())
                    
                    if isinstance(result, list):
                        # Validate structure
                        valid_items = []
                        for item in result:
                            if "source" in item and "target" in item:
                                valid_items.append({
                                    "source": str(item["source"]),
                                    "target": str(item["target"]),
                                    "phonetic": str(item.get("phonetic", "")),
                                    "difficulty": str(item.get("difficulty", difficulty))
                                })
                        return valid_items
                    
                    logger.warning("Unexpected JSON structure from Gemini: %s", type(result))
                    return []

            except httpx.HTTPStatusError as e:
                logger.error("Gemini HTTP error (status %d): %s", e.response.status_code, e.response.text)
                self.rotate_key()
            except httpx.RequestError as e:
                logger.error("Gemini network error: %s", e)
                # Network errors might just be transient, but we rotate anyway
                self.rotate_key()
            except json.JSONDecodeError as e:
                logger.error("Gemini returned invalid JSON: %s", e)
                # Not a key issue, but we try again
            except Exception as e:
                logger.error("Gemini vocabulary generation failed unexpectedly: %s", e)
                self.rotate_key()

        return []
