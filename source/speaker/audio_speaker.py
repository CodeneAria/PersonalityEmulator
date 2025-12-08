"""Audio playback module using simpleaudio."""
from __future__ import annotations

import io
import wave
import os
from pathlib import Path
from typing import Optional

import simpleaudio as sa


class AudioSpeaker:
    """Class for playing audio bytes using simpleaudio.

    This class handles audio playback from binary data (audio_bytes),
    attempting to play in memory and falling back to file saving if playback fails.
    """

    def __init__(self, fallback_dir: Optional[str | Path] = None):
        """Initialize AudioSpeaker.

        Args:
            fallback_dir: Directory to save audio files if playback fails.
                         If None, uses current directory.
        """
        self.fallback_dir = Path(fallback_dir) if fallback_dir else Path(".")
        self.fallback_dir.mkdir(parents=True, exist_ok=True)

    def play(self, audio_bytes: bytes, fallback_filename: Optional[str] = None) -> bool:
        """Play audio from binary data.

        Attempts to play audio in memory using simpleaudio.
        If playback fails, saves the audio to a file in the fallback directory.

        Args:
            audio_bytes: WAV audio data as bytes.
            fallback_filename: Filename to use if saving to file (without extension).
                              If None, uses "audio_output".

        Returns:
            True if audio was played successfully, False if saved to file.
        """
        try:
            bio = io.BytesIO(audio_bytes)
            with wave.open(bio, 'rb') as wav_read:
                wave_obj = sa.WaveObject.from_wave_read(wav_read)
                play_obj = wave_obj.play()
                play_obj.wait_done()
            return True
        except Exception as e:
            # Fallback: save to file
            filename = fallback_filename or "audio_output"
            out_path = self.fallback_dir / f"{filename}.wav"
            print(
                f"Failed to play audio: {e}\nSaving to file instead: {out_path}")

            with open(out_path, mode='wb') as f:
                f.write(audio_bytes)
            return False

    def play_multiple(
        self,
        audio_bytes_list: list[bytes],
        fallback_prefix: Optional[str] = None
    ) -> list[bool]:
        """Play multiple audio files sequentially.

        Args:
            audio_bytes_list: List of WAV audio data as bytes.
            fallback_prefix: Prefix for fallback filenames.
                           Files will be named as "{prefix}_{index:03d}.wav".
                           If None, uses "audio".

        Returns:
            List of booleans indicating success (True) or fallback (False) for each audio.
        """
        prefix = fallback_prefix or "audio"
        results = []

        for i, audio_bytes in enumerate(audio_bytes_list):
            fallback_name = f"{prefix}_{i:03d}"
            success = self.play(audio_bytes, fallback_filename=fallback_name)
            results.append(success)

        return results
