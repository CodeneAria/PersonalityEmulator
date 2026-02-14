from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from enum import Enum
from typing import Set


class MessageSource(Enum):
    CHAT = "chat"
    VOICE = "voice"
    SYSTEM = "system"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


# Set of allowed source string values
ALLOWED_SOURCES: Set[str] = {s.value for s in MessageSource}


def normalize_source(value) -> str:
    """Normalize a source value to a valid lower-case string.

    If the provided value is not one of the allowed sources, defaults to
    `MessageSource.SYSTEM.value`.
    """
    if isinstance(value, MessageSource):
        return value.value
    if value is None:
        return MessageSource.SYSTEM.value
    v = str(value).lower()
    return v if v in ALLOWED_SOURCES else MessageSource.SYSTEM.value
