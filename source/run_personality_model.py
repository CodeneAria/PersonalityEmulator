"""
Main runner script for the Personality Emulator that integrates
 KoboldCpp AI model with voice synthesis.

This module provides a simple entry point that creates and runs
a PersonalityModelRunner instance.

"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from source.personality_model_runner import PersonalityModelRunner


def main() -> int:
    """Entry point for the personality model runner.

    Returns:
        Exit code from PersonalityModelRunner.
    """
    runner = PersonalityModelRunner()

    return runner.run()


if __name__ == "__main__":
    raise SystemExit(main())
