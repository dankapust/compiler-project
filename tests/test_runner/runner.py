from __future__ import annotations

import argparse
import difflib
import sys
from dataclasses import dataclass
from pathlib import Path

# Allow running tests without installing the package
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))

from lexer.scanner import Scanner  # noqa: E402
from lexer.token import TokenType  # noqa: E402
from preprocessor.preprocessor import Preprocessor  # noqa: E402


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
    # also write actual for convenience
    src_path.with_suffix(".tokens.actual").write_text(actual, encoding="utf-8")
    return CaseResult(name=str(src_path), ok=False, diff=diff)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tests.test_runner")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Write/update all expected golden files from current output",
    )
    parser.add_argument(
        "--only",
        choices=["all", "lexer", "preprocessor"],
        default="all",
        help="Run only lexer tests, preprocessor tests, or all",
    )
    args = parser.parse_args(argv)

    root = _ROOT
    lexer_valid_dir = root / "tests" / "lexer" / "valid"
    lexer_invalid_dir = root / "tests" / "lexer" / "invalid"

    results: list[CaseResult] = []

    if args.only in ("all", "lexer"):
        lexer_cases = sorted(lexer_valid_dir.glob("*.src")) + sorted(lexer_invalid_dir.glob("*.src"))
        if not lexer_cases:
            print("No lexer test cases found.", file=sys.stderr)
            return 2
        for c in lexer_cases:
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


