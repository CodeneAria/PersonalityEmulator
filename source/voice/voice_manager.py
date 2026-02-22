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
import httpx

sys.path.append(str(Path(__file__).resolve().parents[2]))

from configuration.communcation_settings import (
    VOICE_GENERATOR_PORT,
    AUDIO_PLAYER_PORT,
    SPEECH_RECOGNIZER_PORT,
    HOSTNAME,
    RESPONSE_STATUS_CODE_SUCCESS,
    RESPONSE_STATUS_CODE_NOT_FOUND,
    RESPONSE_STATUS_CODE_ERROR,
    USE_YUKKURI,
    YUKKURI_SPEAK_URL,
    YUKKURI_SPEAK_STOP_URL,
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
        audio_player_port: int = AUDIO_PLAYER_PORT,
        speech_recognizer_port: int = SPEECH_RECOGNIZER_PORT,
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
        self.speech_recognizer_process: Optional[subprocess.Popen] = None
        self.speech_recognizer_port: int = speech_recognizer_port
        self.speech_recognizer_url: str = f"http://{host}:{speech_recognizer_port}"

        # For backward compatibility
        self.base_url = self.voice_gen_url
        self.port = voice_gen_port
        self.process = self.voice_gen_process

        # Async processing
        self.text_queue: queue.Queue = queue.Queue()
        self.worker_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.clear_event = threading.Event()
        self.clear_before_count = 0  # Number of items in queue when clear was requested

        # Voice output stop flag tracking
        self._prev_voice_output_stop_flag: bool = False

    def start(self, wait_time: float = 5.0, start_audio_player: bool = True, start_speech_recognizer: bool = True) -> bool:
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

        # Start SpeechRecognizer if requested
        if start_speech_recognizer:
            speech_rec_success = self._start_speech_recognizer(wait_time)
            if not speech_rec_success:
                self.stop()
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
            return True

        path = Path.cwd() / "source" / "voice" / \
            "speaker" / "voice_generator.py"
        if not path.is_file():
            raise FileNotFoundError(
                f"VoiceGenerator script not found at {path}")
        voice_generator_script = path

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
                print(
                    f"[VoiceManager] VoiceGenerator process exited with code {self.voice_gen_process.returncode}")
                # Try to get stderr/stdout
                try:
                    stdout, stderr = self.voice_gen_process.communicate(
                        timeout=1)
                    if stderr:
                        print(
                            f"[VoiceManager] VoiceGenerator stderr: {stderr}")
                    if stdout:
                        print(
                            f"[VoiceManager] VoiceGenerator stdout: {stdout}")
                except Exception:
                    pass
                return False

            # Verify server is responding with retries
            print(f"[VoiceManager] Checking if VoiceGenerator is responding...")
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    response = requests.get(
                        f"{self.voice_gen_url}/queue_status", timeout=2)
                    if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                        self.process = self.voice_gen_process  # Backward compatibility
                        print(f"[VoiceManager] VoiceGenerator is responding")
                        return True
                    else:
                        print(
                            f"[VoiceManager] VoiceGenerator returned unexpected status code: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        print(
                            f"[VoiceManager] VoiceGenerator not ready yet, retrying... ({attempt + 1}/{max_retries})")
                        time.sleep(1)
                    else:
                        print(
                            f"[VoiceManager] VoiceGenerator is not responding after {max_retries} attempts: {e}")
                        return False

            return False
        except Exception as e:
            print(f"[VoiceManager] Failed to start VoiceGenerator: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _start_audio_player(self, wait_time: float = 2.0) -> bool:
        """Start AudioPlayer subprocess.

        Args:
            wait_time: Time to wait for server to start (seconds).

        Returns:
            True if server started successfully, False otherwise.
        """
        if self.audio_player_process is not None:
            return True

        path = Path.cwd() / "source" / "voice" / \
            "speaker" / "audio_player.py"
        if not path.is_file():
            raise FileNotFoundError(
                f"AudioPlayer script not found at {path}")
        audio_speaker_script = path

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
                print(
                    f"[VoiceManager] AudioPlayer process exited with code {self.audio_player_process.returncode}")
                try:
                    stdout, stderr = self.audio_player_process.communicate(
                        timeout=1)
                    if stderr:
                        print(f"[VoiceManager] AudioPlayer stderr: {stderr}")
                    if stdout:
                        print(f"[VoiceManager] AudioPlayer stdout: {stdout}")
                except Exception:
                    pass
                return False

            # Verify server is responding with retries
            print(f"[VoiceManager] Checking if AudioPlayer is responding...")
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    response = requests.get(
                        f"{self.audio_player_url}/health", timeout=2)
                    if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                        print(f"[VoiceManager] AudioPlayer is responding")
                        return True
                    else:
                        print(
                            f"[VoiceManager] AudioPlayer returned unexpected status code: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        print(
                            f"[VoiceManager] AudioPlayer not ready yet, retrying... ({attempt + 1}/{max_retries})")
                        time.sleep(1)
                    else:
                        print(
                            f"[VoiceManager] AudioPlayer is not responding after {max_retries} attempts: {e}")
                        return False

            return False
        except Exception as e:
            print(f"[VoiceManager] Failed to start AudioPlayer: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _start_speech_recognizer(self, wait_time: float = 2.0) -> bool:
        """Start SpeechRecognizer subprocess.

        Args:
            wait_time: Time to wait for server to start (seconds).

        Returns:
            True if started and responding, False otherwise.
        """
        print(f"[VoiceManager] Starting SpeechRecognizer...")
        if self.speech_recognizer_process is not None:
            return True

        path = Path.cwd() / "source" / "voice" / "listener" / "speech_recognizer.py"
        if not path.is_file():
            raise FileNotFoundError(
                f"SpeechRecognizer script not found at {path}")
        recognizer_script = path

        try:
            self.speech_recognizer_process = subprocess.Popen(
                [sys.executable, str(recognizer_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            print(
                f"[VoiceManager] Waiting for SpeechRecognizer to start (PID: {self.speech_recognizer_process.pid})...")

            # Retry loop to check for HTTP endpoint readiness
            max_retries = 5
            for attempt in range(max_retries):
                time.sleep(1)

                # Check process still running
                if self.speech_recognizer_process.poll() is not None:
                    print(
                        f"[VoiceManager] SpeechRecognizer process exited with code {self.speech_recognizer_process.returncode}")
                    try:
                        stdout, stderr = self.speech_recognizer_process.communicate(
                            timeout=1)
                        if stderr:
                            print(
                                f"[VoiceManager] SpeechRecognizer stderr: {stderr}")
                        if stdout:
                            print(
                                f"[VoiceManager] SpeechRecognizer stdout: {stdout}")
                    except Exception:
                        pass
                    return False

                # Check if HTTP endpoint is responding
                try:
                    response = requests.get(
                        f"{self.speech_recognizer_url}/health", timeout=2)
                    if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                        print(
                            f"[VoiceManager] SpeechRecognizer is responding on {self.speech_recognizer_url}")
                        return True
                    else:
                        print(
                            f"[VoiceManager] SpeechRecognizer returned unexpected status code: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        print(
                            f"[VoiceManager] SpeechRecognizer not ready yet, retrying... ({attempt + 1}/{max_retries})")
                    else:
                        print(
                            f"[VoiceManager] SpeechRecognizer HTTP not available after {max_retries} attempts: {e}")

            # If we exhausted retries, report failure
            print(
                f"[VoiceManager] Failed to confirm SpeechRecognizer HTTP server is up")
            return False

        except Exception as e:
            print(f"[VoiceManager] Failed to start SpeechRecognizer: {e}")
            import traceback
            traceback.print_exc()
            return False

    def is_speech_recognizer_running(self) -> bool:
        """Check if SpeechRecognizer process is running.

        Returns:
            True if running, False otherwise.
        """
        if self.speech_recognizer_process is None:
            return False
        return self.speech_recognizer_process.poll() is None

    def set_voice_input_active(self, active: bool) -> bool:
        """Set the voice input active state on SpeechRecognizer.

        Args:
            active: True to enable voice recognition, False to disable.

        Returns:
            True if successful, False otherwise.
        """
        if self.speech_recognizer_url is None:
            return False
        try:
            response = requests.post(
                f"{self.speech_recognizer_url}/voice_input_active",
                json={"active": active},
                timeout=3
            )
            return response.status_code == RESPONSE_STATUS_CODE_SUCCESS
        except requests.exceptions.RequestException as e:
            print(f"[VoiceManager] Failed to set voice input active: {e}")
            return False

    def get_recognized_sentence(self) -> Optional[str]:
        """Get the oldest recognized sentence from SpeechRecognizer.

        Returns:
            The recognized sentence, or None if queue is empty.
        """
        if self.speech_recognizer_url is None:
            return None
        try:
            response = requests.get(
                f"{self.speech_recognizer_url}/get_sentence",
                timeout=3
            )
            if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                data = response.json()
                return data.get("text")
            return None
        except requests.exceptions.RequestException:
            return None

    def get_all_recognized_sentences(self) -> Optional[str]:
        """Get all recognized sentences from SpeechRecognizer and clear the queue.

        Returns:
            Combined sentence string, or None if error occurred.
        """
        if self.speech_recognizer_url is None:
            return None
        try:
            response = requests.get(
                f"{self.speech_recognizer_url}/get_all_sentences",
                timeout=3
            )
            if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                data = response.json()
                text = data.get("text", "")
                return text if text else None
            return None
        except requests.exceptions.RequestException:
            return None

    def get_user_input_sentence(self) -> Optional[str]:
        """Retrieve the latest recognized sentence from SpeechRecognizer.
           This method first tries to get the sentence via HTTP from the SpeechRecognizer.
           If that fails (e.g., no HTTP server exposed), it falls back to checking
           a local SpeechRecognizer instance if one was attached.

            Returns:
            The oldest recognized sentence, or None if not available.
        """
        # If recognizer exposes an HTTP API, prefer that
        if self.speech_recognizer_url is not None:
            try:
                resp = requests.get(
                    f"{self.speech_recognizer_url}/latest", timeout=3)
                if resp.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                    try:
                        data = resp.json()
                        # Accept {'text': '...'} or raw string
                        if isinstance(data, dict):
                            return data.get("text")
                        return str(data)
                    except ValueError:
                        return resp.text or None
                return None
            except requests.exceptions.RequestException:
                return None

        # Best-effort: if a local SpeechRecognizer instance was attached, use it
        local = getattr(self, "_local_speech_recognizer", None)
        if local is not None:
            try:
                return local.get_oldest_sentence()
            except Exception:
                return None

        return None

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

        # Stop AudioPlayer
        if self.audio_player_process is not None:
            self.audio_player_process.terminate()
            try:
                self.audio_player_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.audio_player_process.kill()
                self.audio_player_process.wait()
            self.audio_player_process = None

        # Stop SpeechRecognizer
        if self.speech_recognizer_process is not None:
            try:
                self.speech_recognizer_process.terminate()
                try:
                    self.speech_recognizer_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.speech_recognizer_process.kill()
                    self.speech_recognizer_process.wait()
            except Exception:
                pass
            finally:
                self.speech_recognizer_process = None

    def _worker_loop(self) -> None:
        """Worker thread loop for async voice generation and playback."""
        while not self.stop_event.is_set():
            try:
                # Check clear event before getting from queue
                if self.clear_event.is_set():
                    # Use the count recorded when clear was requested
                    items_to_clear = self.clear_before_count

                    # Clear only the items that existed when clear was requested
                    cleared_count = 0
                    for _ in range(items_to_clear):
                        try:
                            self.text_queue.get_nowait()
                            cleared_count += 1
                        except queue.Empty:
                            break

                    remaining = self.text_queue.qsize()
                    # Clear remote queues
                    self.clear_queue()
                    self.clear_event.clear()
                    self.clear_before_count = 0
                    continue

                # Get text from queue with timeout (check clear event frequently)
                try:
                    text = self.text_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                # Generate voice
                if not self._generate_voice_sync(text):
                    continue

                # Check clear event before playing
                if self.clear_event.is_set():
                    # Use the count recorded when clear was requested
                    items_to_clear = self.clear_before_count

                    # Clear only the items that existed when clear was requested
                    cleared_count = 0
                    for _ in range(items_to_clear):
                        try:
                            self.text_queue.get_nowait()
                            cleared_count += 1
                        except queue.Empty:
                            break

                    remaining = self.text_queue.qsize()

                    # Clear remote queues
                    self.clear_queue()
                    self.clear_event.clear()
                    self.clear_before_count = 0
                    continue

                # Play audio
                result = self._play_audio_sync()

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
                data = response.json()
                return True
            else:
                return False
        except requests.exceptions.RequestException as e:
            print(f"Failed to communicate with VoiceGenerator: {e}")
            return False

    def stop_audio_playback(self) -> bool:
        try:
            response = requests.post(
                f"{self.audio_player_url}/stop", timeout=2)
            return response.status_code == RESPONSE_STATUS_CODE_SUCCESS
        except:
            return False

    def handle_voice_output_stop_flag(self, current_stop_flag: bool) -> None:
        """Handle voice output stop flag changes.

        When flag changes from False to True, clears voice queues and stops audio playback.

        Args:
            current_stop_flag: Current voice output stop flag state.
        """
        if current_stop_flag and not self._prev_voice_output_stop_flag:
            # Flag changed from False to True - stop everything
            print(
                "[VoiceManager] Voice output stop requested - clearing queues and stopping playback")

            try:
                self.clear_queue()
            except Exception as e:
                print(f"[VoiceManager] Failed to clear queue: {e}")

            if USE_YUKKURI:
                httpx.post(YUKKURI_SPEAK_STOP_URL, timeout=5.0)
            else:
                try:
                    self.stop_audio_playback()
                except Exception as e:
                    print(f"[VoiceManager] Failed to stop audio playback: {e}")

        # Update previous state
        self._prev_voice_output_stop_flag = current_stop_flag

    def _play_audio_sync(self) -> bool:
        """Get audio and play it synchronously.

        Returns:
            True if audio was retrieved and played successfully, False otherwise.
        """
        if self.stop_event.is_set() or self.clear_event.is_set():
            return False

        audio_bytes = self.get_audio()
        if audio_bytes is None:
            return False

        play_thread = threading.Thread(
            target=self.play_audio,
            args=(audio_bytes,),
            daemon=True
        )
        play_thread.start()

        while play_thread.is_alive():
            if self.stop_event.is_set() or self.clear_event.is_set():
                self.stop_audio_playback()
                return False
            time.sleep(0.05)

        return True

    def generate_voice(self, text: Union[str, list[str]]) -> bool:
        """Queue text for async voice generation and playback.
        Args:
            text: Single text string or list of text strings to generate voice for.
        """
        if USE_YUKKURI:
            httpx.post(YUKKURI_SPEAK_URL, json={
                "text": text}, timeout=10.0)
        else:
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
                return None
            else:
                return None
        except requests.exceptions.RequestException as e:
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
                return False
        except requests.exceptions.RequestException as e:
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
                return {}
        except requests.exceptions.RequestException as e:
            print(f"Failed to communicate with VoiceGenerator: {e}")
            return {}

    def clear_queue(self) -> bool:
        """Clear all queues in VoiceGenerator.

        Returns:
            True if successful, False otherwise.
        """
        self.text_queue.queue.clear()

        try:
            response = requests.post(f"{self.voice_gen_url}/clear", timeout=5)

            if response.status_code == RESPONSE_STATUS_CODE_SUCCESS:
                return True
            else:
                return False
        except requests.exceptions.RequestException as e:
            print(f"Failed to communicate with VoiceGenerator: {e}")
            return False

    def request_clear(self) -> None:
        """Request to clear all queues (async).

        This sets a flag that will cause the worker thread to clear all queues
        on its next iteration.
        """
        current_size = self.text_queue.qsize()
        self.clear_before_count = current_size
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
