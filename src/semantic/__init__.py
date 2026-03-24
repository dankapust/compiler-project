"""Semantic analysis: symbol tables, types, decorated AST (Sprint 3)."""

from semantic.analyzer import SemanticAnalyzer
from semantic.errors import SemanticError
from semantic.output import DecoratedAST, format_decorated_ast_text, format_symbol_table_json
from semantic.symbol_table import SymbolInfo, SymbolKind, SymbolTable
from semantic.type_system import Type, TypeKind

__all__ = [
    "SemanticAnalyzer",
    "SemanticError",
    "DecoratedAST",
    "format_decorated_ast_text",
    "format_symbol_table_json",
    "SymbolInfo",
    "SymbolKind",
    "SymbolTable",
    "Type",
    "TypeKind",
]
