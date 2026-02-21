"""
Debug script to test the voice pipeline step by step.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import time
import requests

from source.voice.voice_manager import VoiceManager
from configuration.communcation_settings import (
    HOSTNAME,
    VOICEVOX_PORT,
    VOICE_GENERATOR_PORT,
    AUDIO_PLAYER_PORT,
)


def check_voicevox_server():
    """Check if VOICEVOX server is running."""
    print("=" * 60)
    print("1. Checking VOICEVOX server...")
    try:
        response = requests.get(
            f"http://{HOSTNAME}:{VOICEVOX_PORT}/version", timeout=2)
        if response.status_code == 200:
            print(f"✓ VOICEVOX server is running on port {VOICEVOX_PORT}")
            print(f"  Version: {response.json()}")
            return True
        else:
            print(f"✗ VOICEVOX server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ VOICEVOX server is not reachable: {e}")
        return False


def test_voice_manager_start():
    """Test VoiceManager startup."""
    print("=" * 60)
    print("2. Testing VoiceManager startup...")

    vm = VoiceManager()

    print(f"  Starting VoiceManager (host={HOSTNAME})...")
    try:
        success = vm.start()

        if success:
            print("✓ VoiceManager started successfully")
        else:
            print("✗ VoiceManager failed to start")

            # Try to get more details
            if vm.voice_gen_process is not None and vm.voice_gen_process.poll() is not None:
                print("  VoiceGenerator process exited")
                if vm.voice_gen_process.stderr:
                    stderr_output = vm.voice_gen_process.stderr.read()
                    if stderr_output:
                        print(f"  stderr: {stderr_output}")
                if vm.voice_gen_process.stdout:
                    stdout_output = vm.voice_gen_process.stdout.read()
                    if stdout_output:
                        print(f"  stdout: {stdout_output}")

            return None
    except Exception as e:
        print(f"✗ Exception during VoiceManager start: {e}")
        import traceback
        traceback.print_exc()
        return None

    # Check if subprocesses are running
    print("\n  Checking subprocesses:")

    # Check VoiceGenerator
    if vm.voice_gen_process is not None:
        if vm.voice_gen_process.poll() is None:
            print(
                f"  ✓ VoiceGenerator process is running (PID: {vm.voice_gen_process.pid})")
        else:
            print(f"  ✗ VoiceGenerator process has exited")
            # Print stderr if available
            if vm.voice_gen_process.stderr:
                stderr = vm.voice_gen_process.stderr.read()
                if stderr:
                    print(f"    stderr: {stderr}")
    else:
        print("  ✗ VoiceGenerator process was not started")

    # Check AudioPlayer
    if vm.audio_player_process is not None:
        if vm.audio_player_process.poll() is None:
            print(
                f"  ✓ AudioPlayer process is running (PID: {vm.audio_player_process.pid})")
        else:
            print(f"  ✗ AudioPlayer process has exited")
    else:
        print("  ✗ AudioPlayer process was not started")

    # Check SpeechRecognizer
    if vm.speech_recognizer_process is not None:
        if vm.speech_recognizer_process.poll() is None:
            print(
                f"  ✓ SpeechRecognizer process is running (PID: {vm.speech_recognizer_process.pid})")
        else:
            print(f"  ✗ SpeechRecognizer process has exited")
    else:
        print("  ✗ SpeechRecognizer process was not started")

    return vm


def test_voice_generator_endpoint(vm: VoiceManager):
    """Test VoiceGenerator HTTP endpoint."""
    print("=" * 60)
    print("3. Testing VoiceGenerator HTTP endpoint...")

    try:
        response = requests.get(
            f"http://{HOSTNAME}:{VOICE_GENERATOR_PORT}/queue_status", timeout=2)
        if response.status_code == 200:
            print(f"✓ VoiceGenerator endpoint is responding")
            print(f"  Status: {response.json()}")
            return True
        else:
            print(
                f"✗ VoiceGenerator endpoint returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ VoiceGenerator endpoint is not reachable: {e}")
        return False


def test_audio_player_endpoint(vm: VoiceManager):
    """Test AudioPlayer HTTP endpoint."""
    print("=" * 60)
    print("4. Testing AudioPlayer HTTP endpoint...")

    try:
        response = requests.get(
            f"http://{HOSTNAME}:{AUDIO_PLAYER_PORT}/health", timeout=2)
        if response.status_code == 200:
            print(f"✓ AudioPlayer endpoint is responding")
            print(f"  Status: {response.json()}")
            return True
        else:
            print(
                f"✗ AudioPlayer endpoint returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ AudioPlayer endpoint is not reachable: {e}")
        return False


def test_voice_generation(vm: VoiceManager):
    """Test voice generation through VoiceManager."""
    print("=" * 60)
    print("5. Testing voice generation...")

    test_text = "こんにちは、私は博麗霊夢です。"
    print(f"  Generating voice for: '{test_text}'")

    # Queue text
    success = vm.generate_voice(test_text)
    if success:
        print("✓ Text queued successfully")
    else:
        print("✗ Failed to queue text")
        return False

    # Wait for processing
    print("  Waiting for voice generation and playback...")
    time.sleep(5)

    # Check queue status
    try:
        status = vm.get_queue_status()
        print(f"  Queue status: {status}")
        return True
    except Exception as e:
        print(f"✗ Failed to get queue status: {e}")
        return False


def main():
    print("Voice Pipeline Debug Tool")
    print("=" * 60)

    # Step 0: Test VoiceGenerator script directly
    print("=" * 60)
    print("0. Testing VoiceGenerator script directly...")
    from pathlib import Path
    import subprocess

    voice_gen_script = Path.cwd() / "source" / "voice" / \
        "speaker" / "voice_generator.py"
    if not voice_gen_script.exists():
        print(f"✗ VoiceGenerator script not found at {voice_gen_script}")
    else:
        print(f"✓ VoiceGenerator script found at {voice_gen_script}")
        print("  Attempting to run for 3 seconds...")
        try:
            proc = subprocess.Popen(
                [sys.executable, str(voice_gen_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            time.sleep(3)

            if proc.poll() is None:
                print("✓ VoiceGenerator process is running")
                proc.terminate()
                proc.wait(timeout=2)
            else:
                print(
                    f"✗ VoiceGenerator process exited with code {proc.returncode}")
                stdout, stderr = proc.communicate()
                if stdout:
                    print(f"  stdout: {stdout}")
                if stderr:
                    print(f"  stderr: {stderr}")
        except Exception as e:
            print(f"✗ Error running VoiceGenerator: {e}")
            import traceback
            traceback.print_exc()

    # Step 1: Check VOICEVOX
    voicevox_ok = check_voicevox_server()

    if not voicevox_ok:
        print("\n⚠️  VOICEVOX server is not running. Voice synthesis will fail.")
        print("Please start VOICEVOX server first.")
        return 1

    # Step 2: Start VoiceManager
    vm = test_voice_manager_start()

    if vm is None:
        print("\n✗ VoiceManager failed to start. Stopping.")
        return 2

    # Step 3: Test VoiceGenerator endpoint
    voice_gen_ok = test_voice_generator_endpoint(vm)

    # Step 4: Test AudioPlayer endpoint
    audio_player_ok = test_audio_player_endpoint(vm)

    # Step 5: Test voice generation
    if voice_gen_ok and audio_player_ok:
        test_voice_generation(vm)
    else:
        print("\n✗ Cannot test voice generation because endpoints are not responding")

    # Cleanup
    print("=" * 60)
    print("Cleaning up...")
    vm.stop()
    print("Done.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
