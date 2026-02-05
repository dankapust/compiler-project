## MiniCompiler (Sprint 1) — Lexer/Tokenizer

MiniCompiler is a учебный проект компилятора для упрощённого C-подобного языка. В Sprint 1 мы создаём основу репозитория и реализуем **лексический анализатор (scanner/lexer)**: превращаем исходный текст в поток токенов с позициями (строка/колонка) и ошибками.

### Team

- MiniCompiler Team (добавьте имена участников)

### Repository Structure

```text
compiler-project/
├── src/
│   ├── lexer/
│   └── utils/
├── tests/
│   ├── lexer/
│   │   ├── valid/
│   │   └── invalid/
│   └── test_runner/
├── examples/
├── docs/
└── README.md
```

### Language Specification

См. `docs/language_spec.md`.

### Build / Install (all platforms)

Требования:
- Python 3.8+

Установка в editable-режиме:

```bash
python -m pip install -U pip
python -m pip install -e .
```

Сборка пакета (опционально):

```bash
python -m pip install -U build
python -m build
```

### Quick Start

Лексический анализ файла:

```bash
compiler lex --input examples/hello.src --output tokens.txt
```

Если на Windows команда `compiler` не находится (ошибка “не распознано как имя командлета”), это значит что папка со скриптами Python не добавлена в `PATH`.

Варианты:
- Запуск без PATH:

```bash
python -m cli lex --input examples/hello.src --output tokens.txt
```

- Или добавьте в `PATH` директорию из предупреждения pip (обычно что-то вроде `...\\Python38\\Scripts`) и откройте новый терминал.

### Run Tests

Запуск всех golden-тестов лексера одной командой:

```bash
python -m tests.test_runner
```

Формат ожидаемого вывода токенов:

```text
LINE:COLUMN TOKEN_TYPE "LEXEME" [LITERAL_VALUE]
```


