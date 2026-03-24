from __future__ import annotations

import argparse
import difflib
import sys
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))

from lexer.scanner import Scanner  # noqa: E402
from lexer.token import TokenType  # noqa: E402
from preprocessor.preprocessor import Preprocessor  # noqa: E402
from parser.parser import Parser  # noqa: E402
from parser.pretty import pretty_print  # noqa: E402
from parser.codec import node_to_jsonable, from_jsonable  # noqa: E402
from parser.ll1_tables import compute_all, table_to_markdown  # noqa: E402
from semantic.analyzer import SemanticAnalyzer  # noqa: E402
from semantic.output import format_symbol_table_text, format_type_annotations  # noqa: E402


@dataclass(frozen=True)
class CaseResult:
    name: str
    ok: bool
    diff: str | None = None


def _tokenize_text(text: str, use_preprocessor: bool = True) -> str:
    if use_preprocessor:
        pp = Preprocessor(text)
        text = pp.process()
    sc = Scanner(text)
    out_lines: list[str] = []
    while True:
        tok = sc.next_token()
        out_lines.append(tok.format())
        if tok.type == TokenType.END_OF_FILE:
            break
    return "\n".join(out_lines) + "\n"


def _tokens_from_source(text: str, use_preprocessor: bool = True) -> tuple[list, list, list]:
    pp_errors: list = []
    if use_preprocessor:
        pp = Preprocessor(text)
        text = pp.process()
        pp_errors = pp.errors
    sc = Scanner(text)
    toks = []
    while True:
        t = sc.next_token()
        toks.append(t)
        if t.type == TokenType.END_OF_FILE:
            break
    return toks, sc.errors, pp_errors


def _parse_text(text: str, use_preprocessor: bool = True) -> str:
    toks, lex_errors, pp_errors = _tokens_from_source(text, use_preprocessor)
    p = Parser(tokens=toks)
    program = p.parse()

    lines: list[str] = []
    for e in pp_errors:
        lines.append(f"ОШИБКА {e.format()}")
    for e in lex_errors:
        lines.append(f"ОШИБКА {e.format()}")
    for e in p.errors:
        lines.append(f"ОШИБКА {e.format()}")
    lines.append("AST:")
    lines.append(pretty_print(program).rstrip("\n"))

    try:
        program2 = from_jsonable(node_to_jsonable(program))
        if program2 != program:
            lines.append("ОШИБКА несовпадение round-trip: AST != decode(encode(AST))")
        else:
            lines.append("ОБРАТНЫЙ_ЦИКЛ: OK")
    except Exception as ex:
        lines.append(f"ОШИБКА сбой round-trip: {ex}")

    return "\n".join(lines) + "\n"


def _semantic_pipeline_text(text: str, src_name: str = "test.src", use_preprocessor: bool = True) -> str:
    processed = text
    pp_errors: list = []
    if use_preprocessor:
        pp = Preprocessor(text)
        processed = pp.process()
        pp_errors = pp.errors

    sc = Scanner(processed)
    toks = []
    while True:
        t = sc.next_token()
        toks.append(t)
        if t.type == TokenType.END_OF_FILE:
            break
    lex_errors = sc.errors
    lines: list[str] = []
    for e in pp_errors:
        lines.append(f"ЭТАП {e.format().strip()}")
    for e in lex_errors:
        lines.append(f"ЭТАП {e.format().strip()}")
    p = Parser(tokens=toks)
    program = p.parse()
    for e in p.errors:
        lines.append(f"ЭТАП {e.format().strip()}")
    if p.errors or lex_errors or pp_errors:
        lines.append("СЕМАНТИКА: ПРОПУЩЕНО")
        return "\n".join(lines) + "\n"

    sem = SemanticAnalyzer(file_name=src_name, source_text=processed)
    sem.analyze(program)
    dec = sem.get_decorated_ast()
    lines.append("СЕМАНТИЧЕСКИЕ_ОШИБКИ:")
    errs = sem.get_errors()
    if errs:
        for err in errs:
            lines.append(err.format().strip())
    else:
        lines.append("(нет)")
    lines.append("ТАБЛИЦА_СИМВОЛОВ:")
    lines.append(format_symbol_table_text(sem.get_symbol_table()).rstrip("\n"))
    lines.append("АННОТАЦИИ_ТИПОВ:")
    lines.append(format_type_annotations(program, dec.expr_types).rstrip("\n"))
    lines.append("ОБРАТНЫЙ_ЦИКЛ_JSON:")
    try:
        program2 = from_jsonable(node_to_jsonable(program))
        if program2 == program:
            lines.append("кодирование AST: OK")
        else:
            lines.append("кодирование AST: НЕСОВПАДЕНИЕ")
    except Exception as ex:
        lines.append(f"кодирование AST: СБОЙ {ex}")
    return "\n".join(lines) + "\n"


def _run_case(src_path: Path, update: bool) -> CaseResult:
    expected_path = src_path.with_suffix(".tokens")
    actual = _tokenize_text(src_path.read_text(encoding="utf-8"))

    if update or not expected_path.exists():
        expected_path.write_text(actual, encoding="utf-8")
        return CaseResult(name=str(src_path), ok=True, diff=None)

    expected = expected_path.read_text(encoding="utf-8")
    if expected == actual:
        return CaseResult(name=str(src_path), ok=True, diff=None)

    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile=str(expected_path),
            tofile=str(src_path) + " (actual)",
        )
    )
    src_path.with_suffix(".tokens.actual").write_text(actual, encoding="utf-8")
    return CaseResult(name=str(src_path), ok=False, diff=diff)


def _run_parser_case(src_path: Path, update: bool) -> CaseResult:
    expected_path = src_path.with_suffix(".expected")
    actual = _parse_text(src_path.read_text(encoding="utf-8"))

    if update or not expected_path.exists():
        expected_path.write_text(actual, encoding="utf-8")
        return CaseResult(name=str(src_path), ok=True, diff=None)

    expected = expected_path.read_text(encoding="utf-8")
    if expected == actual:
        return CaseResult(name=str(src_path), ok=True, diff=None)

    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile=str(expected_path),
            tofile=str(src_path) + " (actual)",
        )
    )
    src_path.with_suffix(".expected.actual").write_text(actual, encoding="utf-8")
    return CaseResult(name=str(src_path), ok=False, diff=diff)


def _run_semantic_case(src_path: Path, update: bool) -> CaseResult:
    expected_path = src_path.with_suffix(".expected")
    actual = _semantic_pipeline_text(src_path.read_text(encoding="utf-8"), src_name="test.src")

    if update or not expected_path.exists():
        expected_path.write_text(actual, encoding="utf-8")
        return CaseResult(name=str(src_path), ok=True, diff=None)

    expected = expected_path.read_text(encoding="utf-8")
    if expected == actual:
        return CaseResult(name=str(src_path), ok=True, diff=None)

    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile=str(expected_path),
            tofile=str(src_path) + " (actual)",
        )
    )
    src_path.with_suffix(".expected.actual").write_text(actual, encoding="utf-8")
    return CaseResult(name=str(src_path), ok=False, diff=diff)


def _ll1_md_text(grammar_path: Path) -> str:
    _g, first, follow, table, conflicts = compute_all(grammar_path)
    parts: list[str] = []
    parts.append("## FIRST\n")
    for k in sorted(nt for nt in _g.nonterminals()):
        parts.append(f"- {k}: {sorted(first[k])}\n")
    parts.append("\n## FOLLOW\n")
    for k in sorted(nt for nt in _g.nonterminals()):
        parts.append(f"- {k}: {sorted(follow[k])}\n")
    parts.append("\n## Predictive table (LL(1))\n\n")
    parts.append(table_to_markdown(_g, table))
    if conflicts:
        parts.append("\n## Conflicts\n")
        for c in conflicts:
            parts.append(f"- {c}\n")
    return "".join(parts)


def _run_ll1_case(grammar_path: Path, update: bool) -> CaseResult:
    expected_path = grammar_path.with_suffix(".expected")
    try:
        actual = _ll1_md_text(grammar_path)
    except Exception as e:
        actual = f"ОШИБКА не удалось загрузить грамматику: {e}\n"

    if update or not expected_path.exists():
        expected_path.write_text(actual, encoding="utf-8")
        return CaseResult(name=str(grammar_path), ok=True, diff=None)

    expected = expected_path.read_text(encoding="utf-8")
    if expected == actual:
        return CaseResult(name=str(grammar_path), ok=True, diff=None)

    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile=str(expected_path),
            tofile=str(grammar_path) + " (actual)",
        )
    )
    grammar_path.with_suffix(".expected.actual").write_text(actual, encoding="utf-8")
    return CaseResult(name=str(grammar_path), ok=False, diff=diff)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tests.test_runner")
    ap.add_argument("--update", action="store_true",
                    help="Write/update all expected golden files from current output")
    ap.add_argument("--only", choices=["all", "lexer", "parser", "preprocessor", "ll1", "semantic"], default="all",
                    help="Run only specific test category")
    args = ap.parse_args(argv)

    root = _ROOT
    results: list[CaseResult] = []

    if args.only in ("all", "lexer"):
        lexer_valid = root / "tests" / "lexer" / "valid"
        lexer_invalid = root / "tests" / "lexer" / "invalid"
        cases = sorted(lexer_valid.glob("*.src")) + sorted(lexer_invalid.glob("*.src"))
        if not cases:
            print("No lexer test cases found.", file=sys.stderr)
            return 2
        for c in cases:
            results.append(_run_case(c, update=args.update))

    if args.only in ("all", "preprocessor"):
        import importlib.util
        test_path = root / "tests" / "preprocessor" / "test_preprocessor.py"
        spec = importlib.util.spec_from_file_location("test_preprocessor", test_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            failed = []
            for name in dir(mod):
                if name.startswith("test_"):
                    func = getattr(mod, name)
                    if callable(func):
                        try:
                            func()
                        except AssertionError as e:
                            failed.append(f"{name}: {e}")
                        except Exception as e:
                            failed.append(f"{name}: {type(e).__name__}: {e}")
            if failed:
                results.append(CaseResult(name="preprocessor unit tests", ok=False, diff="\n".join(failed)))
            else:
                results.append(CaseResult(name="preprocessor unit tests", ok=True, diff=None))

    if args.only in ("all", "parser"):
        parser_valid = root / "tests" / "parser" / "valid"
        parser_invalid = root / "tests" / "parser" / "invalid"
        cases = sorted(parser_valid.rglob("*.src")) + sorted(parser_invalid.rglob("*.src"))
        if not cases:
            print("No parser test cases found.", file=sys.stderr)
            return 2
        for c in cases:
            results.append(_run_parser_case(c, update=args.update))

    if args.only in ("all", "ll1"):
        ll1_dir = root / "tests" / "ll1"
        cases = sorted(ll1_dir.glob("*.txt"))
        if not cases:
            print("No ll1 test cases found.", file=sys.stderr)
            return 2
        for c in cases:
            results.append(_run_ll1_case(c, update=args.update))

    if args.only in ("all", "semantic"):
        sem_root = root / "tests" / "semantic"
        cases = sorted(sem_root.rglob("*.src"))
        if not cases:
            print("No semantic test cases found.", file=sys.stderr)
            return 2
        for c in cases:
            results.append(_run_semantic_case(c, update=args.update))

    if not results:
        print("No test cases found.", file=sys.stderr)
        return 2

    failed = [r for r in results if not r.ok]
    for r in results:
        status = "OK" if r.ok else "FAIL"
        print(f"{status}: {r.name}")

    if failed:
        print("\n--- diffs ---", file=sys.stderr)
        for r in failed:
            assert r.diff is not None
            print(r.diff, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
