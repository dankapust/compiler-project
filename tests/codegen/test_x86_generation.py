import pytest
from ir import IRGenerator
from semantic.analyzer import SemanticAnalyzer
from parser.parser import Parser
from lexer.scanner import Scanner
from codegen.x86_generator import X86Generator

def compile_to_asm(source: str) -> str:
    scanner = Scanner(source)
    tokens = []
    while True:
        t = scanner.next_token()
        tokens.append(t)
        if t.type.name == "END_OF_FILE":
            break
    
    parser = Parser(tokens)
    program = parser.parse()
    
    analyzer = SemanticAnalyzer(file_name="test.src", source_text=source)
    analyzer.analyze(program)
    
    generator = IRGenerator(
        analyzer.get_symbol_table(),
        analyzer.get_decorated_ast(),
        analyzer.get_registered_struct_types(),
    )
    ir_prog = generator.generate(program)
    
    codegen = X86Generator(ir_prog)
    return codegen.generate()

def test_simple_add():
    source = """
    fn main() -> int {
        int a = 5;
        int b = 10;
        int c = a + b;
        return c;
    }
    """
    asm = compile_to_asm(source)
    assert "global main" in asm
    assert "main:" in asm
    assert "push rbp" in asm
    assert "mov rbp, rsp" in asm
    assert "add rax," in asm
    assert "ret" in asm

def test_function_call():
    source = """
    fn add(int x, int y) -> int {
        return x + y;
    }
    fn main() -> int {
        return add(2, 3);
    }
    """
    asm = compile_to_asm(source)
    assert "global add" in asm
    assert "global main" in asm
    assert "call add" in asm
    assert "rdi" in asm
    assert "rsi" in asm

def test_modulo():
    source = """
    fn main() -> int {
        return 37 % 5;
    }
    """
    asm = compile_to_asm(source)
    assert "cqo" in asm
    assert "idiv" in asm
    assert "rdx" in asm.lower()


def test_stack_alignment_before_external_call():
    source = """
    fn callee(int a, int b, int c, int d, int e, int f, int g) -> int {
        return g;
    }
    fn main() -> int {
        return callee(1, 2, 3, 4, 5, 6, 42);
    }
    """
    asm = compile_to_asm(source)
    assert "call callee" in asm
    pre, _, _ = asm.partition("call callee")
    assert "sub rsp" in pre


def test_global_int_in_dot_data():
    source = """
    int gi = 100;
    fn main() -> int {
        int x = gi;
        return x;
    }
    """
    asm = compile_to_asm(source)
    assert "section .data" in asm
    assert "gi dd 100" in asm


def test_struct_field_asm():
    source = """
    struct Pt { int x; int y; }
    fn main() -> int {
        Pt p;
        p.x = 40;
        p.y = 2;
        return p.x + p.y;
    }
    """
    asm = compile_to_asm(source)
    assert "GEP" in asm.upper() or "lea rax" in asm
    assert "mov dword" in asm or "dword [" in asm


def test_if_else():
    source = """
    fn main() -> int {
        int x = 5;
        if (x > 0) {
            return 1;
        } else {
            return 0;
        }
    }
    """
    asm = compile_to_asm(source)
    assert "cmp" in asm
    assert any(jcc in asm for jcc in ("jne", "je", "jg", "jl", "jge", "jle", "ja", "jb", "jae", "jbe"))
    assert "ret" in asm
