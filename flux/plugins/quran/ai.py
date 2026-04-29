"""Gemini AI client for verse identification.

Handles prompt engineering, file uploading (or URL sharing), 
and key rotation for the Gemini 1.5 API.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from flux.logger import get_logger

logger = get_logger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

class GeminiAIClient:
    """Async client for Gemini API with key rotation."""

    def __init__(self, api_keys: list[str]):
        self.api_keys = api_keys
        self._current_key_idx = 0

    @property
    def current_key(self) -> str:
        return self.api_keys[self._current_key_idx]

    def rotate_key(self):
        """Switch to the next available API key."""
        self._current_key_idx = (self._current_key_idx + 1) % len(self.api_keys)
        logger.info("Rotated to Gemini API key index %d", self._current_key_idx)

    async def identify_verse(self, video_url: str | None = None, audio_path: str | None = None) -> dict[str, Any] | None:
        """Ask Gemini to identify the Quranic verse from a URL or audio file.
        
        Returns {"surah": int, "ayah": int, "confidence": float} or None.
        """
        if not video_url and not audio_path:
            return None

        # Build prompt
        prompt = (
            "You are an expert in Quranic studies. Identify the Quranic verse in this video/audio. "
            "Return ONLY a JSON object with 'surah' (number) and 'ayah' (number). "
            "If it contains multiple verses, return the first one. "
            "If you are unsure, return null. "
            "Example: {\"surah\": 2, \"ayah\": 255}"
        )

        if video_url:
            prompt += f"\n\nVideo URL: {video_url}"
        
        # For now, we support URL-based identification as it's lighter on bandwidth.
        # Audio file upload can be added later if needed.
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        # Try with current key, rotate on failure
        for _ in range(len(self.api_keys)):
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
                    
                    # Parse JSON from response
                    text_response = data['candidates'][0]['content']['parts'][0]['text']
                    # Extract JSON block if Gemini wrapped it in markdown
                    if "```json" in text_response:
                        text_response = text_response.split("```json")[1].split("```")[0]
                    elif "```" in text_response:
                        text_response = text_response.split("```")[1].split("```")[0]
                    
                    result = json.loads(text_response.strip())
                    if result and result.get("surah") and result.get("ayah"):
                        return {
                            "surah": int(result["surah"]),
                            "ayah": int(result["ayah"]),
                            "method": "gemini_ai",
                            "confidence": 0.9 # Gemini is usually high confidence for this
                        }
                    return None

            except Exception as e:
                logger.error("Gemini ID attempt failed: %s", e)
                self.rotate_key()

        return None
