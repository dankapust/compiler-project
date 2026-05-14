from __future__ import annotations

import struct
from typing import Any

from parser.ast import (
    ASTVisitor,
    ProgramNode,
    LiteralExpr,
    IdentifierExpr,
    MemberAccessExpr,
    BinaryExpr,
    UnaryExpr,
    CallExpr,
    AssignmentExpr,
    IncDecExpr,
    BlockStmt,
    ExprStmt,
    IfStmt,
    WhileStmt,
    ForStmt,
    BreakStmt,
    ContinueStmt,
    SwitchStmt,
    SwitchCase,
    ReturnStmt,
    VarDeclStmt,
    EmptyStmt,
    Param,
    FunctionDecl,
    StructDecl,
)
from semantic.type_system import (
    Type,
    TypeKind,
    BOOL,
    ERROR_T,
    FLOAT,
    INT,
    STRING,
    VOID,
    struct_field_byte_offset,
    type_size_bytes,
)
from semantic.analyzer import DecoratedAST, SymbolTable, SymbolKind
from .basic_block import BasicBlock, IRFunction, IRGlobal, IRProgram
from .ir_instructions import (
    IROpcode,
    IRInstruction,
    IRTemp,
    IRLiteral,
    IRVar,
    IRLabel,
    IRMemory,
)


class IRGenerator(ASTVisitor):
    def __init__(
        self,
        symbol_table: SymbolTable,
        decorated_ast: DecoratedAST,
        struct_types: dict[str, Type] | None = None,
    ):
        self.symbol_table = symbol_table
        self.decorated_ast = decorated_ast
        self._struct_types = dict(struct_types or {})
        self.program = IRProgram()

        self._temp_counter = 0
        self._label_counter = 0

        self.current_function: IRFunction | None = None
        self.current_block: BasicBlock | None = None
        self._control_stack: list[dict[str, str | None]] = []

    def _new_temp(self, type_str: str | None = None) -> IRTemp:
        self._temp_counter += 1
        return IRTemp(self._temp_counter, type=type_str)

    def _new_label(self, prefix: str = "L") -> str:
        self._label_counter += 1
        return f"{prefix}_{self._label_counter}"

    def _add_instruction(self, instr: IRInstruction):
        if self.current_block:
            self.current_block.add_instruction(instr)

    def _switch_block(self, new_block: BasicBlock):
        self.current_block = new_block

    def _named_type_str(self, name: str) -> Type:
        match name:
            case "void":
                return VOID
            case "int":
                return INT
            case "float":
                return FLOAT
            case "bool":
                return BOOL
            case "string":
                return STRING
        if name in self._struct_types:
            return self._struct_types[name]
        return ERROR_T

    def _type_from_decorated(self, ann: str | None) -> Type:
        if not ann:
            return ERROR_T
        return self._named_type_str(ann)

    def _resolve_ir_var(self, plain_name: str) -> IRVar:
        sym = self.symbol_table.lookup(plain_name)
        if sym and sym.kind == SymbolKind.VARIABLE and sym.stack_offset is None:
            return IRVar(plain_name)
        return IRVar(f"{plain_name}_{self.symbol_table.scope_depth()}")

    def _aligned_slot_size(self, raw: int) -> int:
        if raw <= 0:
            return 8
        return max(((raw + 7) // 8) * 8, 8)

    def _emit_aggregate_address_of_lvalue(self, lv: IdentifierExpr | MemberAccessExpr) -> IRTemp:
        if isinstance(lv, IdentifierExpr):
            st_t = self._type_from_decorated(self.decorated_ast.get_type(lv))
            if st_t.kind != TypeKind.STRUCT:
                raise RuntimeError("internal: address-of expected struct lvalue")
            v = self._resolve_ir_var(lv.name)
            addr = self._new_temp("*")
            self._add_instruction(IRInstruction(IROpcode.GEP, addr, [IRMemory(v), IRLiteral(0)]))
            return addr
        assert isinstance(lv, MemberAccessExpr)
        subt = self._type_from_decorated(self.decorated_ast.get_type(lv.base))
        if subt.kind != TypeKind.STRUCT:
            raise RuntimeError("internal: struct field chain expected struct object type")
        base_addr = self._emit_aggregate_address_of_lvalue(lv.base)
        off = struct_field_byte_offset(subt, lv.member)
        addr = self._new_temp("*")
        self._add_instruction(IRInstruction(IROpcode.GEP, addr, [base_addr, IRLiteral(off)]))
        return addr

    def generate(self, node: ProgramNode) -> IRProgram:
        self.visit_program(node)
        return self.program

    def get_function_ir(self, name: str) -> IRFunction | None:
        for f in self.program.functions:
            if f.name == name:
                return f
        return None

    def get_all_ir(self) -> IRProgram:
        return self.program

    def visit_program(self, node: ProgramNode) -> Any:
        for decl in node.declarations:
            decl.accept(self)
        return self.program

    def visit_function_decl(self, node: FunctionDecl) -> Any:
        func = IRFunction(
            name=node.name,
            return_type=node.return_type,
            params=[(p.param_type, p.name) for p in node.params],
        )
        self.current_function = func
        self.program.add_function(func)

        entry_block = BasicBlock(self._new_label(f"entry_{node.name}"))
        func.entry_block = entry_block
        func.add_block(entry_block)

        exit_block = BasicBlock(self._new_label(f"exit_{node.name}"))
        func.exit_block = exit_block

        self._switch_block(entry_block)

        for i, param in enumerate(node.params):
            var_op = IRVar(f"{param.name}_{self.symbol_table.scope_depth()}")
            self._add_instruction(IRInstruction(IROpcode.STORE, IRMemory(var_op), [IRTemp(i)]))
            pt = self._named_type_str(param.param_type)
            self.program.slot_sizes[var_op.name] = self._aligned_slot_size(type_size_bytes(pt))

        if node.body:
            node.body.accept(self)

        self.current_block.add_successor(exit_block)
        func.add_block(exit_block)
        self._switch_block(exit_block)

        self.current_function = None
        self.current_block = None
        return None

    def visit_block(self, node: BlockStmt) -> Any:
        for stmt in node.statements:
            stmt.accept(self)
        return None

    def visit_var_decl(self, node: VarDeclStmt) -> Any:
        t = self._named_type_str(node.var_type)
        if t.kind == TypeKind.VOID or t.kind == TypeKind.ERROR:
            sz = 8
        else:
            sz = self._aligned_slot_size(type_size_bytes(t))

        if self.current_function is None:
            init_int: int | None = None
            init_float_bits: int | None = None
            if node.initializer and isinstance(node.initializer, LiteralExpr):
                iv = node.initializer.value
                if isinstance(iv, bool):
                    init_int = int(iv)
                elif isinstance(iv, int):
                    init_int = iv
                elif isinstance(iv, float):
                    init_float_bits = struct.unpack("I", struct.pack("f", float(iv)))[0]
            self.program.globals.append(
                IRGlobal(
                    asm_name=node.name,
                    size_bytes=sz if t.kind != TypeKind.VOID else 8,
                    init_int=init_int,
                    init_float_bits=init_float_bits,
                )
            )
            return None

        var_op = self._resolve_ir_var(node.name)
        self.program.slot_sizes[var_op.name] = sz

        if node.initializer:
            val_op = node.initializer.accept(self)
            self._add_instruction(IRInstruction(IROpcode.STORE, IRMemory(var_op), [val_op]))
        return None

    def visit_expr_stmt(self, node: ExprStmt) -> Any:
        node.expression.accept(self)
        return None

    def visit_assignment(self, node: AssignmentExpr) -> Any:
        val_op = node.value.accept(self)

        if isinstance(node.target, IdentifierExpr):
            var_op = self._resolve_ir_var(node.target.name)
            self._add_instruction(IRInstruction(IROpcode.STORE, IRMemory(var_op), [val_op]))
            return val_op

        if isinstance(node.target, MemberAccessExpr):
            addr = self._emit_aggregate_address_of_lvalue(node.target)
            self._add_instruction(IRInstruction(IROpcode.STORE, IRMemory(addr), [val_op]))
            return val_op

        return val_op

    def visit_identifier(self, node: IdentifierExpr) -> Any:
        var_op = self._resolve_ir_var(node.name)
        node_type = self.decorated_ast.get_type(node)
        temp = self._new_temp(str(node_type) if node_type else None)
        self._add_instruction(IRInstruction(IROpcode.LOAD, temp, [IRMemory(var_op)]))
        return temp

    def visit_literal(self, node: LiteralExpr) -> Any:
        return IRLiteral(node.value)

    def visit_binary(self, node: BinaryExpr) -> Any:
        if node.operator in ("&&", "||"):
            return self._emit_short_circuit(node)

        left_op = node.left.accept(self)
        right_op = node.right.accept(self)

        op_map = {
            "+": IROpcode.ADD,
            "-": IROpcode.SUB,
            "*": IROpcode.MUL,
            "/": IROpcode.DIV,
            "%": IROpcode.MOD,
            "==": IROpcode.CMP_EQ,
            "!=": IROpcode.CMP_NE,
            "<": IROpcode.CMP_LT,
            "<=": IROpcode.CMP_LE,
            ">": IROpcode.CMP_GT,
            ">=": IROpcode.CMP_GE,
            "&&": IROpcode.AND,
            "||": IROpcode.OR,
        }

        node_type = self.decorated_ast.get_type(node)
        temp = self._new_temp(str(node_type) if node_type else None)
        opcode = op_map.get(node.operator, IROpcode.ADD)
        self._add_instruction(IRInstruction(opcode, temp, [left_op, right_op]))
        return temp

    def _emit_short_circuit(self, node: BinaryExpr) -> IRTemp:
        result = self._new_temp("bool")
        rhs_block = BasicBlock(self._new_label("L_sc_rhs"))
        short_block = BasicBlock(self._new_label("L_sc_short"))
        end_block = BasicBlock(self._new_label("L_sc_end"))

        left_op = node.left.accept(self)
        if node.operator == "&&":
            self._add_instruction(IRInstruction(IROpcode.JUMP_IF, None, [left_op, IRLabel(rhs_block.label)]))
            self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(short_block.label)]))
        else:
            self._add_instruction(IRInstruction(IROpcode.JUMP_IF, None, [left_op, IRLabel(short_block.label)]))
            self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(rhs_block.label)]))
        self.current_block.add_successor(rhs_block)
        self.current_block.add_successor(short_block)

        self.current_function.add_block(rhs_block)
        self._switch_block(rhs_block)
        right_op = node.right.accept(self)
        self._add_instruction(IRInstruction(IROpcode.STORE, IRMemory(result), [right_op]))
        self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(end_block.label)]))
        self.current_block.add_successor(end_block)

        self.current_function.add_block(short_block)
        self._switch_block(short_block)
        self._add_instruction(IRInstruction(IROpcode.STORE, IRMemory(result), [IRLiteral(0 if node.operator == "&&" else 1)]))
        self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(end_block.label)]))
        self.current_block.add_successor(end_block)

        self.current_function.add_block(end_block)
        self._switch_block(end_block)
        loaded = self._new_temp("bool")
        self._add_instruction(IRInstruction(IROpcode.LOAD, loaded, [IRMemory(result)]))
        return loaded

    def visit_unary(self, node: UnaryExpr) -> Any:
        operand = node.operand.accept(self)
        temp = self._new_temp()
        if node.operator == "-":
            self._add_instruction(IRInstruction(IROpcode.NEG, temp, [operand]))
        elif node.operator == "!":
            self._add_instruction(IRInstruction(IROpcode.NOT, temp, [operand]))
        return temp

    def visit_call(self, node: CallExpr) -> Any:
        arg_ops = [arg.accept(self) for arg in node.arguments]
        for i, arg in enumerate(arg_ops):
            self._add_instruction(IRInstruction(IROpcode.PARAM, None, [IRLiteral(i), arg]))

        node_type = self.decorated_ast.get_type(node)
        temp = self._new_temp(str(node_type) if node_type else None)
        self._add_instruction(
            IRInstruction(IROpcode.CALL, temp, [IRLabel(node.callee), IRLiteral(len(arg_ops))])
        )
        return temp

    def visit_return(self, node: ReturnStmt) -> Any:
        ret_val = None
        if node.value:
            ret_val = node.value.accept(self)

        self._add_instruction(IRInstruction(IROpcode.RETURN, None, [ret_val] if ret_val else []))
        self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(self.current_function.exit_block.label)]))
        return None

    def visit_if(self, node: IfStmt) -> Any:
        cond_op = node.condition.accept(self)

        then_block = BasicBlock(self._new_label("L_then"))
        then_block.comment = "then branch"
        else_block = BasicBlock(self._new_label("L_else"))
        else_block.comment = "else branch"
        end_block = BasicBlock(self._new_label("L_endif"))
        end_block.comment = "endif (join point)"

        if node.else_branch:
            self._add_instruction(IRInstruction(IROpcode.JUMP_IF, None, [cond_op, IRLabel(then_block.label)]))
            self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(else_block.label)]))

            self.current_block.add_successor(then_block)
            self.current_block.add_successor(else_block)
        else:
            self._add_instruction(IRInstruction(IROpcode.JUMP_IF, None, [cond_op, IRLabel(then_block.label)]))
            self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(end_block.label)]))

            self.current_block.add_successor(then_block)
            self.current_block.add_successor(end_block)

        self.current_function.add_block(then_block)
        self._switch_block(then_block)
        node.then_branch.accept(self)
        self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(end_block.label)]))
        self.current_block.add_successor(end_block)

        if node.else_branch:
            self.current_function.add_block(else_block)
            self._switch_block(else_block)
            node.else_branch.accept(self)
            self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(end_block.label)]))
            self.current_block.add_successor(end_block)

        self.current_function.add_block(end_block)
        self._switch_block(end_block)

        return None

    def visit_while(self, node: WhileStmt) -> Any:
        cond_block = BasicBlock(self._new_label("L_while_cond"))
        body_block = BasicBlock(self._new_label("L_while_body"))
        end_block = BasicBlock(self._new_label("L_while_end"))

        self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(cond_block.label)]))
        self.current_block.add_successor(cond_block)

        self.current_function.add_block(cond_block)
        self._switch_block(cond_block)
        cond_op = node.condition.accept(self)

        self._add_instruction(IRInstruction(IROpcode.JUMP_IF, None, [cond_op, IRLabel(body_block.label)]))
        self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(end_block.label)]))
        self.current_block.add_successor(body_block)
        self.current_block.add_successor(end_block)

        self.current_function.add_block(body_block)
        self._switch_block(body_block)
        self._control_stack.append({"break": end_block.label, "continue": cond_block.label})
        node.body.accept(self)
        self._control_stack.pop()
        self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(cond_block.label)]))
        self.current_block.add_successor(cond_block)

        self.current_function.add_block(end_block)
        self._switch_block(end_block)
        return None

    def visit_for(self, node: ForStmt) -> Any:
        if node.init:
            node.init.accept(self)

        cond_block = BasicBlock(self._new_label("L_for_cond"))
        body_block = BasicBlock(self._new_label("L_for_body"))
        update_block = BasicBlock(self._new_label("L_for_update"))
        end_block = BasicBlock(self._new_label("L_for_end"))

        self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(cond_block.label)]))
        self.current_block.add_successor(cond_block)

        self.current_function.add_block(cond_block)
        self._switch_block(cond_block)
        if node.condition:
            cond_op = node.condition.accept(self)
            self._add_instruction(IRInstruction(IROpcode.JUMP_IF, None, [cond_op, IRLabel(body_block.label)]))
            self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(end_block.label)]))
            self.current_block.add_successor(body_block)
            self.current_block.add_successor(end_block)
        else:
            self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(body_block.label)]))
            self.current_block.add_successor(body_block)

        self.current_function.add_block(body_block)
        self._switch_block(body_block)
        self._control_stack.append({"break": end_block.label, "continue": update_block.label})
        node.body.accept(self)
        self._control_stack.pop()
        self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(update_block.label)]))
        self.current_block.add_successor(update_block)

        self.current_function.add_block(update_block)
        self._switch_block(update_block)
        if node.update:
            node.update.accept(self)
        self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(cond_block.label)]))
        self.current_block.add_successor(cond_block)

        self.current_function.add_block(end_block)
        self._switch_block(end_block)
        return None

    def visit_incdec(self, node: IncDecExpr) -> Any:
        if isinstance(node.target, IdentifierExpr):
            var_op = self._resolve_ir_var(node.target.name)

            temp_old = self._new_temp()
            self._add_instruction(IRInstruction(IROpcode.LOAD, temp_old, [IRMemory(var_op)]))

            op = IROpcode.ADD if node.operator == "++" else IROpcode.SUB
            temp_new = self._new_temp()
            self._add_instruction(IRInstruction(op, temp_new, [temp_old, IRLiteral(1)]))
            self._add_instruction(IRInstruction(IROpcode.STORE, IRMemory(var_op), [temp_new]))

            return temp_new if node.prefix else temp_old
        return None

    def visit_break(self, node: BreakStmt) -> Any:
        for ctx in reversed(self._control_stack):
            br = ctx.get("break")
            if br:
                self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(br)]))
                return None
        return None

    def visit_continue(self, node: ContinueStmt) -> Any:
        for ctx in reversed(self._control_stack):
            cont = ctx.get("continue")
            if cont:
                self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(cont)]))
                return None
        return None

    def visit_switch_case(self, node: SwitchCase) -> Any:
        return None

    def visit_switch(self, node: SwitchStmt) -> Any:
        cond_op = node.expression.accept(self)
        end_block = BasicBlock(self._new_label("L_switch_end"))
        default_block = BasicBlock(self._new_label("L_switch_default")) if node.default_body else end_block
        case_blocks = [BasicBlock(self._new_label("L_switch_case")) for _ in node.cases]

        for i, case_node in enumerate(node.cases):
            case_val = case_node.value.accept(self)
            cmp_tmp = self._new_temp("bool")
            self._add_instruction(IRInstruction(IROpcode.CMP_EQ, cmp_tmp, [cond_op, case_val]))
            self._add_instruction(IRInstruction(IROpcode.JUMP_IF, None, [cmp_tmp, IRLabel(case_blocks[i].label)]))
            self.current_block.add_successor(case_blocks[i])

        self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(default_block.label)]))
        self.current_block.add_successor(default_block)

        self._control_stack.append({"break": end_block.label, "continue": None})
        for i, case_node in enumerate(node.cases):
            self.current_function.add_block(case_blocks[i])
            self._switch_block(case_blocks[i])
            for stmt in case_node.body:
                stmt.accept(self)
            if i + 1 < len(case_blocks):
                self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(case_blocks[i + 1].label)]))
                self.current_block.add_successor(case_blocks[i + 1])
            else:
                self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(default_block.label if node.default_body else end_block.label)]))
                self.current_block.add_successor(default_block if node.default_body else end_block)

        if node.default_body:
            self.current_function.add_block(default_block)
            self._switch_block(default_block)
            for stmt in node.default_body:
                stmt.accept(self)
            self._add_instruction(IRInstruction(IROpcode.JUMP, None, [IRLabel(end_block.label)]))
            self.current_block.add_successor(end_block)

        self._control_stack.pop()
        self.current_function.add_block(end_block)
        self._switch_block(end_block)
        return None

    def visit_empty_stmt(self, node: EmptyStmt) -> Any:
        return None

    def visit_param(self, node: Param) -> Any:
        return None

    def visit_struct_decl(self, node: StructDecl) -> Any:
        return None

    def visit_member_access(self, node: MemberAccessExpr) -> Any:
        addr_temp = self._emit_aggregate_address_of_lvalue(node)
        node_type = self.decorated_ast.get_type(node)
        val_temp = self._new_temp(str(node_type) if node_type else None)
        self._add_instruction(IRInstruction(IROpcode.LOAD, val_temp, [IRMemory(addr_temp)]))
        return val_temp
