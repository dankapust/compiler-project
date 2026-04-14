## MiniCompiler

MiniCompiler — учебный проект компилятора для упрощённого C-подобного языка.

- Sprint 1: лексический анализатор (lexer), тесты, препроцессор
- Sprint 2: формальная грамматика, парсер (recursive descent), AST, визуализация
- Sprint 3: семантический анализ (таблица символов, типы, проверки, декорированный AST)
- Sprint 4: промежуточное представление (IR), генерация трёхадресного кода, CFG, peephole-оптимизации

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

Опции парсера: `--input`, `--ast-format [text|dot|json]`, `--output`, `--verbose`, `--no-preprocess`, `--max-errors N`

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

Опции `ir`: `--format [text|dot|json]`, `--output`, `--optimize`, `--stats`, `--no-preprocess`.

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

Если на Windows команда `compiler` не находится, используйте:
```bash
python -m cli lex --input examples/hello.src --output tokens.txt
python -m cli parse --input examples/hello.src --ast-format text
python -m cli check --input examples/hello.src
python -m cli symbols --input examples/hello.src --format json
python -m cli ir --input examples/test_ir.src
python -m cli ir --input examples/test_ir.src --optimize --stats
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
python -m pytest tests/ir/ -v
```

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

