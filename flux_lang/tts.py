"""TTS dispatcher — Edge TTS (free) and Inworld AI."""

from __future__ import annotations

import base64
import uuid
from abc import ABC, abstractmethod
from typing import Any

import httpx

from flux_lang.utils import get_logger

logger = get_logger(__name__)


class VoiceInfo:
    def __init__(self, voice_id: str, name: str, language: str, gender: str = "", description: str = ""):
        self.voice_id = voice_id
        self.name = name
        self.language = language
        self.gender = gender
        self.description = description

    def __repr__(self) -> str:
        return f"{self.name} ({self.language})"


class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, voice_id: str, params: dict[str, Any] | None = None) -> bytes:
        ...

    @abstractmethod
    async def list_voices(self) -> list[VoiceInfo]:
        ...


class EdgeTTSProvider(TTSProvider):
    """Microsoft Edge TTS — free, no API key."""

    def __init__(self) -> None:
        self._voices: list[VoiceInfo] | None = None

    async def list_voices(self) -> list[VoiceInfo]:
        if self._voices is not None:
            return self._voices
        try:
            import edge_tts
        except ImportError as exc:
            raise ImportError("edge-tts not installed. Run: pip install edge-tts") from exc

        raw = await edge_tts.list_voices()
        voices = []
        for v in raw:
            voices.append(VoiceInfo(
                voice_id=v.get("ShortName", ""),
                name=v.get("FriendlyName", v.get("ShortName", "")),
                language=v.get("Locale", ""),
                gender=v.get("Gender", ""),
                description=v.get("Status", ""),
            ))
        self._voices = voices
        return voices

    async def synthesize(self, text: str, voice_id: str, params: dict[str, Any] | None = None) -> bytes:
        try:
            import edge_tts
        except ImportError as exc:
            raise ImportError("edge-tts not installed. Run: pip install edge-tts") from exc

        params = params or {}
        rate = params.get("rate", "+0%")
        pitch = params.get("pitch", "+0Hz")
        volume = params.get("volume", "+0%")

        communicate = edge_tts.Communicate(text, voice=voice_id, rate=rate, pitch=pitch, volume=volume)
        audio = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
        return audio


class InworldTTSProvider(TTSProvider):
    """Inworld AI TTS — free web API."""

    def __init__(self) -> None:
        self._voices: list[VoiceInfo] | None = None

    async def list_voices(self) -> list[VoiceInfo]:
        if self._voices is not None:
            return self._voices
        url = "https://inworld.ai/api/list-voices"
        headers = {
            "accept": "*/*",
            "origin": "https://inworld.ai",
            "referer": "https://inworld.ai/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/148.0.0.0 Safari/537.36",
        }
        cookies = {"inworld_uid": str(uuid.uuid4())}
        voices = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, cookies=cookies, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
                for v in data.get("voices", []):
                    langs = v.get("languages", ["en"])
                    lang = langs[0] if isinstance(langs, list) and langs else str(langs)
                    voices.append(VoiceInfo(
                        voice_id=v.get("voiceId", ""),
                        name=v.get("displayName", v.get("voiceId", "")),
                        language=lang,
                        gender="",
                        description=v.get("description", ""),
                    ))
        except Exception as e:
            logger.error("Failed to fetch Inworld voices: %s", e)
        self._voices = voices
        return voices

    async def synthesize(self, text: str, voice_id: str, params: dict[str, Any] | None = None) -> bytes:
        params = params or {}
        model_id = params.get("modelId", "inworld-tts-2")
        url = "https://inworld.ai/api/create-speech"
        headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "origin": "https://inworld.ai",
            "referer": "https://inworld.ai/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/148.0.0.0 Safari/537.36",
        }
        cookies = {"inworld_uid": str(uuid.uuid4())}
        payload = {
            "text": text,
            "voiceId": voice_id,
            "modelId": model_id,
            "deliveryMode": "DEFAULT",
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 48000},
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, cookies=cookies, json=payload, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            b64 = data.get("result", {}).get("audioContent")
            if not b64:
                raise RuntimeError("Inworld returned no audioContent")
            return base64.b64decode(b64)


_PROVIDERS: dict[str, TTSProvider] = {
    "edge_tts": EdgeTTSProvider(),
    "inworld": InworldTTSProvider(),
}


def _provider_instance(provider: str) -> TTSProvider:
    p = _PROVIDERS.get(provider)
    if not p:
        raise ValueError(f"Unknown TTS provider: {provider}")
    return p


async def list_voices(provider: str) -> list[VoiceInfo]:
    """List all voices for a provider."""
    return await _provider_instance(provider).list_voices()


async def voices_for_language(provider: str, lang_code: str) -> list[VoiceInfo]:
    """List voices filtered by language code (e.g. 'en', 'it')."""
    all_voices = await list_voices(provider)
    filtered = []
    code_lower = lang_code.lower()
    for v in all_voices:
        # EdgeTTS locales look like 'en-US', 'it-IT'
        # Inworld languages look like 'en', 'it'
        if v.language.lower().startswith(code_lower):
            filtered.append(v)
    return filtered


async def synthesize(text: str, voice_id: str, provider: str, params: dict[str, Any] | None = None) -> bytes:
    """Synthesize text to audio bytes."""
    return await _provider_instance(provider).synthesize(text, voice_id, params)
