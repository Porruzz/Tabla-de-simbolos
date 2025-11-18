# lexer.py
"""
Lexer (analizador léxico) para un subconjunto de Python basado en la
gramática PEG que compartiste.

Características:
- Genera tokens:
    * NAME, NUMBER, STRING
    * NEWLINE, INDENT, DEDENT, ENDMARKER
    * TYPE_COMMENT (líneas que empiecen con '# type:')
    * Operadores (+, -, *, /, //, **, etc.) y delimitadores (()[]{},:.;)
- Maneja indentación al estilo Python usando una pila de indentaciones.
- Ignora comentarios normales ('# ...') excepto los TYPE_COMMENT.
- No soporta f-strings ni todas las rarezas de CPython; para fines
  de compiladores de clase, es más que suficiente.

Uso típico:
    from lexer import Lexer

    source = open("archivo.mpy").read()
    lexer = Lexer(source)
    tokens = lexer.tokenize()
"""

from __future__ import annotations

from typing import List, Optional
from tokens import (
    Token,
    # Tokens básicos
    TT_NAME, TT_NUMBER, TT_STRING,
    TT_NEWLINE, TT_INDENT, TT_DEDENT, TT_TYPE_COMMENT,
    TT_ENDMARKER,
    # Operadores y signos
    TT_PLUS, TT_MINUS, TT_STAR, TT_SLASH, TT_DOUBLE_SLASH,
    TT_PERCENT, TT_AT, TT_PIPE, TT_AMPERSAND, TT_CARET, TT_TILDE,
    TT_LSHIFT, TT_RSHIFT, TT_DOUBLE_STAR,
    TT_EQUAL, TT_EQEQUAL, TT_NOTEQUAL, TT_LESSEQUAL, TT_GREATEREQUAL,
    TT_LESS, TT_GREATER,
    TT_LPAREN, TT_RPAREN, TT_LBRACKET, TT_RBRACKET,
    TT_LBRACE, TT_RBRACE,
    TT_COMMA, TT_COLON, TT_SEMI, TT_DOT, TT_ARROW,
    TT_PLUSEQUAL, TT_MINEQUAL, TT_STAREQUAL, TT_SLASHEQUAL,
    TT_PERCENTEQUAL, TT_ATEQUAL, TT_AMPEREQUAL, TT_PIPEEQUAL,
    TT_CARETEQUAL, TT_LSHIFTEQUAL, TT_RSHIFTEQUAL,
    TT_DOUBLE_STAREQUAL, TT_DOUBLE_SLASHEQUAL,
)


class LexerError(Exception):
    """Error léxico con información de línea y columna."""

    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"[LexerError] {message} (línea {line}, columna {column})")
        self.line = line
        self.column = column


class Lexer:
    def __init__(self, text: str, filename: str = "<stdin>"):
        self.text = text
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1
        self.length = len(text)

        # Pila de indentaciones (en espacios). Comienza en 0.
        self.indent_stack = [0]

        # Flag para saber si estamos al inicio lógico de una línea
        self.at_line_start = True

    # =========================
    #  Helpers básicos
    # =========================

    @property
    def current_char(self) -> Optional[str]:
        if self.pos >= self.length:
            return None
        return self.text[self.pos]

    def _advance(self, n: int = 1):
        for _ in range(n):
            if self.pos >= self.length:
                return
            ch = self.text[self.pos]
            self.pos += 1
            if ch == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1

    def _peek(self, k: int = 1) -> Optional[str]:
        idx = self.pos + k
        if idx >= self.length:
            return None
        return self.text[idx]

    # =========================
    #  Tokenización principal
    # =========================

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

        while True:
            ch = self.current_char
            if ch is None:
                break

            if self.at_line_start:
                # Manejar indentación y líneas en blanco/comentarios
                self._handle_line_start(tokens)
                ch = self.current_char
                if ch is None:
                    break

            # Espacios en medio de la línea
            if ch in ' \t\r':
                self._advance()
                continue

            # Comentarios
            if ch == '#':
                self._handle_comment(tokens)
                continue

            # Nueva línea
            if ch == '\n':
                # Emitimos NEWLINE solo si no estamos "al inicio" por indent
                tok = Token(TT_NEWLINE, '\n', self.line, self.col)
                tokens.append(tok)
                self._advance()
                self.at_line_start = True
                continue

            # Números
            if ch.isdigit() or (ch == '.' and (self._peek() or '').isdigit()):
                tokens.append(self._number())
                continue

            # Identificadores / keywords
            if ch.isalpha() or ch == '_':
                tokens.append(self._identifier_or_keyword())
                continue

            # Cadenas de texto (simples, no fstrings avanzados)
            if ch in ('"', "'"):
                tokens.append(self._string_literal())
                continue

            # Operadores y signos
            op_token = self._operator_or_punct()
            if op_token is not None:
                tokens.append(op_token)
                continue

            # Si nada matchea, es un error
            raise LexerError(f"Carácter inesperado: {repr(ch)}", self.line, self.col)

        # Al final del archivo: emitir NEWLINE si la última línea no termina
        # con salto (esto ayuda al parser estilo Python)
        if tokens and tokens[-1].type != TT_NEWLINE:
            tokens.append(Token(TT_NEWLINE, '\n', self.line, self.col))

        # DEDENTs pendientes
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            tokens.append(Token(TT_DEDENT, None, self.line, self.col))

        # ENDMARKER
        tokens.append(Token(TT_ENDMARKER, None, self.line, self.col))
        return tokens

    # =========================
    #  Inicio de línea / indent
    # =========================

    def _handle_line_start(self, tokens: List[Token]):
        """
        Maneja indentación al inicio lógico de una línea:
        - Cuenta espacios y tabs hasta el primer no-blanco (o fin de línea).
        - Si la línea es solo comentario o solo whitespace, no cambia indent.
        - Si es una línea real de código, emite INDENT/DEDENT según cambios.
        """
        self.at_line_start = False
        start_line = self.line
        start_col = self.col

        indent = 0
        pos_backup = self.pos
        col_backup = self.col

        # Contar espacios/tabs
        while True:
            ch = self.current_char
            if ch in (' ', '\t'):
                if ch == ' ':
                    indent += 1
                    self._advance()
                elif ch == '\t':
                    # Para simplificar, tratamos tab como 4 espacios
                    indent += 4
                    self._advance()
            else:
                break

        ch = self.current_char

        # Línea vacía o solo comentario: no afecta indent, se maneja en el loop principal
        if ch == '\n' or ch is None or ch == '#':
            # No emitimos INDENT/DEDENT
            # Dejamos que NEWLINE y/o comentario se manejen aparte
            return

        # Línea con código: comparo indent con la pila
        prev_indent = self.indent_stack[-1]

        if indent > prev_indent:
            # Nuevo nivel de indentación
            self.indent_stack.append(indent)
            tokens.append(Token(TT_INDENT, None, start_line, start_col))
        elif indent < prev_indent:
            # Salimos de uno o más niveles
            while self.indent_stack and indent < self.indent_stack[-1]:
                self.indent_stack.pop()
                tokens.append(Token(TT_DEDENT, None, start_line, start_col))

            if indent != self.indent_stack[-1]:
                raise LexerError(
                    "Indentación inválida (no coincide con ningún nivel previo)",
                    start_line,
                    start_col,
                )

        # Si indent == prev_indent, no hacemos nada (misma indentación)

    # =========================
    #  Comentarios
    # =========================

    def _handle_comment(self, tokens: List[Token]):
        """
        Maneja comentarios:
        - Si la línea empieza con '# type:', emitimos TYPE_COMMENT.
        - En otro caso, se ignora el comentario (hasta fin de línea).
        No consume el '\n'; eso se procesa fuera.
        """
        start_line = self.line
        start_col = self.col

        # Leemos todo el comentario en bruto
        comment_text = ''
        while self.current_char is not None and self.current_char != '\n':
            comment_text += self.current_char
            self._advance()

        # Normalizamos para detectar "type:"
        stripped = comment_text.lstrip('#').lstrip()

        if stripped.startswith("type:"):
            # Emitir TYPE_COMMENT con el texto completo (sin el salto de línea)
            tokens.append(Token(TT_TYPE_COMMENT, stripped, start_line, start_col))
        # Si no, el comentario se ignora

    # =========================
    #  Números
    # =========================

    def _number(self) -> Token:
        """
        Escanea un NUMBER estilo Python simple:
        - Enteros: 123
        - Reales: 1.23, 0.5, .5, 5., etc.
        - Con exponente: 1e10, 2.3e-5
        """
        start_line = self.line
        start_col = self.col

        num_str = ''
        ch = self.current_char

        # Caso .123
        if ch == '.':
            num_str += ch
            self._advance()
            ch = self.current_char
            if ch is None or not ch.isdigit():
                raise LexerError("Número inválido después de '.'", start_line, start_col)

        # Parte entera
        while self.current_char is not None and self.current_char.isdigit():
            num_str += self.current_char
            self._advance()

        # Parte fraccionaria
        if self.current_char == '.':
            num_str += '.'
            self._advance()
            while self.current_char is not None and self.current_char.isdigit():
                num_str += self.current_char
                self._advance()

        # Exponente
        ch = self.current_char
        if ch in ('e', 'E'):
            num_str += ch
            self._advance()
            ch = self.current_char
            if ch in ('+', '-'):
                num_str += ch
                self._advance()
            if self.current_char is None or not self.current_char.isdigit():
                raise LexerError("Exponente inválido en número", self.line, self.col)
            while self.current_char is not None and self.current_char.isdigit():
                num_str += self.current_char
                self._advance()

        # Convertimos a float (puedes cambiar a int si quieres según formato)
        try:
            value = float(num_str)
        except ValueError:
            raise LexerError(f"Número inválido: {num_str}", start_line, start_col)

        return Token(TT_NUMBER, value, start_line, start_col)

    # =========================
    #  Identificadores / NAME
    # =========================

    def _identifier_or_keyword(self) -> Token:
        """
        Escanea un identificador (NAME).
        No distinguimos aquí keywords: el parser las identifica por el value.
        """
        start_line = self.line
        start_col = self.col
        ident = ''

        while self.current_char is not None and (
            self.current_char.isalnum() or self.current_char == '_'
        ):
            ident += self.current_char
            self._advance()

        # type = TT_NAME para todo; el parser revisará value
        return Token(TT_NAME, ident, start_line, start_col)

    # =========================
    #  Cadenas STRING (simple)
    # =========================

    def _string_literal(self) -> Token:
        """
        Escanea una cadena de texto delimitada por ' o ".
        Soporta escapes simples (\\n, \\\\, \", \', etc).
        No se manejan f-strings ni prefijos complejos.
        """
        start_line = self.line
        start_col = self.col
        quote = self.current_char
        self._advance()  # Consumir la comilla inicial

        value_chars = []
        while True:
            ch = self.current_char
            if ch is None:
                raise LexerError("Cadena sin cerrar", start_line, start_col)

            if ch == '\\':
                # Escape simple
                self._advance()
                esc = self.current_char
                if esc is None:
                    raise LexerError("Fin de archivo en escape de cadena", self.line, self.col)

                if esc == 'n':
                    value_chars.append('\n')
                elif esc == 't':
                    value_chars.append('\t')
                elif esc == 'r':
                    value_chars.append('\r')
                elif esc == '\\':
                    value_chars.append('\\')
                elif esc == quote:
                    value_chars.append(quote)
                else:
                    # Escape genérico: mantenemos el char
                    value_chars.append(esc)
                self._advance()
                continue

            if ch == quote:
                # Fin de cadena
                self._advance()
                break

            if ch == '\n':
                raise LexerError("Salto de línea dentro de cadena sin cerrar", self.line, self.col)

            value_chars.append(ch)
            self._advance()

        value = ''.join(value_chars)
        return Token(TT_STRING, value, start_line, start_col)

    # =========================
    #  Operadores / Puntuación
    # =========================

    def _operator_or_punct(self) -> Optional[Token]:
        """
        Reconoce operadores y signos de puntuación, prefiriendo
        siempre el match más largo (por ejemplo '**=' antes que '**').
        """
        ch = self.current_char
        if ch is None:
            return None

        start_line = self.line
        start_col = self.col

        # Tabla de operadores multi-char, ordenados por longitud
        # (para hacer greedy matching).
        multi_ops = {
            '>>=': TT_RSHIFTEQUAL,
            '<<=': TT_LSHIFTEQUAL,
            '**=': TT_DOUBLE_STAREQUAL,
            '//=': TT_DOUBLE_SLASHEQUAL,
            '==': TT_EQEQUAL,
            '!=': TT_NOTEQUAL,
            '<=': TT_LESSEQUAL,
            '>=': TT_GREATEREQUAL,
            '<<': TT_LSHIFT,
            '>>': TT_RSHIFT,
            '**': TT_DOUBLE_STAR,
            '//': TT_DOUBLE_SLASH,
            '+=': TT_PLUSEQUAL,
            '-=': TT_MINEQUAL,
            '*=': TT_STAREQUAL,
            '/=': TT_SLASHEQUAL,
            '%=': TT_PERCENTEQUAL,
            '@=': TT_ATEQUAL,
            '&=': TT_AMPEREQUAL,
            '|=': TT_PIPEEQUAL,
            '^=': TT_CARETEQUAL,
            '->': TT_ARROW,
        }

        # Probamos 3, 2 y 1 caracteres
        for size in (3, 2):
            fragment = self._peek_fragment(size)
            if fragment in multi_ops:
                tok_type = multi_ops[fragment]
                self._advance(size)
                return Token(tok_type, fragment, start_line, start_col)

        # Operadores de 1 caracter y signos
        single_map = {
            '+': TT_PLUS,
            '-': TT_MINUS,
            '*': TT_STAR,
            '/': TT_SLASH,
            '%': TT_PERCENT,
            '@': TT_AT,
            '|': TT_PIPE,
            '&': TT_AMPERSAND,
            '^': TT_CARET,
            '~': TT_TILDE,
            '=': TT_EQUAL,
            '<': TT_LESS,
            '>': TT_GREATER,
            '(': TT_LPAREN,
            ')': TT_RPAREN,
            '[': TT_LBRACKET,
            ']': TT_RBRACKET,
            '{': TT_LBRACE,
            '}': TT_RBRACE,
            ',': TT_COMMA,
            ':': TT_COLON,
            ';': TT_SEMI,
            '.': TT_DOT,
        }

        if ch in single_map:
            tok_type = single_map[ch]
            self._advance()
            return Token(tok_type, ch, start_line, start_col)

        return None

    def _peek_fragment(self, n: int) -> str:
        """
        Devuelve los próximos n caracteres sin avanzar el cursor.
        Si no hay suficientes caracteres, devuelve la subcadena posible.
        """
        end = min(self.pos + n, self.length)
        return self.text[self.pos:end]
