"""
TTS Service — High-level API for synthesizing speech.
"""

from __future__ import annotations

from typing import Dict

from flux.logger import get_logger
from flux.tts.base import TTSAgent, VoiceInfo
from flux.tts.edge_tts import edge_tts_agent
from flux.tts.inworld import inworld_agent

logger = get_logger(__name__)

class TTSService:
    """
    Registry and high-level wrapper for TTS providers.
    """
    
    def __init__(self):
        self._agents: Dict[str, TTSAgent] = {
            inworld_agent.id: inworld_agent,
            edge_tts_agent.id: edge_tts_agent,
        }
        self._default_agent_id = inworld_agent.id

    def get_agent(self, agent_id: str | None = None) -> TTSAgent:
        """Get a specific TTS agent, or the default."""
        agent_id = agent_id or self._default_agent_id
        agent = self._agents.get(agent_id)
        if not agent:
            logger.warning("TTS agent '%s' not found, falling back to default", agent_id)
            return self._agents[self._default_agent_id]
        return agent

    async def get_voices(self, agent_id: str | None = None) -> Dict[str, VoiceInfo]:
        """Fetch available voices for an agent."""
        agent = self.get_agent(agent_id)
        return await agent.get_voices()

    async def synthesize(
        self, 
        text: str, 
        voice_id: str, 
        agent_id: str | None = None,
        params: dict | None = None
    ) -> bytes:
        """
        Synthesize speech.
        
        Args:
            text: The text to speak.
            voice_id: The provider-specific voice ID (e.g. 'Orietta', 'en-US-JennyNeural').
            agent_id: The TTS provider ('inworld' or 'edge_tts').
            params: Optional provider config (e.g., speed, pitch, model).
            
        Returns:
            Audio bytes in WAV format.
        """
        agent = self.get_agent(agent_id)
        logger.debug("Synthesizing TTS via %s (voice: %s): %s...", agent.name, voice_id, text[:20])
        
        try:
            audio_bytes = await agent.synthesize(text, voice_id, params)
            logger.debug("Successfully generated %d bytes of audio.", len(audio_bytes))
            return audio_bytes
        except Exception as e:
            logger.error("TTS synthesis failed on %s: %s", agent.name, e)
            raise

# Singleton service
tts_service = TTSService()

# Expose main methods at module level for convenience
async def synthesize(text: str, voice_id: str, agent_id: str | None = None, params: dict | None = None) -> bytes:
    return await tts_service.synthesize(text, voice_id, agent_id, params)

async def get_voices(agent_id: str | None = None) -> Dict[str, VoiceInfo]:
    return await tts_service.get_voices(agent_id)
