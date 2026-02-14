"""Integration test to verify speech recognition functionality.

This test will:
- check that an audio input device is available and skip the test if not
- instantiate `SpeechRecognizer` and load models
- start recognition in a background thread for a short period
- allow the user to speak during that period
- verify that recognized sentences can be retrieved via get_oldest_sentence
- properly stop and clean up resources

Run with:
    pytest tests/test_speech_recognizer.py -q -s
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import time
import pytest
import pyaudio

from source.voice.listener.speech_recognizer import SpeechRecognizer

from config.person_settings import (
    WHISPER_MODEL_NAME,
)


def _has_input_device() -> bool:
    """Check if any audio input device is available."""
    try:
        audio = pyaudio.PyAudio()
        device_count = audio.get_device_count()
        has_input = False

        for i in range(device_count):
            info = audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                has_input = True
                break

        audio.terminate()
        return has_input
    except Exception:
        return False


def test_speech_recognizer_initialization():
    """Test that SpeechRecognizer can be instantiated without errors."""
    recognizer = SpeechRecognizer()

    assert recognizer is not None
    assert recognizer.model_id == WHISPER_MODEL_NAME
    assert recognizer.rate == 16000
    assert recognizer.chunk == 512
    assert recognizer.channels == 1
    assert recognizer.vad_threshold == 0.5
    assert recognizer.sentence_queue == []
    assert recognizer.is_running == False


def test_speech_recognizer_model_loading():
    """Test that models can be loaded without errors."""
    if not _has_input_device():
        pytest.skip("No audio input device available")

    recognizer = SpeechRecognizer()

    # Load models
    recognizer.start_speach_to_text_model()

    # Verify models are loaded
    assert recognizer.vad_model is not None, "VAD model not loaded"
    assert recognizer.whisper_model is not None, "Whisper model not loaded"
    assert recognizer.audio is not None, "PyAudio not initialized"

    # Clean up
    if recognizer.audio is not None:
        recognizer.audio.terminate()


def test_speech_recognizer_recognition_workflow():
    """Test speech recognition workflow with actual microphone input.

    This test starts recognition, waits for user to speak, then retrieves
    the recognized text. This is an interactive test.
    """
    if not _has_input_device():
        pytest.skip("No audio input device available")

    recognizer = SpeechRecognizer()

    # Load models
    print("\n[Test] Loading speech recognition models...")
    recognizer.start_speach_to_text_model()

    assert recognizer.vad_model is not None
    assert recognizer.whisper_model is not None

    # Start recognition in background thread
    print("[Test] Starting recognition thread...")
    recognizer.start_recognition_thread()

    # Wait for recognition to start
    time.sleep(1.0)
    assert recognizer.is_running == True

    recognizer.set_voice_input_active(True)

    # Allow time for user to speak (10 seconds)
    print("\n" + "=" * 60)
    print("[Test] Please speak into your microphone now!")
    print("[Test] You have 10 seconds to say something in Japanese...")
    print("=" * 60 + "\n")

    for i in range(10, 0, -1):
        print(f"[Test] {i} seconds remaining...", end="\r")
        time.sleep(1.0)

    print("\n[Test] Recognition period ended.")

    # Disable voice input
    print("[Test] Disabling voice input...")
    recognizer.set_voice_input_active(False)

    # Stop recognition
    print("[Test] Stopping recognition...")
    recognizer.stop()

    # Wait for thread to finish
    time.sleep(1.0)
    assert recognizer.is_running == False

    # Check if any sentences were recognized
    print(f"[Test] Sentences in queue: {len(recognizer)}")

    if len(recognizer) > 0:
        print("[Test] Retrieved sentences:")
        while not recognizer.is_empty():
            sentence = recognizer.get_oldest_sentence()
            assert sentence is not None
            assert isinstance(sentence, str)
            assert len(sentence) > 0
            print(f"  - {sentence}")
    else:
        print("[Test] No speech detected. This is OK if you didn't speak.")

    # Verify queue operations work
    recognizer.sentence_queue.append("test sentence")
    assert len(recognizer) == 1
    assert not recognizer.is_empty()

    sentence = recognizer.get_oldest_sentence()
    assert sentence == "test sentence"
    assert recognizer.is_empty()

    # Clean up
    if recognizer.audio is not None:
        recognizer.audio.terminate()

    print("[Test] Speech recognizer test completed successfully!")


def test_speech_recognizer_queue_operations():
    """Test queue management operations."""
    recognizer = SpeechRecognizer()

    # Initially empty
    assert recognizer.is_empty() == True
    assert len(recognizer) == 0
    assert recognizer.get_oldest_sentence() is None

    # Add items manually
    recognizer.sentence_queue.append("first sentence")
    recognizer.sentence_queue.append("second sentence")
    recognizer.sentence_queue.append("third sentence")

    assert recognizer.is_empty() == False
    assert len(recognizer) == 3

    # Get sentences in FIFO order
    assert recognizer.get_oldest_sentence() == "first sentence"
    assert len(recognizer) == 2

    assert recognizer.get_oldest_sentence() == "second sentence"
    assert len(recognizer) == 1

    # Get queue copy
    queue_copy = recognizer.get_sentence_queue()
    assert queue_copy == ["third sentence"]
    assert len(recognizer) == 1  # Original queue unchanged

    # Clear queue
    recognizer.clear_queue()
    assert recognizer.is_empty() == True
    assert len(recognizer) == 0


def test_speech_recognizer_stop_without_start():
    """Test that stop() can be called safely without starting recognition."""
    recognizer = SpeechRecognizer()

    # Should not raise an error
    recognizer.stop()

    assert recognizer.is_running == False
    assert recognizer.recognition_thread is None


if __name__ == "__main__":
    # Run tests interactively
    print("Running Speech Recognizer Tests\n")

    print("Test 1: Initialization")
    test_speech_recognizer_initialization()
    print("✓ Passed\n")

    print("Test 2: Model Loading")
    try:
        test_speech_recognizer_model_loading()
        print("✓ Passed\n")
    except Exception as e:
        print(f"✗ Skipped or Failed: {e}\n")

    print("Test 3: Queue Operations")
    test_speech_recognizer_queue_operations()
    print("✓ Passed\n")

    print("Test 4: Stop Without Start")
    test_speech_recognizer_stop_without_start()
    print("✓ Passed\n")

    print("Test 5: Recognition Workflow (Interactive)")
    try:
        test_speech_recognizer_recognition_workflow()
        print("✓ Passed\n")
    except Exception as e:
        print(f"✗ Skipped or Failed: {e}\n")

    print("\nAll tests completed!")
