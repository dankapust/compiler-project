## MiniCompiler (Sprint 1)

MiniCompiler — учебный проект компилятора для упрощённого **C-подобного языка** (исходники в `.src`: `fn`, `int`, `if`, `while` и т.д.). Реализация компилятора — на Python.

**Sprint 1:** лексический анализатор (lexer), препроцессор (опционально, stretch goal).

### Team

- MiniCompiler Team
- Kapustin Danila

### Repository Structure (STR-1)

```text
compiler-project/
├── src/
│   ├── lexer/           # Лексический анализатор (сканер)
│   ├── preprocessor/    # Опционально (Sprint 1 stretch)
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

### Language Specification (LANG-1)

См. **`docs/language_spec.md`** — лексическая грамматика в EBNF: ключевые слова, идентификаторы, литералы, операторы, разделители, комментарии.

### Build / Install (STR-2)

Требования: **Python 3.8+**

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

### Команды для демонстрации работы

Из корня проекта (`Kompilator`):

```bash
# 1. Установка (один раз)
python -m pip install -e .

# 2. Токенизация примера — вывод в файл
#    (на Windows команда compiler часто не в PATH — используйте вариант ниже)
python -m cli lex --input examples/hello.src --output tokens.txt

# Просмотр результата (Windows)
type tokens.txt

# Вариант через compiler (если папка Scripts в PATH):
# compiler lex --input examples/hello.src --output tokens.txt

# 3. Запуск всех тестов лексера
python -m tests.test_runner --only lexer

# 4. Запуск всех тестов (лексер + препроцессор)
python -m tests.test_runner
```

### Quick Start (STR-3)

**Лексический анализ (LEX-2):**

```bash
compiler lex --input examples/hello.src --output tokens.txt
```

Если команда `compiler` не находится (Windows), запуск через модуль:

```bash
python -m cli lex --input examples/hello.src --output tokens.txt
```

Опции лексера: `--input`, `--output`, `--no-preprocess` (пропустить препроцессор), `--fail-on-error` (код выхода 1 при ошибках лексики).

### Preprocessor (Sprint 1 Stretch, optional)

Препроцессор можно использовать перед лексическим анализом: удаление комментариев, макросы `#define`, `#ifdef` и т.д. По умолчанию включён. Отключить: `compiler lex --no-preprocess ...`

### Run Tests (TEST-3, TEST-4)

**Запуск всех тестов одной командой:**

```bash
python -m tests.test_runner
```

**Только лексер / только препроцессор:**

```bash
python -m tests.test_runner --only lexer
python -m tests.test_runner --only preprocessor
```

**Формат вывода токенов (TEST-3):**

```text
LINE:COLUMN TOKEN_TYPE "LEXEME" [LITERAL_VALUE]
```

Пример:

```text
1:1 KW_FN "fn"
1:4 IDENTIFIER "main"
1:8 LPAREN "("
1:9 RPAREN ")"
1:10 LBRACE "{"
2:5 KW_INT "int"
2:9 IDENTIFIER "counter"
2:16 ASSIGN "="
2:18 INT_LITERAL "42" 42
2:20 SEMICOLON ";"
3:1 RBRACE "}"
4:1 END_OF_FILE ""
```

Ожидаемые результаты хранятся в файлах `.tokens` рядом с каждым `.src` в `tests/lexer/valid/` и `tests/lexer/invalid/`. При расхождении выводится diff. Обновить эталоны: `python -m tests.test_runner --update`.
