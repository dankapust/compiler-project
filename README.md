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

### Quick Start (STR-3)

Из корня проекта:

```bash
# Установка (один раз)
python -m pip install -e .

# Токенизация примера (LEX-2). На Windows предпочтительно:
python -m cli lex --input examples/hello.src --output tokens.txt
# Или, если compiler в PATH:  compiler lex --input examples/hello.src --output tokens.txt

# Просмотр:  type tokens.txt   (Windows)  или  cat tokens.txt

# Тесты (TEST-4): все — одной командой
python -m tests.test_runner
# Только лексер:  python -m tests.test_runner --only lexer
```

Опции лексера: `--input`, `--output`, `--no-preprocess`, `--fail-on-error`.

### Preprocessor (Sprint 1 Stretch, optional)

Препроцессор можно использовать перед лексическим анализом: удаление комментариев, макросы `#define`, `#ifdef` и т.д. По умолчанию включён. Отключить: `compiler lex --no-preprocess ...`

### Формат вывода токенов (TEST-3)

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

---

### Соответствие Sprint 1 (чеклист)

| Область | Требования |
|--------|------------|
| **STR** | STR-1 структура ✓, STR-2 pyproject.toml + entry points ✓, STR-3 README ✓, STR-4 модули lexer/token/utils ✓ |
| **LANG** | docs/language_spec.md: EBNF, ключевые слова (LANG-2), идентификаторы 255 (LANG-3), литералы (LANG-4), операторы/разделители (LANG-5), пробелы/комментарии (LANG-6) ✓ |
| **LEX** | Token: type, lexeme, line, col, literal (LEX-1). Scanner: конструктор, next_token, peek_token, is_at_end, get_line/get_column (LEX-2). Все токены и EOF (LEX-3). Позиции и CRLF (LEX-4). Ошибки с позицией, восстановление (LEX-5) ✓ |
| **TEST** | valid/ + invalid/ (TEST-2), формат LINE:COLUMN TOKEN "LEXEME" [VALUE] (TEST-3), test_runner с diff (TEST-4), ≥20 valid / ≥10 invalid (TEST-5) ✓ |
