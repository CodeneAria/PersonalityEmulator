"""Voice manager module for controlling VoiceGenerator subprocess."""
import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from __future__ import annotations
import subprocess
import time
from typing import Optional, Union
import requests

sys.path.append(str(Path(__file__).resolve().parents[2]))

from config.communcation_settings import (
    VOICE_GENERATOR_PORT,
    AUDIO_PLAYER_PORT,
    HOSTNAME,
    RESPONSE_STATUS_CODE_SUCCESS,
    RESPONSE_STATUS_CODE_NOT_FOUND,
    RESPONSE_STATUS_CODE_ERROR,
)


class VoiceManager:
    """Manager class for controlling VoiceGenerator in a separate process.

    This class starts VoiceGenerator as a subprocess and communicates
    with it via HTTP requests.
    """

    def __init__(
        self,
        host: str = HOSTNAME,
        voice_gen_port: int = VOICE_GENERATOR_PORT,
        audio_player_port: int = AUDIO_PLAYER_PORT
    ):
        """Initialize VoiceManager.

        Args:
            host: Hostname for the VoiceGenerator and AudioSpeaker servers.
            voice_gen_port: Port number for the VoiceGenerator server.
            audio_player_port: Port number for the AudioSpeaker server.
        """
        self.host = host
        self.voice_gen_port = voice_gen_port
        self.audio_player_port = audio_player_port
        self.voice_gen_url = f"http://{host}:{voice_gen_port}"
        self.audio_player_url = f"http://{host}:{audio_player_port}"
        self.voice_gen_process: Optional[subprocess.Popen] = None
        self.audio_player_process: Optional[subprocess.Popen] = None

        # For backward compatibility
        self.base_url = self.voice_gen_url
        self.port = voice_gen_port
        self.process = self.voice_gen_process

    def start(self, wait_time: float = 2.0, start_audio_player: bool = True) -> bool:
        """Start VoiceGenerator and optionally AudioSpeaker subprocesses.

        Args:
            wait_time: Time to wait for servers to start (seconds).
            start_audio_player: Whether to start AudioSpeaker subprocess.

        Returns:
            True if all servers started successfully, False otherwise.
        """
        # Start VoiceGenerator
        voice_gen_success = self._start_voice_generator(wait_time)
        if not voice_gen_success:
            return False

        # Start AudioSpeaker if requested
        if start_audio_player:
            audio_player_success = self._start_audio_player(wait_time)
            if not audio_player_success:
                self.stop()  # Stop VoiceGenerator if AudioSpeaker fails
                return False

        return True

    def _start_voice_generator(self, wait_time: float = 2.0) -> bool:
        """Start VoiceGenerator subprocess.

        Args:
            wait_time: Time to wait for server to start (seconds).

        Returns:
            True if server started successfully, False otherwise.
        """
        if self.voice_gen_process is not None:
            print("VoiceGenerator process is already running.")
            return True

        voice_generator_script = Path(
            __file__).resolve().parent / "voice_generator.py"

        try:
            self.voice_gen_process = subprocess.Popen(
                [sys.executable, str(voice_generator_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for server to start
            time.sleep(wait_time)

            # Check if process is still running
            if self.voice_gen_process.poll() is not None:
                print("VoiceGenerator process failed to start.")
                return False

            # Verify server is responding
            try:
                response = requests.get(
                    f"{self.voice_gen_url}/queue_status", timeout=2)
                if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                    print(f"VoiceGenerator started on {self.voice_gen_url}")
                    self.process = self.voice_gen_process  # Backward compatibility
                    return True
            except requests.exceptions.RequestException:
                print("VoiceGenerator server is not responding.")
                return False

            return True
        except Exception as e:
            print(f"Failed to start VoiceGenerator: {e}")
            return False

    def _start_audio_player(self, wait_time: float = 2.0) -> bool:
        """Start AudioSpeaker subprocess.

        Args:
            wait_time: Time to wait for server to start (seconds).

        Returns:
            True if server started successfully, False otherwise.
        """
        if self.audio_player_process is not None:
            print("AudioSpeaker process is already running.")
            return True

        audio_speaker_script = Path(
            __file__).resolve().parent / "audio_speaker.py"

        try:
            self.audio_player_process = subprocess.Popen(
                [sys.executable, str(audio_speaker_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for server to start
            time.sleep(wait_time)

            # Check if process is still running
            if self.audio_player_process.poll() is not None:
                print("AudioSpeaker process failed to start.")
                return False

            # Verify server is responding
            try:
                response = requests.get(
                    f"{self.audio_player_url}/health", timeout=2)
                if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                    print(f"AudioSpeaker started on {self.audio_player_url}")
                    return True
            except requests.exceptions.RequestException:
                print("AudioSpeaker server is not responding.")
                return False

            return True
        except Exception as e:
            print(f"Failed to start AudioSpeaker: {e}")
            return False

    def stop(self) -> None:
        """Stop VoiceGenerator and AudioSpeaker subprocesses."""
        # Stop VoiceGenerator
        if self.voice_gen_process is not None:
            self.voice_gen_process.terminate()
            try:
                self.voice_gen_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.voice_gen_process.kill()
                self.voice_gen_process.wait()
            self.voice_gen_process = None
            self.process = None  # Backward compatibility
            print("VoiceGenerator stopped.")

        # Stop AudioSpeaker
        if self.audio_player_process is not None:
            self.audio_player_process.terminate()
            try:
                self.audio_player_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.audio_player_process.kill()
                self.audio_player_process.wait()
            self.audio_player_process = None
            print("AudioSpeaker stopped.")

    def generate_voice(self, text: Union[str, list[str]]) -> bool:
        """Send text to VoiceGenerator for voice generation.

        Args:
            text: Single text string or list of text strings.

        Returns:
            True if request was successful, False otherwise.
        """
        try:
            response = requests.post(
                f"{self.voice_gen_url}/generate",
                json={"text": text},
                timeout=10
            )

            if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                data = response.json()
                print(
                    f"Voice generation successful. Queue count: {data.get('count', 0)}")
                return True
            else:
                print(f"Voice generation failed: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Failed to communicate with VoiceGenerator: {e}")
            return False

    def get_audio(self) -> Optional[bytes]:
        """Get audio data from VoiceGenerator.

        Returns:
            WAV binary data if available, None otherwise.
        """
        try:
            response = requests.get(
                f"{self.voice_gen_url}/get_audio", timeout=10)

            if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                return response.content
            elif response.status_code == RESPONSE_STATUS_CODE_NOT_FOUND:
                print("Audio queue is empty.")
                return None
            else:
                print(f"Failed to get audio: {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Failed to communicate with VoiceGenerator: {e}")
            return None

    def play_audio(self, audio_bytes: bytes) -> bool:
        """Send audio data to AudioSpeaker for playback.

        This method blocks until playback is complete.

        Args:
            audio_bytes: WAV binary data to play.

        Returns:
            True if playback was successful, False otherwise.
        """
        try:
            response = requests.post(
                f"{self.audio_player_url}/play",
                data=audio_bytes,
                headers={'Content-Type': 'application/octet-stream'},
                timeout=30
            )

            if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                return True
            else:
                print(f"Failed to play audio: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Failed to communicate with AudioSpeaker: {e}")
            return False

    def get_and_play_audio(self) -> bool:
        """Get audio from VoiceGenerator and play it via AudioSpeaker.

        This method retrieves one audio from the queue, plays it, and then
        discards it. Blocks until playback is complete.

        Returns:
            True if audio was retrieved and played successfully, False otherwise.
        """
        audio_bytes = self.get_audio()
        if audio_bytes is None:
            return False

        return self.play_audio(audio_bytes)

    def play_all_queued_audio(self) -> int:
        """Play all audio currently in the VoiceGenerator queue.

        This method retrieves and plays all audio in the queue sequentially.
        Each audio is discarded after playback.

        Returns:
            Number of audio files successfully played.
        """
        played_count = 0

        while True:
            status = self.get_queue_status()
            if not status or status.get('is_empty', True):
                break

            if self.get_and_play_audio():
                played_count += 1
            else:
                break

        return played_count

    def get_queue_status(self) -> dict:
        """Get current queue status from VoiceGenerator.

        Returns:
            Dictionary with 'count' and 'is_empty' keys, or empty dict on error.
        """
        try:
            response = requests.get(
                f"{self.voice_gen_url}/queue_status", timeout=5)

            if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                return response.json()
            else:
                print(f"Failed to get queue status: {response.text}")
                return {}
        except requests.exceptions.RequestException as e:
            print(f"Failed to communicate with VoiceGenerator: {e}")
            return {}

    def clear_queue(self) -> bool:
        """Clear all queues in VoiceGenerator.

        Returns:
            True if successful, False otherwise.
        """
        try:
            response = requests.post(f"{self.voice_gen_url}/clear", timeout=5)

            if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                print("Queue cleared successfully.")
                return True
            else:
                print(f"Failed to clear queue: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Failed to communicate with VoiceGenerator: {e}")
            return False

    def get_audio_player_status(self) -> dict:
        """Get current status of AudioSpeaker.

        Returns:
            Dictionary with 'is_playing' key, or empty dict on error.
        """
        try:
            response = requests.get(
                f"{self.audio_player_url}/status", timeout=5)

            if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                return response.json()
            else:
                print(f"Failed to get audio player status: {response.text}")
                return {}
        except requests.exceptions.RequestException as e:
            print(f"Failed to communicate with AudioSpeaker: {e}")
            return {}

    def is_running(self) -> bool:
        """Check if VoiceGenerator process is running.

        Returns:
            True if running, False otherwise.
        """
        if self.voice_gen_process is None:
            return False

        # Check if process is still alive
        return self.voice_gen_process.poll() is None

    def is_audio_player_running(self) -> bool:
        """Check if AudioSpeaker process is running.

        Returns:
            True if running, False otherwise.
        """
        if self.audio_player_process is None:
            return False

        # Check if process is still alive
        return self.audio_player_process.poll() is None

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
