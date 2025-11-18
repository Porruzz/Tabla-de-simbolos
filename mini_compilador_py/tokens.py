# tokens.py
"""
Definición de tipos de tokens y clase Token para el mini-compilador
basado en la gramática PEG de Python.

La idea es:
- El lexer producirá instancias de Token.
- El parser trabajará principalmente con:
    * type  -> clase general del token (NAME, NUMBER, STRING, NEWLINE, etc.)
    * value -> lexema o valor semántico (por ejemplo, 123.4, "if", "a")
    * line / column -> posición para mensajes de error
- Las palabras reservadas de Python se representan con type=NAME
  y value="if", "def", "class", etc. El parser verificará el value
  cuando necesite un keyword específico.
"""

from dataclasses import dataclass
from typing import Any, Set


# =========================
#  TIPOS BÁSICOS DE TOKEN
# =========================

# Tokens de alto nivel / estructurales
TT_NAME        = "NAME"
TT_NUMBER      = "NUMBER"
TT_STRING      = "STRING"

TT_NEWLINE     = "NEWLINE"
TT_INDENT      = "INDENT"
TT_DEDENT      = "DEDENT"
TT_TYPE_COMMENT = "TYPE_COMMENT"

TT_FSTRING_START  = "FSTRING_START"
TT_FSTRING_MIDDLE = "FSTRING_MIDDLE"
TT_FSTRING_END    = "FSTRING_END"

TT_TSTRING_START  = "TSTRING_START"
TT_TSTRING_MIDDLE = "TSTRING_MIDDLE"
TT_TSTRING_END    = "TSTRING_END"

TT_ELLIPSIS    = "ELLIPSIS"     # '...'
TT_ENDMARKER   = "ENDMARKER"    # fin de archivo


# Operadores y signos de puntuación (podemos mapearlos por lexema en el lexer)
TT_PLUS        = "PLUS"         # +
TT_MINUS       = "MINUS"        # -
TT_STAR        = "STAR"         # *
TT_SLASH       = "SLASH"        # /
TT_DOUBLE_SLASH = "DOUBLE_SLASH"  # //
TT_PERCENT     = "PERCENT"      # %
TT_AT          = "AT"           # @
TT_PIPE        = "PIPE"         # |
TT_AMPERSAND   = "AMPERSAND"    # &
TT_CARET       = "CARET"        # ^
TT_TILDE       = "TILDE"        # ~
TT_LSHIFT      = "LSHIFT"       # <<
TT_RSHIFT      = "RSHIFT"       # >>
TT_DOUBLE_STAR = "DOUBLE_STAR"  # **

TT_EQUAL       = "EQUAL"        # =
TT_EQEQUAL     = "EQEQUAL"      # ==
TT_NOTEQUAL    = "NOTEQUAL"     # !=
TT_LESSEQUAL   = "LESSEQUAL"    # <=
TT_GREATEREQUAL = "GREATEREQUAL"  # >=
TT_LESS        = "LESS"         # <
TT_GREATER     = "GREATER"      # >

TT_LPAREN      = "LPAREN"       # (
TT_RPAREN      = "RPAREN"       # )
TT_LBRACKET    = "LBRACKET"     # [
TT_RBRACKET    = "RBRACKET"     # ]
TT_LBRACE      = "LBRACE"       # {
TT_RBRACE      = "RBRACE"       # }

TT_COMMA       = "COMMA"        # ,
TT_COLON       = "COLON"        # :
TT_SEMI        = "SEMI"         # ;
TT_DOT         = "DOT"          # .
TT_ARROW       = "ARROW"        # ->
TT_PLUSEQUAL   = "PLUSEQUAL"    # +=
TT_MINEQUAL    = "MINEQUAL"     # -=
TT_STAREQUAL   = "STAREQUAL"    # *=
TT_SLASHEQUAL  = "SLASHEQUAL"   # /=
TT_PERCENTEQUAL = "PERCENTEQUAL" # %=
TT_ATEQUAL     = "ATEQUAL"      # @=
TT_AMPEREQUAL  = "AMPEREQUAL"   # &=
TT_PIPEEQUAL   = "PIPEEQUAL"    # |=
TT_CARETEQUAL  = "CARETEQUAL"   # ^=
TT_LSHIFTEQUAL = "LSHIFTEQUAL"  # <<=
TT_RSHIFTEQUAL = "RSHIFTEQUAL"  # >>=
TT_DOUBLE_STAREQUAL = "DOUBLE_STAREQUAL"  # **=
TT_DOUBLE_SLASHEQUAL = "DOUBLE_SLASHEQUAL"  # //=


# ===================================
#  PALABRAS RESERVADAS (KEYWORDS)
# ===================================
# La gramática distingue entre "keywords" y "soft keywords".
# Para simplificar:
# - El lexer devolverá type = NAME para todos.
# - El value será el texto ("if", "while", "match", "case"...).
# - El parser, cuando necesite un keyword, verificará value.
# Esto encaja bien con la gramática PEG que usa 'if', 'while', etc.

KEYWORDS: Set[str] = {
    # Control de flujo
    "if", "elif", "else",
    "while", "for", "in",
    "try", "except", "finally",
    "with", "async", "await",
    "match", "case",

    # Funciones, clases y tipos
    "def", "class", "lambda",
    "type",

    # Excepciones y retorno
    "raise", "return", "yield",

    # Importaciones
    "import", "from", "as",

    # Sentencias simples
    "pass", "break", "continue",
    "global", "nonlocal", "del",
    "assert",

    # Booleanos y constantes especiales
    "True", "False", "None",

    # Operadores lógicos y de pertenencia
    "and", "or", "not",
    "is",

    # Otros usados en la gramática (por ejemplo en patrones)
    # (si agregas más reglas, aquí las puedes sumar)
}


def is_keyword(ident: str) -> bool:
    """
    Devuelve True si el identificador pertenece al conjunto
    de palabras reservadas de Python que soporta este compilador.
    """
    return ident in KEYWORDS


# ==========================================================
#  CLASE TOKEN
# ==========================================================

@dataclass
class Token:
    """
    Representa un token producido por el lexer.

    Atributos:
        type  - tipo de token (por ejemplo: NAME, NUMBER, STRING, NEWLINE, etc.)
        value - lexema o valor interpretado:
                  * NAME  -> string con el nombre o keyword
                  * NUMBER -> valor numérico (int o float)
                  * STRING -> contenido de la cadena (sin comillas)
                  * otros -> normalmente el propio lexema o None
        line  - número de línea (1-based)
        column - número de columna (1-based, contando desde el inicio de línea)
    """
    type: str
    value: Any
    line: int
    column: int

    def __repr__(self) -> str:
        return (
            f"Token(type={self.type!r}, value={self.value!r}, "
            f"line={self.line}, column={self.column})"
        )
