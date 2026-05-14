import os
import shutil
import subprocess
import sys
from pathlib import Path


def _compile_cmd(src_file: str, asm_file: str) -> list[str]:
    """editable install exposes `compiler`; else `python -m cli` with PYTHONPATH=src."""
    compiler = shutil.which("compiler")
    if compiler:
        return [compiler, "compile", "--input", src_file, "--output", asm_file]
    return [sys.executable, "-m", "cli", "compile", "--input", src_file, "--output", asm_file]


def run_test(src_file: str, expected_exit_code: int = 0) -> bool:
    src_path = Path(src_file)
    base_name = src_path.stem
    asm_file = f"{base_name}.asm"
    obj_file = f"{base_name}.o"
    rt_obj = "runtime.o"
    exe_file = base_name

    print(f"Testing {src_file}...")

    repo_root = Path(__file__).resolve().parents[2]
    src_dir = str(repo_root / "src")
    runtime_asm = repo_root / "src" / "runtime" / "runtime.asm"

    # 1. Compile to assembly
    try:
        my_env = os.environ.copy()
        my_env["PYTHONPATH"] = src_dir + os.pathsep + my_env.get("PYTHONPATH", "")
        subprocess.run(_compile_cmd(src_file, asm_file), check=True, cwd=str(repo_root), env=my_env)
    except subprocess.CalledProcessError:
        print(f"FAILED: Compilation error for {src_file}")
        return False

    # 2. Assemble with NASM
    try:
        subprocess.run(["nasm", "-f", "elf64", asm_file, "-o", obj_file], check=True, cwd=str(repo_root))
        if not os.path.exists(rt_obj):
            subprocess.run(["nasm", "-f", "elf64", str(runtime_asm), "-o", rt_obj], check=True, cwd=str(repo_root))
    except FileNotFoundError:
        print("FAILED: nasm not found")
        return False
    except subprocess.CalledProcessError:
        print(f"FAILED: NASM error for {asm_file}")
        return False

    # 3. Link
    try:
        subprocess.run(["ld", "-o", exe_file, rt_obj, obj_file], check=True, cwd=str(repo_root))
    except FileNotFoundError:
        print("FAILED: ld not found")
        return False
    except subprocess.CalledProcessError:
        print(f"FAILED: Linking error for {obj_file}")
        return False

    # 4. Execute
    try:
        result = subprocess.run([str(repo_root / exe_file)], capture_output=True, text=True)
        if result.stdout:
            print(f"Program output:\n{result.stdout.strip()}")
        if result.stderr:
            print(f"Program errors:\n{result.stderr.strip()}")
            
        if result.returncode != expected_exit_code:
            print(f"FAILED: Exit code mismatch. Expected {expected_exit_code}, got {result.returncode}")
            return False
        print(f"PASSED: {src_file}")
        return True
    except Exception as e:
        print(f"FAILED: Execution error: {e}")
        return False
    finally:
        # Cleanup
        for f in [repo_root / asm_file, repo_root / obj_file, repo_root / exe_file]:
            if f.exists():
                f.unlink()

if __name__ == "__main__":
    # Usage: python test_pipeline.py <src_file> [expected_exit_code]
    if len(sys.argv) > 1:
        expected = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        run_test(sys.argv[1], expected)
    else:
        print("Usage: python test_pipeline.py <src_file> [expected_exit_code]")
