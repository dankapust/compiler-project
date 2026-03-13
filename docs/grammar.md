## Грамматика языка MiniCompiler (в стиле БНФ/EBNF)

### Содержание

- Обозначения
- Программа
- Препроцессор
- Объявления
- Типы
- Инструкции
- Выражения
- Приоритет операторов
- LL(1) свойства грамматики
- Примеры

### Обозначения

| Символ | Значение |
|---|---|
| `{ ... }` | повторение 0 или более раз |
| `[ ... ]` | опционально |
| `( ... )` | группировка |
| `|` | альтернатива |
| `"..."` | терминальный символ (лексема) |
| `?...?` | специальная последовательность |

### Программа

Программа состоит из последовательности объявлений верхнего уровня.

```ebnf
Program = { Declaration } EOF ;
```

### Препроцессор

Директивы препроцессора обрабатываются **до** синтаксического анализа и не входят в синтаксическую грамматику.

Поддерживаются:

- `#define NAME value`
- `#undef NAME`
- `#ifdef NAME ... #endif`
- `#ifndef NAME ... #endif`

### Объявления

```ebnf
Declaration = FunctionDecl | StructDecl | Statement ;

FunctionDecl = "fn" Identifier "(" [ Parameters ] ")" [ "->" Type ] Block ;
Parameters   = Parameter { "," Parameter } ;
Parameter    = Type Identifier ;

StructDecl   = "struct" Identifier "{" { VarDecl } "}" ;

VarDecl      = Type Identifier [ "=" Expression ] ";" ;
```

### Типы

```ebnf
Type = "int" | "float" | "bool" | "void" | Identifier ;
```

Замечание: `Identifier` в позиции типа используется для пользовательских типов (имён `struct`).

### Инструкции

```ebnf
Statement  = Block | IfStmt | WhileStmt | ForStmt | ReturnStmt | ExprStmt | VarDecl | ";" ;
Block      = "{" { Statement } "}" ;

IfStmt     = "if" "(" Expression ")" Statement [ "else" Statement ] ;
WhileStmt  = "while" "(" Expression ")" Statement ;

ForStmt    = "for" "(" [ ForInit ] ";" [ Expression ] ";" [ Expression ] ")" Statement ;
ForInit    = VarDeclNoSemi | Expression ;
VarDeclNoSemi = Type Identifier [ "=" Expression ] ;

ReturnStmt = "return" [ Expression ] ";" ;
ExprStmt   = Expression ";" ;
```

Решение “висячего else”: `else` привязывается к ближайшему (вложенному) `if`, у которого нет `else`.

### Выражения

Грамматика выражений задаётся по уровням приоритета (от низшего к высшему).

```ebnf
Expression     = Assignment ;
Assignment     = LogicalOr [ ( "=" | "+=" | "-=" | "*=" | "/=" | "%=" ) Assignment ] ;

LogicalOr      = LogicalAnd { "||" LogicalAnd } ;
LogicalAnd     = Equality { "&&" Equality } ;

Equality       = Relational [ ( "==" | "!=" ) Relational ] ;
Relational     = Additive [ ( "<" | "<=" | ">" | ">=" ) Additive ] ;

Additive       = Multiplicative { ( "+" | "-" ) Multiplicative } ;
Multiplicative = Unary { ( "*" | "/" | "%" ) Unary } ;

Unary          = ( "++" | "--" | "-" | "!" ) Unary
              | Postfix [ ( "++" | "--" ) ] ;

Postfix        = PrimaryBase { PostfixSuffix } ;
PrimaryBase    = Literal | Identifier | "(" Expression ")" ;
PostfixSuffix  = "(" [ Arguments ] ")"
              | "[" Expression "]"
              | "." Identifier ;

Arguments      = Expression { "," Expression } ;

Literal        = IntLiteral | FloatLiteral | StringLiteral | BoolLiteral | "null" ;
```

### Приоритет операторов

| Уровень (высокий → низкий) | Категория | Операторы/формы | Ассоциативность |
|---:|---|---|---|
| 1 | PrimaryBase | литералы, идентификаторы, `(expr)` | — |
| 2 | Postfix-цепочка | `()` `[]` `.` | левая (цепочка) |
| 3 | Постфиксные | `x++` `x--` | левая |
| 4 | Унарные | `-` `!` `++x` `--x` | правая |
| 5 | Мультипликативные | `*` `/` `%` | левая |
| 6 | Аддитивные | `+` `-` | левая |
| 7 | Сравнения | `<` `<=` `>` `>=` | неассоциативные |
| 8 | Равенство | `==` `!=` | неассоциативные |
| 9 | Логическое И | `&&` | левая |
| 10 | Логическое ИЛИ | `||` | левая |
| 11 | Присваивание | `=` `+=` `-=` `*=` `/=` `%=` | правая |

### LL(1) свойства грамматики

#### If/else

Так как ветки `if/else` — блоки `{ ... }`, неоднозначность “висячего else” отсутствует.

#### Типы vs выражения (известные типы)

`Type` может начинаться с `Identifier`, и выражение тоже может начинаться с `Identifier`. Чтобы сделать выбор на уровне `Statement` LL(1), используется идея “известных типов”:

- `TYPE_ID`: идентификатор, который является именем типа (имя `struct`)
- `IDENT`: обычный идентификатор

#### Forward-типы

Чтобы поддержать `T x;` до `struct T { ... }`, используется 2 прохода:

1. По токенам собираются все имена `struct` в множество `KnownTypes`
2. Парсинг выполняется с различением `TYPE_ID` и `IDENT`

#### LValue (для присваивания и ++/--)

Грамматика задаёт формы выражений. Допустимость цели проверяется отдельно:

- Разрешены: `Identifier`, `x[i]`, `x.field`, а также эти формы в скобках
- Запрещены: цели, содержащие вызов `(...)` в postfix-цепочке (например `f().x`)

### Примеры

```c
fn main() {
    int x = 5;
    x++;
    ++x;
    int y = x++ + ++x;
}
```

```c
struct Point {
    int x;
    int y;
};

fn main() {
    Point p;
    int a = p.x + p.y;
}
```

