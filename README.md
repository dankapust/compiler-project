## MiniCompiler

MiniCompiler — учебный проект компилятора для упрощённого C-подобного языка.

- Sprint 1: лексический анализатор (lexer), тесты, препроцессор
- Sprint 2: формальная грамматика, парсер (recursive descent), AST, визуализация
- Sprint 3: семантический анализ (таблица символов, типы, проверки, декорированный AST)
- Sprint 4: промежуточное представление (IR), генерация трёхадресного кода, CFG, peephole-оптимизации
- Sprint 5: генерация кода x86-64 (System V ABI), работа со стеком, пролог/эпилог функций
- Sprint 6: расширенный control flow, short-circuit логика, loop control, switch/case

### Team

- Капустин Данила

### Repository Structure

```text
compiler-project/
├── src/
│   ├── lexer/
│   ├── parser/
│   │   ├── parser.py
│   │   ├── ast.py
│   │   ├── pretty.py
│   │   ├── dot.py
│   │   ├── codec.py
│   │   ├── errors.py
│   │   └── grammar.txt
│   ├── semantic/
│   │   ├── analyzer.py
│   │   ├── symbol_table.py
│   │   ├── type_system.py
│   │   ├── errors.py
│   │   └── output.py
│   ├── ir/
│   │   ├── ir_instructions.py
│   │   ├── basic_block.py
│   │   ├── ir_generator.py
│   │   ├── control_flow.py
│   │   └── output.py
│   ├── codegen/
│   │   ├── abi.py               # номера GPR/XMM аргументов, caller/callee saved
│   │   ├── stack_frame.py       # смещения [rbp−N], выравнивание фрейма
│   │   ├── register_allocator.py
│   │   └── x86_generator.py    # NASM ELF64, инструкции и вызовы
│   ├── runtime/
│   │   └── runtime.asm          # print_int / print_string / read_int / exit / _start
│   ├── preprocessor/
│   ├── utils/
│   └── cli.py
├── tests/
│   ├── lexer/
│   │   ├── valid/
│   │   └── invalid/
│   ├── parser/
│   │   ├── valid/       (expressions/, statements/, declarations/, full_programs/)
│   │   └── invalid/     (syntax_errors/)
│   ├── preprocessor/
│   ├── semantic/
│   │   ├── valid/   (type_compatibility/, nested_scopes/, complex_programs/, …)
│   │   └── invalid/ (undeclared_variable/, type_mismatch/, …)
│   ├── ir/
│   │   ├── test_expressions.py
│   │   ├── test_control_flow.py
│   │   ├── test_functions.py
│   │   └── test_integration.py
│   ├── codegen/
│   │   ├── test_x86_generation.py
│   │   ├── test_pipeline.py       # компиляция → nasm → ld → запуск (Linux)
│   │   ├── valid/                 # arithmetic_ops/, control_flow/, …
│   │   └── invalid/
│   └── test_runner/
├── examples/
├── docs/
└── README.md
```

### Language Specification

Лексическая грамматика: `docs/language_spec.md`

Синтаксическая грамматика (с примерами и LL(1) заметками): `docs/grammar.md`

Формальная грамматика (EBNF): `src/parser/grammar.txt`

### Build / Install

Требования: Python 3.10+

```bash
python -m pip install -e .
```

### Quick Start

**Лексический анализ:**
```bash
compiler lex --input examples/hello.src --output tokens.txt
```

**Парсинг и вывод AST:**
```bash
compiler parse --input examples/hello.src --ast-format text
compiler parse --input examples/hello.src --ast-format dot --output ast.dot
compiler parse --input examples/hello.src --ast-format json --output ast.json
```

**Визуализация (Graphviz):**
```bash
compiler parse --input examples/hello.src --ast-format dot --output ast.dot
dot -Tpng ast.dot -o ast.png
```

Можно сразу получить PNG (если установлен Graphviz и доступна команда `dot`):
```bash
compiler parse --input examples/hello.src --ast-format dot --output ast.dot --render-png
```

**LL(1) таблицы (FIRST/FOLLOW + предиктивная таблица):**
```bash
compiler ll1 --format md --output ll1.md
compiler ll1 --format dot --output ll1_conflicts.dot
dot -Tpng ll1_conflicts.dot -o ll1_conflicts.png
```

Можно проверить/продемонстрировать вывод для конфликтной или неправильной грамматики:
```bash
compiler ll1 --format md --grammar tests/ll1/conflict_grammar.txt
compiler ll1 --format md --grammar tests/ll1/invalid_grammar.txt
```

Опции парсера: `--input`, `--ast-format [text|dot|json]`, `--output`, `--render-png` (при `--ast-format dot`, если есть `dot`), `--verbose`, `--no-preprocess`, `--max-errors N`

### Семантический анализ (Sprint 3)

Пайплайн: **препроцессор → лексер → парсер → семантика**. Проверяются объявления, области видимости, типы выражений, вызовы функций, `return`, условия `if`/`while`/`for`, использование переменных до инициализации.

**Полный отчёт (ошибки + дамп таблицы символов):**
```bash
compiler check --input examples/hello.src --output semantic_report.txt
```

**С аннотациями типов и кратким отчётом:**
```bash
compiler check --input examples/hello.src --show-types --report
```

**Только дамп таблицы символов (текст или JSON):**
```bash
compiler symbols --input examples/hello.src
compiler symbols --input examples/hello.src --format json --output symbols.json
```

Опции `check`: `--verbose`, `--show-types`, `--report`, `--no-preprocess`, `--max-errors N` (на этапе парсера).

**Пример сообщения об ошибке (stderr/файл отчёта):**
```text
семантическая ошибка: несовместимость типов при присваивании в «x»
  --> program.src:3:5
   | в функции «main»
   = ожидалось: int
   = получено: string
```

**Тесты семантики (golden):**
```bash
python -m tests.test_runner --only semantic
```

**Модульные тесты таблицы символов и типов:**
```bash
python -m unittest discover -s tests/semantic -p "test_*.py" -v
```

### Промежуточное представление — IR (Sprint 4)

Пайплайн: **препроцессор → лексер → парсер → семантика → IR**. Генерируется трёхадресный код, организованный в базовые блоки с графом потока управления (CFG).

**Генерация IR (текстовый формат):**
```bash
compiler ir --input examples/test_ir.src
compiler ir --input examples/test_ir.src --format text --output program.ir
```

**Генерация CFG (Graphviz):**
```bash
compiler ir --input examples/test_ir.src --format dot --output cfg.dot
dot -Tpng cfg.dot -o cfg.png
```

**JSON-представление IR:**
```bash
compiler ir --input examples/test_ir.src --format json --output program_ir.json
```

**Статистика IR:**
```bash
compiler ir --input examples/test_ir.src --stats
```

**IR с peephole-оптимизациями:**
```bash
compiler ir --input examples/test_ir.src --optimize
compiler ir --input examples/test_ir.src --optimize --stats
```

Опции `ir`: `--format [text|dot|json]`, `--output`, `--optimize`, `--stats`, `--render-png` (при `--format dot`), `--no-preprocess`.

#### Набор инструкций IR

| Категория | Инструкции |
|---|---|
| Арифметика | `ADD`, `SUB`, `MUL`, `DIV`, `MOD`, `NEG` |
| Логика | `AND`, `OR`, `NOT`, `XOR` |
| Сравнения | `CMP_EQ`, `CMP_NE`, `CMP_LT`, `CMP_LE`, `CMP_GT`, `CMP_GE` |
| Память | `LOAD`, `STORE`, `ALLOCA`, `GEP` |
| Поток управления | `JUMP`, `JUMP_IF`, `JUMP_IF_NOT`, `LABEL`, `PHI` |
| Функции | `CALL`, `RETURN`, `PARAM` |

#### Пример трансформации исходный код → IR

Исходный код:
```c
int factorial(int n) {
    if (n <= 1) { return 1; }
    else { return n * factorial(n - 1); }
}
```

Сгенерированный IR:
```text
function factorial: int (int n)
  entry_factorial_1:
    [n_1] = STORE t0
    t1 = LOAD [n_1]
    t2 = CMP_LE t1, 1
    JUMP_IF t2, L_then_3
    JUMP L_else_4

  L_then_3:
    RETURN 1
    JUMP exit_factorial_2

  L_else_4:
    t3 = LOAD [n_1]
    t4 = LOAD [n_1]
    t5 = SUB t4, 1
    PARAM 0, t5
    t6 = CALL factorial, 1
    t7 = MUL t3, t6
    RETURN t7
    JUMP exit_factorial_2

  L_endif_5:
    JUMP exit_factorial_2

  exit_factorial_2:
```

#### Peephole-оптимизации

Поддерживаемые оптимизации:
- Алгебраическое упрощение: `x + 0 → x`, `x * 1 → x`, `x * 0 → 0`
- Свёртка констант: `3 + 4 → 7`
- Снижение силы: `x * 2 → x + x`
- Удаление мёртвого кода
- Сцепление переходов: `JUMP L1; L1: JUMP L2 → JUMP L2`

Если на Windows команда `compiler` не находится, используйте (часто удобнее лаунчер `py`):
```bash
py -m cli lex --input examples/hello.src --output tokens.txt
py -m cli parse --input examples/hello.src --ast-format text
py -m cli check --input examples/hello.src
py -m cli symbols --input examples/hello.src --format json
py -m cli ir --input examples/test_ir.src
py -m cli ir --input examples/test_ir.src --optimize --stats
py -m cli compile --input examples/hello.src --output hello.asm
py -m cli compile --input examples/hello.src --output hello.asm --optimize --target x86_64
```
(На Linux/macOS обычно подойдёт `python -m cli ...` из корня проекта с `PYTHONPATH=src` или после `pip install -e .`.)

### Генерация кода x86-64 (Sprint 5)

Пайплайн: **препроцессор → лексер → парсер → семантика → IR → x86-64 Assembly**.
Генерируется ассемблерный код в синтаксисе NASM, соответствующий спецификации System V AMD64 ABI.

**Компиляция в ассемблер:**
```bash
compiler compile --input examples/hello.src --output hello.asm
compiler compile --input program.src --output program.asm --optimize
```
Цель по умолчанию: `--target x86_64`. Флаг `--optimize` включает peephole для IR перед кодогенерацией.

Альтернатива без entrypoint `compiler`:
```bash
py -m cli compile --input examples/hello.src --output hello.asm
```

**Сборка и запуск (Linux x86_64):**
```bash
nasm -f elf64 hello.asm -o hello.o
nasm -f elf64 src/runtime/runtime.asm -o runtime.o
ld -o hello runtime.o hello.o
gcc -no-pie -o hello hello.o runtime.o
./hello
echo $?
```

#### System V AMD64 ABI (соответствие)
- Целые/указатели: первые 6 аргументов в **RDI, RSI, RDX, RCX, R8, R9**, возврат **RAX** (для простых типов).
- Числа с плавающей точкой в **XMM0–XMM7**, возврат в **XMM0** (SSE: `movss`, `addss`, …).
- Аргументы сверх регистров — на стек (по байтам вниз через `sub rsp`, порядок согласован с вызывающим кодом генератора).
- Перед каждым **`call`** поддерживается **выровненный по 16 байт RSP** (вставляется паддинг, если суммарные «стековые» аргументы нарушают выравнивание).
- Метки блоков задаются именами блоков из IR (`entry_…`, `L_then_…`). Строковые литералы: **`.L.str0`**, … (**ASM-5**).

#### Особенности реализации
- **Управление стеком**: пролог `push rbp` / `mov rbp, rsp` / при необходимости `sub rsp, N`, эпилог `mov rsp, rbp` (если ранее было выделение) или только `pop rbp`; **N кратно 16**.
- **Красная зона (Should, STK-5)** для функций без `CALL`: если локальные/временные умещаются в **≤128 байт**, RSP можно не менять и адресовать локальные как `[rbp−N]` в зоне под текущим RSP — это зафиксировано в коде генератора (`x86_generator.py`).
- **Локалы и временные**: смещения **`[rbp−8]`**, **`[rbp−16]`**, …; сохранённые кадры и возврат — положительные смещения от RBP (**MEM-1**).
- Размер операнда: для основного типа языка генерируются 64-битные регистры GPR и `cqo`/`idiv` при делении/остатке (**ASM-3** как для машинных слов ELF64).

#### Runtime (`src/runtime/runtime.asm`)
| Символ | Соглашение вызова | Назначение |
|--------|-------------------|------------|
| `print_int` | целое в **RDI** | печать числа со строкой перевода строки через `write` |
| `print_string` | указатель на ASCIIZ в **RDI** | печать до `\0` |
| `read_int` | результат в **RAX** | чтение строки со stdin → целое |
| `exit` | код в **RDI** | `syscall` exit (60) |
| `_start` | — | `call main`; затем `exit` с кодом возвата в **RAX** |

Системные вызовы: номер в **RAX**, аргументы в **RDI/RSI/RDX/R10/R8/R9**, возврат в **RAX** (конвенции Linux x86_64).

Глобальные переменные (**MEM-3**): константные литералы `int`/`bool`/`float` записываются в **`.data`** (`dd`), остальные — в **`.bss`** (`resb` с байтовым размером типа). В кодоген используется символ языка без суффиксов областей видимости. Поля **`struct`**: IR **GEP** с байтовым смещением (как в `type_system`) и обращение к памяти под размер типа поля (**dword**/SSE для `int`/`float`).

На Windows удобно запускать: `py -m pytest tests/codegen/ -v` и `py -m pytest tests/ir/ -v`.

#### Пример трансляции IR → x86-64

IR:
```text
function add: int (int a, int b)
  entry_add_1:
    [a_1] = STORE t0
    [b_1] = STORE t1
    t1:int = LOAD [a_1]
    t2:int = LOAD [b_1]
    t3:int = ADD t1:int, t2:int
    RETURN t3:int
```

x86-64 (NASM):
```nasm
add:
    push rbp
    mov rbp, rsp
    sub rsp, 16
    mov [rbp-8], rdi     ; сохранение параметра a
    mov [rbp-16], rsi    ; сохранение параметра b
    mov rax, [rbp-8]
    add rax, [rbp-16]
    mov rsp, rbp
    pop rbp
    ret
```

### Control Flow и Short-Circuit (Sprint 6)

Добавлены конструкции:
- `if/else`, вложенные условия с уникальными метками блоков;
- `while`, `for`, поддержка `break`/`continue`;
- `switch/case/default` (линейный lowering в сравнения + переходы);
- короткое замыкание для `&&` и `||` на уровне CFG/IR (ветвления, а не eager `AND/OR`).

#### Пример if/else (фрагмент ASM)
```nasm
    cmp rax, 0
    jne L_then_1
    jmp L_else_2
L_then_1:
    mov rax, 1
    ret
L_else_2:
    mov rax, 0
    ret
```

#### Пример while (фрагмент ASM)
```nasm
L_while_cond_1:
    cmp rax, 10
    jge L_while_end_2
    ; body...
    jmp L_while_cond_1
L_while_end_2:
```

#### Пример short-circuit `&&`
```text
left
JUMP_IF left, L_sc_rhs
JUMP L_sc_short_false
L_sc_rhs:
  right
  ...
```

### Preprocessor (Stretch Goal)

Препроцессор включён по умолчанию. Поддерживает:
- Удаление комментариев (`//`, `/* */`) с сохранением номеров строк
- Макросы: `#define NAME value`, `#undef`, `#ifdef`, `#ifndef`, `#endif`

Отключить: `--no-preprocess`

### Run Tests

```bash
python -m tests.test_runner
python -m tests.test_runner --only lexer
python -m tests.test_runner --only parser
python -m tests.test_runner --only preprocessor
python -m tests.test_runner --only ll1
python -m tests.test_runner --only semantic
py -m pytest tests/ir/ -v
py -m pytest tests/codegen/ -v
py -m pytest tests/ir/generation/control_flow/test_sprint6_control_flow.py -v
py -m pytest tests/codegen/test_sprint6_codegen.py -v
```
(На Windows через лаунчер Python обычно удобнее `py`; на Linux/macOS можно `python -m pytest`.)

**Формат вывода токенов (лексер):**
```text
LINE:COLUMN TOKEN_TYPE "LEXEME" [LITERAL_VALUE]
```

**Пример вывода AST (text):**
```text
Program [1:1]:
  FunctionDecl: main -> void [1:1]
    Parameters: []
    Body:
      Block [1:11]:
        VarDeclStmt: int counter = 42 [2:5]
```

