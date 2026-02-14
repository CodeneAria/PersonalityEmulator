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
import subprocess
import time

from config.communcation_settings import (
    AUDIO_QUERY_ENDPOINT,
    SYNTHESIS_ENDPOINT,
    HOSTNAME,
    VOICEVOX_PORT,
)

from config.person_settings import (
    SPEAKER_ID,
    VOICE_SPEED_SCALE,
    VOICE_PITCH_SCALE,
    VOICEVOX_DICTIONARY_PATH,
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

    def __init__(self, speaker_id: int = SPEAKER_ID,
                 speed_scale: float = VOICE_SPEED_SCALE,
                 user_dict_path: str | None = None):
        """Initialize VoicevoxCommunicator.

        Args:
            speaker_id: VOICEVOX speaker ID to use for voice synthesis.
            speed_scale: Speech speed multiplier (1.0 = normal speed).
        """
        self.speaker_id = speaker_id
        self.speed_scale = speed_scale
        self.pitch_scale = VOICE_PITCH_SCALE
        self._voicevox_process = None

        # Base URL for VOICEVOX API (constructed from HOSTNAME and VOICEVOX_PORT)
        self._base_url = f"http://{HOSTNAME}:{VOICEVOX_PORT}"

        # Check if VOICEVOX server is already running
        voicevox_already_running = False
        try:
            response = requests.get(f"{self._base_url}/version", timeout=1)
            if response.status_code == 200:
                voicevox_already_running = True
                print("[VoicevoxCommunicator] VOICEVOX server is already running")
        except requests.exceptions.RequestException:
            pass

        # Start VOICEVOX server process only if not already running
        if not voicevox_already_running:
            subprocess_command = f"/opt/voicevox_engine/linux-nvidia/run --host {HOSTNAME} --port {VOICEVOX_PORT}"
            try:
                self._voicevox_process = subprocess.Popen(
                    subprocess_command,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print("[VoicevoxCommunicator] VOICEVOX server started")

                # Wait for VOICEVOX server to be ready
                print(
                    "[VoicevoxCommunicator] Waiting for VOICEVOX server to start...")
                for _ in range(10):  # Try for up to 10 seconds
                    time.sleep(1)
                    try:
                        response = requests.get(
                            f"{self._base_url}/version", timeout=1)
                        if response.status_code == 200:
                            print(
                                "[VoicevoxCommunicator] VOICEVOX server is ready")
                            break
                    except requests.exceptions.RequestException:
                        continue
            except Exception as e:
                print(
                    f"[VoicevoxCommunicator] Error starting VOICEVOX: {e}", file=sys.stderr)

        # Post user dictionary to VOICEVOX
        post_command = f'curl -X POST "http://{HOSTNAME}:{VOICEVOX_PORT}/import_user_dict?override=true" -H "Content-Type: application/json" --data-binary @"{VOICEVOX_DICTIONARY_PATH}"'
        try:
            subprocess.run(post_command, shell=True, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(
                "[VoicevoxCommunicator] User dictionary imported successfully via curl")
        except Exception as e:
            print(
                f"[VoicevoxCommunicator] Error posting user dictionary to VOICEVOX: {e}", file=sys.stderr)

        # If a user dictionary path is provided, attempt to read and import it
        if user_dict_path:
            try:
                ud_path = Path(user_dict_path).expanduser()
                with ud_path.open('r', encoding='utf-8') as f:
                    dict_data = json.load(f)

                try:
                    res = requests.post(
                        f"{self._base_url}/import_user_dict",
                        json=dict_data,
                        headers={'Content-Type': 'application/json'},
                        timeout=10,
                    )
                    res.raise_for_status()
                    print(
                        "[VoicevoxCommunicator] User dictionary imported successfully via API")
                except requests.exceptions.RequestException as e:
                    print(
                        f"[VoicevoxCommunicator] Failed to import user dict: {e}")
            except Exception as e:
                print(
                    f"[VoicevoxCommunicator] Failed to read user dict file '{user_dict_path}': {e}")

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
            query['pitchScale'] = self.pitch_scale

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

    def __del__(self):
        """Clean up VOICEVOX server process when this object is destroyed."""
        if self._voicevox_process is not None:
            try:
                voicevox_kill_command = "pkill -f voicevox"
                subprocess.run(voicevox_kill_command, shell=True)
                print("[VoicevoxCommunicator] VOICEVOX server stopped")
            except Exception as e:
                print(
                    f"[VoicevoxCommunicator] Error stopping VOICEVOX: {e}", file=sys.stderr)
