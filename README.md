## MiniCompiler

MiniCompiler — учебный проект компилятора для упрощённого C-подобного языка.

- Sprint 1: лексический анализатор (lexer), тесты, препроцессор
- Sprint 2: формальная грамматика, парсер (recursive descent), AST, визуализация

### Team

- Kapustin Danila

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
│   └── test_runner/
├── examples/
├── docs/
└── README.md
```

### Language Specification

Лексическая грамматика: `docs/language_spec.md`

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

Опции парсера: `--input`, `--ast-format [text|dot|json]`, `--output`, `--verbose`, `--no-preprocess`, `--max-errors N`

Если на Windows команда `compiler` не находится, используйте:
```bash
python -m cli lex --input examples/hello.src --output tokens.txt
python -m cli parse --input examples/hello.src --ast-format text
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
