"""Integration test to verify VOICEVOX TTS synthesis and playback.

This test will:
- check that the VOICEVOX server is reachable at the configured host/port and
  skip the test if not reachable (so CI won't fail when VOICEVOX isn't running)
- instantiate `VoicevoxCommunicator` (optionally importing the user dict)
- call `synthesize` with example Japanese text and assert non-empty WAV bytes
- save the WAV to a temporary file for manual inspection
- if `simpleaudio` is available, attempt to play the generated WAV (non-fatal)

Run with:
    pytest tests/test_voicevox_integration.py -q
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import socket
from pathlib import Path
import pytest
import subprocess
import atexit
import time

from source.speaker.voicevox.voicevox_communicator import VoicevoxCommunicator
from config.communcation_settings import HOSTNAME, VOICEVOX_PORT

# start voicevox in background (do not block); register cleanup at exit
subprocess_command = f"/opt/voicevox_engine/linux-nvidia/run --host {HOSTNAME} --port {VOICEVOX_PORT}"
proc = None
try:
    proc = subprocess.Popen(
        subprocess_command,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
except Exception as e:
    print(f"Error starting VOICEVOX: {e}", file=sys.stderr)
else:
    def _cleanup_voicevox():
        global proc
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        except Exception:
            pass

    atexit.register(_cleanup_voicevox)

# wait until VOICEVOX is reachable before running tests
time.sleep(5)


def _is_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def test_voicevox_synthesize_and_play(tmp_path: Path):
    """Try to synthesize text via VOICEVOX and optionally play it.

    The test is skipped if VOICEVOX is not reachable at the configured host/port.
    """
    if not _is_port_open(HOSTNAME, VOICEVOX_PORT):
        pytest.skip(f"VOICEVOX not reachable at {HOSTNAME}:{VOICEVOX_PORT}")

    # Prefer the project's user dictionary if present
    user_dict_path = Path("personality/hakurei_reimu/word_dictionary.json")
    if user_dict_path.exists():
        user_dict_arg = str(user_dict_path)
    else:
        user_dict_arg = None

    vc = VoicevoxCommunicator(
        user_dict_path=user_dict_arg) if user_dict_arg else VoicevoxCommunicator()

    sample_text = "こんにちは、私は博麗霊夢です。そのくらい、あなたがやりなさいよ。"

    audio_bytes = vc.synthesize(sample_text)

    assert audio_bytes is not None and len(
        audio_bytes) > 0, "VOICEVOX synthesize returned no audio"

    tmp_path = Path("./temp_voicevox_test_output")
    if not tmp_path.exists():
        tmp_path.mkdir(parents=True, exist_ok=True)
    out_file = tmp_path / "voicevox_test.wav"
    out_file.write_bytes(audio_bytes)

    # Attempt to play the audio if simpleaudio is available. Failure to play should not fail the test.
    try:
        import io
        import wave
        import simpleaudio as sa

        with wave.open(io.BytesIO(audio_bytes), 'rb') as wav_read:
            wave_obj = sa.WaveObject.from_wave_read(wav_read)
            play_obj = wave_obj.play()
            play_obj.wait_done()
    except Exception:
        # Non-fatal: playback is optional in test environments
        pass

    # Save a copy under project output for manual inspection if desired
    try:
        output_dir = Path("output_audio")
        output_dir.mkdir(exist_ok=True)
        (output_dir / "voicevox_test.wav").write_bytes(audio_bytes)
    except Exception:
        pass


if __name__ == "__main__":
    test_voicevox_synthesize_and_play(Path("./temp_test_output"))
