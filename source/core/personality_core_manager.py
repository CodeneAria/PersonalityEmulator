"""
Personality Core Manager module.

This module provides the PersonalityCoreManager class that manages the Llama model
lifecycle, handles conversation history, and generates streaming text responses.
"""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from typing import Optional, Generator, Callable
import urllib.request
import shutil
import subprocess

from llama_cpp import Llama

from config.person_settings import (
    LLM_MODEL_PATH,
    LLM_MODEL_DOWNLOAD_PATH,
    LLM_N_CTX,
    LLM_N_THREADS,
    LLM_N_GPU_LAYERS,
    LLM_SYSTEM_PROMPT,
    PERSONALITY_CORE_SIGNATURE,
)


class PersonalityCoreManager:
    """Manager class for Llama-based personality model.

    This class handles the lifecycle of the Llama model, manages conversation
    history, and provides streaming text generation with sentence-based callbacks
    for voice synthesis integration.
    """

    def __init__(
        self,
        model_path: str = LLM_MODEL_PATH,
        n_ctx: int = LLM_N_CTX,
        n_threads: int = LLM_N_THREADS,
        n_gpu_layers: int = LLM_N_GPU_LAYERS,
        system_prompt: str = LLM_SYSTEM_PROMPT,
    ):
        """Initialize PersonalityCoreManager.

        Args:
            model_path: Path to the GGUF model file.
            n_ctx: Context window size.
            n_threads: Number of CPU threads to use.
            n_gpu_layers: Number of layers to offload to GPU (-1 for all).
            system_prompt: System prompt for the conversation.
        """
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.n_gpu_layers = n_gpu_layers
        self.system_prompt = system_prompt

        self.llm: Optional[Llama] = None
        self.messages: list[dict] = []
        self.is_running = False

        # Callback for sentence completion (for voice synthesis)
        self.on_sentence_complete: Optional[Callable[[str], None]] = None

    def start(self) -> bool:
        """Load and initialize the Llama model.

        Returns:
            True if model loaded successfully, False otherwise.
        """
        if self.llm is not None:
            print(f"{PERSONALITY_CORE_SIGNATURE} Model already loaded")
            return True

        # Ensure the model file exists locally; download if missing
        if not self._ensure_model_exists():
            download_command = f"curl -L -C - -o {self.model_path} {LLM_MODEL_DOWNLOAD_PATH}"
            print(
                f"{PERSONALITY_CORE_SIGNATURE} Model not found. Downloading using command: {download_command}")
            subprocess.run(download_command, shell=True, check=True)

        try:
            print(
                f"{PERSONALITY_CORE_SIGNATURE} Loading model from {self.model_path}...")
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=self.n_gpu_layers,
            )
            print(f"{PERSONALITY_CORE_SIGNATURE} Model loaded successfully")

            # Initialize conversation with system prompt
            self.messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            self.is_running = True
            return True

        except Exception as e:
            print(
                f"{PERSONALITY_CORE_SIGNATURE} Failed to load model: {e}", file=sys.stderr)
            return False

    def _ensure_model_exists(self) -> bool:
        """Ensure the model file exists locally; download if missing.

        Returns:
            True if the model file exists or was downloaded successfully, False otherwise.
        """
        model_file = Path(self.model_path)
        if model_file.exists():
            return True

        download_url = LLM_MODEL_DOWNLOAD_PATH
        try:
            model_file.parent.mkdir(parents=True, exist_ok=True)
            print(
                f"{PERSONALITY_CORE_SIGNATURE} Model not found at {self.model_path}, downloading from {download_url}...")
            with urllib.request.urlopen(download_url) as resp, open(model_file, "wb") as out_file:
                shutil.copyfileobj(resp, out_file)
            print(
                f"{PERSONALITY_CORE_SIGNATURE} Downloaded model to {self.model_path}")
            return True
        except Exception as e:
            print(
                f"{PERSONALITY_CORE_SIGNATURE} Failed to download model: {e}", file=sys.stderr)
            return False

    def stop(self) -> None:
        """Stop and cleanup the Llama model."""
        self.is_running = False
        if self.llm is not None:
            try:
                self.llm.close()
            except Exception:
                pass
            self.llm = None
            print(f"{PERSONALITY_CORE_SIGNATURE} Model closed")

    def clear_history(self) -> None:
        """Clear conversation history, keeping only the system prompt."""
        self.messages = [
            {"role": "system", "content": self.system_prompt}
        ]

    def add_user_message(self, text: str) -> None:
        """Add a user message to the conversation history.

        Args:
            text: User's input text.
        """
        if text and text.strip():
            self.messages.append({"role": "user", "content": text})

    def generate_response_stream(
        self,
        user_input: Optional[str] = None
    ) -> Generator[str, None, str]:
        """Generate a streaming response from the model.

        If user_input is provided, it will be added to the history first.
        Yields text chunks as they are generated and calls on_sentence_complete
        callback when a sentence boundary (。！？) is detected.

        Args:
            user_input: Optional user input to add before generating.

        Yields:
            Text chunks as they are generated.

        Returns:
            The complete assistant response text.
        """
        if self.llm is None:
            raise RuntimeError("Model not loaded. Call start() first.")

        if user_input:
            self.add_user_message(user_input)

        # Create streaming completion
        stream = self.llm.create_chat_completion(
            messages=self.messages,
            stream=True
        )

        assistant_text = ""
        sentence_buffer = ""

        for chunk in stream:
            if not self.is_running:
                break

            delta = chunk["choices"][0]["delta"]
            if "content" in delta:
                text_chunk = delta["content"]
                assistant_text += text_chunk
                sentence_buffer += text_chunk

                # Yield the chunk for immediate output
                yield text_chunk

                # Check for sentence boundaries and trigger callback
                self._process_sentence_buffer(sentence_buffer)
                # Update buffer to contain only incomplete sentence
                sentence_buffer = self._get_remaining_buffer(sentence_buffer)

        # Process any remaining text in buffer
        if sentence_buffer.strip() and self.on_sentence_complete:
            self.on_sentence_complete(sentence_buffer.strip())

        # Add complete response to history
        if assistant_text:
            self.messages.append(
                {"role": "assistant", "content": assistant_text})

        return assistant_text

    def _process_sentence_buffer(self, buffer: str) -> None:
        """Process buffer and call callback for complete sentences.

        Args:
            buffer: Current text buffer.
        """
        if not self.on_sentence_complete:
            return

        # Split by sentence-ending characters
        sentence_endings = ['。', '！', '？', '!', '?']
        sentences = []
        current = ""

        for char in buffer:
            current += char
            if char in sentence_endings:
                if current.strip():
                    sentences.append(current.strip())
                current = ""

        # Call callback for each complete sentence (except the last incomplete one)
        for sentence in sentences:
            self.on_sentence_complete(sentence)

    def _get_remaining_buffer(self, buffer: str) -> str:
        """Get the remaining incomplete sentence from buffer.

        Args:
            buffer: Current text buffer.

        Returns:
            Text after the last sentence boundary.
        """
        sentence_endings = ['。', '！', '？', '!', '?']

        last_end_pos = -1
        for i, char in enumerate(buffer):
            if char in sentence_endings:
                last_end_pos = i

        if last_end_pos >= 0:
            return buffer[last_end_pos + 1:]
        return buffer

    def generate_response(self, user_input: str) -> str:
        """Generate a complete response from the model (non-streaming).

        Args:
            user_input: User's input text.

        Returns:
            The complete assistant response text.
        """
        response = ""
        for chunk in self.generate_response_stream(user_input):
            response += chunk
        return response

    def get_messages(self) -> list[dict]:
        """Get a copy of the conversation history.

        Returns:
            List of message dictionaries.
        """
        return self.messages.copy()

    def set_system_prompt(self, prompt: str) -> None:
        """Set a new system prompt and reset conversation.

        Args:
            prompt: New system prompt.
        """
        self.system_prompt = prompt
        self.clear_history()

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
