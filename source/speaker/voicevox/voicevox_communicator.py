"""VOICEVOX-specific voice synthesis implementation."""
from __future__ import annotations

import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))
sys.path.append(str(Path(__file__).resolve().parents[3]))

import json
from abc import ABC, abstractmethod
from typing import Optional
import requests

from config.communcation_settings import (
    AUDIO_QUERY_ENDPOINT,
    SYNTHESIS_ENDPOINT,
    SPEAKER_ID_KASUKABE_TSUMUGI,
    VOICE_SPEED_SCALE,
)


class VoiceSynthesizerInterface(ABC):
    """Abstract base class for voice synthesis engines.

    This interface allows VoiceGenerator to work with different
    voice synthesis backends (VOICEVOX, OpenAI TTS, etc.) without
    modification.
    """

    @abstractmethod
    def synthesize(self, text: str) -> Optional[bytes]:
        """Generate audio from text.

        Args:
            text: Text string to convert to speech.

        Returns:
            WAV binary data if successful, None on error.
        """
        pass


class VoicevoxCommunicator(VoiceSynthesizerInterface):
    """VOICEVOX-specific voice synthesis implementation.

    This class handles all VOICEVOX API communication and audio generation.
    """

    def __init__(self, speaker_id: int = SPEAKER_ID_KASUKABE_TSUMUGI,
                 speed_scale: float = VOICE_SPEED_SCALE):
        """Initialize VoicevoxCommunicator.

        Args:
            speaker_id: VOICEVOX speaker ID to use for voice synthesis.
            speed_scale: Speech speed multiplier (1.0 = normal speed).
        """
        self.speaker_id = speaker_id
        self.speed_scale = speed_scale

    def synthesize(self, text: str) -> Optional[bytes]:
        """Generate audio from text using VOICEVOX API.

        Args:
            text: Text string to convert to speech.

        Returns:
            WAV binary data if successful, None on error.
        """
        if not text or text.strip() == "":
            return None

        try:
            # Step 1: Create audio query
            res1 = requests.post(
                AUDIO_QUERY_ENDPOINT,
                params={'text': text, 'speaker': self.speaker_id}
            )
            res1.raise_for_status()

            # Step 2: Modify query with speed scale
            query = res1.json()
            query['speedScale'] = self.speed_scale

            # Step 3: Synthesize speech
            res2 = requests.post(
                SYNTHESIS_ENDPOINT,
                params={'speaker': self.speaker_id},
                data=json.dumps(query)
            )
            res2.raise_for_status()

            return res2.content

        except requests.exceptions.RequestException as e:
            print(
                f"[VoicevoxCommunicator] Failed to synthesize text '{text}': {e}")
            return None
