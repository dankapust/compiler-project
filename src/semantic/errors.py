from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticError:
    category: str
    message: str
    line: int
    column: int
    file_name: str = ""
    context: str = ""
    expected: str | None = None
    found: str | None = None
    suggestion: str | None = None
    source_line: str | None = None

    def format(self) -> str:
        lines: list[str] = []
        loc = f"{self.file_name}:{self.line}:{self.column}" if self.file_name else f"{self.line}:{self.column}"
        type_map: dict[str, str] = {
            "undeclared_identifier": "необъявленный идентификатор",
            "duplicate_declaration": "дубликат объявления",
            "type_mismatch": "несовпадение типов",
            "argument_count_mismatch": "ошибка количества аргументов",
            "argument_type_mismatch": "ошибка типов аргументов",
            "invalid_return_type": "недопустимый return",
            "invalid_condition_type": "недопустимое условие",
            "use_before_declaration": "использование до инициализации",
            "invalid_assignment_target": "недопустимая цель присваивания",
            "scope_error": "ошибка области видимости",
        }
        type_ru = type_map.get(self.category, self.category)
        lines.append(f"семантическая ошибка ({type_ru}): {self.message}")
        lines.append(f"  --> {loc}")
        if self.context:
            lines.append(f"   | {self.context}")
        if self.expected is not None or self.found is not None:
            if self.expected is not None:
                lines.append(f"   = ожидалось: {self.expected}")
            if self.found is not None:
                lines.append(f"   = получено: {self.found}")
        if self.suggestion:
            lines.append(f"   = примечание: {self.suggestion}")

        if self.source_line is not None:
            lines.append("")
            lines.append("   |")
            lines.append(f"{self.line} | {self.source_line}")
            caret_col = max(0, self.column - 1)
            lines.append(f"   | {' ' * caret_col}^")
        return "\n".join(lines) + "\n"
