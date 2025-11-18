# symtable.py
"""
Tabla de símbolos para el mini-compilador basado en la gramática PEG de Python.

Objetivos:
- Llevar registro de:
    * variables
    * parámetros de funciones
    * funciones (nombre, parámetros, tipo de retorno)
- Soportar scopes anidados:
    * global
    * local de función
    * (podrías extender a clases, comprensiones, etc.)

Diseño:
- SymbolEntry: entrada individual en la tabla (nombre, tipo, clase de símbolo, etc.)
- SymbolTable: un scope con:
    * diccionario name -> SymbolEntry
    * referencia al scope padre
- SymbolTableStack: helper para manejar el scope actual como stack (push/pop)

No hacemos inferencia de tipos real; para el proyecto usaremos strings simples
como "int", "float", "str", "bool", "function", etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, List


# ==========================================================
#  CLASES BÁSICAS
# ==========================================================

@dataclass
class SymbolEntry:
    """
    Entrada de símbolo en la tabla:

    Atributos:
        name        : nombre del identificador
        kind        : clase de símbolo (por ejemplo: 'variable', 'function', 'param')
        typ         : tipo del símbolo (string simple: 'int', 'float', 'str', etc.)
        scope_name  : nombre del scope lógico al que pertenece (p. ej. 'global', nombre de función)
        offset      : posición relativa (opcional) para uso posterior en generación de código
    """
    name: str
    kind: str
    typ: str
    scope_name: str
    offset: Optional[int] = None

    def __repr__(self) -> str:
        return (
            f"SymbolEntry(name={self.name!r}, kind={self.kind!r}, "
            f"type={self.typ!r}, scope={self.scope_name!r}, offset={self.offset!r})"
        )


class SymbolTable:
    """
    Representa un scope (tabla de símbolos) con un padre opcional.

    Ejemplo de cadena de scopes:
        global (padre=None)
            └── función foo (padre=global)
                    └── sub-scope (if, while, etc.) (padre=foo)
    """

    def __init__(self, scope_name: str = "global", parent: Optional["SymbolTable"] = None):
        self.scope_name: str = scope_name
        self.parent: Optional["SymbolTable"] = parent
        self.entries: Dict[str, SymbolEntry] = {}

    # -------------------------
    #  Operaciones básicas
    # -------------------------

    def define(self, name: str, kind: str = "variable", typ: str = "unknown") -> SymbolEntry:
        """
        Crea una nueva entrada en el scope actual.

        Si el símbolo ya existe en ESTE scope, lanza excepción.
        (No mira en los padres; eso permite shadowing correctamente.)
        """
        if name in self.entries:
            raise RuntimeError(
                f"Símbolo redeclarado en scope '{self.scope_name}': {name}"
            )

        entry = SymbolEntry(
            name=name,
            kind=kind,
            typ=typ,
            scope_name=self.scope_name,
        )
        self.entries[name] = entry
        return entry

    def lookup_local(self, name: str) -> Optional[SymbolEntry]:
        """
        Busca un símbolo SOLO en el scope actual.
        """
        return self.entries.get(name)

    def lookup(self, name: str) -> Optional[SymbolEntry]:
        """
        Busca un símbolo en este scope y, si no está,
        recorre recursivamente los scopes padres.
        """
        entry = self.lookup_local(name)
        if entry is not None:
            return entry
        if self.parent is not None:
            return self.parent.lookup(name)
        return None

    def __repr__(self) -> str:
        entries_str = ", ".join(
            f"{name}: {entry!r}" for name, entry in self.entries.items()
        )
        return f"SymbolTable(scope={self.scope_name!r}, entries={{ {entries_str} }})"


# ==========================================================
#  PILA DE TABLAS (MANEJO DE SCOPES)
# ==========================================================

class SymbolTableStack:
    """
    Helper para manejar scopes como una pila:

        stack = SymbolTableStack()
        stack.push_scope("global")
        ...
        stack.push_scope("func foo")
        ...
        stack.pop_scope()
    """

    def __init__(self):
        self.stack: List[SymbolTable] = []

    # -------------------------
    #  Gestión de la pila
    # -------------------------

    def push_scope(self, scope_name: str) -> SymbolTable:
        """
        Crea un nuevo scope (SymbolTable) como hijo del scope actual
        y lo pone en la cima de la pila. Si la pila está vacía, el padre
        es None (scope raíz).
        """
        parent = self.stack[-1] if self.stack else None
        table = SymbolTable(scope_name=scope_name, parent=parent)
        self.stack.append(table)
        return table

    def pop_scope(self) -> SymbolTable:
        """
        Saca el scope actual de la pila y lo devuelve.
        """
        if not self.stack:
            raise RuntimeError("Intento de pop_scope() con pila de scopes vacía")
        return self.stack.pop()

    @property
    def current_scope(self) -> SymbolTable:
        """
        Devuelve el scope actual (cima de la pila).
        """
        if not self.stack:
            raise RuntimeError("No hay scope actual: la pila está vacía")
        return self.stack[-1]

    # -------------------------
    #  Atajos sobre el scope actual
    # -------------------------

    def define(self, name: str, kind: str = "variable", typ: str = "unknown") -> SymbolEntry:
        """
        Define un símbolo en el scope actual.
        """
        return self.current_scope.define(name, kind=kind, typ=typ)

    def lookup(self, name: str) -> Optional[SymbolEntry]:
        """
        Busca un símbolo a partir del scope actual hacia los padres.
        """
        return self.current_scope.lookup(name)

    def __repr__(self) -> str:
        return "SymbolTableStack(" + " -> ".join(
            f"{table.scope_name}" for table in self.stack
        ) + ")"
