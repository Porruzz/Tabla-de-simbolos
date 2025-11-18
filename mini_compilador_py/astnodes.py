# astnodes.py
"""
Definición de nodos de AST para el mini-compilador basado en la
gramática PEG de Python.

Diseño:
- Separamos la jerarquía en:
    * Node  : base de todos los nodos
    * Stmt  : base para sentencias
    * Expr  : base para expresiones

- Incluimos nodos suficientes para representar:
    * Programa (lista de sentencias)
    * Asignaciones
    * Expresiones aritméticas, lógicas y de comparación
    * Llamadas a función, atributos, subíndices
    * Estructuras de control básicas (if, while, for)
    * Definiciones de función y retornos

Puedes extender este módulo sin romper nada si agregas nuevos nodos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Union


# ==========================================================
#  BASES
# ==========================================================

class Node:
    """Nodo base de todo el AST."""
    pass


class Stmt(Node):
    """Nodo base para todas las sentencias."""
    pass


class Expr(Node):
    """Nodo base para todas las expresiones."""
    pass


# ==========================================================
#  PROGRAMA / MÓDULO
# ==========================================================

@dataclass
class Program(Node):
    """
    Representa el archivo completo:

        Program(body=[sent1, sent2, ...])
    """
    body: List[Stmt] = field(default_factory=list)


# ==========================================================
#  EXPRESIONES BÁSICAS
# ==========================================================

@dataclass
class Name(Expr):
    """
    Identificador, por ejemplo: a, total, _x
    """
    id: str


@dataclass
class Num(Expr):
    """
    Constante numérica (int o float).
    """
    value: float


@dataclass
class Str(Expr):
    """
    Constante de cadena, por ejemplo: "hola".
    """
    value: str


@dataclass
class Bool(Expr):
    """
    Constante booleana: True o False.
    """
    value: bool


@dataclass
class NoneLiteral(Expr):
    """
    Constante None.
    """
    pass


# ==========================================================
#  EXPRESIONES COMPUESTAS
# ==========================================================

@dataclass
class BinOp(Expr):
    """
    Operación binaria aritmética / bit a bit:

        left op right

    Donde op puede ser: '+', '-', '*', '/', '//', '%', '@',
    '<<', '>>', '&', '|', '^', '**'
    """
    left: Expr
    op: str
    right: Expr


@dataclass
class UnaryOp(Expr):
    """
    Operador unario:

        +expr, -expr, ~expr, not expr

    Donde op puede ser: '+', '-', '~', 'not'
    """
    op: str
    operand: Expr


@dataclass
class BoolOp(Expr):
    """
    Operaciones lógicas encadenadas:

        expr1 and expr2 and expr3
        expr1 or expr2 or expr3

    op: 'and' o 'or'
    """
    op: str
    values: List[Expr]


@dataclass
class Compare(Expr):
    """
    Comparaciones encadenadas:

        left op1 right1 op2 right2 ...

    Ejemplo:
        a < b <= c

    ops: lista de strings con cada operador ('<', '==', 'is', 'in', 'not in', etc.)
    comparators: lista de Expr (right1, right2, ...)
    """
    left: Expr
    ops: List[str]
    comparators: List[Expr]


@dataclass
class Call(Expr):
    """
    Llamada a función:

        func(args, kwargs...)

    args: lista de argumentos posicionales
    keywords: pares (nombre, valor) para kwargs
    """
    func: Expr
    args: List[Expr] = field(default_factory=list)
    keywords: List["KeywordArg"] = field(default_factory=list)


@dataclass
class KeywordArg(Node):
    """
    Argumento con nombre en una llamada:

        name=value
    """
    name: str
    value: Expr


@dataclass
class Attribute(Expr):
    """
    Acceso a atributo:

        value.attr
    """
    value: Expr
    attr: str


@dataclass
class Subscript(Expr):
    """
    Acceso por índice o slice:

        value[slice]
    """
    value: Expr
    slice: "Slice"


@dataclass
class Slice(Node):
    """
    Slice simple o extendido:

        start:stop:step (cualquiera puede ser None)
    """
    start: Optional[Expr]
    stop: Optional[Expr]
    step: Optional[Expr]


# ==========================================================
#  SENTENCIAS
# ==========================================================

@dataclass
class ExprStmt(Stmt):
    """
    Sentencia de expresión:

        expr
    """
    value: Expr


@dataclass
class Assign(Stmt):
    """
    Asignación simple:

        targets = value

    Para este proyecto usaremos típicamente un solo target,
    pero la lista permite (a, b) = expr, etc.
    """
    targets: List[Expr]
    value: Expr


@dataclass
class AugAssign(Stmt):
    """
    Asignación aumentada:

        target op= value

    Ejemplo: a += 1
    """
    target: Expr
    op: str   # '+=', '-=', '*=', '/=', etc.
    value: Expr


@dataclass
class Return(Stmt):
    """
    Sentencia return:

        return value
    """
    value: Optional[Expr] = None


@dataclass
class Pass(Stmt):
    """Sentencia 'pass'."""
    pass


@dataclass
class Break(Stmt):
    """Sentencia 'break'."""
    pass


@dataclass
class Continue(Stmt):
    """Sentencia 'continue'."""
    pass


@dataclass
class If(Stmt):
    """
    Sentencia if / elif / else:

        if test:
            body
        elif test2:
            orelse_if
        else:
            orelse

    Se modela como:
        test, body, orelse (lista de Stmt)
    Donde orelse puede contener otro If (elif) o un bloque simple (else).
    """
    test: Expr
    body: List[Stmt] = field(default_factory=list)
    orelse: List[Stmt] = field(default_factory=list)


@dataclass
class While(Stmt):
    """
    Sentencia while:

        while test:
            body
        else:
            orelse
    """
    test: Expr
    body: List[Stmt] = field(default_factory=list)
    orelse: List[Stmt] = field(default_factory=list)


@dataclass
class For(Stmt):
    """
    Sentencia for:

        for target in iter:
            body
        else:
            orelse
    """
    target: Expr
    iter: Expr
    body: List[Stmt] = field(default_factory=list)
    orelse: List[Stmt] = field(default_factory=list)


# ==========================================================
#  FUNCIONES
# ==========================================================

@dataclass
class Arg(Node):
    """
    Parámetro de función:

        nombre: tipo? = default?

    Para simplificar:
        - annotation y default son opcionales y pueden ser Expr
    """
    name: str
    annotation: Optional[Expr] = None
    default: Optional[Expr] = None


@dataclass
class Arguments(Node):
    """
    Conjunto de parámetros de función (muy simplificado respecto a Python real).
    Considera solo posicionales con default opcional.
    """
    args: List[Arg] = field(default_factory=list)


@dataclass
class FunctionDef(Stmt):
    """
    Definición de función:

        def name(args):
            body

    Para simplificar:
        - no se manejan decoradores aquí (se pueden agregar luego)
        - returns: anotación de tipo de retorno opcional
    """
    name: str
    args: Arguments
    body: List[Stmt] = field(default_factory=list)
    returns: Optional[Expr] = None
    decorators: List[Expr] = field(default_factory=list)


# ==========================================================
#  UTILIDADES
# ==========================================================

def pretty_print(node: Node, indent: int = 0) -> None:
    """
    Imprime el AST de forma legible para depuración.
    No es obligatorio usarlo en el compilador, pero ayuda muchísimo
    para entender que está generando el parser.
    """
    prefix = "  " * indent
    if isinstance(node, list):
        print(prefix + "[")
        for item in node:
            pretty_print(item, indent + 1)
        print(prefix + "]")
        return

    if not isinstance(node, Node):
        print(prefix + repr(node))
        return

    cls_name = node.__class__.__name__
    print(f"{prefix}{cls_name}(")
    for field_name in getattr(node, "__dataclass_fields__", {}):
        value = getattr(node, field_name)
        print(f"{prefix}  {field_name} = ", end="")
        if isinstance(value, Node) or isinstance(value, list):
            print()
            pretty_print(value, indent + 2)
        else:
            print(repr(value))
    print(f"{prefix})")
