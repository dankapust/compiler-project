from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScanError:
    message: str
    line: int
    column: int

    def format(self) -> str:
        return f"{self.line}:{self.column} {self.message}"


