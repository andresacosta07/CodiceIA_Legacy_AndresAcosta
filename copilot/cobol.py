"""Parser determinista de un subconjunto de COBOL (formato fijo) → AST.

Subconjunto soportado: DATA DIVISION (PIC numérico/alfanumérico, COMP-3/BINARY, VALUE, COPY de copybooks),
PROCEDURE DIVISION con párrafos; MOVE, COMPUTE [ROUNDED], ADD, SUBTRACT, MULTIPLY, DIVIDE [GIVING], IF/ELSE,
EVALUATE (TRUE o sujeto), PERFORM (párrafo, THRU, UNTIL, N TIMES), GO TO, GOBACK/STOP RUN, y sentencias de
infraestructura (OPEN/CLOSE/READ/WRITE/DISPLAY/EXEC SQL) que se reconocen y se aíslan.
Cualquier otra construcción lanza UnsupportedConstruct con la línea (nunca se ignora en silencio).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


class UnsupportedConstruct(Exception):
    """Construcción COBOL fuera del subconjunto soportado por el motor local."""


_TOKEN = re.compile(r"""\s*(?:(?P<str>'(?:[^']|'')*'|"(?:[^"]|"")*")|(?P<num>\d+\.\d+|\d+)(?![A-Za-z_\-])"""
                    r"""|(?P<op>\*\*|>=|<=|<>|[=<>+\-*/():,;])|(?P<dot>\.)|(?P<word>[A-Za-z0-9][A-Za-z0-9\-_]*))""")
VERBS = {"MOVE", "COMPUTE", "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "IF", "ELSE", "END-IF", "EVALUATE", "WHEN", "END-EVALUATE",
         "PERFORM", "END-PERFORM", "GO", "GOBACK", "STOP", "EXIT", "CONTINUE", "DISPLAY", "OPEN", "CLOSE", "READ", "WRITE",
         "END-READ", "END-WRITE", "EXEC", "END-EXEC", "NEXT", "REWRITE", "INITIALIZE", "ACCEPT", "CALL", "STRING", "UNSTRING",
         "INSPECT", "SET", "SEARCH", "SORT", "MERGE", "RETURN", "RELEASE", "CANCEL", "ALTER", "ON"}
FIGURATIVE = {"ZERO", "ZEROS", "ZEROES", "SPACE", "SPACES", "HIGH-VALUE", "HIGH-VALUES", "LOW-VALUE", "LOW-VALUES"}
INFRA = {"open", "close", "read", "write", "display", "exec", "accept"}
ARITH = {"compute", "add", "subtract", "multiply", "divide"}


@dataclass
class Tok:
    kind: str  # str num op dot word
    text: str
    line: int


@dataclass
class Item:
    name: str
    level: int
    group: str
    file: str
    line: int
    pic: str = ""
    usage: str = "DISPLAY"
    numeric: bool = False
    int_digits: int = 0
    scale: int = 0
    signed: bool = False
    size: int = 0
    value: Any = None
    elementary: bool = True
    from_copybook: bool = False


@dataclass
class Para:
    name: str
    start: int
    end: int = 0
    stmts: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Program:
    program_id: str
    file: str
    items: dict[str, Item]
    paragraphs: list[Para]
    comments: dict[int, str]
    lines: list[str]
    copybooks: list[str]

    def para(self, name: str) -> Para | None:
        return next((p for p in self.paragraphs if p.name == name), None)


def _pic(pic: str, where: str) -> tuple[bool, int, int, bool, int]:
    """(numérico, enteros, decimales, con signo, tamaño alfanumérico)."""
    p = pic.upper().rstrip(".")
    if re.search(r"[^9SVXA()0-9]", p):
        raise UnsupportedConstruct(f"{where}: PIC editada o no soportada: {pic}")
    expanded = re.sub(r"([9XA])\((\d+)\)", lambda m: m.group(1) * int(m.group(2)), p)
    if "9" in expanded:
        signed = expanded.startswith("S")
        body = expanded.replace("S", "")
        ints, _, decs = body.partition("V")
        return True, ints.count("9"), decs.count("9"), signed, 0
    return False, 0, 0, False, len(expanded.replace("S", ""))


def _lit(text: str) -> Any:
    t = text.strip().rstrip(".")
    if t[:1] in "'\"":
        return t[1:-1]
    if t.upper() in FIGURATIVE:
        return "" if t.upper().startswith(("SPACE", "HIGH", "LOW")) else "0"
    return t


def _strip_line(ln: str) -> str | None:
    """Contenido de las columnas 8-72; None si es comentario o línea vacía."""
    if len(ln) > 6 and ln[6] in "*/":
        return None
    body = ln[7:72] if len(ln) > 7 else ""
    return body if body.strip() else None


def parse_program(artifacts: list[dict[str, Any]]) -> Program:
    main = next((a for a in artifacts if a["language"] == "cobol"), None)
    if main is None:
        raise UnsupportedConstruct("El motor local solo admite COBOL (se encontró otro lenguaje).")
    lines = main["text"].split("\n")
    copy_idx = {re.sub(r"\.[^.]*$", "", a["path"].split("/")[-1]).upper(): a for a in artifacts if a["language"] == "cobol-copybook"}
    comments = {i: ln[7:72].strip() for i, ln in enumerate(lines, 1) if len(ln) > 7 and ln[6] == "*" and ln[7:72].strip()}
    m = re.search(r"PROGRAM-ID\.\s*([A-Z0-9\-]+)", main["text"], re.I)
    pid = (m.group(1) if m else "PROGRAM").upper()
    proc_at = next((i for i, ln in enumerate(lines) if re.search(r"\bPROCEDURE\s+DIVISION\b", ln, re.I)), None)
    if proc_at is None:
        raise UnsupportedConstruct("No se encontró PROCEDURE DIVISION.")
    items: dict[str, Item] = {}
    copybooks: list[str] = []

    def read_items(src_lines: list[str], fname: str, from_copy: bool, group_ref: list[str], offset: int = 0) -> None:
        buf, start = "", 0
        for i, ln in enumerate(src_lines, 1):
            body = _strip_line(ln)
            if body is None:
                continue
            cm = re.match(r"^\s*COPY\s+([A-Z0-9\-]+)\s*\.?\s*$", body, re.I)
            if cm:
                name = cm.group(1).upper()
                copybooks.append(name)
                art = copy_idx.get(name)
                if art is None:
                    raise UnsupportedConstruct(f"{fname}:{i}: copybook {name} no incluido en la carga.")
                read_items(art["text"].split("\n"), art["path"], True, group_ref)
                continue
            if not buf:
                start = i
            buf += " " + body.strip()
            if not buf.rstrip().endswith("."):
                continue
            sent, buf = buf.strip(), ""
            im = re.match(r"^(\d{2})\s+([A-Z0-9\-]+)(?:\s+(.*?))?\.$", sent, re.I)
            if not im:
                continue
            level, name, rest = int(im.group(1)), im.group(2).upper(), (im.group(3) or "")
            if level in (66, 88):
                continue
            if level == 1:
                group_ref[0] = name
            if re.search(r"\bOCCURS\b|\bREDEFINES\b", rest, re.I):
                raise UnsupportedConstruct(f"{fname}:{start}: OCCURS/REDEFINES no soportado ({name}).")
            pm = re.search(r"\bPIC(?:TURE)?\s+(?:IS\s+)?(\S+)", rest, re.I)
            it = Item(name=name, level=level, group=group_ref[0], file=fname, line=start, from_copybook=from_copy)
            if pm:
                it.pic = pm.group(1)
                it.numeric, it.int_digits, it.scale, it.signed, it.size = _pic(it.pic, f"{fname}:{start}")
                um = re.search(r"\b(COMP-3|COMP-5|COMP|BINARY|PACKED-DECIMAL)\b", rest, re.I)
                it.usage = um.group(1).upper() if um else "DISPLAY"
                vm = re.search(r"\bVALUE(?:\s+IS)?\s+(.+)$", rest, re.I)
                if vm:
                    it.value = _lit(vm.group(1))
            else:
                it.elementary = False
            items[name] = it

    read_items(lines[:proc_at], main["path"], False, [""])
    # ---- tokens de la PROCEDURE DIVISION
    toks: list[Tok] = []
    for i in range(proc_at + 1, len(lines)):
        body = _strip_line(lines[i])
        if body is None:
            continue
        pos = 0
        while pos < len(body):
            tm = _TOKEN.match(body, pos)
            if not tm or tm.end() == pos:
                if not body[pos:].strip():
                    break
                raise UnsupportedConstruct(f"{main['path']}:{i + 1}: carácter no reconocido: {body[pos:pos + 12]!r}")
            pos = tm.end()
            kind = tm.lastgroup or ""
            toks.append(Tok(kind, tm.group(kind).upper() if kind == "word" else tm.group(kind), i + 1))
    return _Parser(toks, items, main["path"], lines, comments, pid, copybooks).parse()


class _Parser:
    def __init__(self, toks: list[Tok], items: dict[str, Item], fname: str, lines: list[str], comments: dict[int, str],
                 pid: str, copybooks: list[str]) -> None:
        self.t, self.i, self.items, self.fname = toks, 0, items, fname
        self.lines, self.comments, self.pid, self.copybooks = lines, comments, pid, copybooks

    # --- utilidades
    def peek(self, k: int = 0) -> Tok | None:
        return self.t[self.i + k] if self.i + k < len(self.t) else None

    def err(self, msg: str) -> UnsupportedConstruct:
        tk = self.peek() or self.t[-1]
        return UnsupportedConstruct(f"{self.fname}:{tk.line}: {msg} (cerca de '{tk.text}')")

    def is_word(self, *words: str) -> bool:
        tk = self.peek()
        return bool(tk and tk.kind == "word" and tk.text in words)

    def take(self) -> Tok:
        tk = self.peek()
        if tk is None:
            raise UnsupportedConstruct("Fin inesperado del programa.")
        self.i += 1
        return tk

    def expect_word(self, w: str) -> None:
        if not self.is_word(w):
            raise self.err(f"se esperaba {w}")
        self.i += 1

    def last_line(self) -> int:
        return self.t[self.i - 1].line

    # --- programa
    def parse(self) -> Program:
        paras: list[Para] = []
        cur: Para | None = None
        while self.peek():
            tk = self.peek()
            nxt = self.peek(1)
            if tk and tk.kind == "word" and tk.text not in VERBS and nxt and nxt.kind == "dot":
                if cur:
                    cur.end = self.t[self.i - 1].line
                cur = Para(tk.text, tk.line)
                paras.append(cur)
                self.i += 2
                continue
            if tk and tk.kind == "word" and nxt and nxt.text == "SECTION":
                self.i += 3
                continue
            if cur is None:
                cur = Para("MAIN-SECTION", tk.line if tk else 0)
                paras.append(cur)
            if tk and tk.kind == "dot":
                self.i += 1
                continue
            cur.stmts.append(self.stmt())
        if cur:
            cur.end = self.t[-1].line
        prog = Program(self.pid, self.fname, self.items, paras, self.comments, self.lines, self.copybooks)
        self.check_refs(prog)
        return prog

    def check_refs(self, prog: Program) -> None:
        names = {p.name for p in prog.paragraphs}

        def walk(stmts: list[dict[str, Any]]) -> None:
            for s in stmts:
                for key in ("body", "orelse"):
                    walk(s.get(key) or [])
                for w in s.get("whens", []):
                    walk(w["body"])
                if s["t"] in ("perform", "goto") and s["target"] not in names:
                    raise UnsupportedConstruct(f"{self.fname}:{s['line']}: párrafo inexistente {s['target']}")
        for p in prog.paragraphs:
            walk(p.stmts)

    # --- bloques y sentencias
    def block(self, stop: set[str]) -> list[dict[str, Any]]:
        out = []
        while True:
            tk = self.peek()
            if tk is None or tk.kind == "dot" or (tk.kind == "word" and tk.text in stop):
                return out
            out.append(self.stmt())

    def stmt(self) -> dict[str, Any]:
        tk = self.peek()
        assert tk is not None
        if tk.kind != "word":
            raise self.err("sentencia no reconocida")
        v, line = tk.text, tk.line
        self.i += 1
        node: dict[str, Any]
        if v == "MOVE":
            node = self.s_move()
        elif v == "COMPUTE":
            node = self.s_compute()
        elif v == "ADD":
            node = self.s_addsub("add", "TO")
        elif v == "SUBTRACT":
            node = self.s_addsub("subtract", "FROM")
        elif v == "MULTIPLY":
            node = self.s_multiply()
        elif v == "DIVIDE":
            node = self.s_divide()
        elif v == "IF":
            node = self.s_if()
        elif v == "EVALUATE":
            node = self.s_evaluate()
        elif v == "PERFORM":
            node = self.s_perform()
        elif v == "GO":
            self.expect_word("TO")
            node = {"t": "goto", "target": self.take().text}
        elif v in ("GOBACK", "STOP"):
            if v == "STOP":
                self.expect_word("RUN")
            node = {"t": "stop"}
        elif v in ("EXIT", "CONTINUE"):
            if self.is_word("PROGRAM"):
                self.i += 1
            node = {"t": "nop"}
        elif v == "NEXT":
            self.expect_word("SENTENCE")
            node = {"t": "nop"}
        elif v in ("OPEN", "CLOSE", "DISPLAY", "WRITE", "ACCEPT"):
            while self.peek() and self.peek().kind in ("str", "num", "word", "op") and not (self.peek().kind == "word" and self.peek().text in VERBS):
                self.i += 1
            node = {"t": "infra", "kind": v.lower()}
        elif v == "READ":
            while self.peek() and not (self.peek().kind == "dot" or self.is_word("END-READ")):
                self.i += 1
            if self.is_word("END-READ"):
                self.i += 1
            node = {"t": "infra", "kind": "read"}
        elif v == "EXEC":
            while self.peek() and not self.is_word("END-EXEC"):
                self.i += 1
            self.i += 1
            node = {"t": "infra", "kind": "exec"}
        else:
            raise UnsupportedConstruct(f"{self.fname}:{line}: verbo COBOL no soportado por el motor local: {v}")
        node["line"], node["end"] = line, self.last_line()
        return node

    # --- expresiones
    def operand(self) -> dict[str, Any]:
        return self.expr_add()

    def expr_add(self) -> dict[str, Any]:
        left = self.expr_mul()
        while self.peek() and self.peek().kind == "op" and self.peek().text in "+-":
            op = self.take().text
            left = {"e": "bin", "op": op, "l": left, "r": self.expr_mul()}
        return left

    def expr_mul(self) -> dict[str, Any]:
        left = self.expr_pow()
        while self.peek() and self.peek().kind == "op" and self.peek().text in ("*", "/"):
            op = self.take().text
            left = {"e": "bin", "op": op, "l": left, "r": self.expr_pow()}
        return left

    def expr_pow(self) -> dict[str, Any]:
        base = self.expr_unary()
        if self.peek() and self.peek().kind == "op" and self.peek().text == "**":
            self.i += 1
            return {"e": "bin", "op": "**", "l": base, "r": self.expr_pow()}
        return base

    def expr_unary(self) -> dict[str, Any]:
        tk = self.peek()
        if tk and tk.kind == "op" and tk.text in "+-":
            self.i += 1
            inner = self.expr_unary()
            return {"e": "neg", "x": inner} if tk.text == "-" else inner
        return self.expr_primary()

    def expr_primary(self) -> dict[str, Any]:
        tk = self.take()
        if tk.kind == "num":
            return {"e": "num", "v": tk.text}
        if tk.kind == "str":
            return {"e": "str", "v": tk.text[1:-1].replace("''", "'")}
        if tk.kind == "op" and tk.text == "(":
            inner = self.expr_add()
            if not (self.peek() and self.peek().text == ")"):
                raise self.err("se esperaba ')'")
            self.i += 1
            return inner
        if tk.kind == "word":
            if tk.text in FIGURATIVE:
                return {"e": "fig", "v": tk.text}
            if tk.text not in self.items:
                raise UnsupportedConstruct(f"{self.fname}:{tk.line}: identificador no declarado: {tk.text}")
            return {"e": "id", "n": tk.text}
        raise UnsupportedConstruct(f"{self.fname}:{tk.line}: expresión no soportada cerca de '{tk.text}'")

    def ident(self) -> str:
        tk = self.take()
        if tk.kind != "word" or tk.text not in self.items:
            raise UnsupportedConstruct(f"{self.fname}:{tk.line}: se esperaba un campo declarado, se encontró '{tk.text}'")
        if not self.items[tk.text].elementary:
            raise UnsupportedConstruct(f"{self.fname}:{tk.line}: operaciones sobre grupos no soportadas ({tk.text})")
        return tk.text

    # --- condiciones
    def cond(self) -> dict[str, Any]:
        left = self.cond_and()
        while self.is_word("OR"):
            self.i += 1
            left = {"c": "or", "l": left, "r": self.cond_and()}
        return left

    def cond_and(self) -> dict[str, Any]:
        left = self.cond_not()
        while self.is_word("AND"):
            self.i += 1
            left = {"c": "and", "l": left, "r": self.cond_not()}
        return left

    def cond_not(self) -> dict[str, Any]:
        if self.is_word("NOT"):
            self.i += 1
            return {"c": "not", "x": self.cond_not()}
        tk = self.peek()
        if tk and tk.kind == "op" and tk.text == "(":
            save = self.i
            self.i += 1
            try:
                inner = self.cond()
                if self.peek() and self.peek().text == ")":
                    self.i += 1
                    return inner
            except UnsupportedConstruct:
                pass
            self.i = save
        left = self.operand()
        neg = False
        if self.is_word("IS"):
            self.i += 1
        if self.is_word("NOT"):
            self.i += 1
            neg = True
        op = self.relop()
        right = self.operand()
        node = {"c": "cmp", "op": op, "l": left, "r": right}
        return {"c": "not", "x": node} if neg else node

    def relop(self) -> str:
        tk = self.take()
        if tk.kind == "op" and tk.text in ("=", ">", "<", ">=", "<=", "<>"):
            return tk.text
        words = {"EQUAL": "=", "GREATER": ">", "LESS": "<"}
        if tk.kind == "word" and tk.text in words:
            op = words[tk.text]
            if self.is_word("THAN", "TO"):
                self.i += 1
            if self.is_word("OR") and self.peek(1) and self.peek(1).text == "EQUAL":
                self.i += 2
                if self.is_word("TO"):
                    self.i += 1
                op += "="
            return op
        raise UnsupportedConstruct(f"{self.fname}:{tk.line}: operador relacional no soportado: {tk.text}")

    # --- sentencias
    def s_move(self) -> dict[str, Any]:
        src = self.operand()
        self.expect_word("TO")
        targets = [self.ident()]
        while self.peek() and self.peek().kind == "word" and self.peek().text not in VERBS and self.peek().text in self.items:
            targets.append(self.ident())
        return {"t": "move", "src": src, "targets": targets}

    def rounded(self) -> bool:
        if self.is_word("ROUNDED"):
            self.i += 1
            return True
        return False

    def s_compute(self) -> dict[str, Any]:
        target = self.ident()
        rnd = self.rounded()
        if not (self.peek() and self.peek().text == "="):
            raise self.err("se esperaba '=' en COMPUTE")
        self.i += 1
        expr = self.expr_add()
        if self.is_word("ON", "SIZE"):
            raise self.err("ON SIZE ERROR no soportado")
        return {"t": "compute", "target": target, "rounded": rnd, "expr": expr}

    def s_addsub(self, kind: str, prep: str) -> dict[str, Any]:
        operands = [self.operand()]
        while self.peek() and not self.is_word(prep):
            operands.append(self.operand())
        self.expect_word(prep)
        target = self.ident()
        rnd = self.rounded()
        if self.is_word("GIVING"):
            raise self.err("GIVING en ADD/SUBTRACT no soportado")
        return {"t": kind, "operands": operands, "target": target, "rounded": rnd}

    def s_multiply(self) -> dict[str, Any]:
        a = self.operand()
        self.expect_word("BY")
        target = self.ident()
        rnd = self.rounded()
        if self.is_word("GIVING"):
            raise self.err("MULTIPLY ... GIVING no soportado")
        return {"t": "multiply", "factor": a, "target": target, "rounded": rnd}

    def s_divide(self) -> dict[str, Any]:
        a = self.operand()
        if self.is_word("INTO"):
            self.i += 1
            target = self.ident()
            rnd = self.rounded()
            if self.is_word("GIVING"):
                raise self.err("DIVIDE INTO ... GIVING no soportado")
            return {"t": "divide_into", "divisor": a, "target": target, "rounded": rnd}
        self.expect_word("BY")
        b = self.operand()
        self.expect_word("GIVING")
        target = self.ident()
        rnd = self.rounded()
        if self.is_word("REMAINDER"):
            raise self.err("REMAINDER no soportado")
        return {"t": "divide", "a": a, "b": b, "target": target, "rounded": rnd}

    def s_if(self) -> dict[str, Any]:
        c = self.cond()
        if self.is_word("THEN"):
            self.i += 1
        body = self.block({"ELSE", "END-IF"})
        orelse: list[dict[str, Any]] = []
        if self.is_word("ELSE"):
            self.i += 1
            orelse = self.block({"END-IF"})
        if self.is_word("END-IF"):
            self.i += 1
        return {"t": "if", "cond": c, "body": body, "orelse": orelse}

    def s_evaluate(self) -> dict[str, Any]:
        subject = None
        if self.is_word("TRUE"):
            self.i += 1
        else:
            subject = self.operand()
        whens = []
        while self.is_word("WHEN"):
            line = self.take().line
            if self.is_word("OTHER"):
                self.i += 1
                c = None
            elif subject is None:
                c = self.cond()
            else:
                c = {"c": "cmp", "op": "=", "l": subject, "r": self.operand()}
            body = self.block({"WHEN", "END-EVALUATE"})
            whens.append({"cond": c, "body": body, "line": line})
        if self.is_word("END-EVALUATE"):
            self.i += 1
        return {"t": "evaluate", "whens": whens}

    def s_perform(self) -> dict[str, Any]:
        if self.is_word("UNTIL"):
            self.i += 1
            c = self.cond()
            body = self.block({"END-PERFORM"})
            if self.is_word("END-PERFORM"):
                self.i += 1
            return {"t": "perform_until", "cond": c, "body": body}
        if self.is_word("VARYING"):
            raise self.err("PERFORM VARYING no soportado")
        tk = self.take()
        if tk.kind != "word":
            raise self.err("PERFORM inválido")
        target, thru = tk.text, None
        if self.is_word("THRU", "THROUGH"):
            self.i += 1
            thru = self.take().text
        if self.is_word("UNTIL"):
            self.i += 1
            return {"t": "perform_para_until", "target": target, "cond": self.cond()}
        nxt = self.peek()
        if nxt and nxt.kind in ("num", "word") and self.peek(1) and self.peek(1).text == "TIMES":
            count = {"e": "num", "v": nxt.text} if nxt.kind == "num" else {"e": "id", "n": nxt.text}
            self.i += 2
            return {"t": "perform", "target": target, "thru": thru, "times": count}
        return {"t": "perform", "target": target, "thru": thru, "times": None}
