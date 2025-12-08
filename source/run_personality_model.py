"""Minimal runner for koboldcpp.

Behavior (simplified per user request):
- If `kobold_cpp/koboldcpp` does not exist, download the official release.
- Spawn `./koboldcpp` in the `kobold_cpp` directory and do not wait.
- Process output and manage voice generation.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from source.kobold_cpp.koboldcpp_manager import KoboldCppManager
from source.speaker.voice_manager import VoiceManager

KOBOLD_CPP_SIGNATURE = "[KoboldCpp]"


def main() -> int:
    # Initialize KoboldCpp manager
    kobold_manager = KoboldCppManager()

    # Start KoboldCpp process
    try:
        master_fd, slave_fd, koboldcpp_process = kobold_manager.start_koboldcpp()
    except Exception as e:
        print(f"Failed to start KoboldCpp: {e}", file=sys.stderr)
        return 2

    os.close(slave_fd)

    capture_state = False
    captured_text = ""
    previous_capture_state = False

    vm = VoiceManager()
    try:
        vm.start()
    except Exception as e:
        print(f"[Runner] Failed to start VoiceManager: {e}", file=sys.stderr)

    try:
        with os.fdopen(master_fd, mode='r', buffering=1) as r:
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
                    capture_state = False
                    captured_text = ""

                    # Clear queues when capture_state becomes False
                    if previous_capture_state and not capture_state:
                        try:
                            vm.request_clear()
                        except Exception as e:
                            print(
                                f"[Runner] Failed to clear queues: {e}", file=sys.stderr)

                elif line.startswith("Output:"):
                    capture_state = True

                previous_capture_state = capture_state

                if capture_state:
                    captured_text = line.removeprefix("Output:").strip()
                    if captured_text == "":
                        continue

                    texts = captured_text.split('。')
                    # Filter out empty strings
                    texts = [text for text in texts if text.strip() != '']

                    if not texts:
                        continue

                    try:
                        # Queue each sentence separately so the worker will
                        # generate and play them one-by-one.
                        for t in texts:
                            vm.generate_voice(t)
                    except Exception as e:
                        print(
                            f"[Runner] VoiceManager error: {e}", file=sys.stderr)

    finally:
        try:
            vm.stop()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
