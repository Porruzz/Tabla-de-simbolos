# parser.py
"""
Parser recursivo descendente para un subconjunto de Python basado en la
gramática PEG que compartiste.

Genera un AST usando los nodos definidos en `astnodes.py` y mantiene una
tabla de símbolos con scopes anidados usando `symtable.py`.

Subconjunto soportado (suficiente para AST + código de 3 direcciones):
- Programa: lista de sentencias.
- Sentencias simples:
    * expresión (ExprStmt)
    * asignación: a = expr
    * asignación aumentada: a += expr, etc.
    * return expr
    * pass, break, continue
- Sentencias compuestas:
    * if / elif / else
    * while / else
    * for ... in ... / else
    * def nombre(parámetros): bloque
- Expresiones:
    * and / or / not
    * comparaciones: ==, !=, <, >, <=, >=
    * +, -, *, /, //, %
    * ** (potencia)
    * unarios: +, -, ~, not
    * atom: NAME, NUMBER, STRING, (expr)
    * llamadas: f(x, y, z, k=v)
    * atributos: obj.attr
    * subíndices: a[i]

No implementa TODO el PEG de Python, pero es coherente con tu proyecto:
te permite representar el AST_D y luego generar código en tres direcciones.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from tokens import (
    Token,
    # tipos básicos
    TT_NAME, TT_NUMBER, TT_STRING,
    TT_NEWLINE, TT_INDENT, TT_DEDENT, TT_ENDMARKER,
    # operadores y signos
    TT_PLUS, TT_MINUS, TT_STAR, TT_SLASH, TT_DOUBLE_SLASH,
    TT_PERCENT, TT_TILDE, TT_DOUBLE_STAR,
    TT_EQUAL,
    TT_EQEQUAL, TT_NOTEQUAL, TT_LESS, TT_GREATER,
    TT_LESSEQUAL, TT_GREATEREQUAL,
    TT_LPAREN, TT_RPAREN, TT_LBRACKET, TT_RBRACKET,
    TT_DOT, TT_COMMA, TT_COLON,
    TT_PLUSEQUAL, TT_MINEQUAL, TT_STAREQUAL, TT_SLASHEQUAL,
    TT_PERCENTEQUAL, TT_AMPEREQUAL, TT_PIPEEQUAL,
    TT_CARETEQUAL, TT_LSHIFTEQUAL, TT_RSHIFTEQUAL,
    TT_DOUBLE_STAREQUAL, TT_DOUBLE_SLASHEQUAL,
)

from astnodes import (
    Node,
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

from symtable import SymbolTableStack


class ParserError(SyntaxError):
    """Error de sintaxis con información de línea y columna."""

    def __init__(self, message: str, token: Token):
        msg = f"[ParserError] {message} (línea {token.line}, columna {token.column})"
        super().__init__(msg)
        self.token = token


class Parser:
    def __init__(self, tokens: List[Token]):
        if not tokens:
            raise ValueError("La lista de tokens no puede estar vacía")

        self.tokens: List[Token] = tokens
        self.pos: int = 0
        self.current: Token = self.tokens[self.pos]

        # Pila de tablas de símbolos: empezamos con scope global
        self.symstack = SymbolTableStack()
        self.symstack.push_scope("global")

        # Mapa de tokens de asignación aumentada a string de operador
        self.augassign_ops = {
            TT_PLUSEQUAL: "+=",
            TT_MINEQUAL: "-=",
            TT_STAREQUAL: "*=",
            TT_SLASHEQUAL: "/=",
            TT_DOUBLE_SLASHEQUAL: "//=",
            TT_PERCENTEQUAL: "%=",
            TT_AMPEREQUAL: "&=",
            TT_PIPEEQUAL: "|=",
            TT_CARETEQUAL: "^=",
            TT_LSHIFTEQUAL: "<<=",
            TT_RSHIFTEQUAL: ">>=",
            TT_DOUBLE_STAREQUAL: "**=",
        }

    # ==========================================================
    #  Helpers básicos
    # ==========================================================

    def _advance(self) -> None:
        """Avanza al siguiente token."""
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
            self.current = self.tokens[self.pos]

    def _eat(self, token_type: str) -> Token:
        """Consume un token del tipo esperado o lanza error."""
        tok = self.current
        if tok.type == token_type:
            self._advance()
            return tok
        raise ParserError(f"Se esperaba token {token_type}, se encontró {tok.type}", tok)

    def _peek_token(self, k: int = 1) -> Token:
        """Mira el token k posiciones adelante sin consumirlo."""
        idx = self.pos + k
        if idx >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[idx]

    def _is_keyword(self, word: str) -> bool:
        """Devuelve True si el token actual es NAME con ese lexema."""
        return self.current.type == TT_NAME and self.current.value == word

    def _expect_keyword(self, word: str) -> Token:
        """Consume un NAME con el valor `word` o lanza error."""
        tok = self.current
        if tok.type == TT_NAME and tok.value == word:
            self._advance()
            return tok
        raise ParserError(f"Se esperaba keyword '{word}'", tok)

    def _error(self, message: str) -> None:
        raise ParserError(message, self.current)

    # ==========================================================
    #  Entrada principal
    # ==========================================================

    def parse(self) -> Program:
        """
        file: [statements] ENDMARKER
        """
        body: List[Stmt] = []

        while self.current.type != TT_ENDMARKER:
            # saltar NEWLINE sueltos
            if self.current.type == TT_NEWLINE:
                self._advance()
                continue
            if self.current.type in (TT_INDENT, TT_DEDENT):
                self._error("INDENT/DEDENT inesperado al nivel superior")
            stmt = self.parse_statement()
            body.append(stmt)

        return Program(body=body)

    # ==========================================================
    #  Sentencias
    # ==========================================================

    def parse_statement(self) -> Stmt:
        """
        statement: compound_stmt | simple_stmt
        """
        if self._is_keyword("if"):
            return self.parse_if_stmt()
        if self._is_keyword("while"):
            return self.parse_while_stmt()
        if self._is_keyword("for"):
            return self.parse_for_stmt()
        if self._is_keyword("def"):
            return self.parse_function_def()

        # resto: simple_stmt
        return self.parse_simple_stmt()

    # --------------------------
    #  Sentencias simples
    # --------------------------

    def parse_simple_stmt(self) -> Stmt:
        """
        simple_stmt (versión reducida):
            - expr_stmt
            - return_stmt
            - pass_stmt
            - break_stmt
            - continue_stmt
        y debe terminar con NEWLINE (o al final del bloque/archivo).
        """
        if self._is_keyword("return"):
            node = self.parse_return_stmt()
        elif self._is_keyword("pass"):
            node = self.parse_pass_stmt()
        elif self._is_keyword("break"):
            node = self.parse_break_stmt()
        elif self._is_keyword("continue"):
            node = self.parse_continue_stmt()
        else:
            node = self.parse_expr_or_assignment()

        # Consumir NEWLINE si está; si estamos justo antes de DEDENT/ENDMARKER
        # también lo aceptamos, para ser un poco tolerantes.
        if self.current.type == TT_NEWLINE:
            self._advance()
        elif self.current.type in (TT_DEDENT, TT_ENDMARKER):
            # permitido: final de bloque / archivo
            pass
        else:
            self._error("Se esperaba fin de sentencia (NEWLINE)")

        return node

    def parse_return_stmt(self) -> Return:
        """
        return_stmt: 'return' [expression]
        """
        self._expect_keyword("return")
        # Puede no tener expresión
        if self.current.type in (TT_NEWLINE, TT_DEDENT, TT_ENDMARKER):
            return Return(value=None)
        value = self.parse_expression()
        return Return(value=value)

    def parse_pass_stmt(self) -> Pass:
        self._expect_keyword("pass")
        return Pass()

    def parse_break_stmt(self) -> Break:
        self._expect_keyword("break")
        return Break()

    def parse_continue_stmt(self) -> Continue:
        self._expect_keyword("continue")
        return Continue()

    def parse_expr_or_assignment(self) -> Stmt:
        """
        Distingue entre:
            expr_stmt: expression
            assign_stmt: target '=' expression
            augassign: target op= expression
        """
        left_expr = self.parse_expression()

        tok = self.current

        # Asignación simple: a = expr
        if tok.type == TT_EQUAL:
            target = self._ensure_assignable(left_expr)
            self._advance()  # '='
            value = self.parse_expression()

            # Registrar símbolo de variable en el scope actual (si no existe localmente)
            if isinstance(target, Name):
                scope = self.symstack.current_scope
                if scope.lookup_local(target.id) is None:
                    scope.define(target.id, kind="variable", typ="unknown")

            return Assign(targets=[target], value=value)

        # Asignación aumentada: a += expr, etc.
        if tok.type in self.augassign_ops:
            op_str = self.augassign_ops[tok.type]
            target = self._ensure_assignable(left_expr)
            self._advance()  # consume op=
            value = self.parse_expression()
            return AugAssign(target=target, op=op_str, value=value)

        # Sentencia de expresión normal
        return ExprStmt(value=left_expr)

    def _ensure_assignable(self, expr: Expr) -> Expr:
        """
        Verifica que una expresión pueda usarse como target de asignación:
        NAME, Attribute, Subscript.
        """
        if isinstance(expr, (Name, Attribute, Subscript)):
            return expr
        self._error("Expresión no asignable (se esperaba variable, atributo o subíndice)")

    # --------------------------
    #  Sentencias compuestas
    # --------------------------

    def parse_if_stmt(self) -> If:
        """
        if_stmt (forma típica):
            if expr: suite
                [elif expr: suite]*
                [else: suite]
        """
        self._expect_keyword("if")
        test = self.parse_expression()
        self._eat(TT_COLON)
        body = self.parse_block()

        # elif / else
        orelse: List[Stmt] = []
        current_orelse = orelse

        # Encadenar elif como If dentro de orelse, estilo Python
        while self._is_keyword("elif"):
            self._advance()
            elif_test = self.parse_expression()
            self._eat(TT_COLON)
            elif_body = self.parse_block()
            new_if = If(test=elif_test, body=elif_body, orelse=[])
            current_orelse.append(new_if)
            current_orelse = new_if.orelse

        if self._is_keyword("else"):
            self._advance()
            self._eat(TT_COLON)
            else_body = self.parse_block()
            current_orelse.extend(else_body)

        return If(test=test, body=body, orelse=orelse)

    def parse_while_stmt(self) -> While:
        """
        while_stmt:
            while expr: suite
                [else: suite]
        """
        self._expect_keyword("while")
        test = self.parse_expression()
        self._eat(TT_COLON)
        body = self.parse_block()

        orelse: List[Stmt] = []
        if self._is_keyword("else"):
            self._advance()
            self._eat(TT_COLON)
            orelse = self.parse_block()

        return While(test=test, body=body, orelse=orelse)

    def parse_for_stmt(self) -> For:
        """
        for_stmt (versión reducida, sin async):
            for target in expr: suite
                [else: suite]
        """
        self._expect_keyword("for")
        target_expr = self.parse_expression()
        self._expect_keyword("in")
        iter_expr = self.parse_expression()
        self._eat(TT_COLON)
        body = self.parse_block()

        orelse: List[Stmt] = []
        if self._is_keyword("else"):
            self._advance()
            self._eat(TT_COLON)
            orelse = self.parse_block()

        return For(target=target_expr, iter=iter_expr, body=body, orelse=orelse)

    def parse_function_def(self) -> FunctionDef:
        """
        function_def (forma reducida, sin async, sin decoradores, sin anotaciones):
            def NAME '(' [param_list] ')' ':' suite
        """
        self._expect_keyword("def")
        name_tok = self._eat(TT_NAME)
        func_name = name_tok.value

        # Registrar símbolo de función en scope actual
        scope = self.symstack.current_scope
        if scope.lookup_local(func_name) is None:
            scope.define(func_name, kind="function", typ="function")

        self._eat(TT_LPAREN)
        params = self.parse_parameters()
        self._eat(TT_RPAREN)
        self._eat(TT_COLON)

        # Nuevo scope para la función
        func_scope_name = f"func {func_name}"
        self.symstack.push_scope(func_scope_name)

        # Registrar parámetros como símbolos dentro del scope de la función
        for arg in params:
            self.symstack.define(arg.name, kind="param", typ="unknown")

        body = self.parse_block()

        # Cerrar scope de la función
        self.symstack.pop_scope()

        args_node = Arguments(args=params)
        return FunctionDef(name=func_name, args=args_node, body=body, returns=None, decorators=[])

    def parse_parameters(self) -> List[Arg]:
        """
        parámetros simples: NAME (',' NAME)* [',']
        sin defaults ni anotaciones (pueden añadirse luego).
        """
        params: List[Arg] = []

        if self.current.type == TT_RPAREN:
            return params  # sin parámetros

        while True:
            if self.current.type != TT_NAME:
                self._error("Se esperaba nombre de parámetro")
            name_tok = self._eat(TT_NAME)
            params.append(Arg(name=name_tok.value))

            if self.current.type == TT_COMMA:
                # posible coma final
                next_tok = self._peek_token()
                self._eat(TT_COMMA)
                if next_tok.type == TT_RPAREN:
                    break
                continue
            break

        return params

    # --------------------------
    #  Bloques / suites
    # --------------------------

    def parse_block(self) -> List[Stmt]:
        """
        suite reducida:
        - forma en bloque:
            NEWLINE INDENT statements DEDENT
        - forma en línea:
            simple_stmt (en la misma línea que ':')
        """
        # Forma en bloque (lo habitual en tu proyecto)
        if self.current.type == TT_NEWLINE:
            self._eat(TT_NEWLINE)
            self._eat(TT_INDENT)
            stmts: List[Stmt] = []
            while self.current.type not in (TT_DEDENT, TT_ENDMARKER):
                if self.current.type == TT_NEWLINE:
                    self._advance()
                    continue
                stmts.append(self.parse_statement())
            self._eat(TT_DEDENT)
            return stmts

        # Forma en línea: "if x: a = 1"
        # Parseamos una única sentencia simple
        stmt = self.parse_simple_stmt()
        return [stmt]

    # ==========================================================
    #  Expresiones
    # ==========================================================

    def parse_expression(self) -> Expr:
        """
        expression (subconjunto):
            or_test
        """
        return self.parse_or()

    def parse_or(self) -> Expr:
        """
        disjunction:
            conjunction ('or' conjunction)*
        """
        node = self.parse_and()

        while self._is_keyword("or"):
            self._advance()
            right = self.parse_and()
            if isinstance(node, BoolOp) and node.op == "or":
                node.values.append(right)
            else:
                node = BoolOp(op="or", values=[node, right])

        return node

    def parse_and(self) -> Expr:
        """
        conjunction:
            inversion ('and' inversion)*
        """
        node = self.parse_not()

        while self._is_keyword("and"):
            self._advance()
            right = self.parse_not()
            if isinstance(node, BoolOp) and node.op == "and":
                node.values.append(right)
            else:
                node = BoolOp(op="and", values=[node, right])

        return node

    def parse_not(self) -> Expr:
        """
        inversion:
            'not' inversion
            | comparison
        """
        if self._is_keyword("not"):
            tok = self.current
            self._advance()
            operand = self.parse_not()
            return UnaryOp(op="not", operand=operand)
        return self.parse_comparison()

    def parse_comparison(self) -> Expr:
        """
        comparison (subconjunto):
            arith_expr (comp_op arith_expr)*
        comp_op: '==', '!=', '<', '>', '<=', '>='
        """
        node = self.parse_arith_expr()
        ops: List[str] = []
        comparators: List[Expr] = []

        while self.current.type in (
            TT_EQEQUAL, TT_NOTEQUAL,
            TT_LESS, TT_GREATER,
            TT_LESSEQUAL, TT_GREATEREQUAL,
        ):
            op_tok = self.current
            self._advance()
            op_str = self._map_compare_op(op_tok.type)
            right = self.parse_arith_expr()
            ops.append(op_str)
            comparators.append(right)

        if ops:
            return Compare(left=node, ops=ops, comparators=comparators)
        return node

    def _map_compare_op(self, token_type: str) -> str:
        mapping = {
            TT_EQEQUAL: "==",
            TT_NOTEQUAL: "!=",
            TT_LESS: "<",
            TT_GREATER: ">",
            TT_LESSEQUAL: "<=",
            TT_GREATEREQUAL: ">=",
        }
        return mapping[token_type]

    def parse_arith_expr(self) -> Expr:
        """
        sum:
            term (('+' | '-') term)*
        """
        node = self.parse_term()

        while self.current.type in (TT_PLUS, TT_MINUS):
            op_tok = self.current
            self._advance()
            op_str = "+" if op_tok.type == TT_PLUS else "-"
            right = self.parse_term()
            node = BinOp(left=node, op=op_str, right=right)

        return node

    def parse_term(self) -> Expr:
        """
        term:
            factor (('*' | '/' | '//' | '%') factor)*
        """
        node = self.parse_factor()

        while self.current.type in (TT_STAR, TT_SLASH, TT_DOUBLE_SLASH, TT_PERCENT):
            op_tok = self.current
            self._advance()
            if op_tok.type == TT_STAR:
                op_str = "*"
            elif op_tok.type == TT_SLASH:
                op_str = "/"
            elif op_tok.type == TT_DOUBLE_SLASH:
                op_str = "//"
            else:
                op_str = "%"
            right = self.parse_factor()
            node = BinOp(left=node, op=op_str, right=right)

        return node

    def parse_factor(self) -> Expr:
        """
        factor:
            ('+' | '-' | '~') factor
            | power
        """
        if self.current.type in (TT_PLUS, TT_MINUS, TT_TILDE):
            op_tok = self.current
            self._advance()
            op_str = {
                TT_PLUS: "+",
                TT_MINUS: "-",
                TT_TILDE: "~",
            }[op_tok.type]
            operand = self.parse_factor()
            return UnaryOp(op=op_str, operand=operand)
        return self.parse_power()

    def parse_power(self) -> Expr:
        """
        power:
            primary ['**' factor]
        """
        node = self.parse_primary()

        if self.current.type == TT_DOUBLE_STAR:
            self._advance()
            right = self.parse_factor()
            node = BinOp(left=node, op="**", right=right)

        return node

    def parse_primary(self) -> Expr:
        """
        primary:
            atom ('.' NAME | '(' [arglist] ')' | '[' expression ']')*
        """
        node = self.parse_atom()

        while True:
            if self.current.type == TT_DOT:
                # atributo: obj.attr
                self._advance()
                name_tok = self._eat(TT_NAME)
                node = Attribute(value=node, attr=name_tok.value)
                continue

            if self.current.type == TT_LPAREN:
                # llamada: func(args...)
                self._advance()
                args, keywords = self.parse_arglist()
                self._eat(TT_RPAREN)
                node = Call(func=node, args=args, keywords=keywords)
                continue

            if self.current.type == TT_LBRACKET:
                # subíndice: obj[expr]
                self._advance()
                # Para simplificar, solo soportamos un índice simple,
                # no slices start:stop:step. Puedes extenderlo si quieres.
                index_expr = self.parse_expression()
                self._eat(TT_RBRACKET)
                slice_node = Slice(start=index_expr, stop=None, step=None)
                node = Subscript(value=node, slice=slice_node)
                continue

            break

        return node

    def parse_arglist(self) -> Tuple[List[Expr], List[KeywordArg]]:
        """
        arglist reducida:
            (positional | keyword) (',' (positional | keyword))* [',']
        keyword: NAME '=' expression
        """
        args: List[Expr] = []
        keywords: List[KeywordArg] = []

        # Sin argumentos
        if self.current.type == TT_RPAREN:
            return args, keywords

        while True:
            # keyword si: NAME '='
            if self.current.type == TT_NAME and self._peek_token().type == TT_EQUAL:
                name_tok = self._eat(TT_NAME)
                self._eat(TT_EQUAL)
                value = self.parse_expression()
                keywords.append(KeywordArg(name=name_tok.value, value=value))
            else:
                # posicional
                expr = self.parse_expression()
                args.append(expr)

            if self.current.type == TT_COMMA:
                # podría haber coma final
                next_tok = self._peek_token()
                self._eat(TT_COMMA)
                if next_tok.type == TT_RPAREN:
                    break
                continue
            break

        return args, keywords

    def parse_atom(self) -> Expr:
        """
        atom:
            NAME | NUMBER | STRING | '(' expression ')'
            y constantes True/False/None como Bool/NoneLiteral.
        """
        tok = self.current

        if tok.type == TT_NAME:
            self._advance()
            if tok.value == "True":
                return Bool(True)
            if tok.value == "False":
                return Bool(False)
            if tok.value == "None":
                return NoneLiteral()
            return Name(id=tok.value)

        if tok.type == TT_NUMBER:
            self._advance()
            return Num(value=tok.value)

        if tok.type == TT_STRING:
            self._advance()
            return Str(value=tok.value)

        if tok.type == TT_LPAREN:
            self._advance()
            expr = self.parse_expression()
            self._eat(TT_RPAREN)
            return expr

        self._error("Se esperaba NAME, NUMBER, STRING o '(' expresión ')'")


# ==========================================================
#  Helper para uso directo
# ==========================================================

def parse_tokens(tokens: List[Token]) -> Program:
    """
    Helper rápido:
        from lexer import Lexer
        from parser import parse_tokens

        lx = Lexer(source)
        tokens = lx.tokenize()
        ast = parse_tokens(tokens)
    """
    parser = Parser(tokens)
    return parser.parse()
