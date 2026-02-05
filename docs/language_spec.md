## MiniCompiler Language Spec (Sprint 1) — Lexical Grammar

### Character Set / Encoding

- Source files are interpreted as **UTF-8** text.
- Lexer treats ASCII control characters only as whitespace/newlines where specified.

### Token Categories

- **Keywords**: reserved words listed below
- **Identifiers**
- **Literals**: integer, float, string, boolean
- **Operators**
- **Delimiters**
- **End-of-file** marker
- **Error** token (used for recovery; scanning continues)

### Keywords (LANG-2)

Reserved words:

`if`, `else`, `while`, `for`, `int`, `float`, `bool`, `return`, `true`, `false`, `void`, `struct`, `fn`

Note: In the implementation, `true`/`false` are recognized as **boolean literals** with typed values.

### Lexical Grammar (EBNF) (LANG-1)

Whitespace and comments are skipped and not emitted as tokens.

EBNF:

```ebnf
letter      = "A"…"Z" | "a"…"z" ;
digit       = "0"…"9" ;
underscore  = "_" ;

identifier  = letter, { letter | digit | underscore } ;

int_lit     = digit, { digit } ;
float_lit   = digit, { digit }, ".", digit, { digit } ;
bool_lit    = "true" | "false" ;
string_lit  = '"', { string_char }, '"' ;
string_char = ? any char except '"' and newline ? | escape ;
escape      = "\", ( "\" | "n" | "t" | "r" | '"' ) ;

keyword     = "if" | "else" | "while" | "for" | "int" | "float" | "bool"
            | "return" | "void" | "struct" | "fn" ;

operator    = "+" | "-" | "*" | "/" | "%" 
            | "==" | "!=" | "<" | "<=" | ">" | ">="
            | "=" | "+=" | "-=" | "*=" | "/=" | "%="
            | "&&" ;

delimiter   = "(" | ")" | "{" | "}" | "[" | "]" | "," | ";" ;
```

### Regular Expressions (LANG-1)

- **Identifier**: `[A-Za-z][A-Za-z0-9_]{0,254}`
- **Integer**: `[0-9]+` (range checked as 32-bit signed at lex time)
- **Float**: `[0-9]+\.[0-9]+`
- **String**: `"([^"\\\n\r]|\\.)*"` (escapes are limited in Sprint 1)
- **Boolean**: `true|false`

### Identifiers (LANG-3)

- Start with letter `[a-zA-Z]`
- Followed by letters, digits, or underscores
- Max length: **255**
- Case-sensitive

### Literals (LANG-4)

- **Integer**: decimal digits; checked to fit \( [-2^{31}, 2^{31}-1] \)
- **Float**: decimal digits + dot + decimal digits
- **String**: double-quoted; basic escapes supported
- **Boolean**: `true` or `false`

### Operators & Delimiters (LANG-5)

- Arithmetic: `+ - * / %`
- Relational: `== != < <= > >=`
- Logical: `&&`
- Assignment (used by lexer tests): `= += -= *= /= %=`
- Delimiters: `(` `)` `{` `}` `[` `]` `,` `;`

### Whitespace & Comments (LANG-6)

- Whitespace: space, tab, newline (`\n`), carriage return (`\r`)
- Newlines: both Unix (`\n`) and Windows (`\r\n`) are supported and counted as one line break.
- Single-line comment: `//` until end-of-line
- Multi-line comment: `/* ... */` (nesting supported in implementation)


