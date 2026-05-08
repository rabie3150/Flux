"""
Inworld AI Text-to-Speech Agent.
"""

from __future__ import annotations

import base64
import uuid
import httpx
from typing import Dict, Optional
from flux.logger import get_logger

from flux.tts.base import TTSAgent, VoiceInfo

logger = get_logger(__name__)

class InworldAgent(TTSAgent):
    """
    Inworld AI TTS Provider.
    """
    
    def __init__(self):
        super().__init__()
        self._voices_cache: Dict[str, VoiceInfo] | None = None

    @property
    def name(self) -> str:
        return "Inworld AI"

    @property
    def id(self) -> str:
        return "inworld"

    async def get_voices(self) -> Dict[str, VoiceInfo]:
        """Fetch the voice list from Inworld API asynchronously."""
        if self._voices_cache is not None:
            return self._voices_cache

        url = "https://inworld.ai/api/list-voices"
        headers = {
            "accept": "*/*",
            "origin": "https://inworld.ai",
            "referer": "https://inworld.ai/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/148.0.0.0 Safari/537.36"
        }
        cookies = {
            "inworld_uid": str(uuid.uuid4())
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, cookies=cookies, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                voices_list = data.get("voices", [])
        except Exception as e:
            logger.error("Failed to fetch Inworld voices: %s", e)
            return {}

        voices_dict = {}
        for v in voices_list:
            voice_id = v.get("voiceId")
            if not voice_id:
                continue
                
            name = v.get("displayName", voice_id)
            desc = v.get("description", "")
            langs = v.get("languages", ["en"])
            lang_str = langs[0] if isinstance(langs, list) and langs else str(langs)

            voices_dict[voice_id] = VoiceInfo(
                id=voice_id,
                name=name,
                description=desc,
                language=lang_str
            )

        self._voices_cache = voices_dict
        return voices_dict

    async def synthesize(self, text: str, voice_id: str, params: dict | None = None) -> bytes:
        """
        Synthesize text using Inworld API.
        Returns bytes representing a valid WAV file.
        """
        params = params or {}
        # Inworld v2 seems to be standard now
        model_id = params.get("modelId", "inworld-tts-2")

        url = "https://inworld.ai/api/create-speech"
        headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "origin": "https://inworld.ai",
            "referer": "https://inworld.ai/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/148.0.0.0 Safari/537.36"
        }
        cookies = {
            "inworld_uid": str(uuid.uuid4())
        }

        payload = {
            "text": text,
            "voiceId": voice_id,
            "modelId": model_id,
            "deliveryMode": "DEFAULT",  # Gets full base64 audio instantly instead of NDJSON streaming
            "audioConfig": {
                "audioEncoding": "LINEAR16",
                "sampleRateHertz": 48000
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, 
                    headers=headers, 
                    cookies=cookies, 
                    json=payload, 
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                b64_audio = data.get("result", {}).get("audioContent")
                if not b64_audio:
                    raise RuntimeError("Inworld API returned success but no audioContent.")
                    
                return base64.b64decode(b64_audio)
                
            except httpx.HTTPStatusError as e:
                logger.error("Inworld TTS error (status %d): %s", e.response.status_code, e.response.text)
                raise RuntimeError(f"Inworld API error: {e.response.status_code}") from e
            except Exception as e:
                logger.error("Inworld TTS synthesis failed: %s", e)
                raise RuntimeError(f"Inworld TTS failed: {e}") from e

# Singleton instance for the service registry
inworld_agent = InworldAgent()
