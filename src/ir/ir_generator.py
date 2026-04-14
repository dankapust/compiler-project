from typing import Any
from parser.ast import (
    ASTVisitor, ProgramNode, LiteralExpr, IdentifierExpr, MemberAccessExpr,
    BinaryExpr, UnaryExpr, CallExpr, AssignmentExpr, IncDecExpr,
    BlockStmt, ExprStmt, IfStmt, WhileStmt, ForStmt, ReturnStmt,
    VarDeclStmt, EmptyStmt, Param, FunctionDecl, StructDecl
)
from semantic.type_system import Type
from semantic.analyzer import DecoratedAST, SymbolTable, SymbolKind
from .ir_instructions import (
    IROpcode, IRInstruction, IRTemp, IRLiteral, IRVar, IRLabel, IRMemory, IROperand
)
from .basic_block import BasicBlock, IRFunction, IRProgram


class IRGenerator(ASTVisitor):
    def __init__(self, symbol_table: SymbolTable, decorated_ast: DecoratedAST):
        self.symbol_table = symbol_table
        self.decorated_ast = decorated_ast
        self.program = IRProgram()

        self._temp_counter = 0
        self._label_counter = 0

        self.current_function: IRFunction | None = None
        self.current_block: BasicBlock | None = None

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
            params=[(p.param_type, p.name) for p in node.params]
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
        scope_depth = self.symbol_table.scope_depth()
        var_op = IRVar(f"{node.name}_{scope_depth}")

        self._add_instruction(IRInstruction(IROpcode.ALLOCA, var_op, []))

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
            var_op = IRVar(f"{node.target.name}_{self.symbol_table.scope_depth()}")
            self._add_instruction(IRInstruction(IROpcode.STORE, IRMemory(var_op), [val_op]))
            return val_op

        elif isinstance(node.target, MemberAccessExpr):
            pass

        return val_op

    def visit_identifier(self, node: IdentifierExpr) -> Any:
        var_op = IRVar(f"{node.name}_{self.symbol_table.scope_depth()}")
        node_type = self.decorated_ast.get_type(node)
        temp = self._new_temp(str(node_type) if node_type else None)
        self._add_instruction(IRInstruction(IROpcode.LOAD, temp, [IRMemory(var_op)]))
        return temp

    def visit_literal(self, node: LiteralExpr) -> Any:
        return IRLiteral(node.value)

    def visit_binary(self, node: BinaryExpr) -> Any:
        left_op = node.left.accept(self)
        right_op = node.right.accept(self)

        op_map = {
            "+": IROpcode.ADD, "-": IROpcode.SUB, "*": IROpcode.MUL,
            "/": IROpcode.DIV, "%": IROpcode.MOD,
            "==": IROpcode.CMP_EQ, "!=": IROpcode.CMP_NE,
            "<": IROpcode.CMP_LT, "<=": IROpcode.CMP_LE,
            ">": IROpcode.CMP_GT, ">=": IROpcode.CMP_GE,
            "&&": IROpcode.AND, "||": IROpcode.OR
        }

        node_type = self.decorated_ast.get_type(node)
        temp = self._new_temp(str(node_type) if node_type else None)
        opcode = op_map.get(node.operator, IROpcode.ADD)
        self._add_instruction(IRInstruction(opcode, temp, [left_op, right_op]))
        return temp

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
        self._add_instruction(IRInstruction(IROpcode.CALL, temp, [IRLabel(node.callee), IRLiteral(len(arg_ops))]))
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
        else_block = BasicBlock(self._new_label("L_else"))
        end_block = BasicBlock(self._new_label("L_endif"))

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
        
        # GEN-4: PHI nodes for values merging at join points
        # Placeholder for SSA version:
        # self._add_instruction(IRInstruction(IROpcode.PHI, self._new_temp(), [
        #     IRPhiParam(v1, IRLabel(then_block.label)),
        #     IRPhiParam(v2, IRLabel(else_block.label))
        # ]))
        
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
        node.body.accept(self)
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
        node.body.accept(self)
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
            var_op = IRVar(f"{node.target.name}_{self.symbol_table.scope_depth()}")

            temp_old = self._new_temp()
            self._add_instruction(IRInstruction(IROpcode.LOAD, temp_old, [IRMemory(var_op)]))

            op = IROpcode.ADD if node.operator == "++" else IROpcode.SUB
            temp_new = self._new_temp()
            self._add_instruction(IRInstruction(op, temp_new, [temp_old, IRLiteral(1)]))
            self._add_instruction(IRInstruction(IROpcode.STORE, IRMemory(var_op), [temp_new]))

            return temp_new if node.prefix else temp_old
        return None

    def visit_empty_stmt(self, node: EmptyStmt) -> Any:
        return None

    def visit_param(self, node: Param) -> Any:
        return None

    def visit_struct_decl(self, node: StructDecl) -> Any:
        return None

    def visit_member_access(self, node: MemberAccessExpr) -> Any:
        base_op = node.object.accept(self)
        field_name = node.member
        
        node_type = self.decorated_ast.get_type(node)
        addr_temp = self._new_temp(f"{node_type}*")
        # GEP dest, base, field
        self._add_instruction(IRInstruction(IROpcode.GEP, addr_temp, [base_op, IRVar(field_name)]))
        
        val_temp = self._new_temp(str(node_type) if node_type else None)
        self._add_instruction(IRInstruction(IROpcode.LOAD, val_temp, [IRMemory(addr_temp)]))
        return val_temp
