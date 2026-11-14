"""Motor local determinista (SIN IA) para COBOL. Se usa cuando no hay clave de la API.

Implementa las mismas etapas que los agentes (analyze, rules, codegen, oracle, qa_cases, docs) con salidas que cumplen
los mismos esquemas, de modo que el resto del pipeline (verificadores, HITL, equivalencia, empaquetado) no cambia.
Todo se deriva del AST del programa; lo que no se puede traducir con fidelidad lanza UnsupportedConstruct.
La procedencia se rotula en la UI y en los reportes como «motor local determinista (sin IA)».
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
import re
from pathlib import Path
from typing import Any

from . import verify
from .cobol import ARITH, FIGURATIVE, INFRA, Item, Para, Program, UnsupportedConstruct, parse_program

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "local_cache"
SRC_RX = re.compile(r'<legacy_source file="(?P<f>[^"]*)" language="(?P<l>[^"]*)">\n(?P<b>.*?)\n</legacy_source>', re.S)


# ---------------------------------------------------------------------------------------------------- utilidades
def sources_from_prompt(user: str) -> list[dict[str, Any]]:
    arts = []
    for m in SRC_RX.finditer(user):
        text = "\n".join(re.sub(r"^\s*\d+\| ?", "", ln, count=1) for ln in m.group("b").split("\n"))
        arts.append({"path": m.group("f"), "language": m.group("l"), "text": text})
    return arts


def _json_after(user: str, marker: str) -> Any:
    at = user.find(marker)
    if at < 0:
        return None
    start = user.find("{", at)
    if start < 0:
        start = user.find("[", at)
    try:
        obj, _ = json.JSONDecoder().raw_decode(user[start:])
        return obj
    except (ValueError, TypeError):
        return None


def _key(io: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(io, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]


def _snake(name: str, prefix: str) -> str:
    n = name[len(prefix):] if prefix and name.startswith(prefix) else name
    return n.strip("-").lower().replace("-", "_")


def _camel(name: str) -> str:
    parts = name.lower().split("-")
    s = parts[0] + "".join(p.capitalize() for p in parts[1:])
    return s if not s[0].isdigit() else "_" + s


def _pascal(name: str) -> str:
    s = "".join(p.capitalize() for p in re.split(r"[-_]", name))
    return s if not s[:1].isdigit() else "P" + s


def _pm(name: str) -> str:
    """Nombre de método de un párrafo: prefijo fijo para no chocar con run/table/following del servicio."""
    return "para" + _pascal(name)


def _q(s: str) -> str:
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


# ---------------------------------------------------------------------------------------------------- modelo de E/S
def io_model(prog: Program) -> dict[str, Any]:
    written: set[str] = set()

    def walk(stmts: list[dict[str, Any]]) -> None:
        for s in stmts:
            t = s["t"]
            if t == "move":
                written.update(s["targets"])
            elif t in ARITH or t in ("divide_into", "multiply"):
                written.add(s["target"])
            for k in ("body", "orelse"):
                walk(s.get(k) or [])
            for w in s.get("whens", []):
                walk(w["body"])
    for p in prog.paragraphs:
        walk(p.stmts)
    elementary = [i for i in prog.items.values() if i.elementary]
    io_items = [i for i in elementary if i.from_copybook] or [i for i in elementary if not i.name.startswith("WS-") and i.value is None and i.level > 1]
    groups = [i.group for i in io_items]
    prefix = ""
    if io_items:
        first = io_items[0].name.split("-")[0] + "-"
        prefix = first if all(i.name.startswith(first) for i in io_items) else ""
    inputs = [i for i in io_items if i.name not in written]
    outputs = [i for i in io_items if i.name in written]
    names = {i.name: _snake(i.name, prefix) for i in io_items}

    def field(i: Item) -> dict[str, Any]:
        ftype = "string" if not i.numeric else ("decimal" if i.scale else "integer")
        return {"name": names[i.name], "type": ftype, "scale": i.scale, "description": f"Campo {i.name} ({i.pic})"}
    return {"inputs": inputs, "outputs": outputs, "names": names, "contract": {
        "description": f"Programa {prog.program_id} (fuente {hashlib.sha256(chr(10).join(prog.lines).encode()).hexdigest()[:10]}): función pura derivada de la PROCEDURE DIVISION (entradas: {len(inputs)}, salidas: {len(outputs)}).",
        "inputs": [field(i) for i in inputs], "outputs": [field(i) for i in outputs]}, "groups": sorted(set(groups))}


# ---------------------------------------------------------------------------------------------------- lectura legible
def _expr_text(e: dict[str, Any], names: dict[str, str]) -> str:
    k = e["e"]
    if k == "num":
        return e["v"]
    if k == "str":
        return "'" + e["v"] + "'"
    if k == "fig":
        return e["v"].lower()
    if k == "id":
        return names.get(e["n"], e["n"].lower())
    if k == "neg":
        return "-" + _expr_text(e["x"], names)
    return f"({_expr_text(e['l'], names)} {e['op']} {_expr_text(e['r'], names)})"


def _cond_text(c: dict[str, Any], names: dict[str, str]) -> str:
    k = c["c"]
    if k == "cmp":
        return f"{_expr_text(c['l'], names)} {c['op']} {_expr_text(c['r'], names)}"
    if k == "not":
        return "no (" + _cond_text(c["x"], names) + ")"
    return f"{_cond_text(c['l'], names)} {'y' if k == 'and' else 'o'} {_cond_text(c['r'], names)}"


def _action_text(s: dict[str, Any], names: dict[str, str]) -> str:
    n = lambda x: names.get(x, x.lower())  # noqa: E731
    t = s["t"]
    rnd = " (redondeado)" if s.get("rounded") else " (truncado)"
    if t == "move":
        return f"{', '.join(n(x) for x in s['targets'])} ← {_expr_text(s['src'], names)}"
    if t == "compute":
        return f"{n(s['target'])} = {_expr_text(s['expr'], names)}{rnd}"
    if t == "add":
        return f"{n(s['target'])} += {' + '.join(_expr_text(o, names) for o in s['operands'])}"
    if t == "subtract":
        return f"{n(s['target'])} -= {' + '.join(_expr_text(o, names) for o in s['operands'])}"
    if t == "multiply":
        return f"{n(s['target'])} *= {_expr_text(s['factor'], names)}"
    if t == "divide":
        return f"{n(s['target'])} = {_expr_text(s['a'], names)} / {_expr_text(s['b'], names)}{rnd}"
    if t == "divide_into":
        return f"{n(s['target'])} /= {_expr_text(s['divisor'], names)}"
    return t


def _mentions(node: Any, out: set[str]) -> None:
    if isinstance(node, dict):
        if node.get("e") == "id":
            out.add(node["n"])
        for k in ("target",):
            if isinstance(node.get(k), str) and node["t" if "t" in node else "e"] in ARITH | {"divide_into", "multiply"}:
                out.add(node[k])
        if "targets" in node:
            out.update(node["targets"])
        for v in node.values():
            _mentions(v, out)
    elif isinstance(node, list):
        for v in node:
            _mentions(v, out)


# ---------------------------------------------------------------------------------------------------- reglas
def _hint(prog: Program, line: int) -> str:
    parts, ln = [], line - 1
    while ln in prog.comments:
        parts.insert(0, prog.comments[ln])
        ln -= 1
    text = " ".join(parts).strip()
    text = re.sub(r"^(REGLA|RULE)\s*:\s*", "", text, flags=re.I)
    return (text[:1].upper() + text[1:].lower()) if text else ""


def _src_ref(prog: Program, node: dict[str, Any]) -> dict[str, Any]:
    first = (prog.lines[node["line"] - 1][7:72]).strip()
    return {"file": prog.file, "start_line": node["line"], "end_line": node["end"], "quote": first}


def _is_effect(s: dict[str, Any]) -> bool:
    if s["t"] == "move":
        return s["src"]["e"] != "fig"
    return s["t"] in ARITH or s["t"] in ("divide_into", "multiply")


def reachable(prog: Program) -> list[Para]:
    order = [p.name for p in prog.paragraphs]
    seen: set[str] = set()
    todo = [order[0]] if order else []

    def targets(stmts: list[dict[str, Any]]) -> tuple[set[str], bool]:
        tg: set[str] = set()
        terminal = False
        for s in stmts:
            if s["t"] in ("perform", "goto", "perform_para_until"):
                tg.add(s["target"])
                if s.get("thru"):
                    i, j = order.index(s["target"]), order.index(s["thru"])
                    tg.update(order[i:j + 1])
            for k in ("body", "orelse"):
                a, _ = targets(s.get(k) or [])
                tg |= a
            for w in s.get("whens", []):
                a, _ = targets(w["body"])
                tg |= a
        if stmts and stmts[-1]["t"] in ("stop", "goto"):
            terminal = True
        return tg, terminal
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        seen.add(n)
        p = prog.para(n)
        assert p is not None
        tg, terminal = targets(p.stmts)
        todo += [t for t in tg if t not in seen]
        idx = order.index(n)
        if not terminal and idx + 1 < len(order):
            todo.append(order[idx + 1])
    return [p for p in prog.paragraphs if p.name in seen]


def extract_rules(prog: Program, names: dict[str, str]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []

    def add(node: dict[str, Any], para: Para, name: str, desc: str, cat: str, conds: list[str], acts: list[str],
            data: set[str], conf: float, table: dict[str, Any] | None = None, ref_node: dict[str, Any] | None = None) -> None:
        rid = f"R-{len(rules) + 1:03d}"
        fields = sorted({names.get(d, d.lower()) for d in data})
        gh = [f"Escenario: {name}", f"  Dado que {conds[0] if conds else 'se ejecuta el párrafo ' + para.name}"]
        gh += ["  Cuando se procesa la solicitud", f"  Entonces {acts[0] if acts else 'se aplica la regla'}"]
        gh += [f"  Y {a}" for a in acts[1:4]]
        rules.append({"id": rid, "name": name[:90], "description": desc, "category": cat, "conditions": conds, "actions": acts,
                      "data_items": fields, "source_refs": [_src_ref(prog, ref_node or node)], "confidence": conf,
                      "assumptions": [f"Regla derivada del párrafo {para.name} del COBOL original."], "gherkin": "\n".join(gh),
                      "decision_table": table or {"columns": [], "rows": []}, "para": para.name})

    def reject_code(body: list[dict[str, Any]]) -> tuple[str, str] | None:
        status = code = None
        for s in body:
            if s["t"] == "move" and s["src"]["e"] == "str":
                for t in s["targets"]:
                    if re.search(r"STATUS|ESTADO", t) and status is None:
                        status = s["src"]["v"]
                    elif re.search(r"ERR|CODE|COD|MSG", t):
                        code = s["src"]["v"]
        return (status, code) if status and code else None

    def walk(stmts: list[dict[str, Any]], para: Para) -> None:
        group: list[dict[str, Any]] = []

        def flush() -> None:
            if not group:
                return
            hint = _hint(prog, group[0]["line"])
            data: set[str] = set()
            _mentions(group, data)
            acts = [_action_text(s, names) for s in group]
            base = f"Cálculo en {para.name.replace('-', ' ').title()}"
            title = (f"{base}: {hint}" if hint and len(group) > 1 else hint) if hint else base
            title = title[:90]
            add(group[0], para, title, (hint + ". " if hint else "") + "Fórmulas: " + "; ".join(acts) + ".", "calculation", [], acts, data,
                0.8, ref_node={**group[0], "end": group[-1]["end"]})
            group.clear()

        for st in stmts:
            if _is_effect(st) and st["t"] != "move":
                group.append(st)
                continue
            flush()
            if st["t"] == "if":
                effects = [s for s in st["body"] if _is_effect(s)]
                if effects:
                    data: set[str] = set()
                    _mentions(st["cond"], data)
                    _mentions(effects, data)
                    cond = _cond_text(st["cond"], names)
                    hint = _hint(prog, st["line"])
                    rc = reject_code(effects)
                    then_ref = {**st, "end": st["body"][-1]["end"]}  # solo la rama THEN (no los IF anidados del ELSE)
                    if rc:
                        name = hint[:70] if hint else f"Rechazo {rc[1]}"
                        desc = (hint + ". " if hint else "") + f"Si {cond}, la solicitud se rechaza con el código de error {rc[1]}."
                        add(st, para, name, desc, "validation", [cond], [f"rechazar con estado {rc[0]} y código {rc[1]}"], data, 0.9, ref_node=then_ref)
                    else:
                        acts = [_action_text(s, names) for s in effects]
                        name = hint[:70] if hint else f"Condición en {para.name.replace('-', ' ').title()}"
                        add(st, para, name, (hint + ". " if hint else "") + f"Cuando {cond}: {'; '.join(acts)}.", "decision", [cond], acts, data, 0.88, ref_node=then_ref)
                walk([s for s in st["body"] if not _is_effect(s)], para)
                walk(st["orelse"], para)
            elif st["t"] == "evaluate":
                rows, data, conds, acts = [], set(), [], []
                for w in st["whens"]:
                    eff = [s for s in w["body"] if _is_effect(s)]
                    c = _cond_text(w["cond"], names) if w["cond"] else "En cualquier otro caso"
                    a = "; ".join(_action_text(s, names) for s in eff)
                    rows.append([c, a])
                    if w["cond"]:
                        _mentions(w["cond"], data)
                        conds.append(c)
                    _mentions(eff, data)
                    acts.append(f"{c} → {a}")
                hint = _hint(prog, st["line"])
                name = hint[:70] if hint else f"Tabla de decisión en {para.name.replace('-', ' ').title()}"
                add(st, para, name, (hint + ". " if hint else "") + "Matriz de decisión: " + " | ".join(acts) + ".", "decision", conds, acts, data, 0.9,
                    table={"columns": ["Condición", "Acción"], "rows": rows})
            elif st["t"] in ("perform_until", "perform_para_until"):
                walk(st.get("body") or [], para)
        flush()

    for p in reachable(prog):
        walk(p.stmts, p)
    return rules


# ---------------------------------------------------------------------------------------------------- análisis
def _flags(stmts: list[dict[str, Any]]) -> tuple[bool, bool, int]:
    logic = infra = False
    cc = 0

    def go(ss: list[dict[str, Any]]) -> None:
        nonlocal logic, infra, cc
        for s in ss:
            t = s["t"]
            if t == "infra":
                infra = True
            elif t in ("if", "evaluate") or _is_effect(s):
                logic = True
            if t == "if":
                cc += 1
                cc += len(re.findall(r'"c": "(?:and|or)"', json.dumps(s["cond"])))
            elif t == "evaluate":
                cc += max(0, len([w for w in s["whens"] if w["cond"]]))
            elif t in ("perform_until", "perform_para_until"):
                cc += 1
            for k in ("body", "orelse"):
                go(s.get(k) or [])
            for w in s.get("whens", []):
                go(w["body"])
    go(stmts)
    return logic, infra, cc + 1


def _save_cache(arts: list[dict[str, Any]], io: dict[str, Any]) -> None:
    """Las etapas posteriores (sin código en el prompt) recuperan el fuente por el hash del contrato de E/S."""
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / f"{_key(io['contract'])}.json").write_text(json.dumps(arts, ensure_ascii=False), encoding="utf-8")


def stage_analyze(user: str) -> dict[str, Any]:
    arts = sources_from_prompt(user)
    prog = parse_program(arts)
    io = io_model(prog)
    _save_cache(arts, io)
    live = {p.name for p in reachable(prog)}
    names = io["names"]
    units = [{"name": prog.program_id, "kind": "program", "file": prog.file, "start_line": 1, "end_line": len(prog.lines),
              "summary": f"Programa COBOL {prog.program_id} con {len(prog.paragraphs)} párrafos.", "classification": "mixed",
              "calls": [], "data_read": [], "data_written": []}]
    risks = []
    for p in prog.paragraphs:
        logic, infra, cc = _flags(p.stmts)
        calls: list[str] = []
        rd: set[str] = set()
        _mentions(p.stmts, rd)

        def collect(ss: list[dict[str, Any]]) -> None:
            for s in ss:
                if s["t"] in ("perform", "goto", "perform_para_until"):
                    calls.append(s["target"])
                for k in ("body", "orelse"):
                    collect(s.get(k) or [])
                for w in s.get("whens", []):
                    collect(w["body"])
        collect(p.stmts)
        cls = "mixed" if logic and infra else "business" if logic else "infrastructure"
        hint = _hint(prog, p.stmts[0]["line"]) if p.stmts else ""
        summ = (hint + ". " if hint else "") + ("Código muerto: ningún flujo llega a este párrafo. " if p.name not in live else "") + \
            ("Lógica de negocio." if cls == "business" else "Infraestructura (E/S, SQL, mensajes)." if cls == "infrastructure" else "Orquestación y/o lógica mezclada con E/S.")
        units.append({"name": p.name, "kind": "paragraph", "file": prog.file, "start_line": p.start, "end_line": p.end, "summary": summ,
                      "classification": cls, "calls": sorted(set(calls)), "data_read": sorted(names.get(x, x) for x in rd)[:12], "data_written": []})
        if cc >= 3:
            risks.append({"unit": p.name, "level": "high" if cc >= 6 else "medium", "reason": f"Complejidad ciclomática aproximada {cc}"})
    risks.sort(key=lambda r: r["level"] != "high")
    data_items = []
    for i in prog.items.values():
        if i.elementary:
            data_items.append({"name": i.name, "legacy_type": f"PIC {i.pic} {i.usage}".strip(),
                               "modern_type": f"Decimal (escala {i.scale})" if i.numeric else f"string({i.size})", "scale": i.scale,
                               "description": "Entrada/salida del contrato" if i.name in names else "Variable interna del programa"})
    return {"language": "COBOL", "dialect": "COBOL de formato fijo (subconjunto soportado por el motor local)",
            "domain_summary": f"Programa {prog.program_id}: " + (_hint(prog, prog.paragraphs[0].stmts[0]["line"]) or "lógica de negocio derivada del código") +
                              f" Entradas: {', '.join(names[i.name] for i in io['inputs'])}. Salidas: {', '.join(names[i.name] for i in io['outputs'])}.",
            "units": units, "entry_points": [prog.paragraphs[0].name], "data_items": data_items, "io_contract": io["contract"],
            "risks": risks or [{"unit": prog.program_id, "level": "low", "reason": "Sin construcciones complejas"}], "security_findings": []}


def stage_rules(user: str) -> dict[str, Any]:
    arts = sources_from_prompt(user)
    prog = parse_program(arts)
    io = io_model(prog)
    rules = extract_rules(prog, io["names"])
    from . import local_llm  # enriquecimiento opcional con modelo local (solo redacción)
    better = local_llm.rewrite_rule_descriptions(rules)
    for r in rules:
        if r["id"] in better:
            r["description"] = better[r["id"]]
            r["assumptions"].append(f"Descripción redactada con el modelo local {local_llm.model()}; condiciones, acciones y citas son deterministas.")
    return {"rules": rules}


# ---------------------------------------------------------------------------------------------------- backends
def _check_pow(exp: dict[str, Any], items: dict[str, Item]) -> None:
    """El exponente debe ser un entero ≥ 0 (literal o campo entero sin signo); lo demás cambiaría el resultado en silencio."""
    ok = (exp["e"] == "num" and "." not in exp["v"]) or (exp["e"] == "id" and items[exp["n"]].numeric and items[exp["n"]].scale == 0 and not items[exp["n"]].signed)
    if not ok:
        raise UnsupportedConstruct("Exponente fraccionario, negativo o calculado en '**' no soportado por el motor local.")


def _etype(e: dict[str, Any], items: dict[str, Item]) -> str:
    k = e["e"]
    if k in ("num", "neg", "bin"):
        return "num"
    if k == "str":
        return "str"
    if k == "fig":
        return "str" if e["v"].startswith(("SPACE", "HIGH", "LOW")) else "num"
    return "num" if items[e["n"]].numeric else "str"


class _Gen:
    """Base de los generadores: recorre el AST con una función de emisión por lenguaje."""

    def __init__(self, prog: Program, io: dict[str, Any], tags: dict[str, list[str]]) -> None:
        self.p, self.io, self.items = prog, io, prog.items
        self.live = reachable(prog)
        self.order = [x.name for x in self.live]
        self.tags = tags  # párrafo -> ids de reglas aprobadas

    def lit_num(self, v: str) -> str:
        return v


class TsGen(_Gen):
    def f(self, name: str) -> str:
        return "s." + _camel(name)

    def expr(self, e: dict[str, Any]) -> str:
        k = e["e"]
        if k == "num":
            return f"Decimal.of({_q(e['v'])})"
        if k == "fig":
            return "Decimal.zero(0)" if _etype(e, self.items) == "num" else "''"
        if k == "str":
            return _q(e["v"])
        if k == "id":
            return self.f(e["n"])
        if k == "neg":
            return self.expr(e["x"]) + ".negate()"
        op = e["op"]
        if op == "**":
            _check_pow(e["r"], self.items)
            return f"{self.expr(e['l'])}.pow({self.expr(e['r'])}.toInteger())"
        if op == "/":
            return f"{self.expr(e['l'])}.dividedBy({self.expr(e['r'])}, 30, 'DOWN')"
        return f"{self.expr(e['l'])}.{'plus' if op == '+' else 'minus' if op == '-' else 'times'}({self.expr(e['r'])})"

    def cond(self, c: dict[str, Any]) -> str:
        k = c["c"]
        if k == "and":
            return f"({self.cond(c['l'])} && {self.cond(c['r'])})"
        if k == "or":
            return f"({self.cond(c['l'])} || {self.cond(c['r'])})"
        if k == "not":
            return f"!({self.cond(c['x'])})"
        lt, rt = _etype(c["l"], self.items), _etype(c["r"], self.items)
        if lt != rt:
            raise UnsupportedConstruct("Comparación entre tipos distintos (numérico/alfanumérico) no soportada.")
        op = c["op"]
        if lt == "str":
            sop = {"=": "===", "<>": "!==", ">": ">", "<": "<", ">=": ">=", "<=": "<="}[op]
            return f"{self.expr(c['l'])} {sop} {self.expr(c['r'])}"
        m = {"=": "equals", "<>": None, ">": "gt", "<": "lt", ">=": "gte", "<=": "lte"}[op]
        if m is None:
            return f"!{self.expr(c['l'])}.equals({self.expr(c['r'])})"
        return f"{self.expr(c['l'])}.{m}({self.expr(c['r'])})"

    def store(self, name: str, value: str, rounded: bool) -> str:
        it = self.items[name]
        if it.numeric:
            return f"{self.f(name)} = {value}.toPic({it.int_digits}, {it.scale}, {str(it.signed).lower()}, {str(rounded).lower()});"
        return f"{self.f(name)} = {value};"

    def move_value(self, src: dict[str, Any], target: str) -> str:
        it = self.items[target]
        if it.numeric:
            if src["e"] == "fig":
                return f"Decimal.zero({it.scale})"
            if _etype(src, self.items) != "num":
                raise UnsupportedConstruct(f"MOVE alfanumérico a campo numérico {target} no soportado.")
            return self.expr(src)
        if src["e"] == "fig":
            return "''"
        if src["e"] == "str":
            return _q(src["v"][: it.size])
        if src["e"] == "id" and not self.items[src["n"]].numeric:
            return self.f(src["n"])
        raise UnsupportedConstruct(f"MOVE numérico a campo alfanumérico {target} no soportado.")

    def stmts(self, ss: list[dict[str, Any]], ind: int) -> list[str]:
        out: list[str] = []
        pad = "  " * ind
        for s in ss:
            t = s["t"]
            if t == "move":
                for tg in s["targets"]:
                    out.append(pad + self.store(tg, self.move_value(s["src"], tg), False))
            elif t == "compute":
                out.append(pad + self.store(s["target"], self.expr(s["expr"]), s["rounded"]))
            elif t in ("add", "subtract"):
                total = self.expr(s["operands"][0])
                for o in s["operands"][1:]:
                    total += f".plus({self.expr(o)})"
                op = "plus" if t == "add" else "minus"
                out.append(pad + self.store(s["target"], f"{self.f(s['target'])}.{op}({total})", s["rounded"]))
            elif t == "multiply":
                out.append(pad + self.store(s["target"], f"{self.f(s['target'])}.times({self.expr(s['factor'])})", s["rounded"]))
            elif t == "divide":
                out.append(pad + self.store(s["target"], f"{self.expr(s['a'])}.dividedBy({self.expr(s['b'])}, 30, 'DOWN')", s["rounded"]))
            elif t == "divide_into":
                out.append(pad + self.store(s["target"], f"{self.f(s['target'])}.dividedBy({self.expr(s['divisor'])}, 30, 'DOWN')", s["rounded"]))
            elif t == "if":
                out.append(pad + f"if ({self.cond(s['cond'])}) {{")
                out += self.stmts(s["body"], ind + 1)
                if s["orelse"]:
                    out.append(pad + "} else {")
                    out += self.stmts(s["orelse"], ind + 1)
                out.append(pad + "}")
            elif t == "evaluate":
                first = True
                for w in s["whens"]:
                    head = "if" if first else "} else if"
                    if w["cond"] is None:
                        out.append(pad + ("} else {" if not first else "{"))
                    else:
                        out.append(pad + f"{head} ({self.cond(w['cond'])}) {{")
                    out += self.stmts(w["body"], ind + 1)
                    first = False
                out.append(pad + "}")
            elif t == "perform":
                names = [s["target"]] if not s["thru"] else self.order[self.order.index(s["target"]): self.order.index(s["thru"]) + 1]
                body = []
                for n in names:
                    body += [f"const flow = this.{_pm(n)}(s);", "if (flow !== null) {", "  return flow;", "}"]
                if s["times"]:
                    out.append(pad + f"for (let i = 0; i < {self.expr(s['times'])}.toInteger(); i += 1) {{")
                    out += [pad + "  " + b for b in body]
                    out.append(pad + "}")
                else:
                    out.append(pad + "{")
                    out += [pad + "  " + b for b in body]
                    out.append(pad + "}")
            elif t == "perform_until":
                out.append(pad + f"while (!({self.cond(s['cond'])})) {{")
                out += self.stmts(s["body"], ind + 1)
                out.append(pad + "}")
            elif t == "perform_para_until":
                out.append(pad + f"while (!({self.cond(s['cond'])})) {{")
                out += [pad + f"  const flow = this.{_pm(s['target'])}(s);", pad + "  if (flow !== null) {", pad + "    return flow;", pad + "  }"]
                out.append(pad + "}")
            elif t == "goto":
                out.append(pad + f"return {_q(s['target'])};")
            elif t == "stop":
                out.append(pad + "return STOP;")
            elif t == "infra":
                out.append(pad + f"// (infraestructura legacy {s['kind'].upper()} omitida del dominio: la resuelven los adaptadores)")
        return out

    def files(self) -> list[dict[str, str]]:
        pid = _pascal(self.p.program_id)
        state, service = f"{pid}State", f"{pid}Service"
        io = self.io
        names = io["names"]
        # --- estado
        fields = []
        for it in self.items.values():
            if not it.elementary:
                continue
            init = f"Decimal.zero({it.scale})" if it.numeric else _q(str(it.value) if it.value is not None and not it.numeric else "")
            if it.numeric and it.value not in (None, ""):
                init = f"Decimal.of({_q(str(it.value))}).toPic({it.int_digits}, {it.scale}, {str(it.signed).lower()}, false)"
            ftype = "Decimal" if it.numeric else "string"
            fields.append(f"  {_camel(it.name)}: {ftype} = {init};")
        state_ts = ("import { Decimal } from '../shared/decimal.ts';\n\n/** Memoria de trabajo del programa legacy (WORKING-STORAGE + registros de E/S). */\n"
                    f"export class {state} {{\n" + "\n".join(fields) + "\n}\n")
        # --- servicio de dominio
        methods = []
        for p in self.live:
            body = self.stmts(p.stmts, 2)
            tag = self.tags.get(p.name, [])
            doc = [f"  /**", f"   * Párrafo {p.name} del COBOL original (líneas {p.start}-{p.end})."] + [f"   * @rule {r}" for r in tag] + ["   */"]
            methods += doc + [f"  private {_pm(p.name)}(s: {state}): Flow {{"] + body + ["    return null;", "  }", ""]
        table = ",\n".join(f"    {_q(n)}: (s) => this.{_pm(n)}(s)" for n in self.order)
        service_ts = (f"import {{ Decimal }} from '../shared/decimal.ts';\nimport type {{ {state} }} from '../model/{state}.ts';\n\n"
                      "const STOP = '__STOP__';\nconst ORDER: readonly string[] = [" + ", ".join(_q(n) for n in self.order) + "];\n"
                      f"type Flow = string | null;\n\n/**\n * Servicio de dominio: ejecuta la lógica de {self.p.program_id}. El flujo del legacy (PERFORM / GO TO / fall-through)\n"
                      " * se resuelve con valores de flujo explícitos, sin saltos incondicionales.\n */\n"
                      f"export class {service} {{\n  private readonly table: Record<string, (s: {state}) => Flow> = {{\n{table},\n  }};\n\n"
                      f"  run(state: {state}): {state} {{\n    let current: string | null = ORDER[0] ?? null;\n    while (current !== null && current !== STOP) {{\n"
                      "      const flow: Flow = this.table[current](state);\n      current = flow === null ? this.following(current) : flow;\n    }\n    return state;\n  }\n\n"
                      "  private following(name: string): string | null {\n    return ORDER[ORDER.indexOf(name) + 1] ?? null;\n  }\n\n" + "\n".join(methods) + "}\n")
        # --- aplicación
        port_in = (f"import type {{ {state} }} from '../../../domain/model/{state}.ts';\n\nexport interface Run{pid}UseCase {{\n  execute(state: {state}): {state};\n}}\n")
        port_out = (f"import type {{ {state} }} from '../../../domain/model/{state}.ts';\n\n/** Puerto de salida: reemplaza el EXEC SQL de auditoría del legacy. */\n"
                    f"export interface AuditPort {{\n  record(state: {state}): void;\n}}\n")
        usecase = (f"import type {{ {state} }} from '../../domain/model/{state}.ts';\nimport type {{ {service} }} from '../../domain/service/{service}.ts';\n"
                   f"import type {{ AuditPort }} from '../port/out/AuditPort.ts';\nimport type {{ Run{pid}UseCase }} from '../port/in/Run{pid}UseCase.ts';\n\n"
                   f"export class Run{pid} implements Run{pid}UseCase {{\n  private readonly service: {service};\n  private readonly audit: AuditPort;\n\n"
                   f"  constructor(service: {service}, audit: AuditPort) {{\n    this.service = service;\n    this.audit = audit;\n  }}\n\n"
                   f"  execute(state: {state}): {state} {{\n    const result = this.service.run(state);\n    this.audit.record(result);\n    return result;\n  }}\n}}\n")
        # --- infraestructura
        ins, outs = [], []
        for it in io["inputs"]:
            n = names[it.name]
            ins.append(f"  state.{_camel(it.name)} = " + (f"Decimal.of(input[{_q(n)}]).toPic({it.int_digits}, {it.scale}, {str(it.signed).lower()}, false);" if it.numeric
                                                          else f"String(input[{_q(n)}]);"))
        for it in io["outputs"]:
            n = names[it.name]
            outs.append(f"    {n}: state.{_camel(it.name)}" + (".toString()" if it.numeric else "") + ",")
        mapper = (f"import {{ Decimal }} from '../../../domain/shared/decimal.ts';\nimport {{ {state} }} from '../../../domain/model/{state}.ts';\n\n"
                  f"export function toState(input: Record<string, string>): {state} {{\n  const state = new {state}();\n" + "\n".join(ins) + "\n  return state;\n}\n\n"
                  f"export function toOutput(state: {state}): Record<string, string> {{\n  return {{\n" + "\n".join(outs) + "\n  };\n}\n")
        audit = (f"import type {{ {state} }} from '../../../domain/model/{state}.ts';\nimport type {{ AuditPort }} from '../../../application/port/out/AuditPort.ts';\n\n"
                 f"export class InMemoryAudit implements AuditPort {{\n  readonly entries: {state}[] = [];\n\n  record(state: {state}): void {{\n    this.entries.push(state);\n  }}\n}}\n")
        index = (f"import {{ {service} }} from './domain/service/{service}.ts';\nimport {{ Run{pid} }} from './application/usecase/Run{pid}.ts';\n"
                 "import { InMemoryAudit } from './infrastructure/adapter/out/InMemoryAudit.ts';\nimport { toOutput, toState } from './infrastructure/adapter/in/StateMapper.ts';\n\n"
                 f"// Composition root: sin lógica de negocio.\nconst useCase = new Run{pid}(new {service}(), new InMemoryAudit());\n\n"
                 "export function execute(input: Record<string, string>): Record<string, string> {\n  return toOutput(useCase.execute(toState(input)));\n}\n")
        pkg = json.dumps({"name": self.p.program_id.lower(), "version": "1.0.0", "type": "module", "scripts": {"test": "node --test tests/"}}, indent=2)
        readme = (f"# {self.p.program_id} (migrado)\n\nGenerado por el motor local determinista a partir de {self.p.file}.\n\n"
                  "- `src/domain`: estado y servicio de dominio (reglas de negocio)\n- `src/application`: caso de uso y puertos\n- `src/infrastructure`: adaptadores\n"
                  "- Ejecutar pruebas: `node --test tests/`\n")
        f = lambda path, content: {"path": path, "content": content}  # noqa: E731
        return [f(f"src/domain/model/{state}.ts", state_ts), f(f"src/domain/service/{service}.ts", service_ts),
                f(f"src/application/port/in/Run{pid}UseCase.ts", port_in), f("src/application/port/out/AuditPort.ts", port_out),
                f(f"src/application/usecase/Run{pid}.ts", usecase), f("src/infrastructure/adapter/in/StateMapper.ts", mapper),
                f("src/infrastructure/adapter/out/InMemoryAudit.ts", audit), f("src/index.ts", index), f("package.json", pkg), f("README.md", readme)]


class PyGen(_Gen):
    HEAD = '''from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, localcontext

STOP = "__STOP__"


def _store(v, ints, scale, signed, rounded):
    with localcontext() as c:
        c.prec = 30000
        q = Decimal(1).scaleb(-scale)
        r = v.quantize(q, rounding=ROUND_HALF_UP if rounded else ROUND_DOWN)
        a = abs(r) % (Decimal(10) ** ints)
        r = (-a if (signed and r < 0) else a).quantize(q)
        return r


def _div(a, b):
    with localcontext() as c:
        c.prec = 400
        return (a / b).quantize(Decimal(1).scaleb(-30), rounding=ROUND_DOWN)


def _pow(a, n):
    with localcontext() as c:
        c.prec = 30000
        return a ** int(n)

'''

    def expr(self, e: dict[str, Any]) -> str:
        k = e["e"]
        if k == "num":
            return f"Decimal({e['v']!r})"
        if k == "fig":
            return "Decimal(0)" if _etype(e, self.items) == "num" else "''"
        if k == "str":
            return repr(e["v"])
        if k == "id":
            return f"s[{e['n']!r}]"
        if k == "neg":
            return f"(-{self.expr(e['x'])})"
        op = e["op"]
        if op == "**":
            _check_pow(e["r"], self.items)
            return f"_pow({self.expr(e['l'])}, {self.expr(e['r'])})"
        if op == "/":
            return f"_div({self.expr(e['l'])}, {self.expr(e['r'])})"
        return f"({self.expr(e['l'])} {op} {self.expr(e['r'])})"

    def cond(self, c: dict[str, Any]) -> str:
        k = c["c"]
        if k in ("and", "or"):
            return f"({self.cond(c['l'])} {k} {self.cond(c['r'])})"
        if k == "not":
            return f"(not {self.cond(c['x'])})"
        op = {"=": "==", "<>": "!="}.get(c["op"], c["op"])
        return f"({self.expr(c['l'])} {op} {self.expr(c['r'])})"

    def store(self, name: str, value: str, rounded: bool) -> str:
        it = self.items[name]
        if it.numeric:
            return f"s[{name!r}] = _store({value}, {it.int_digits}, {it.scale}, {it.signed}, {rounded})"
        return f"s[{name!r}] = {value}"

    def move_value(self, src: dict[str, Any], target: str) -> str:
        it = self.items[target]
        if it.numeric:
            return f"Decimal(0)" if src["e"] == "fig" else self.expr(src)
        if src["e"] == "fig":
            return "''"
        if src["e"] == "str":
            return repr(src["v"][: it.size])
        return self.expr(src)

    def stmts(self, ss: list[dict[str, Any]], ind: int) -> list[str]:
        out: list[str] = []
        pad = "    " * ind
        for s in ss:
            t = s["t"]
            if t == "move":
                for tg in s["targets"]:
                    out.append(pad + self.store(tg, self.move_value(s["src"], tg), False))
            elif t == "compute":
                out.append(pad + self.store(s["target"], self.expr(s["expr"]), s["rounded"]))
            elif t in ("add", "subtract"):
                total = " + ".join(self.expr(o) for o in s["operands"])
                out.append(pad + self.store(s["target"], f"(s[{s['target']!r}] {'+' if t == 'add' else '-'} ({total}))", s["rounded"]))
            elif t == "multiply":
                out.append(pad + self.store(s["target"], f"(s[{s['target']!r}] * {self.expr(s['factor'])})", s["rounded"]))
            elif t == "divide":
                out.append(pad + self.store(s["target"], f"_div({self.expr(s['a'])}, {self.expr(s['b'])})", s["rounded"]))
            elif t == "divide_into":
                out.append(pad + self.store(s["target"], f"_div(s[{s['target']!r}], {self.expr(s['divisor'])})", s["rounded"]))
            elif t == "if":
                out.append(pad + f"if {self.cond(s['cond'])}:")
                out += self.stmts(s["body"], ind + 1) or [pad + "    pass"]
                if s["orelse"]:
                    out.append(pad + "else:")
                    out += self.stmts(s["orelse"], ind + 1)
            elif t == "evaluate":
                first = True
                for w in s["whens"]:
                    out.append(pad + ("else:" if w["cond"] is None else f"{'if' if first else 'elif'} {self.cond(w['cond'])}:"))
                    out += self.stmts(w["body"], ind + 1) or [pad + "    pass"]
                    first = False
            elif t == "perform":
                names = [s["target"]] if not s["thru"] else self.order[self.order.index(s["target"]): self.order.index(s["thru"]) + 1]
                body = []
                for n in names:
                    body += [f"flow = P_{n.replace('-', '_')}(s)", "if flow is not None:", "    return flow"]
                if s["times"]:
                    out.append(pad + f"for _ in range(int({self.expr(s['times'])})):")
                    out += [pad + "    " + b for b in body]
                else:
                    out += [pad + b for b in body]
            elif t == "perform_until":
                out.append(pad + f"while not {self.cond(s['cond'])}:")
                out += self.stmts(s["body"], ind + 1) or [pad + "    pass"]
            elif t == "perform_para_until":
                out.append(pad + f"while not {self.cond(s['cond'])}:")
                out += [pad + f"    flow = P_{s['target'].replace('-', '_')}(s)", pad + "    if flow is not None:", pad + "        return flow"]
            elif t == "goto":
                out.append(pad + f"return {s['target']!r}")
            elif t == "stop":
                out.append(pad + "return STOP")
        return out

    def code(self) -> str:
        lines = [self.HEAD]
        for p in self.live:
            lines.append(f"def P_{p.name.replace('-', '_')}(s):")
            lines += self.stmts(p.stmts, 1) or []
            lines += ["    return None", ""]
        lines.append("PARAS = {" + ", ".join(f"{n!r}: P_{n.replace('-', '_')}" for n in self.order) + "}")
        lines.append(f"ORDER = {self.order!r}")
        lines += ["", "", "def run(inp):", "    s = {}"]
        for it in self.items.values():
            if it.elementary:
                init = "Decimal(0)" if it.numeric else repr(str(it.value) if it.value is not None else "")
                if it.numeric and it.value not in (None, ""):
                    init = f"Decimal({str(it.value)!r})"
                lines.append(f"    s[{it.name!r}] = {init}")
        for it in self.io["inputs"]:
            n = self.io["names"][it.name]
            lines.append(f"    s[{it.name!r}] = " + (f"_store(Decimal(inp[{n!r}]), {it.int_digits}, {it.scale}, {it.signed}, False)" if it.numeric else f"str(inp[{n!r}])"))
        lines += [f"    cur = ORDER[0]", "    while cur is not None and cur != STOP:", "        flow = PARAS[cur](s)",
                  "        if flow is None:", "            i = ORDER.index(cur) + 1", "            cur = ORDER[i] if i < len(ORDER) else None",
                  "        else:", "            cur = flow", "    return {"]
        for it in self.io["outputs"]:
            n = self.io["names"][it.name]
            lines.append(f"        {n!r}: " + (f"format(s[{it.name!r}], 'f')," if it.numeric else f"s[{it.name!r}].rstrip(),"))
        lines.append("    }")
        return "\n".join(lines) + "\n"


def _tags(prog: Program, rules: list[dict[str, Any]], approved: set[str] | None) -> dict[str, list[str]]:
    tags: dict[str, list[str]] = {}
    for r in rules:
        if approved is not None and r["id"] not in approved:
            continue
        tags.setdefault(r["para"], []).append(r["id"])
    return tags


def _program_for(user: str) -> tuple[Program, dict[str, Any], list[dict[str, Any]]]:
    arts = sources_from_prompt(user)
    if not arts:  # etapas sin código en el prompt: se recupera por el contrato de E/S
        io_c = None
        for marker in ("CONTRATO DE E/S", "ANÁLISIS DEL LEGACY"):
            obj = _json_after(user, marker)
            if isinstance(obj, dict):
                io_c = obj.get("io_contract", obj)
                break
        path = CACHE / f"{_key(io_c)}.json" if io_c else None
        if not path or not path.exists():
            raise UnsupportedConstruct("No se encontró el código fuente analizado (repita el análisis).")
        arts = json.loads(path.read_text(encoding="utf-8"))
    prog = parse_program(arts)
    io = io_model(prog)
    _save_cache(arts, io)
    return prog, io, extract_rules(prog, io["names"])


def stage_codegen(user: str, system: str = "") -> dict[str, Any]:
    if system and "proyecto TypeScript" not in system:
        raise UnsupportedConstruct("Sin la API de Claude solo se genera el destino Node.js/TypeScript (Java y C# requieren la API).")
    prog, io, rules = _program_for(user)
    approved_list = _json_after(user, "CATÁLOGO DE REGLAS APROBADO")
    approved = {r["id"] for r in approved_list} if isinstance(approved_list, list) else None
    gen = TsGen(prog, io, _tags(prog, rules, approved))
    files = gen.files()
    all_ids = {r["id"] for r in rules}
    rejected = sorted(all_ids - (approved or all_ids))
    dead = [p.name for p in prog.paragraphs if p.name not in {x.name for x in gen.live}]
    pid = _pascal(prog.program_id)
    assumptions = ["Redondeo COBOL ROUNDED = mitad hacia arriba (HALF_UP); sin ROUNDED = truncamiento.",
                   "Divisiones intermedias exactas a 30 decimales (truncadas) antes de almacenar en el campo destino.",
                   "Los rechazos de negocio se devuelven como salidas (status/código), no como excepciones.",
                   "Generado por el motor local determinista: transpila el programa completo (subconjunto COBOL soportado)."]
    if rejected:
        assumptions.append(f"Reglas rechazadas en la revisión ({', '.join(rejected)}): el motor local transpila el programa completo y no las excluye del código.")
    props = "\n".join(f"        {f['name']}:\n          type: string" for f in io["contract"]["inputs"])
    oprops = "\n".join(f"        {f['name']}:\n          type: string" for f in io["contract"]["outputs"])
    openapi = (f"openapi: 3.0.3\ninfo:\n  title: {prog.program_id} API\n  version: 1.0.0\npaths:\n  /{prog.program_id.lower()}:\n    post:\n      summary: Ejecuta la lógica migrada\n"
               f"      requestBody:\n        required: true\n        content:\n          application/json:\n            schema:\n              $ref: '#/components/schemas/Request'\n"
               f"      responses:\n        '200':\n          description: Resultado\n          content:\n            application/json:\n              schema:\n                $ref: '#/components/schemas/Response'\n"
               f"components:\n  schemas:\n    Request:\n      type: object\n      properties:\n{props}\n    Response:\n      type: object\n      properties:\n{oprops}\n")
    design = {"summary": f"Arquitectura hexagonal para {prog.program_id}: el estado y los párrafos del legacy se modelan como un servicio de dominio puro "
                         f"({pid}Service) con flujo explícito; el caso de uso Run{pid} orquesta y los adaptadores resuelven E/S y auditoría.",
              "domain_model": [{"name": f"{pid}State", "kind": "entidad de estado", "responsibility": "Memoria de trabajo (WORKING-STORAGE y registros) con precisión decimal exacta"},
                               {"name": f"{pid}Service", "kind": "servicio de dominio", "responsibility": "Reglas de negocio y cálculos (un método por párrafo)"}],
              "ports": [{"name": f"Run{pid}UseCase", "direction": "in", "description": "Ejecuta la lógica de negocio"},
                        {"name": "AuditPort", "direction": "out", "description": "Auditoría (reemplaza el EXEC SQL del legacy)"}],
              "patterns": ["Hexagonal / Puertos y Adaptadores", "Servicio de dominio", "Composition root"],
              "adrs": [{"title": "Aritmética decimal exacta con escala", "context": "Los campos PIC/COMP-3 exigen precisión y redondeo deterministas.",
                        "decision": "Usar un Decimal propio (BigInt escalado) con ROUNDED=HALF_UP, truncamiento y truncado de PIC.", "consequences": "Sin errores de punto flotante; mismo resultado que el legacy."},
                       {"title": "Flujo de control explícito en lugar de GO TO", "context": "El legacy usa PERFORM, GO TO y fall-through entre párrafos.",
                        "decision": "Cada párrafo devuelve un valor de flujo (siguiente párrafo, parada o continuar); un ejecutor lo interpreta.", "consequences": "Se elimina el salto incondicional preservando la semántica."},
                       {"title": "Aislamiento de la infraestructura legacy", "context": "OPEN/READ/WRITE/EXEC SQL no son lógica de negocio.",
                        "decision": f"Se omiten del dominio; la auditoría pasa a AuditPort y la E/S a adaptadores.", "consequences": "Dominio testeable sin base de datos ni archivos."}]
              + ([{"title": "Eliminación de código muerto", "context": f"Párrafos sin ningún camino de ejecución: {', '.join(dead)}.",
                   "decision": "No se migran.", "consequences": "Menos superficie de mantenimiento."}] if dead else [])}
    return {"design": design, "files": files, "openapi_yaml": openapi, "assumptions": assumptions}


def stage_oracle(user: str) -> dict[str, Any]:
    prog, io, rules = _program_for(user)
    return {"python_code": PyGen(prog, io, {}).code(),
            "notes": "Referencia independiente generada por un segundo traductor (Python/decimal) directamente del COBOL; no ejecuta el legacy."}


def _literals(prog: Program, io: dict[str, Any]) -> dict[str, list[str]]:
    """Valores umbral por campo de entrada: literales comparados directamente con el campo."""
    found: dict[str, set[str]] = {i.name: set() for i in io["inputs"]}

    def cond(c: dict[str, Any]) -> None:
        if c["c"] == "cmp":
            for a, b in ((c["l"], c["r"]), (c["r"], c["l"])):
                if a["e"] == "id" and a["n"] in found and b["e"] == "num":
                    found[a["n"]].add(b["v"])
        elif c["c"] == "not":
            cond(c["x"])
        else:
            cond(c["l"])
            cond(c["r"])

    def walk(ss: list[dict[str, Any]]) -> None:
        for s in ss:
            if s["t"] in ("if", "perform_until", "perform_para_until"):
                cond(s["cond"])
            for w in s.get("whens", []):
                if w["cond"]:
                    cond(w["cond"])
                walk(w["body"])
            walk(s.get("body") or [])
            walk(s.get("orelse") or [])
    for p in prog.paragraphs:
        walk(p.stmts)
    return {k: sorted(v, key=lambda x: float(x)) for k, v in found.items()}


def _fmt(d: Any, scale: int) -> str:
    return format(d.quantize(__import__("decimal").Decimal(1).scaleb(-scale)), "f")


def stage_qa_cases(user: str) -> dict[str, Any]:
    from decimal import Decimal
    prog, io, rules = _program_for(user)
    names = io["names"]
    ins = io["inputs"]
    lits = _literals(prog, io)
    py = PyGen(prog, io, {}).code()
    cand: dict[str, list[str]] = {}
    for it in ins:
        step = Decimal(1).scaleb(-it.scale)
        vals: set[str] = set()
        for lit in lits[it.name]:
            d = Decimal(lit)
            for v in (d - step, d, d + step):
                if v >= 0:
                    vals.add(_fmt(v, it.scale))
        if not it.numeric:
            vals = {"A"}
        cand[it.name] = sorted(vals, key=lambda x: float(x) if it.numeric else 0) or ["1"]
    # búsqueda de un caso base aprobado: producto reducido sobre candidatos + medios
    pool = {n: (v + ([_fmt((Decimal(v[0]) + Decimal(v[-1])) / 2, next(i.scale for i in ins if i.name == n))] if len(v) > 1 else [])) for n, v in cand.items()}
    rnd = random.Random(7)
    grid = [dict(zip(pool, combo)) for combo in itertools.islice(itertools.product(*pool.values()), 20000)]
    rnd.shuffle(grid)
    probe = [{"name": f"p{i}", "input": {names[k]: v for k, v in g.items()}} for i, g in enumerate(grid[:400])]
    res = verify.run_oracle(py, probe)
    if not res["ok"]:
        raise UnsupportedConstruct("El oráculo local no pudo ejecutarse: " + res["error"][:200])
    outs = {r["name"]: r.get("output") for r in res["results"] if r["ok"]}
    out_fields = [names[i.name] for i in io["outputs"]]
    status_like = next((f for f in out_fields if re.search(r"status|estado", f)), None)
    code_like = next((f for f in out_fields if re.search(r"error|code|cod", f)), None)

    def sig(o: dict[str, str]) -> tuple:
        return tuple(o.get(f) for f in (status_like, code_like) if f)
    base = None
    best = -1
    for p in probe:
        o = outs.get(p["name"])
        if not o:
            continue
        score = sum(1 for f in out_fields if o[f] not in ("0", "0.00", "0.0000", "", "0.000000000") and f not in (status_like, code_like))
        if score > best:
            best, base = score, p["input"]
    if base is None:
        raise UnsupportedConstruct("No fue posible encontrar un caso base ejecutable.")
    rule_by_field: dict[str, list[str]] = {}
    for r in rules:
        for fld in r["data_items"]:
            rule_by_field.setdefault(fld, []).append(r["id"])
    all_ids = [r["id"] for r in rules]
    cases: list[dict[str, Any]] = [{"name": "caso_base_nominal", "category": "nominal", "rule_ids": all_ids, "rationale": "Camino feliz que ejercita todas las reglas",
                                    "input": [{"name": k, "value": v} for k, v in base.items()]}]
    seen = {json.dumps(base, sort_keys=True)}

    def add(name: str, cat: str, ids: list[str], inp: dict[str, str], why: str) -> None:
        key = json.dumps(inp, sort_keys=True)
        if key in seen:
            return
        seen.add(key)
        cases.append({"name": re.sub(r"[^a-z0-9_]", "_", name.lower()), "category": cat, "rule_ids": ids or all_ids[:1], "rationale": why,
                      "input": [{"name": k, "value": v} for k, v in inp.items()]})
    for it in ins:
        n = names[it.name]
        for v in cand[it.name]:
            add(f"{n}_{v}".replace(".", "_"), "boundary", rule_by_field.get(n, []), {**base, n: v}, f"Valor de frontera de {n}")
    # cobertura por firma de resultado (p. ej. cada código de rechazo)
    sigs = {sig(outs[p["name"]]) for p in probe if outs.get(p["name"])}
    for sg in sorted(sigs, key=str):
        n = sum(1 for c in cases if True)
        for p in probe:
            o = outs.get(p["name"])
            if o and sig(o) == sg:
                add(f"resultado_{'_'.join(str(x) or 'vacio' for x in sg)}_{p['name']}".lower(), "error" if "REJECT" in str(sg) else "nominal", [], p["input"], f"Cubre el resultado {sg}")
                break
    # estrés de redondeo: montos con muchos decimales
    for it in ins:
        if it.numeric and it.scale:
            n = names[it.name]
            for v in ("33333.33", "477777.77", "12345.67", "99999.99"):
                if _fmt(Decimal(v), it.scale) not in cand[it.name]:
                    add(f"redondeo_{n}_{v}".replace(".", "_"), "rounding", rule_by_field.get(n, []) + [r["id"] for r in rules if r["category"] == "calculation"],
                        {**base, n: _fmt(Decimal(v), it.scale)}, "Estrés de redondeo con decimales largos")
            break
    return {"cases": cases[:46]}


def stage_docs(user: str) -> dict[str, Any]:
    analysis = _json_after(user, "ANÁLISIS DEL LEGACY") or {}
    units = analysis.get("units", [])
    paras = [u for u in units if u.get("kind") == "paragraph"]
    biz = [u["name"] for u in paras if u.get("classification") != "infrastructure"]
    infra = [u["name"] for u in paras if u.get("classification") == "infrastructure"]
    ov = ["## Qué hace el programa", analysis.get("domain_summary", ""), "", "## Flujo as-is (párrafos)", ""]
    ov += [f"- **{u['name']}** ({u['classification']}): {u['summary']}" for u in paras]
    ov += ["", "## Lógica de infraestructura que NO se migra", "", ", ".join(infra) or "Ninguna.",
           "", "En el sistema nuevo la auditoría pasa al puerto `AuditPort` y la E/S a adaptadores; el dominio queda puro."]
    flows = []
    for u in paras:
        for c in u.get("calls", []):
            if c in {x["name"] for x in paras}:
                flows.append((u["name"], c))
    seq = ["sequenceDiagram", "  participant Cliente", "  participant API as Adaptador de entrada", "  participant UC as Caso de uso", "  participant DOM as Servicio de dominio",
           "  Cliente->>API: solicitud", "  API->>UC: execute(state)", "  UC->>DOM: run(state)"]
    seen = set()
    for a, b in flows:
        if (a, b) not in seen and len(seen) < 8:
            seen.add((a, b))
            seq.append(f"  DOM->>DOM: {a.replace('-', '_')} invoca {b.replace('-', '_')}")
    seq += ["  DOM-->>UC: estado final", "  UC-->>API: resultado", "  API-->>Cliente: respuesta"]
    arch = ("flowchart LR\n  subgraph Infraestructura\n    IN[Adaptador de entrada]\n    OUT[Adaptador de auditoria]\n  end\n  subgraph Aplicacion\n    UC[Caso de uso]\n    PIN((Puerto de entrada))\n    POUT((Puerto de auditoria))\n  end\n"
            "  subgraph Dominio\n    SVC[Servicio de dominio]\n    ST[Estado]\n  end\n  IN --> PIN --> UC --> SVC --> ST\n  UC --> POUT --> OUT")
    from . import local_llm
    summary = (f"Se analizó el programa legacy, se descubrieron y formalizaron las reglas de negocio con trazabilidad a líneas de origen, "
               f"se aprobaron por un ingeniero y se generó código moderno con arquitectura hexagonal. La equivalencia con el comportamiento original se verifica con "
               f"casos de borde y tolerancia cero en cálculos y redondeos, reduciendo el riesgo de regresión y el tiempo de análisis manual. "
               f"Lógica de negocio: {len(biz)} unidades; infraestructura aislada: {len(infra)}.")
    ai = local_llm.executive_summary(summary + " " + str(analysis.get("domain_summary", "")))
    return {"overview_md": "\n".join(ov),
            "data_dictionary": [{"name": f["name"], "legacy_type": f["type"] + (f" (escala {f['scale']})" if f["scale"] else ""), "modern_type": "Decimal" if f["type"] in ("decimal", "integer") else "string",
                                 "description": f["description"]} for f in (analysis.get("io_contract", {}).get("inputs", []) + analysis.get("io_contract", {}).get("outputs", []))],
            "architecture_mermaid": arch, "sequence_mermaid": "\n".join(seq),
            "glossary": [{"term": "ROUNDED", "definition": "Redondeo de COBOL al almacenar el resultado; mitad hacia arriba."}, {"term": "COMP-3", "definition": "Decimal empaquetado: se modela con Decimal exacto."},
                         {"term": "PIC", "definition": "Descripción del formato (dígitos y escala) de un campo."}, {"term": "Párrafo", "definition": "Unidad de código COBOL invocable con PERFORM."}],
            "executive_summary": ai or summary,
            "assumptions": ["Documentación generada por el motor local determinista a partir del análisis del código"
                            + (" (el resumen ejecutivo fue redactado con el modelo local de IA configurado)." if ai else " (sin IA generativa)."),
                            "Los textos descriptivos de las reglas provienen de los comentarios del propio código cuando existen."]}


STAGES = {"analyze": stage_analyze, "rules": stage_rules, "codegen": stage_codegen, "oracle": stage_oracle, "qa_cases": stage_qa_cases, "docs": stage_docs}


def provider(stage: str, system: str, user: str, schema: dict | None) -> Any:
    fn = STAGES.get(stage)
    if fn is None:
        raise UnsupportedConstruct(f"La etapa '{stage}' no está disponible en el motor local (requiere la API de Claude).")
    return fn(user, system) if stage == "codegen" else fn(user)

