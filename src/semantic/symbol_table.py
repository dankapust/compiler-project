from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from semantic.type_system import Type, type_size_bytes


class SymbolKind(Enum):
    VARIABLE = auto()
    FUNCTION = auto()
    PARAMETER = auto()
    STRUCT = auto()


@dataclass
class SymbolInfo:
    name: str
    type: Type
    kind: SymbolKind
    line: int
    column: int
    return_type: Type | None = None
    param_types: tuple[Type, ...] | None = None
    param_names: tuple[str, ...] | None = None
    struct_fields: dict[str, Type] | None = None
    stack_offset: int | None = None
    size_bytes: int | None = None
    alignment: int | None = None
    initialized: bool = False


@dataclass
class ScopeFrame:
    kind: str
    symbols: dict[str, SymbolInfo] = field(default_factory=dict)


class SymbolTable:
    def __init__(self) -> None:
        self._frames: list[ScopeFrame] = [ScopeFrame("global")]
        self.nesting_depth: int = 0

    def reset(self) -> None:
        self._frames = [ScopeFrame("global")]
        self.nesting_depth = 0

    def enter_scope(self, kind: str) -> None:
        self._frames.append(ScopeFrame(kind))
        self.nesting_depth = len(self._frames) - 1

    def exit_scope(self) -> None:
        if len(self._frames) <= 1:
            raise RuntimeError("нельзя выйти из глобальной области видимости")
        self._frames.pop()
        self.nesting_depth = len(self._frames) - 1

    def current_scope_kind(self) -> str:
        return self._frames[-1].kind

    def scope_depth(self) -> int:
        return len(self._frames)

    def insert(self, name: str, info: SymbolInfo) -> bool:
        cur = self._frames[-1].symbols
        if name in cur:
            return False
        if info.size_bytes is None and info.kind in (SymbolKind.VARIABLE, SymbolKind.PARAMETER):
            info.size_bytes = type_size_bytes(info.type)
        cur[name] = info
        return True

    def lookup_local(self, name: str) -> SymbolInfo | None:
        return self._frames[-1].symbols.get(name)

    def lookup(self, name: str) -> SymbolInfo | None:
        for frame in reversed(self._frames):
            if name in frame.symbols:
                return frame.symbols[name]
        return None

    def dump_scopes(self) -> list[tuple[str, dict[str, SymbolInfo]]]:
        return [(f.kind, dict(f.symbols)) for f in self._frames]
