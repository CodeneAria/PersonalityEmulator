"""Speech recognition module using Faster Whisper and Silero VAD."""
from __future__ import annotations

import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

import threading
from typing import Optional
import numpy as np
import pyaudio
import torch
from faster_whisper import WhisperModel


class SpeechRecognizer:
    """Class for recognizing speech from microphone input.

    This class uses Silero VAD for voice activity detection and
    Faster Whisper for speech-to-text conversion.
    """

    def __init__(
        self,
        model_id: str = "RoachLin/kotoba-whisper-v2.2-faster",
        device: Optional[str] = None,
        compute_type: str = "float16",
        rate: int = 16000,
        chunk: int = 512,
        channels: int = 1,
        vad_threshold: float = 0.5,
        min_audio_length: int = 10
    ):
        """Initialize SpeechRecognizer.

        Args:
            model_id: Faster Whisper model ID.
            device: Device to use ("cuda" or "cpu"). If None, auto-detects.
            compute_type: Compute type for inference.
            rate: Audio sample rate (Hz).
            chunk: Audio chunk size.
            channels: Number of audio channels.
            vad_threshold: Voice activity detection threshold (0.0-1.0).
            min_audio_length: Minimum audio buffer length to process.
        """
        self.model_id = model_id
        self.device = device if device is not None else (
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        if self.device == "cuda":
            self.compute_type = compute_type
        else:
            self.compute_type = "int8"

        self.rate = rate
        self.chunk = chunk
        self.channels = channels
        self.vad_threshold = vad_threshold
        self.min_audio_length = min_audio_length

        # Audio format settings
        self.format = pyaudio.paInt16

        # Model instances
        self.vad_model = None
        self.whisper_model = None
        self.audio = None
        self.stream = None

        # Recognition state
        self.sentence_queue: list[str] = []
        self.is_running = False
        self.recognition_thread: Optional[threading.Thread] = None

    def start_speach_to_text_model(self) -> None:
        """Load and initialize Silero VAD and Faster Whisper models."""
        print("[SpeechRecognizer] Loading models...")

        # Load Silero VAD
        self.vad_model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad'
        )
        print("[SpeechRecognizer] Silero VAD loaded")

        # Load Faster Whisper
        self.whisper_model = WhisperModel(
            self.model_id,
            device=self.device,
            compute_type=self.compute_type
        )
        print(f"[SpeechRecognizer] Faster Whisper loaded on {self.device}")

        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()

        # Display available input devices
        print("[SpeechRecognizer] Available input devices:")
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"  Index {i}: {info['name']}")

        # Display default input device
        try:
            default_device_info = self.audio.get_default_input_device_info()
            print("[SpeechRecognizer] Using microphone:")
            print(f"  Index: {default_device_info['index']}")
            print(f"  Name:  {default_device_info['name']}")
            print(f"  Channels: {default_device_info['maxInputChannels']}")
        except IOError:
            print("[SpeechRecognizer] WARNING: No default input device found")

    def recognize(self) -> None:
        """Start continuous speech recognition in the current thread.

        This method runs in a loop, capturing audio from the microphone,
        detecting voice activity, and transcribing speech to text.
        Call stop() to terminate the recognition loop.
        """
        if self.vad_model is None or self.whisper_model is None or self.audio is None:
            raise RuntimeError(
                "Models not loaded. Call start_speach_to_text_model() first."
            )

        # Open audio stream
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )

        print("[SpeechRecognizer] Listening... (Speak now!)")

        audio_buffer = []
        is_speaking = False
        self.is_running = True

        try:
            while self.is_running:
                # Read audio chunk
                audio_chunk = self.stream.read(
                    self.chunk,
                    exception_on_overflow=False
                )
                audio_int16 = np.frombuffer(audio_chunk, np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0

                # Detect voice activity
                speech_prob = self.vad_model(
                    torch.from_numpy(audio_float32),
                    self.rate
                ).item()

                if speech_prob > self.vad_threshold:
                    if not is_speaking:
                        is_speaking = True
                    audio_buffer.append(audio_int16)
                elif is_speaking:
                    # Voice stopped - transcribe accumulated audio
                    is_speaking = False

                    if len(audio_buffer) > self.min_audio_length:
                        # Convert buffer to float32 for Whisper
                        audio_data = np.concatenate(audio_buffer).astype(
                            np.float32
                        ) / 32768.0

                        # Transcribe speech
                        segments, info = self.whisper_model.transcribe(
                            audio_data,
                            language="ja",
                            beam_size=10,
                            best_of=5,
                            vad_filter=False,
                            without_timestamps=True,
                            repetition_penalty=1.1,
                            condition_on_previous_text=True,
                        )

                        # Add recognized text to queue
                        for segment in segments:
                            text = segment.text.strip()
                            if text:
                                self.sentence_queue.append(text)
                                print(
                                    f"[SpeechRecognizer] [{info.language}] Detected: {text}")

                    audio_buffer = []

        except Exception as e:
            print(f"[SpeechRecognizer] Error during recognition: {e}")
        finally:
            self._cleanup()

    def start_recognition_thread(self) -> None:
        """Start speech recognition in a background thread."""
        if self.recognition_thread is not None and self.recognition_thread.is_alive():
            print("[SpeechRecognizer] Recognition already running")
            return

        self.recognition_thread = threading.Thread(
            target=self.recognize,
            daemon=True
        )
        self.recognition_thread.start()
        print("[SpeechRecognizer] Recognition thread started")

    def stop(self) -> None:
        """Stop the recognition loop."""
        print("[SpeechRecognizer] Stopping recognition...")
        self.is_running = False

        if self.recognition_thread is not None:
            self.recognition_thread.join(timeout=2.0)
            self.recognition_thread = None

    def _cleanup(self) -> None:
        """Clean up audio resources."""
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            print("[SpeechRecognizer] Audio stream closed")

    def get_latest_sentence(self) -> Optional[str]:
        """Get the latest recognized sentence from the queue.

        Returns:
            The latest recognized sentence, or None if queue is empty.
        """
        if self.sentence_queue:
            return self.sentence_queue.pop(0)
        return None

    def get_sentence_queue(self) -> list[str]:
        """Get a copy of the sentence queue.

        Returns:
            List of recognized sentences.
        """
        return self.sentence_queue.copy()

    def clear_queue(self) -> None:
        """Clear the sentence queue."""
        self.sentence_queue.clear()

    def is_empty(self) -> bool:
        """Check if the sentence queue is empty.

        Returns:
            True if queue is empty, False otherwise.
        """
        return len(self.sentence_queue) == 0

    def __len__(self) -> int:
        """Return the number of sentences in the queue.

        Returns:
            Number of sentences in the queue.
        """
        return len(self.sentence_queue)

    def __del__(self):
        """Cleanup when object is destroyed."""
        self.stop()
        if self.audio is not None:
            self.audio.terminate()
