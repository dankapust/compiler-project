from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lexer.scanner import Scanner
from lexer.token import TokenType
from preprocessor.preprocessor import Preprocessor


def _preprocess(source: str, use_preprocessor: bool) -> tuple[str, list]:
    if not use_preprocessor:
        return source, []
    pp = Preprocessor(source)
    return pp.process(), pp.errors


def _cmd_lex(args: argparse.Namespace) -> int:
    src_path = Path(args.input)
    out_path = Path(args.output)

    try:
        source = src_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"error: cannot read input file: {e}", file=sys.stderr)
        return 2

    source, pp_errors = _preprocess(source, getattr(args, "preprocess", True))
    if pp_errors:
        for err in pp_errors:
            print(err.format(), file=sys.stderr)
        if getattr(args, "fail_on_error", False):
            return 1

    scanner = Scanner(source)
    lines: list[str] = []
    while True:
        tok = scanner.next_token()
        lines.append(tok.format())
        if tok.type == TokenType.END_OF_FILE:
            break

    try:
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError as e:
        print(f"error: cannot write output file: {e}", file=sys.stderr)
        return 2

    had_errors = bool(scanner.errors) or bool(pp_errors)
    if scanner.errors:
        for err in scanner.errors:
            print(err.format(), file=sys.stderr)
    return 1 if (had_errors and args.fail_on_error) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="compiler")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_lex = sub.add_parser("lex", help="Tokenize an input source file")
    p_lex.add_argument("--input", required=True, help="Path to .src file")
    p_lex.add_argument("--output", required=True, help="Path to write tokens")
    p_lex.add_argument(
        "--no-preprocess",
        action="store_false",
        dest="preprocess",
        help="Skip preprocessor (comments and macros)",
    )
    p_lex.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit with code 1 if any lexical errors were encountered",
    )
    p_lex.set_defaults(func=_cmd_lex, preprocess=True)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())


