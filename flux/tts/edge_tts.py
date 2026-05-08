"""
Microsoft Edge TTS Agent.
"""

from __future__ import annotations

import asyncio
from typing import Dict, Optional

from flux.logger import get_logger
from flux.tts.base import TTSAgent, VoiceInfo

logger = get_logger(__name__)

class EdgeTTSAgent(TTSAgent):
    """
    Microsoft Edge TTS Provider (Free, no API key).
    """
    
    def __init__(self):
        super().__init__()
        self._voices_cache: Dict[str, VoiceInfo] | None = None

    @property
    def name(self) -> str:
        return "Microsoft Edge TTS (Free)"
    
    @property
    def id(self) -> str:
        return "edge_tts"
        
    async def get_voices(self) -> Dict[str, VoiceInfo]:
        if self._voices_cache is not None:
            return self._voices_cache
            
        try:
            import edge_tts
            voices = await edge_tts.list_voices()
            
            voices_dict = {}
            for v in voices:
                voice_id = v["ShortName"]
                language = v.get("Locale", "Unknown")
                gender = v.get("Gender", "Unknown")
                
                voices_dict[voice_id] = VoiceInfo(
                    id=voice_id,
                    name=v.get("FriendlyName", voice_id),
                    language=language,
                    gender=gender,
                    description=f"{language} ({gender})"
                )
            
            self._voices_cache = voices_dict
            return voices_dict
            
        except ImportError:
            logger.error("edge-tts not installed. Run: pip install edge-tts")
            return {}
        except Exception as e:
            logger.error("Failed to fetch Edge TTS voices: %s", e)
            return {}

    async def synthesize(self, text: str, voice_id: str, params: dict | None = None) -> bytes:
        """
        Synthesize text using EdgeTTS.
        """
        try:
            import edge_tts
        except ImportError:
            raise ImportError("edge-tts not installed. Run: pip install edge-tts")
            
        params = params or {}
        rate = params.get("rate", "+0%")
        pitch = params.get("pitch", "+0Hz")
        volume = params.get("volume", "+0%")
        
        communicate = edge_tts.Communicate(
            text,
            voice=voice_id,
            rate=rate,
            pitch=pitch,
            volume=volume
        )
        
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        
        return audio_data

# Singleton instance
edge_tts_agent = EdgeTTSAgent()
