"""Preprocessor: comment removal and simple macros (Sprint 1 Stretch Goal)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PreprocessorError:
    """Preprocessor error with line/column."""

    message: str
    line: int
    column: int

    def format(self) -> str:
        return f"{self.line}:{self.column} {self.message}"


def _is_identifier_start(c: str) -> bool:
    return ("a" <= c <= "z") or ("A" <= c <= "Z") or c == "_"


def _is_identifier_part(c: str) -> bool:
    return _is_identifier_start(c) or c.isdigit()


class Preprocessor:
    """
    Preprocessor for comment removal and simple macros.

    PRE-1: Removes // and /* */ comments, preserves line numbering.
    PRE-2: Supports #define NAME value, #ifdef, #ifndef, #endif.
    PRE-3: Preprocessor(source), process(), define(), undefine().
    PRE-4: Comments in strings preserved, unterminated comments error, no macro recursion.
    """

    def __init__(self, source: str):
        self._source = source
        self._macros: dict[str, str] = {}
        self.errors: list[PreprocessorError] = []

    def define(self, name: str, value: str) -> None:
        """Define a macro (programmatic API)."""
        self._macros[name] = value

    def undefine(self, name: str) -> None:
        """Undefine a macro (programmatic API)."""
        self._macros.pop(name, None)

    def process(self) -> str:
        """Return cleaned source with comments removed and macros expanded."""
        self.errors.clear()
        result = self._process_directives_and_expand()
        result = self._remove_comments(result)
        return result

    def _process_directives_and_expand(self) -> str:
        """Process directives and expand macros per-line. Return source with conditionals resolved."""
        lines = self._source.split("\n")
        output_lines: list[str] = []
        i = 0
        skip_depth = 0  # How many nested #ifdef we're skipping

        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()
            line_num = i + 1

            if stripped.startswith("#"):
                # Directive line
                parts = stripped[1:].split(None, 2)
                directive = parts[0].lower() if parts else ""

                if directive == "define":
                    if skip_depth == 0 and len(parts) >= 2:
                        name = parts[1]
                        raw_value = parts[2] if len(parts) >= 3 else ""
                        # Strip trailing // comment from value
                        if "//" in raw_value:
                            raw_value = raw_value.split("//")[0]
                        value = raw_value.strip()
                        if not self._valid_macro_name(name):
                            self.errors.append(
                                PreprocessorError(f"invalid macro name: {name}", line_num, 1)
                            )
                        else:
                            self._macros[name] = value
                    output_lines.append("")  # Keep line count, replace directive with empty line
                elif directive == "undef":
                    if skip_depth == 0 and len(parts) >= 2:
                        self._macros.pop(parts[1], None)
                    output_lines.append("")
                elif directive == "ifdef":
                    if len(parts) >= 2:
                        cond = parts[1] in self._macros
                        if not cond:
                            skip_depth += 1
                    output_lines.append("")
                elif directive == "ifndef":
                    if len(parts) >= 2:
                        cond = parts[1] not in self._macros
                        if not cond:
                            skip_depth += 1
                    output_lines.append("")
                elif directive == "endif":
                    if skip_depth > 0:
                        skip_depth -= 1
                    output_lines.append("")
                else:
                    output_lines.append("")  # Unknown directive, keep line
                i += 1
                continue

            if skip_depth > 0:
                output_lines.append("")  # Skipped line, preserve line count
            else:
                # Expand macros in this line (macros current at this point)
                expanded = self._expand_macros_inner(line, set())
                output_lines.append(expanded)
            i += 1

        if skip_depth > 0:
            self.errors.append(
                PreprocessorError("unmatched #ifdef/#ifndef without #endif", len(lines), 1)
            )

        return "\n".join(output_lines)

    def _valid_macro_name(self, name: str) -> bool:
        if not name:
            return False
        if not _is_identifier_start(name[0]) and name[0] != "_":
            return False
        return all(_is_identifier_part(c) for c in name[1:])

    def _remove_comments(self, source: str) -> str:
        """Remove // and /* */ comments. Preserve strings. Preserve line numbering."""
        result: list[str] = []
        i = 0
        n = len(source)
        in_string = False
        escape = False
        string_char = ""

        while i < n:
            c = source[i]

            if escape:
                result.append(c)
                escape = False
                i += 1
                continue

            if in_string:
                if c == "\\":
                    result.append(c)
                    escape = True
                elif c == string_char:
                    result.append(c)
                    in_string = False
                else:
                    result.append(c)
                i += 1
                continue

            if c == '"' or c == "'":
                result.append(c)
                in_string = True
                string_char = c
                i += 1
                continue

            # Single-line comment
            if c == "/" and i + 1 < n and source[i + 1] == "/":
                # Skip until newline, replace with newline to preserve line count
                j = i + 2
                while j < n and source[j] not in ("\n", "\r"):
                    j += 1
                if j < n:
                    result.append(source[j])
                    j += 1
                    if j < n and source[j - 1] == "\r" and source[j] == "\n":
                        result.append("\n")
                        j += 1
                i = j
                continue

            # Multi-line comment
            if c == "/" and i + 1 < n and source[i + 1] == "*":
                start_line = source[:i].count("\n") + 1
                start_col = i - source[:i].rfind("\n") if "\n" in source[:i] else i + 1
                result.append("  ")  # preserve column count for opening "/*"
                j = i + 2
                depth = 1
                while j < n and depth > 0:
                    if j + 1 < n and source[j] == "/" and source[j + 1] == "*":
                        depth += 1
                        result.append("  ")  # preserve column count for "/*"
                        j += 2
                        continue
                    if j + 1 < n and source[j] == "*" and source[j + 1] == "/":
                        depth -= 1
                        result.append("  ")  # preserve column count for "*/"
                        j += 2
                        continue
                    if source[j] in ("\n", "\r"):
                        result.append(source[j])
                        j += 1
                        if j < n and source[j - 1] == "\r" and source[j] == "\n":
                            result.append("\n")
                            j += 1
                    else:
                        result.append(" ")  # Replace comment chars with space
                        j += 1
                if depth > 0:
                    self.errors.append(
                        PreprocessorError("unterminated block comment", start_line, start_col)
                    )
                i = j
                continue

            result.append(c)
            i += 1

        return "".join(result)

    def _expand_macros(self, source: str) -> str:
        """Replace macro names with values. Prevent recursion."""
        if not self._macros:
            return source

        return self._expand_macros_inner(source, set())

    def _expand_macros_inner(self, source: str, expansion_stack: set[str]) -> str:
        """Inner macro expansion with recursion guard."""
        result: list[str] = []
        i = 0
        n = len(source)
        in_string = False
        escape = False
        string_char = ""

        while i < n:
            c = source[i]

            if escape:
                result.append(c)
                escape = False
                i += 1
                continue

            if in_string:
                result.append(c)
                if c == "\\":
                    escape = True
                elif c == string_char:
                    in_string = False
                i += 1
                continue

            if c in ('"', "'"):
                result.append(c)
                in_string = True
                string_char = c
                i += 1
                continue

            # Check for identifier (potential macro)
            if _is_identifier_start(c) or (c == "_" and i + 1 < n and _is_identifier_part(source[i + 1])):
                start = i
                while i < n and _is_identifier_part(source[i]):
                    i += 1
                name = source[start:i]
                if name in self._macros:
                    if name in expansion_stack:
                        self.errors.append(
                            PreprocessorError(
                                f"macro recursion detected: {name}",
                                source[:start].count("\n") + 1,
                                (start - source[:start].rfind("\n")) if "\n" in source[:start] else start + 1,
                            )
                        )
                        result.append(name)
                    else:
                        value = self._macros[name]
                        expansion_stack.add(name)
                        expanded = self._expand_macros_inner(value, expansion_stack)
                        expansion_stack.discard(name)
                        result.append(expanded)
                else:
                    result.append(name)
                continue

            result.append(c)
            i += 1

        return "".join(result)
