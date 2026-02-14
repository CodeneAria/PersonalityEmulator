"""
Personality Model Runner module.

This module provides the PersonalityModelRunner class that manages the lifecycle
of a PersonalityCoreManager, captures its text output, and converts the generated
text into speech using a VoiceManager.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import time
from datetime import datetime
from typing import Optional

from source.core.personality_core_manager import PersonalityCoreManager
from source.voice.voice_manager import VoiceManager
from source.messenger.message_manager import MessageManager

from config.person_settings import (
    WHISPER_TRANSCRIBE_PREFIX,
    PERSONALITY_CORE_SIGNATURE,
)


class PersonalityModelRunner:
    """Manages PersonalityCoreManager AI model and voice synthesis integration.

    This class handles the lifecycle of PersonalityCoreManager, captures its output,
    and converts generated text into speech using VoiceManager.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        """Initialize PersonalityModelRunner.

        Args:
            model_path: Optional path to the GGUF model file.
            system_prompt: Optional system prompt for the conversation.
        """
        # Initialize PersonalityCoreManager with optional parameters
        core_kwargs = {}
        if model_path is not None:
            core_kwargs["model_path"] = model_path
        if system_prompt is not None:
            core_kwargs["system_prompt"] = system_prompt

        self.core_manager = PersonalityCoreManager(**core_kwargs)
        self.vm = VoiceManager()
        self.message_manager = MessageManager()

        self.input_text_history: list[str] = []
        self.input_time_history: list[str] = []
        self.output_text_history: list[str] = []
        self.output_time_history: list[str] = []
        self.processed_message_count: int = 0

        # Voice input state tracking
        self._prev_voice_input_active: bool = False

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

    def store_input_with_timestamp(self, text: str) -> None:
        """Store input text with current timestamp.

        Args:
            text: Text input to store.
        """
        if text and text.strip():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.input_time_history.append(timestamp)
            self.input_text_history.append(text.strip())

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

        if self.input_time_history:
            value = self.input_time_history[-1]
        else:
            value = ""
        self.output_time_history.append(value)

    def _on_sentence_complete(self, sentence: str) -> None:
        """Callback when a sentence is complete.

        Args:
            sentence: The completed sentence text.
        """
        if not sentence or not sentence.strip():
            return

        # Store in history
        self.store_output_history([sentence])

        # Generate voice for the sentence
        try:
            self.vm.generate_voice(sentence)
        except Exception as e:
            print(f"[Runner] VoiceManager error: {e}", file=sys.stderr)

    def _process_user_input(self, text: str, sender: str = "User") -> None:
        """Process user input text and generate LLM response.

        Args:
            text: User input text.
            sender: Message sender name.
        """
        if not text or not text.strip():
            return

        # Store user input
        self.store_input_with_timestamp(text)

        # Display user's voice input in chat first (before assistant response)
        if sender == "Voice":
            self.message_manager.send_message("User (Voice)", text)

        # Clear voice queues for new response
        try:
            self.vm.request_clear()
        except Exception as e:
            print(f"[Runner] Failed to clear queues: {e}", file=sys.stderr)

        # Send initial empty message to get message ID
        message_id = self.message_manager.send_message("Assistant", "")

        # Generate streaming response
        response_text = ""
        try:
            for chunk in self.core_manager.generate_response_stream(text):
                response_text += chunk

                # Update message with accumulated text
                if message_id is not None:
                    self.message_manager.update_message(
                        message_id, response_text)
        except Exception as e:
            error_msg = f"Error: {e}"
            if message_id is not None:
                self.message_manager.update_message(message_id, error_msg)
            else:
                self.message_manager.send_message("System", error_msg)
            print(f"\n[Runner] Generation error: {e}", file=sys.stderr)

    def run(self) -> int:
        """Start and run the personality model with voice synthesis.

        Returns:
            Exit code (0 for success, non-zero for error).
        """
        # Start PersonalityCoreManager
        if not self.core_manager.start():
            print("Failed to start PersonalityCoreManager", file=sys.stderr)
            return 2

        # Set up sentence completion callback for voice synthesis
        self.core_manager.on_sentence_complete = self._on_sentence_complete

        # Start VoiceManager
        try:
            self.vm.start()
        except Exception as e:
            print(
                f"[Runner] Failed to start VoiceManager: {e}", file=sys.stderr)

        # Start MessageManager
        if not self.message_manager.start():
            print("Failed to start MessageManager", file=sys.stderr)
            return 3

        # Print URL for browser access
        chat_url = f"http://{self.message_manager.host}:{self.message_manager.port}"
        print(f"[Runner] Chat window started at: {chat_url}")
        print("[Runner] Waiting for messages... (Press Ctrl-C to quit)")

        try:
            while self.core_manager.is_running:
                # Poll voice input state from MessageManager
                current_voice_active = self.message_manager.update_voice_input_state()

                # Handle voice input state changes
                if current_voice_active != self._prev_voice_input_active:
                    # Update SpeechRecognizer via VoiceManager
                    try:
                        self.vm.set_voice_input_active(current_voice_active)
                        if current_voice_active:
                            print("[Runner] Voice input activated")
                        else:
                            print("[Runner] Voice input deactivated")

                    except Exception as e:
                        print(
                            f"[Runner] Failed to update voice input state: {e}", file=sys.stderr)
                    self._prev_voice_input_active = current_voice_active

                if not current_voice_active:
                    combined_text = self.vm.get_all_recognized_sentences()
                    if combined_text and combined_text.strip():
                        print(
                            f"[Runner] Voice input received (combined): {combined_text}")
                        self._process_user_input(
                            combined_text, sender="Voice")

                # Poll for new messages from browser
                messages = self.message_manager.get_messages()

                # Process only new messages
                if len(messages) > self.processed_message_count:
                    for i in range(self.processed_message_count, len(messages)):
                        msg = messages[i]
                        sender = msg.get("sender", "")
                        text = msg.get("text", "")

                        # Skip system messages, assistant messages, or voice input display messages
                        if not text or sender.lower() in ("assistant", "user (voice)"):
                            continue

                        # Check for exit command
                        if text.strip().lower() in ("exit", "quit"):
                            self.message_manager.send_message(
                                "System", "Shutting down...")
                            self.core_manager.is_running = False
                            break

                        # Process user input
                        self._process_user_input(text, sender=sender)

                    self.processed_message_count = len(messages)

                # Sleep briefly to avoid busy waiting
                time.sleep(0.2)

        except KeyboardInterrupt:
            print("\n[Runner] Interrupted.")
        finally:
            try:
                self.core_manager.stop()
            except Exception:
                pass
            try:
                self.vm.stop()
            except Exception:
                pass
            try:
                self.message_manager.stop()
            except Exception:
                pass

        return 0

    def run_single_response(self, user_input: str) -> str:
        """Generate a single response without interactive loop.

        Args:
            user_input: User's input text.

        Returns:
            The assistant's response text.
        """
        if self.core_manager.llm is None:
            if not self.core_manager.start():
                return ""

        # Set up sentence completion callback for voice synthesis
        self.core_manager.on_sentence_complete = self._on_sentence_complete

        # Store user input
        self.store_input_with_timestamp(user_input)

        # Generate response
        response = ""
        for chunk in self.core_manager.generate_response_stream(user_input):
            response += chunk

        return response
