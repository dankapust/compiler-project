from __future__ import annotations


class LabelManager:
    """Centralized label factory for codegen helpers."""

    def __init__(self) -> None:
        self._counter = 0

    def fresh(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"
