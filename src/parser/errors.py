from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParseError:
    message: str
    line: int
    column: int
    suggestion: str | None = None

    def format(self) -> str:
        base = f"{self.line}:{self.column} {self.message}"
        if self.suggestion:
            base += f" [{self.suggestion}]"
        return base


@dataclass
class ErrorMetrics:
    reported_count: int = 0
    recovered_count: int = 0
    cascade_prevented_count: int = 0

    def format_summary(self) -> str:
        return (
            f"errors reported: {self.reported_count}, "
            f"recovery points: {self.recovered_count}, "
            f"cascade prevented: {self.cascade_prevented_count}"
        )
