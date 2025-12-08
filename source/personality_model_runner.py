"""
Personality Model Runner module.

This module provides the PersonalityModelRunner class that manages the lifecycle
of a KoboldCpp process, captures its text output, and converts the generated text
into speech using a VoiceManager.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from source.kobold_cpp.koboldcpp_manager import KoboldCppManager
from source.speaker.voice_manager import VoiceManager

KOBOLD_CPP_SIGNATURE = "[KoboldCpp]"
WHISPER_TRANSCRIBE_PREFIX = "Whisper Transcribe Output:"


class PersonalityModelRunner:
    """Manages KoboldCpp AI model and voice synthesis integration.

    This class handles the lifecycle of KoboldCpp process, captures its output,
    and converts generated text into speech using VoiceManager.
    """

    def __init__(self):
        """Initialize PersonalityModelRunner."""
        self.kobold_manager = KoboldCppManager()
        self.vm = VoiceManager()
        self.master_fd = None
        self.slave_fd = None
        self.koboldcpp_process = None

        self.capture_state = False
        self.captured_text = ""
        self.previous_capture_state = False

        self.input_text_history = []
        self.input_time_history = []
        self.output_text_history = []

    def store_whisper_input_history(
            self,
            input_text: str
    ) -> None:
        """Store input text and timestamp in history.

        Args:
            input_text: Text input to store (format: "[HH:MM:SS] Whisper Transcribe Output: text").
        """
        import re

        # Extract timestamp and text using regex
        # Pattern: [HH:MM:SS] Whisper Transcribe Output: actual_text
        match = re.match(r'\[(\d{2}:\d{2}:\d{2})\]\s*' +
                         re.escape(WHISPER_TRANSCRIBE_PREFIX) + r'\s*(.*)', input_text)

        if match:
            timestamp = match.group(1)
            text_content = match.group(2).strip()

            if text_content:
                self.input_time_history.append(timestamp)
                self.input_text_history.append(text_content)

    def store_output_history(
            self,
            output_texts: list[str]
    ) -> None:
        """Store output text in history.

        Args:
            output_texts: List of text outputs to store.
        """
        # Remove newlines and add '。' if not already ending with it
        processed_texts = [text.replace('\n', '').replace('\r', '') if text.endswith(
            '。') else text.replace('\n', '').replace('\r', '') + '。' for text in output_texts]
        combined_text = ''.join(processed_texts)
        self.output_text_history.append(combined_text)

    def run(self) -> int:
        """Start and run the personality model with voice synthesis.

        Returns:
            Exit code (0 for success, non-zero for error).
        """
        # Start KoboldCpp process
        try:
            self.master_fd, self.slave_fd, self.koboldcpp_process = self.kobold_manager.start_koboldcpp()
        except Exception as e:
            print(f"Failed to start KoboldCpp: {e}", file=sys.stderr)
            return 2

        os.close(self.slave_fd)

        self.capture_state = False
        self.captured_text = ""
        self.previous_capture_state = False

        try:
            self.vm.start()
        except Exception as e:
            print(
                f"[Runner] Failed to start VoiceManager: {e}", file=sys.stderr)

        try:
            with os.fdopen(self.master_fd, mode='r', buffering=1) as r:
                for line in r:
                    # Writing to stdout may fail (e.g. debugger/pipe closed, I/O errors).
                    # Protect the runner from crashing on such errors and exit loop
                    # gracefully if writes fail.
                    try:
                        print(f"{KOBOLD_CPP_SIGNATURE} {line}", end="")
                    except OSError as e:
                        # Log to stderr and stop trying to write to stdout.
                        try:
                            print(
                                f"[Runner] stdout write failed: {e}", file=sys.stderr)
                        except Exception:
                            # If even stderr is not available, silently stop.
                            pass
                        break

                    if line.startswith("Input:"):
                        self.capture_state = False
                        self.captured_text = ""

                        # Clear queues when capture_state becomes False
                        if self.previous_capture_state and not self.capture_state:
                            try:
                                self.vm.request_clear()
                            except Exception as e:
                                print(
                                    f"[Runner] Failed to clear queues: {e}", file=sys.stderr)

                    elif line.startswith("Output:"):
                        self.capture_state = True

                    if WHISPER_TRANSCRIBE_PREFIX in line:
                        self.store_whisper_input_history(line)

                    self.previous_capture_state = self.capture_state

                    if self.capture_state:
                        self.captured_text = line.removeprefix(
                            "Output:").strip()
                        if self.captured_text == "":
                            continue

                        texts = self.captured_text.split('。')
                        # Filter out empty strings
                        texts = [text for text in texts if text.strip() != '']

                        if not texts:
                            continue

                        self.store_output_history(texts)

                        try:
                            # Queue each sentence separately so the worker will
                            # generate and play them one-by-one.
                            for t in texts:
                                self.vm.generate_voice(t)
                        except Exception as e:
                            print(
                                f"[Runner] VoiceManager error: {e}", file=sys.stderr)

        finally:
            try:
                self.vm.stop()
            except Exception:
                pass

        return 0
