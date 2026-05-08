"""
Base TTS Agent Interface

Abstract base class for all TTS provider agents in Flux.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class VoiceInfo:
    """Information about a voice."""
    id: str
    name: str
    language: str = "en"
    gender: str = "neutral"
    description: str = ""


class TTSAgent(ABC):
    """
    Abstract base class for TTS provider agents.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the TTS provider."""
        pass
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier for the agent (e.g., 'inworld', 'edge_tts')."""
        pass
    
    @abstractmethod
    async def get_voices(self) -> Dict[str, VoiceInfo]:
        """
        Return available voices for this agent.
        """
        pass
    
    @abstractmethod
    async def synthesize(
        self, 
        text: str, 
        voice_id: str, 
        params: dict | None = None
    ) -> bytes:
        """
        Synthesize text to audio.
        
        Args:
            text: Text to synthesize.
            voice_id: The ID of the voice to use.
            params: Agent-specific parameters (like speed, pitch, model).
            
        Returns:
            Audio bytes in WAV format.
        """
        pass
