"""Voice manager module for controlling VoiceGenerator subprocess."""
from __future__ import annotations

import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

import subprocess
import time
import threading
import queue
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
            host: Hostname for the VoiceGenerator and AudioPlayer servers.
            voice_gen_port: Port number for the VoiceGenerator server.
            audio_player_port: Port number for the AudioPlayer server.
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

        # Async processing
        self.text_queue: queue.Queue = queue.Queue()
        self.worker_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.clear_event = threading.Event()

    def start(self, wait_time: float = 2.0, start_audio_player: bool = True) -> bool:
        """Start VoiceGenerator and optionally AudioPlayer subprocesses.

        Args:
            wait_time: Time to wait for servers to start (seconds).
            start_audio_player: Whether to start AudioPlayer subprocess.

        Returns:
            True if all servers started successfully, False otherwise.
        """
        # Start VoiceGenerator
        voice_gen_success = self._start_voice_generator(wait_time)
        if not voice_gen_success:
            return False

        # Start AudioPlayer if requested
        if start_audio_player:
            audio_player_success = self._start_audio_player(wait_time)
            if not audio_player_success:
                self.stop()  # Stop VoiceGenerator if AudioPlayer fails
                return False

        # Start worker thread
        self.stop_event.clear()
        self.clear_event.clear()
        self.worker_thread = threading.Thread(
            target=self._worker_loop, daemon=True)
        self.worker_thread.start()

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
        """Start AudioPlayer subprocess.

        Args:
            wait_time: Time to wait for server to start (seconds).

        Returns:
            True if server started successfully, False otherwise.
        """
        if self.audio_player_process is not None:
            print("AudioPlayer process is already running.")
            return True

        audio_speaker_script = Path(
            __file__).resolve().parent / "audio_player.py"

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
                print("AudioPlayer process failed to start.")
                return False

            # Verify server is responding
            try:
                response = requests.get(
                    f"{self.audio_player_url}/health", timeout=2)
                if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                    print(f"AudioPlayer started on {self.audio_player_url}")
                    return True
            except requests.exceptions.RequestException:
                print("AudioPlayer server is not responding.")
                return False

            return True
        except Exception as e:
            print(f"Failed to start AudioPlayer: {e}")
            return False

    def stop(self) -> None:
        """Stop VoiceGenerator and AudioPlayer subprocesses."""
        # Stop worker thread
        self.stop_event.set()
        if self.worker_thread is not None and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
            self.worker_thread = None

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

        # Stop AudioPlayer
        if self.audio_player_process is not None:
            self.audio_player_process.terminate()
            try:
                self.audio_player_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.audio_player_process.kill()
                self.audio_player_process.wait()
            self.audio_player_process = None
            print("AudioPlayer stopped.")

    def _worker_loop(self) -> None:
        """Worker thread loop for async voice generation and playback."""
        while not self.stop_event.is_set():
            try:
                # Check if clear event is set
                if self.clear_event.is_set():
                    # Clear all queues
                    while not self.text_queue.empty():
                        try:
                            self.text_queue.get_nowait()
                        except queue.Empty:
                            break
                    self.clear_queue()
                    self.clear_event.clear()
                    continue

                # Get text from queue with timeout
                try:
                    text = self.text_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                # Generate voice
                if not self._generate_voice_sync(text):
                    continue

                # Play audio
                self._play_audio_sync()

            except Exception as e:
                print(f"[VoiceManager Worker] Error: {e}")

    def _generate_voice_sync(self, text: Union[str, list[str]]) -> bool:
        """Send text to VoiceGenerator for voice generation (synchronous).

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
                return True
            else:
                print(f"Voice generation failed: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Failed to communicate with VoiceGenerator: {e}")
            return False

    def _play_audio_sync(self) -> bool:
        """Get audio and play it synchronously.

        Returns:
            True if audio was retrieved and played successfully, False otherwise.
        """
        audio_bytes = self.get_audio()
        if audio_bytes is None:
            return False

        return self.play_audio(audio_bytes)

    def generate_voice(self, text: Union[str, list[str]]) -> bool:
        """Queue text for async voice generation and playback.

        Args:
            text: Single text string or list of text strings.

        Returns:
            Always returns True (queuing is non-blocking).
        """
        self.text_queue.put(text)
        return True

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
        """Send audio data to AudioPlayer for playback.

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
            print(f"Failed to communicate with AudioPlayer: {e}")
            return False

    def get_and_play_audio(self) -> bool:
        """Get audio from VoiceGenerator and play it via AudioPlayer.

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
                return True
            else:
                print(f"Failed to clear queue: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Failed to communicate with VoiceGenerator: {e}")
            return False

    def request_clear(self) -> None:
        """Request to clear all queues (async).

        This sets a flag that will cause the worker thread to clear all queues
        on its next iteration.
        """
        self.clear_event.set()

    def get_audio_player_status(self) -> dict:
        """Get current status of AudioPlayer.

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
            print(f"Failed to communicate with AudioPlayer: {e}")
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
        """Check if AudioPlayer process is running.

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
