# codegen3ac.py
"""
Generador de Código en Tres Direcciones (3AC) para el AST del mini-compilador.

Toma el AST construido por `parser.py` (nodos definidos en `astnodes.py`) y
produce una lista de instrucciones de 3 direcciones (cuádruplas).

El objetivo es tener una representación intermedia (IR) clara para:
- visualizar el flujo de control
- analizar y optimizar
- servir de base para una futura generación de código máquina / bytecode

Convención general de 3AC aquí:
    result = arg1 op arg2
    if_false cond goto Lx
    goto Lx
    label Lx
    return value
    param arg
    call func, n_args, result

No es una implementación 100% de Python real, sino un subconjunto coherente
con el parser que ya construimos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from astnodes import (
    Program,
    Stmt, Expr,
    ExprStmt,
    Assign,
    AugAssign,
    Return,
    Pass,
    Break,
    Continue,
    If,
    While,
    For,
    FunctionDef,
    Arguments,
    Arg,
    Name,
    Num,
    Str,
    Bool,
    NoneLiteral,
    BinOp,
    UnaryOp,
    BoolOp,
    Compare,
    Call,
    KeywordArg,
    Attribute,
    Subscript,
    Slice,
)


# ==========================================================
#  Representación de instrucción 3AC
# ==========================================================

@dataclass
class TACInstr:
    """
    Instrucción de código en tres direcciones.

    Campos:
        op      : operación (string), ej. '+', '-', 'if_false_goto', 'call', 'label'
        arg1    : primer operando (string o None)
        arg2    : segundo operando (string o None)
        result  : destino (string o None)
        label   : nombre de etiqueta si aplica (para op='label' o saltos)
        comment : comentario opcional
    """
    op: str
    arg1: Optional[str] = None
    arg2: Optional[str] = None
    result: Optional[str] = None
    label: Optional[str] = None
    comment: Optional[str] = None

    def __str__(self) -> str:
        parts = []

        # Etiqueta (L1:) al inicio si existe
        if self.label:
            parts.append(f"{self.label}:")

        # Instrucciones "especiales"
        if self.op == "label":
            # solo la etiqueta
            pass
        elif self.op == "goto":
            parts.append(f"goto {self.result}")
        elif self.op == "if_false_goto":
            parts.append(f"if_false {self.arg1} goto {self.result}")
        elif self.op == "return":
            if self.arg1 is not None:
                parts.append(f"return {self.arg1}")
            else:
                parts.append("return")
        elif self.op == "param":
            parts.append(f"param {self.arg1}")
        elif self.op == "call":
            # call func, n_args, result
            if self.result:
                parts.append(f"{self.result} = call {self.arg1}, {self.arg2}")
            else:
                parts.append(f"call {self.arg1}, {self.arg2}")
        elif self.op == "func_begin":
            parts.append(f"func_begin {self.result}")
        elif self.op == "func_end":
            parts.append(f"func_end {self.result}")
        else:
            # Forma general result = arg1 op arg2
            if self.result is not None:
                if self.arg2 is not None:
                    parts.append(f"{self.result} = {self.arg1} {self.op} {self.arg2}")
                elif self.arg1 is not None:
                    parts.append(f"{self.result} = {self.op}{self.arg1}")
                else:
                    parts.append(f"{self.result} = {self.op}")
            else:
                # op sin result explícito, muy raro pero lo soportamos
                if self.arg1 is not None and self.arg2 is not None:
                    parts.append(f"{self.arg1} {self.op} {self.arg2}")
                elif self.arg1 is not None:
                    parts.append(f"{self.op} {self.arg1}")
                else:
                    parts.append(self.op)

        if self.comment:
            parts.append(f"    # {self.comment}")

        return " ".join(parts)


# ==========================================================
#  Generador 3AC
# ==========================================================

class CodeGenerator3AC:
    """
    Recorre el AST y genera instrucciones TACInstr.

    Uso:
        from lexer import Lexer
        from parser import parse_tokens
        from codegen3ac import CodeGenerator3AC

        code = open("archivo.py").read()
        tokens = Lexer(code).tokenize()
        ast = parse_tokens(tokens)
        gen = CodeGenerator3AC()
        tac = gen.generate(ast)

        for instr in tac:
            print(instr)
    """

    def __init__(self):
        self.code: List[TACInstr] = []
        self.temp_count = 0
        self.label_count = 0

        # Pilas para manejo de break/continue en bucles
        self.break_stack: List[str] = []
        self.continue_stack: List[str] = []

    # -------------------------
    #  Utilidades
    # -------------------------

    def new_temp(self) -> str:
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self, prefix: str = "L") -> str:
        self.label_count += 1
        return f"{prefix}{self.label_count}"

    def emit(
        self,
        op: str,
        arg1: Optional[str] = None,
        arg2: Optional[str] = None,
        result: Optional[str] = None,
        label: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> TACInstr:
        instr = TACInstr(op=op, arg1=arg1, arg2=arg2, result=result, label=label, comment=comment)
        self.code.append(instr)
        return instr

    def emit_label(self, label: str) -> None:
        self.emit("label", label=label)

    # -------------------------
    #  Entrada principal
    # -------------------------

    def generate(self, program: Program) -> List[TACInstr]:
        self.visit_program(program)
        return self.code

    # ==========================================================
    #  Visitadores de nodos
    # ==========================================================

    # ------ Programa ------
    def visit_program(self, node: Program) -> None:
        for stmt in node.body:
            self.visit_stmt(stmt)

    # ------ Sentencias ------
    def visit_stmt(self, node: Stmt) -> None:
        if isinstance(node, ExprStmt):
            self.visit_exprstmt(node)
        elif isinstance(node, Assign):
            self.visit_assign(node)
        elif isinstance(node, AugAssign):
            self.visit_augassign(node)
        elif isinstance(node, Return):
            self.visit_return(node)
        elif isinstance(node, Pass):
            # no genera código
            pass
        elif isinstance(node, Break):
            self.visit_break(node)
        elif isinstance(node, Continue):
            self.visit_continue(node)
        elif isinstance(node, If):
            self.visit_if(node)
        elif isinstance(node, While):
            self.visit_while(node)
        elif isinstance(node, For):
            self.visit_for(node)
        elif isinstance(node, FunctionDef):
            self.visit_functiondef(node)
        else:
            raise NotImplementedError(f"Sentencia no soportada en 3AC: {type(node).__name__}")

    def visit_exprstmt(self, node: ExprStmt) -> None:
        # evaluamos la expresión y descartamos el resultado (a menos que sea útil por efectos)
        self.visit_expr(node.value)

    def visit_assign(self, node: Assign) -> None:
        """
        targets = value
        Para simplicidad, usamos solo el primer target (lo habitual en este proyecto).
        """
        value_place = self.visit_expr(node.value)
        if not node.targets:
            return

        target = node.targets[0]
        target_place = self.get_lvalue_place(target)
        # Asignación simple en 3AC: target = value
        self.emit("=", arg1=value_place, result=target_place)

    def visit_augassign(self, node: AugAssign) -> None:
        """
        target op= value
        Lo descomponemos en:
            t1 = target
            t2 = t1 (op_base) value
            target = t2
        """
        target_place = self.get_lvalue_place(node.target)
        right_place = self.visit_expr(node.value)

        # Convertimos '+=', '-=' etc a '+', '-' etc.
        op_base = node.op.replace("=", "")  # "+=", "-=", "*=", etc -> "+", "-", "*"
        t = self.new_temp()
        self.emit(op_base, arg1=target_place, arg2=right_place, result=t)
        self.emit("=", arg1=t, result=target_place)

    def visit_return(self, node: Return) -> None:
        if node.value is not None:
            value_place = self.visit_expr(node.value)
            self.emit("return", arg1=value_place)
        else:
            self.emit("return")

    def visit_break(self, node: Break) -> None:
        if not self.break_stack:
            # break fuera de un bucle, generamos algo por defecto
            self.emit("goto", result="__INVALID_BREAK__")
            return
        end_label = self.break_stack[-1]
        self.emit("goto", result=end_label)

    def visit_continue(self, node: Continue) -> None:
        if not self.continue_stack:
            self.emit("goto", result="__INVALID_CONTINUE__")
            return
        cont_label = self.continue_stack[-1]
        self.emit("goto", result=cont_label)

    def visit_if(self, node: If) -> None:
        """
        if test:
            body
        [elif/else modelados en node.orelse]
        """
        cond_place = self.visit_expr(node.test)
        label_else = self.new_label("L_else_")
        label_end = self.new_label("L_end_if_")

        # if_false cond goto else
        self.emit("if_false_goto", arg1=cond_place, result=label_else)

        # cuerpo del if
        for stmt in node.body:
            self.visit_stmt(stmt)

        # salto a fin si hay orelse
        if node.orelse:
            self.emit("goto", result=label_end)

        # else / elif
        self.emit_label(label_else)
        for stmt in node.orelse:
            self.visit_stmt(stmt)

        if node.orelse:
            self.emit_label(label_end)

    def visit_while(self, node: While) -> None:
        """
        while test:
            body
        [else: ...] (no implementamos else en 3AC; se puede extender)
        """
        label_start = self.new_label("L_while_start_")
        label_end = self.new_label("L_while_end_")

        # Registrar labels de bucle
        self.continue_stack.append(label_start)
        self.break_stack.append(label_end)

        self.emit_label(label_start)
        cond_place = self.visit_expr(node.test)
        self.emit("if_false_goto", arg1=cond_place, result=label_end)

        for stmt in node.body:
            self.visit_stmt(stmt)

        # continue salta aquí (label_start)
        self.emit("goto", result=label_start)

        self.emit_label(label_end)

        # Pop de stacks de bucle
        self.continue_stack.pop()
        self.break_stack.pop()

        # (Opcional) while-else se podría implementar aquí usando node.orelse

    def visit_for(self, node: For) -> None:
        """
        for target in iter:
            body
        Representación simplificada en 3AC como un bucle tipo:

            it = iter(...)
            i = 0
            n = len(it)
        L_for_start:
            if_false (i < n) goto L_for_end
            v = it[i]
            target = v
            ...
            i = i + 1
            goto L_for_start
        L_for_end:
        """
        iter_place = self.visit_expr(node.iter)
        idx = self.new_temp()
        length = self.new_temp()

        # i = 0
        self.emit("=", arg1="0", result=idx, comment="for index")
        # n = len(it)
        self.emit("len", arg1=iter_place, result=length, comment="len(iter)")

        label_start = self.new_label("L_for_start_")
        label_end = self.new_label("L_for_end_")

        self.continue_stack.append(label_start)
        self.break_stack.append(label_end)

        self.emit_label(label_start)

        # cond = i < n
        cond = self.new_temp()
        self.emit("<", arg1=idx, arg2=length, result=cond)
        self.emit("if_false_goto", arg1=cond, result=label_end)

        # v = it[i]
        value_temp = self.new_temp()
        self.emit("load_index", arg1=iter_place, arg2=idx, result=value_temp)

        # target = v
        target_place = self.get_lvalue_place(node.target)
        self.emit("=", arg1=value_temp, result=target_place)

        # cuerpo del for
        for stmt in node.body:
            self.visit_stmt(stmt)

        # i = i + 1
        t = self.new_temp()
        self.emit("+", arg1=idx, arg2="1", result=t)
        self.emit("=", arg1=t, result=idx)

        self.emit("goto", result=label_start)
        self.emit_label(label_end)

        self.continue_stack.pop()
        self.break_stack.pop()

    def visit_functiondef(self, node: FunctionDef) -> None:
        """
        func_begin name
        ... cuerpo ...
        func_end name
        """
        func_name = node.name

        # Inicio de función
        self.emit("func_begin", result=func_name)

        # Parámetros (no es obligatorio emitir nada, pero podemos listar param)
        for arg in node.args.args:
            # param nombre_param
            self.emit("param", arg1=arg.name, comment="func param")

        # Cuerpo de la función
        for stmt in node.body:
            self.visit_stmt(stmt)

        # Asegurar un return implícito si no se emitió ninguno explícito
        # (No lo detectamos exactamente; solo añadimos uno vacío al final)
        self.emit("return", comment="implicit return")

        self.emit("func_end", result=func_name)

    # ------ Expresiones ------
    def visit_expr(self, node: Expr) -> str:
        if isinstance(node, Name):
            return node.id
        if isinstance(node, Num):
            # Usamos el literal directo como constante
            return repr(node.value)
        if isinstance(node, Str):
            return repr(node.value)
        if isinstance(node, Bool):
            return "True" if node.value else "False"
        if isinstance(node, NoneLiteral):
            return "None"
        if isinstance(node, BinOp):
            return self.visit_binop(node)
        if isinstance(node, UnaryOp):
            return self.visit_unaryop(node)
        if isinstance(node, BoolOp):
            return self.visit_boolop(node)
        if isinstance(node, Compare):
            return self.visit_compare(node)
        if isinstance(node, Call):
            return self.visit_call(node)
        if isinstance(node, Attribute):
            return self.visit_attribute(node)
        if isinstance(node, Subscript):
            return self.visit_subscript(node)

        raise NotImplementedError(f"Expresión no soportada en 3AC: {type(node).__name__}")

    def visit_binop(self, node: BinOp) -> str:
        left_place = self.visit_expr(node.left)
        right_place = self.visit_expr(node.right)
        result = self.new_temp()
        self.emit(node.op, arg1=left_place, arg2=right_place, result=result)
        return result

    def visit_unaryop(self, node: UnaryOp) -> str:
        operand_place = self.visit_expr(node.operand)
        result = self.new_temp()
        # op puede ser '+', '-', '~', 'not'
        self.emit(node.op, arg1=operand_place, result=result)
        return result

    def visit_boolop(self, node: BoolOp) -> str:
        """
        Para simplificar, no implementamos short-circuiting real.
        Aproximamos: t = v1 op v2 op v3 ...
        """
        if not node.values:
            # Caso degenerado (no debería ocurrir)
            return "False"

        temp = self.visit_expr(node.values[0])

        for expr in node.values[1:]:
            right = self.visit_expr(expr)
            t = self.new_temp()
            self.emit(node.op, arg1=temp, arg2=right, result=t)
            temp = t

        return temp

    def visit_compare(self, node: Compare) -> str:
        """
        Comparaciones encadenadas: a < b < c
        Implementación aproximada:
            t1 = a < b
            t2 = t1 < c   (no equivalente a Python real, pero sirve como IR simple)
        """
        left_place = self.visit_expr(node.left)

        if not node.ops or not node.comparators:
            return left_place

        temp = None
        current_left = left_place

        for op_str, right_expr in zip(node.ops, node.comparators):
            right_place = self.visit_expr(right_expr)
            t = self.new_temp()
            self.emit(op_str, arg1=current_left, arg2=right_place, result=t)
            temp = t
            current_left = temp

        return temp if temp is not None else left_place

    def visit_call(self, node: Call) -> str:
        """
        Llamada a función:

            result = call func, n_args

        Previamente emitimos:
            param arg1
            param arg2
            ...
        NOTA: ignoramos por ahora los keyword args (solo posicionales).
        """
        # Primero evaluamos los args posicionales
        arg_places: List[str] = []
        for arg in node.args:
            arg_places.append(self.visit_expr(arg))

        # Emitimos param para cada arg
        for place in arg_places:
            self.emit("param", arg1=place)

        # Nombre o expresión de la función
        func_place = self.visit_expr(node.func)

        # Número de args posicionales (ignoramos keywords en esta IR)
        n_args = len(arg_places)

        result = self.new_temp()
        self.emit("call", arg1=func_place, arg2=str(n_args), result=result)

        return result

    def visit_attribute(self, node: Attribute) -> str:
        """
        value.attr  -> t = getattr(value, 'attr')
        """
        value_place = self.visit_expr(node.value)
        result = self.new_temp()
        self.emit("getattr", arg1=value_place, arg2=node.attr, result=result)
        return result

    def visit_subscript(self, node: Subscript) -> str:
        """
        value[slice] -> aquí suponemos slice simple: start, sin stop/step.
        Si es start, stop, step, podrías mapear a una operación de slice.
        """
        value_place = self.visit_expr(node.value)
        s = node.slice

        # Caso más simple: solo start (sin stop ni step)
        if s.start is not None and s.stop is None and s.step is None:
            index_place = self.visit_expr(s.start)
            result = self.new_temp()
            self.emit("load_index", arg1=value_place, arg2=index_place, result=result)
            return result

        # Si es un slice completo, usamos un op abstracto "slice"
        start = self.visit_expr(s.start) if s.start is not None else "None"
        stop = self.visit_expr(s.stop) if s.stop is not None else "None"
        step = self.visit_expr(s.step) if s.step is not None else "None"

        result = self.new_temp()
        # Para simplificar, empaquetamos los tres en un pseudo-arg
        slice_descr = f"({start},{stop},{step})"
        self.emit("slice", arg1=value_place, arg2=slice_descr, result=result)
        return result

    # ==========================================================
    #  Utilidad para lvalues
    # ==========================================================

    def get_lvalue_place(self, expr: Expr) -> str:
        """
        Devuelve el "nombre" donde se va a escribir un valor (lvalue).
        Soporta:
            - Name
            - Attribute
            - Subscript
        Para Attribute/Subscript, emitimos operaciones abstractas:
            - store_attr
            - store_index
        Pero devolvemos un nombre simbólico donde se refleja el destino.

        Para uso simple (Asigna a Name), basta con devolver expr.id
        """
        if isinstance(expr, Name):
            return expr.id

        if isinstance(expr, Attribute):
            # obj.attr = value  -> store_attr obj, 'attr', value
            # Aquí devolvemos algo simbólico, pero lo normal será que
            # el generador de asignación use esto de forma directa.
            # Para compatibilidad con Assign/AugAssign, devolvemos
            # un nombre "virtual":
            base = self.visit_expr(expr.value)
            # construimos algo como "base.attr" solo como etiqueta
            return f"{base}.{expr.attr}"

        if isinstance(expr, Subscript):
            base = self.visit_expr(expr.value)
            s = expr.slice
            if s.start is not None and s.stop is None and s.step is None:
                index_place = self.visit_expr(s.start)
                return f"{base}[{index_place}]"
            # slice completo: etiqueta simbólica
            start = self.visit_expr(s.start) if s.start is not None else "None"
            stop = self.visit_expr(s.stop) if s.stop is not None else "None"
            step = self.visit_expr(s.step) if s.step is not None else "None"
            return f"{base}[{start}:{stop}:{step}]"

        raise NotImplementedError("Lvalue no soportado para asignación en 3AC")


# ==========================================================
#  Helper de uso rápido
# ==========================================================

def generate_3ac(program: Program) -> List[TACInstr]:
    """
    Función de conveniencia:
        ast = parse_tokens(tokens)
        3ac = generate_3ac(ast)
    """
    gen = CodeGenerator3AC()
    return gen.generate(program)
