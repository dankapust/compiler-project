## MiniCompiler (Sprint 1)

MiniCompiler — учебный проект компилятора для упрощённого C-подобного языка.

- Лексический анализатор (lexer), тесты, препроцессор (опционально).

### Team


- Капустин Данила


### Repository Structure

```text
compiler-project/
├── src/
│   ├── lexer/
│   ├── preprocessor/
│   ├── utils/
│   └── cli.py
├── tests/
│   ├── lexer/
│   │   ├── valid/
│   │   └── invalid/
│   ├── preprocessor/
│   └── test_runner/
├── examples/
├── docs/
└── README.md
```

### Language Specification

См. `docs/language_spec.md`.

### Build / Install (all platforms)

Требования:
- Python 3.10+

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

**Лексический анализ:**
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

### Preprocessor (Stretch Goal)

Препроцессор включён по умолчанию перед лексическим анализом и парсингом. Поддерживает:
- Удаление комментариев (`//`, `/* */`) с сохранением номеров строк
- Макросы: `#define NAME value`, `#undef`, `#ifdef`, `#ifndef`, `#endif`
- Программный API: `Preprocessor(source)`, `process()`, `define()`, `undefine()`

Отключить: `compiler lex --no-preprocess ...`

### Run Tests

**Запуск всех тестов одной командой:**
```bash
python -m tests.test_runner
```

**Только лексер / только препроцессор:**
```bash
python -m tests.test_runner --only lexer
python -m tests.test_runner --only preprocessor
```

**Формат вывода токенов (лексер):**

```text
LINE:COLUMN TOKEN_TYPE "LEXEME" [LITERAL_VALUE]
```


