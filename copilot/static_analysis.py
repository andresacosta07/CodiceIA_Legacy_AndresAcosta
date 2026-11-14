"""Análisis estático determinista (plugins LanguageAdapter, ADR-002).

- Adaptador COBOL determinista: párrafos, PERFORM/GO TO/CALL/COPY, EXEC SQL, PIC/COMP-3, código muerto.
- Adaptador genérico: LOC y complejidad ciclomática aproximada para cualquier lenguaje.
El LLM trabaja SOBRE esta estructura (y se valida contra ella).
"""
from __future__ import annotations

import re
from typing import Any, Protocol


class LanguageAdapter(Protocol):
    name: str

    def supports(self, language: str) -> bool: ...
    def analyze(self, artifact: dict[str, Any]) -> dict[str, Any]: ...


_DECISION = {
    "cobol": re.compile(r"\b(IF|WHEN|UNTIL|VARYING|AND|OR|EVALUATE)\b", re.I),
    "plsql": re.compile(r"\b(IF|ELSIF|WHEN|WHILE|FOR|LOOP|AND|OR|CASE|EXCEPTION)\b", re.I),
    "rpg": re.compile(r"\b(IF|ELSEIF|WHEN|DOW|DOU|FOR|AND|OR|SELECT)\b", re.I),
    "java": re.compile(r"\b(if|for|while|case|catch)\b|&&|\|\||\?"),
    "generic": re.compile(r"\b(IF|ELSIF|ELSEIF|WHEN|WHILE|FOR|CASE|AND|OR)\b|&&|\|\|", re.I),
}


def _is_comment(language: str, line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if language in ("cobol", "cobol-copybook"):
        return len(line) > 6 and line[6] == "*" or s.startswith("*>")
    if language in ("plsql",):
        return s.startswith("--") or s.startswith("/*") or s.startswith("*")
    if language in ("java",):
        return s.startswith("//") or s.startswith("/*") or s.startswith("*")
    return s.startswith("//") or s.startswith("*")


class GenericAdapter:
    name = "generic"

    def supports(self, language: str) -> bool:
        return True

    def analyze(self, artifact: dict[str, Any]) -> dict[str, Any]:
        lang = artifact["language"]
        lines = artifact["text"].split("\n")
        loc = sum(1 for ln in lines if not _is_comment(lang, ln))
        rx = _DECISION.get(lang, _DECISION["generic"])
        cc = 1 + sum(len(rx.findall(ln)) for ln in lines if not _is_comment(lang, ln))
        return {"rigor": "heuristico", "loc": loc, "total_lines": len(lines), "cyclomatic": cc, "units": [], "edges": [],
                "data_items": [], "tables": [], "dead_units": []}


_PARA = re.compile(r"^ {7,10}([A-Z0-9][A-Z0-9\-]*)\.\s*$")
_SECTION = re.compile(r"^ {7,10}([A-Z0-9][A-Z0-9\-]*)\s+SECTION\.\s*$", re.I)
_PERFORM = re.compile(r"\bPERFORM\s+([A-Z0-9][A-Z0-9\-]*)(?:\s+THRU\s+([A-Z0-9][A-Z0-9\-]*))?", re.I)
_GOTO = re.compile(r"\bGO\s+TO\s+([A-Z0-9][A-Z0-9\-]*)", re.I)
_CALL = re.compile(r"\bCALL\s+['\"]?([A-Z0-9\-]+)['\"]?", re.I)
_COPY = re.compile(r"^\s{6,}COPY\s+([A-Z0-9\-]+)", re.I)
_PIC = re.compile(r"^\s{6,}(\d{2})\s+([A-Z0-9\-]+)\s+(?:PIC(?:TURE)?\s+(\S+?))(?:\s+(?:USAGE\s+(?:IS\s+)?)?(COMP-3|COMP|BINARY|PACKED-DECIMAL|COMP-5))?\s*(?:VALUE\s+.*)?\.\s*$", re.I)
_SQLTABLE = re.compile(r"\b(?:FROM|INTO|UPDATE|JOIN)\s+([A-Z0-9_\.]+)", re.I)
_RESERVED_PARA = {"DIVISION", "SECTION"}


def _pic_scale(pic: str) -> tuple[int, int]:
    """(dígitos enteros, decimales) de una PIC numérica, p.ej. S9(9)V99 -> (9,2)."""
    p = pic.upper().replace("S", "")
    int_part, _, dec_part = p.partition("V")

    def count(s: str) -> int:
        n = 0
        for m in re.finditer(r"9\((\d+)\)|9", s):
            n += int(m.group(1)) if m.group(1) else 1
        return n
    return count(int_part), count(dec_part)


class CobolAdapter:
    name = "cobol-determinista"

    def supports(self, language: str) -> bool:
        return language in ("cobol", "cobol-copybook")

    def analyze(self, artifact: dict[str, Any]) -> dict[str, Any]:
        base = GenericAdapter().analyze(artifact)
        lines = artifact["text"].split("\n")
        in_proc = False
        units: list[dict[str, Any]] = []
        edges: list[dict[str, str]] = []
        data_items: list[dict[str, Any]] = []
        tables: set[str] = set()
        copies: list[str] = []
        cur: dict[str, Any] | None = None
        for i, ln in enumerate(lines, start=1):
            if len(ln) > 6 and ln[6] == "*":
                continue
            body = ln[7:72] if len(ln) > 7 else ""
            if re.search(r"\bPROCEDURE\s+DIVISION\b", ln, re.I):
                in_proc = True
                continue
            m = _COPY.match(ln)
            if m:
                copies.append(m.group(1).upper().rstrip("."))
                edges.append({"from": artifact["path"], "to": m.group(1).upper().rstrip("."), "kind": "COPY"})
            if not in_proc:
                pm = _PIC.match(ln)
                if pm:
                    pic = pm.group(3)
                    usage = (pm.group(4) or "DISPLAY").upper()
                    ints, decs = _pic_scale(pic) if re.search(r"9", pic) else (0, 0)
                    data_items.append({"level": pm.group(1), "name": pm.group(2).upper(), "pic": pic, "usage": usage,
                                       "numeric": bool(re.search(r"9", pic)), "int_digits": ints, "scale": decs,
                                       "signed": pic.upper().startswith("S"), "line": i})
                continue
            if re.search(r"EXEC\s+SQL", ln, re.I) or tables and False:
                pass
            pmatch = _PARA.match(ln)
            if pmatch and pmatch.group(1).upper() not in _RESERVED_PARA and not _SECTION.match(ln):
                if cur:
                    cur["end_line"] = i - 1
                cur = {"name": pmatch.group(1).upper(), "kind": "paragraph", "file": artifact["path"], "start_line": i, "end_line": len(lines)}
                units.append(cur)
                continue
            if cur is not None:
                for pm2 in _PERFORM.finditer(body):
                    edges.append({"from": cur["name"], "to": pm2.group(1).upper(), "kind": "PERFORM"})
                    if pm2.group(2):
                        edges.append({"from": cur["name"], "to": pm2.group(2).upper(), "kind": "PERFORM"})
                for gm in _GOTO.finditer(body):
                    edges.append({"from": cur["name"], "to": gm.group(1).upper(), "kind": "GO TO"})
                for cm in _CALL.finditer(body):
                    edges.append({"from": cur["name"], "to": cm.group(1).upper(), "kind": "CALL"})
                if re.search(r"EXEC\s+SQL", body, re.I):
                    sql_block = " ".join(lines[i - 1: i + 6])
                    for tm in _SQLTABLE.finditer(sql_block):
                        t = tm.group(1).upper()
                        if t not in ("SQL", "END-EXEC", "END", "TABLE") and not t.startswith(":"):
                            tables.add(t)
                            edges.append({"from": cur["name"], "to": t, "kind": "SQL"})
                            break
        if cur:
            cur["end_line"] = len(lines)
        names = {u["name"] for u in units}
        called = {e["to"] for e in edges if e["kind"] in ("PERFORM", "GO TO")}
        entry = units[0]["name"] if units else None
        dead = [u["name"] for u in units if u["name"] not in called and u["name"] != entry]
        base.update({"rigor": "determinista", "units": units, "edges": [e for e in edges if e["kind"] != "SQL" or e["to"] in tables],
                     "data_items": data_items, "tables": sorted(tables), "dead_units": dead, "copybooks": copies,
                     "entry_candidates": [entry] if entry else [], "known_units": sorted(names)})
        return base


ADAPTERS: list[LanguageAdapter] = [CobolAdapter(), GenericAdapter()]


def adapter_for(language: str) -> LanguageAdapter:
    for a in ADAPTERS:
        if a.supports(language):
            return a
    return GenericAdapter()


def analyze_all(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    per_file: list[dict[str, Any]] = []
    for art in artifacts:
        ad = adapter_for(art["language"])
        res = ad.analyze(art)
        res.update({"file": art["path"], "language": art["language"], "adapter": ad.name})
        per_file.append(res)
    return {
        "files": per_file,
        "loc": sum(f["loc"] for f in per_file),
        "total_lines": sum(f["total_lines"] for f in per_file),
        "max_cyclomatic": max((f["cyclomatic"] for f in per_file), default=0),
        "dead_units": [u for f in per_file for u in f.get("dead_units", [])],
        "tables": sorted({t for f in per_file for t in f.get("tables", [])}),
        "edges": [e for f in per_file for e in f.get("edges", [])],
        "rigor": "determinista" if any(f["adapter"] != "generic" for f in per_file) else "heuristico",
    }
