# main.py
"""
main.py – Driver del mini–compilador para el subconjunto de Python

Pipeline completo:
    1. Lexer  : convierte el código fuente en tokens.
    2. Parser : construye el AST y llena la tabla de símbolos.
    3. 3AC    : genera código en tres direcciones a partir del AST.

Uso desde terminal (en Kali Linux):

    python3 main.py programa.py
    python3 main.py programa.py --tokens
    python3 main.py programa.py --ast
    python3 main.py programa.py --symtable
    python3 main.py programa.py --3ac
    python3 main.py programa.py --tokens --ast --symtable --3ac

Si no pasas flags, se muestran AST y 3AC por defecto.
"""

from __future__ import annotations

import argparse
import sys
from typing import List

from lexer import Lexer
from parser import Parser
from astnodes import Program, pretty_print
from codegen3ac import CodeGenerator3AC, TACInstr


def read_source(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        print(f"Error al leer archivo '{path}': {e}", file=sys.stderr)
        sys.exit(1)


def run_pipeline(
    source: str,
    show_tokens: bool = False,
    show_ast: bool = False,
    show_symtable: bool = False,
    show_3ac: bool = False,
) -> None:
    # 1) LEXER
    lexer = Lexer(source)
    tokens = lexer.tokenize()

    if show_tokens:
        print("=== TOKENS ===")
        for t in tokens:
            print(t)
        print()

    # 2) PARSER (usamos la clase Parser para poder acceder a la tabla de símbolos)
    parser = Parser(tokens)
    program: Program = parser.parse()

    if show_ast:
        print("=== AST (árbol de sintaxis abstracta) ===")
        pretty_print(program)
        print()

    if show_symtable:
        print("=== TABLAS DE SÍMBOLOS (ETDS) ===")
        # La pila de scopes suele terminar solo con el global,
        # porque los scopes de función se van haciendo pop al terminar de parsear.
        # Aun así mostramos todos los scopes que estén en la pila.
        for table in parser.symstack.stack:
            print(f"Scope: {table.scope_name}")
            if not table.entries:
                print("  (sin símbolos)")
            else:
                for name, entry in table.entries.items():
                    print(f"  {name}: {entry}")
            print()
        print()

    # 3) GENERACIÓN DE CÓDIGO EN TRES DIRECCIONES
    if show_3ac:
        print("=== CÓDIGO EN TRES DIRECCIONES (3AC) ===")
        gen = CodeGenerator3AC()
        tac: List[TACInstr] = gen.generate(program)
        for instr in tac:
            print(instr)
        print()


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Mini–compilador para un subconjunto de Python (lexer + parser + 3AC)"
    )
    p.add_argument(
        "archivo",
        help="Archivo fuente a compilar (usa '-' para leer desde stdin)",
    )
    p.add_argument(
        "--tokens",
        action="store_true",
        help="Mostrar la lista de tokens generados por el lexer",
    )
    p.add_argument(
        "--ast",
        action="store_true",
        help="Mostrar el AST generado por el parser",
    )
    p.add_argument(
        "--symtable",
        action="store_true",
        help="Mostrar las tablas de símbolos (ETDS) generadas",
    )
    p.add_argument(
        "--3ac",
        action="store_true",
        help="Mostrar el código en tres direcciones generado",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_argparser()
    args = parser.parse_args(argv)

    source = read_source(args.archivo)

    # Si no se pasa ninguna bandera, por defecto mostramos AST y 3AC
    if not (args.tokens or args.ast or args.symtable or args._get_kwargs()):
        # (fallback por si algo raro pasa con argparse)
        args.ast = True
        args.symtable = True
        args._3ac = True

    # Manejo standard: si no hay flags, AST + 3AC
    if not (args.tokens or args.ast or args.symtable or args.__dict__.get("3ac")):
        show_tokens = False
        show_ast = True
        show_symtable = False
        show_3ac = True
    else:
        show_tokens = args.tokens
        show_ast = args.ast
        show_symtable = args.symtable
        # argparse no permite nombre de arg que empiece por número como atributo,
        # así que lo obtenemos así:
        show_3ac = getattr(args, "3ac")

    run_pipeline(
        source,
        show_tokens=show_tokens,
        show_ast=show_ast,
        show_symtable=show_symtable,
        show_3ac=show_3ac,
    )


if __name__ == "__main__":
    main()
