from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lexer.scanner import Scanner
from lexer.token import TokenType
from preprocessor.preprocessor import Preprocessor
from parser.parser import Parser
from parser.pretty import pretty_print
from parser.dot import to_dot
from parser.codec import node_to_jsonable


def _preprocess(source: str, use_preprocessor: bool) -> tuple[str, list]:
    """Apply preprocessor if enabled. Return (source, preprocessor_errors)."""
    if not use_preprocessor:
        return source, []
    pp = Preprocessor(source)
    return pp.process(), pp.errors


def _tokenize(source: str) -> tuple[list, list]:
    """Tokenize source, return (tokens, scan_errors)."""
    scanner = Scanner(source)
    toks = []
    while True:
        t = scanner.next_token()
        toks.append(t)
        if t.type == TokenType.END_OF_FILE:
            break
    return toks, scanner.errors


def _cmd_lex(args: argparse.Namespace) -> int:
    src_path = Path(args.input)
    out_path = Path(args.output)

    try:
        source = src_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"error: cannot read input file: {e}", file=sys.stderr)
        return 2

    source, pp_errors = _preprocess(source, args.preprocess)
    if pp_errors:
        for err in pp_errors:
            print(err.format(), file=sys.stderr)
        if args.fail_on_error:
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


def _cmd_parse(args: argparse.Namespace) -> int:
    src_path = Path(args.input)
    try:
        source = src_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"error: cannot read input file: {e}", file=sys.stderr)
        return 2

    source, pp_errors = _preprocess(source, args.preprocess)
    tokens, lex_errors = _tokenize(source)
    parser = Parser(tokens=tokens, max_errors=args.max_errors)
    program = parser.parse()

    had_errors = False
    if pp_errors:
        had_errors = True
        if args.verbose:
            for e in pp_errors:
                print(e.format(), file=sys.stderr)
    if lex_errors:
        had_errors = True
        if args.verbose:
            for e in lex_errors:
                print(e.format(), file=sys.stderr)
    if parser.errors:
        had_errors = True
        if args.verbose:
            for e in parser.errors:
                print(e.format(), file=sys.stderr)
            m = parser.metrics
            if m.reported_count or m.recovered_count or m.cascade_prevented_count:
                print(f"# {m.format_summary()}", file=sys.stderr)

    match args.ast_format:
        case "text":
            out_text = pretty_print(program)
        case "dot":
            out_text = to_dot(program)
        case "json":
            out_text = json.dumps(node_to_jsonable(program), ensure_ascii=False, indent=2) + "\n"
        case _:
            print(f"error: unknown ast format: {args.ast_format}", file=sys.stderr)
            return 2

    if args.output:
        try:
            Path(args.output).write_text(out_text, encoding="utf-8")
        except OSError as e:
            print(f"error: cannot write output file: {e}", file=sys.stderr)
            return 2
    else:
        sys.stdout.write(out_text)

    return 1 if had_errors else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="compiler")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_lex = sub.add_parser("lex", help="Tokenize an input source file")
    p_lex.add_argument("--input", required=True)
    p_lex.add_argument("--output", required=True)
    p_lex.add_argument("--no-preprocess", action="store_false", dest="preprocess")
    p_lex.add_argument("--fail-on-error", action="store_true")
    p_lex.set_defaults(func=_cmd_lex, preprocess=True)

    p_parse = sub.add_parser("parse", help="Parse input and output AST")
    p_parse.add_argument("--input", required=True)
    p_parse.add_argument("--ast-format", choices=["text", "dot", "json"], default="text")
    p_parse.add_argument("--output", default=None)
    p_parse.add_argument("--verbose", action="store_true")
    p_parse.add_argument("--no-preprocess", action="store_false", dest="preprocess")
    p_parse.add_argument("--max-errors", type=int, default=None, metavar="N")
    p_parse.set_defaults(func=_cmd_parse, preprocess=True)

    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
