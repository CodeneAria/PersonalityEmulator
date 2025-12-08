"""Audio playback module using simpleaudio."""
import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from __future__ import annotations

import io
import wave
from typing import Optional

import simpleaudio as sa
from flask import Flask, request, jsonify

from config.communcation_settings import (
    AUDIO_PLAYER_PORT,
    RESPONSE_STATUS_CODE_SUCCESS,
    RESPONSE_STATUS_CODE_ERROR,
    HOSTNAME,
)


class AudioPlayer:
    """Class for playing audio bytes using simpleaudio.

    This class handles audio playback from binary data (audio_bytes),
    attempting to play in memory and falling back to file saving if playback fails.
    """

    def __init__(self, fallback_dir: Optional[str | Path] = None):
        """Initialize AudioPlayer.

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


# Flask app for HTTP server
app = Flask(__name__)
audio_speaker = AudioPlayer()
is_playing = False


@app.route('/play', methods=['POST'])
def play_audio():
    """Endpoint to play audio from binary data.

    Request:
        Binary WAV data in request body.

    Response JSON format:
        {"status": "success"} or {"status": "error", "message": "..."}
    """
    global is_playing

    if is_playing:
        return jsonify({
            "status": "error",
            "message": "Already playing audio"
        }), 400

    try:
        audio_bytes = request.data

        if not audio_bytes:
            return jsonify({
                "status": "error",
                "message": "No audio data provided"
            }), 400

        is_playing = True
        success = audio_speaker.play(audio_bytes)
        is_playing = False

        return jsonify({
            "status": "success",
            "played": success
        }), RESPONSE_STATUS_CODE_SUCCESS
    except Exception as e:
        is_playing = False
        return jsonify({
            "status": "error",
            "message": str(e)
        }), RESPONSE_STATUS_CODE_ERROR


@app.route('/status', methods=['GET'])
def get_status():
    """Endpoint to check if audio is currently playing.

    Response JSON format:
        {"is_playing": boolean}
    """
    return jsonify({
        "is_playing": is_playing
    }), RESPONSE_STATUS_CODE_SUCCESS


@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint for health check.

    Response JSON format:
        {"status": "ok"}
    """
    return jsonify({"status": "ok"}), RESPONSE_STATUS_CODE_SUCCESS


if __name__ == '__main__':
    app.run(host=HOSTNAME, port=AUDIO_PLAYER_PORT, debug=False)
