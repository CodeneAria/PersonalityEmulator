from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from configuration.person_settings import (
    WORLD_INFO_PATH,
    PERSON_INFO_PATH,
    SCENE_SETTINGS_PATH,
)


class PromptGenerator:
    """Generate a pre-prompt for the LLM by concatenating three markdown files.

    The files (in order) are:
    - WORLD_INFO_PATH
    - PERSON_INFO_PATH
    - SCENE_SETTINGS_PATH

    The generator reads each file and joins them with blank lines.
    """

    def __init__(
        self,
        world_path: str | None = None,
        person_path: str | None = None,
        scene_path: str | None = None,
    ) -> None:
        self.world_path = world_path or WORLD_INFO_PATH
        self.person_path = person_path or PERSON_INFO_PATH
        self.scene_path = scene_path or SCENE_SETTINGS_PATH

    def _read_file(self, path: str) -> str:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")

        return p.read_text(encoding="utf-8")

    def generate_pre_prompt(self) -> str:
        """Return the concatenated contents of the three prompt files.

        The order is world -> person -> scene. Sections are separated by
        two newlines.
        """
        parts: list[str] = []

        parts.append("[世界観設定]")
        parts.append(self._read_file(self.world_path))

        parts.append("[人物設定]")
        parts.append(self._read_file(self.person_path))

        parts.append("[シーン設定]")
        parts.append(self._read_file(self.scene_path))

        return "\n\n".join(part for part in parts if part)
