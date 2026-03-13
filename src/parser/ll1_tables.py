from __future__ import annotations

"""
LL(1) tables (FIRST/FOLLOW/predictive) for the *syntax* grammar.

This module is intentionally decoupled from the recursive-descent implementation:
- It lets you validate that the written grammar is LL(1)
- It produces tables you can paste into reports
- It can emit Graphviz (.dot) to visualize conflicts

Important note about "Type" vs "Identifier" ambiguity:
In the language, user-defined types are introduced by `struct Name { ... }`.
The parser keeps a dynamic set of known type names and treats an IDENTIFIER as a
type-start only if it's in that set. With that refinement, the statement-level
grammar becomes LL(1) again.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


EPS = "EPS"
END = "$"


Symbol = str
NonTerm = str
Term = str


@dataclass(frozen=True)
class Grammar:
    start: NonTerm
    productions: dict[NonTerm, list[list[Symbol]]]

    def nonterminals(self) -> set[NonTerm]:
        return set(self.productions.keys())

    def terminals(self) -> set[Term]:
        nts = self.nonterminals()
        ts: set[str] = set()
        for alts in self.productions.values():
            for rhs in alts:
                for s in rhs:
                    if s != EPS and s not in nts:
                        ts.add(s)
        return ts


def _parse_bnf_section(text: str) -> Grammar:
    in_bnf = False
    productions: dict[NonTerm, list[list[Symbol]]] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("---"):
            continue
        if "BNF (expanded" in line:
            in_bnf = True
            continue
        if not in_bnf:
            continue
        if line.startswith("Conventions:"):
            continue
        if line.startswith("- "):
            continue
        if "->" not in line:
            continue

        lhs, rhs = (part.strip() for part in line.split("->", 1))
        if not lhs:
            continue

        if rhs == EPS:
            symbols = [EPS]
        else:
            symbols = [END if s == "$" else s for s in rhs.split()]
        productions.setdefault(lhs, []).append(symbols)

    if not productions:
        raise ValueError("BNF section not found or empty")
    if "Program" not in productions:
        raise ValueError("BNF does not define start symbol 'Program'")
    return Grammar(start="Program", productions=productions)


def load_grammar_from_grammar_txt(grammar_txt_path: str | Path | None = None) -> Grammar:
    if grammar_txt_path is None:
        grammar_txt_path = Path(__file__).with_name("grammar.txt")
    else:
        grammar_txt_path = Path(grammar_txt_path)
    text = grammar_txt_path.read_text(encoding="utf-8")
    return _parse_bnf_section(text)


def compute_first(g: Grammar) -> dict[Symbol, set[Term]]:
    nts = g.nonterminals()
    first: dict[Symbol, set[Term]] = {EPS: {EPS}}
    for t in g.terminals():
        first[t] = {t}
    for nt in nts:
        first.setdefault(nt, set())

    changed = True
    while changed:
        changed = False
        for nt, alts in g.productions.items():
            for rhs in alts:
                add = first_of_sequence(first, rhs)
                before = len(first[nt])
                first[nt].update(add - {EPS})
                if EPS in add:
                    first[nt].add(EPS)
                if len(first[nt]) != before:
                    changed = True
    return first


def first_of_sequence(first: dict[Symbol, set[Term]], seq: list[Symbol]) -> set[Term]:
    if not seq:
        return {EPS}
    out: set[Term] = set()
    for s in seq:
        s_first = first.get(s, {s})
        out.update(s_first - {EPS})
        if EPS not in s_first:
            return out
    out.add(EPS)
    return out


def compute_follow(g: Grammar, first: dict[Symbol, set[Term]]) -> dict[NonTerm, set[Term]]:
    follow: dict[NonTerm, set[Term]] = {nt: set() for nt in g.nonterminals()}
    follow[g.start].add(END)

    changed = True
    while changed:
        changed = False
        for A, alts in g.productions.items():
            for rhs in alts:
                for i, B in enumerate(rhs):
                    if B not in g.nonterminals():
                        continue
                    beta = rhs[i + 1 :]
                    beta_first = first_of_sequence(first, beta)
                    before = len(follow[B])
                    follow[B].update(beta_first - {EPS})
                    if EPS in beta_first:
                        follow[B].update(follow[A])
                    if len(follow[B]) != before:
                        changed = True
    return follow


def build_predict_table(
    g: Grammar, first: dict[Symbol, set[Term]], follow: dict[NonTerm, set[Term]]
) -> tuple[dict[tuple[NonTerm, Term], list[Symbol]], list[str]]:
    table: dict[tuple[NonTerm, Term], list[Symbol]] = {}
    conflicts: list[str] = []

    for A, alts in g.productions.items():
        for rhs in alts:
            look = first_of_sequence(first, rhs)
            targets = set(look - {EPS})
            if EPS in look:
                targets |= follow[A]
            for a in targets:
                key = (A, a)
                if key in table and table[key] != rhs:
                    conflicts.append(f"conflict M[{A}, {a}] : {table[key]}  vs  {rhs}")
                else:
                    table[key] = rhs
    return table, conflicts


def table_to_markdown(g: Grammar, table: dict[tuple[NonTerm, Term], list[Symbol]]) -> str:
    nts = sorted(g.nonterminals())
    ts = sorted(t for t in g.terminals() | {END} if t != EPS)
    lines: list[str] = []
    lines.append("| NonTerm | " + " | ".join(ts) + " |")
    lines.append("|" + "|".join(["---"] * (len(ts) + 1)) + "|")
    for nt in nts:
        row = [nt]
        for t in ts:
            rhs = table.get((nt, t))
            row.append("" if rhs is None else " ".join(rhs))
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def conflicts_to_dot(conflicts: Iterable[str]) -> str:
    lines = ["digraph LL1Conflicts {", '  node [shape=box, fontname="monospace"];']
    lines.append('  label="LL(1) table conflicts"; labelloc=top;')
    for i, c in enumerate(conflicts, start=1):
        esc = c.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'  n{i} [label="{esc}", color="red"];')
    lines.append("}")
    return "\n".join(lines) + "\n"


def compute_all(
    grammar_txt_path: str | Path | None = None,
) -> tuple[
    Grammar,
    dict[Symbol, set[Term]],
    dict[NonTerm, set[Term]],
    dict[tuple[NonTerm, Term], list[Symbol]],
    list[str],
]:
    g = load_grammar_from_grammar_txt(grammar_txt_path)
    first = compute_first(g)
    follow = compute_follow(g, first)
    table, conflicts = build_predict_table(g, first, follow)
    return g, first, follow, table, conflicts

