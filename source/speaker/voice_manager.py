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

    def __init__(self, host: str = HOSTNAME, port: int = VOICE_GENERATOR_PORT):
        """Initialize VoiceManager.

        Args:
            host: Hostname for the VoiceGenerator server.
            port: Port number for the VoiceGenerator server.
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.process: Optional[subprocess.Popen] = None

    def start(self, wait_time: float = 2.0) -> bool:
        """Start VoiceGenerator subprocess.

        Args:
            wait_time: Time to wait for server to start (seconds).

        Returns:
            True if server started successfully, False otherwise.
        """
        if self.process is not None:
            print("VoiceGenerator process is already running.")
            return True

        voice_generator_script = Path(
            __file__).resolve().parent / "voice_generator.py"

        try:
            self.process = subprocess.Popen(
                [sys.executable, str(voice_generator_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for server to start
            time.sleep(wait_time)

            # Check if process is still running
            if self.process.poll() is not None:
                print("VoiceGenerator process failed to start.")
                return False

            # Verify server is responding
            try:
                response = requests.get(
                    f"{self.base_url}/queue_status", timeout=2)
                if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                    print(f"VoiceGenerator started on {self.base_url}")
                    return True
            except requests.exceptions.RequestException:
                print("VoiceGenerator server is not responding.")
                return False

            return True
        except Exception as e:
            print(f"Failed to start VoiceGenerator: {e}")
            return False

    def stop(self) -> None:
        """Stop VoiceGenerator subprocess."""
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None
            print("VoiceGenerator stopped.")

    def generate_voice(self, text: Union[str, list[str]]) -> bool:
        """Send text to VoiceGenerator for voice generation.

        Args:
            text: Single text string or list of text strings.

        Returns:
            True if request was successful, False otherwise.
        """
        try:
            response = requests.post(
                f"{self.base_url}/generate",
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
            response = requests.get(f"{self.base_url}/get_audio", timeout=10)

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

    def get_queue_status(self) -> dict:
        """Get current queue status from VoiceGenerator.

        Returns:
            Dictionary with 'count' and 'is_empty' keys, or empty dict on error.
        """
        try:
            response = requests.get(f"{self.base_url}/queue_status", timeout=5)

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
            response = requests.post(f"{self.base_url}/clear", timeout=5)

            if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                print("Queue cleared successfully.")
                return True
            else:
                print(f"Failed to clear queue: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Failed to communicate with VoiceGenerator: {e}")
            return False

    def is_running(self) -> bool:
        """Check if VoiceGenerator process is running.

        Returns:
            True if running, False otherwise.
        """
        if self.process is None:
            return False

        # Check if process is still alive
        return self.process.poll() is None

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
