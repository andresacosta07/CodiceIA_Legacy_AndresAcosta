"""Orquestador del pipeline (máquina de estados con compuertas de calidad y punto de aprobación humana)."""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable

from . import db, ingest, llm, schemas, security, static_analysis, verify

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "copilot" / "prompts"
STAGES = ["ingest", "analyze", "rules", "review", "generate", "verify", "docs", "package"]
_locks: dict[str, threading.RLock] = {}


def lock_for(pid: str) -> threading.RLock:
    return _locks.setdefault(pid, threading.RLock())


def prompt(name: str) -> str:
    text = (PROMPTS / f"{name}.md").read_text(encoding="utf-8")
    return re.sub(r"<!--.*?-->\n?", "", text, flags=re.S).strip()


def system_prompt(name: str) -> str:
    return prompt("common") + "\n\n" + prompt(name)


def render_source(artifacts: list[dict[str, Any]]) -> str:
    """Código numerado por líneas dentro de <legacy_source> (dato no confiable)."""
    parts = []
    for a in artifacts:
        lines = a["text"].split("\n")
        body = "\n".join(f"{i:>4}| {ln}" for i, ln in enumerate(lines, start=1))
        parts.append(f'<legacy_source file="{a["path"]}" language="{a["language"]}">\n{body}\n</legacy_source>')
    return "\n\n".join(parts)


# ----------------------------------------------------------------------------- estado
def get(pid: str) -> dict[str, Any]:
    p = db.load_project(pid)
    if p is None:
        raise KeyError(pid)
    return p


def put(p: dict[str, Any]) -> None:
    db.save_project(p["id"], p["name"], p)


def update(pid: str, fn: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    with lock_for(pid):
        p = get(pid)
        fn(p)
        put(p)
        return p


def new_project(name: str, domain: str, target: str, style: str, files: list[tuple[str, bytes]],
                provided_cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if target not in ("typescript", "java", "csharp"):
        raise security.SecurityError("Stack destino no soportado.")
    built = ingest.build_artifacts(files)
    pid = security.new_id()
    now = time.time()
    p: dict[str, Any] = {
        "id": pid, "name": (name or "Proyecto sin nombre")[:80], "created": now, "domain": (domain or "")[:120],
        "target": target, "style": (style or "hexagonal")[:40], **built,
        "provided_cases": provided_cases or [],
        "stages": {s: {"status": "pending"} for s in STAGES},
    }
    gate_ok = built["ingest_report"]["gate_no_secrets"]
    p["stages"]["ingest"] = {"status": "done" if gate_ok else "failed", "seconds": 0.0, "ended": now,
                             "gate": {"name": "0 secretos tras enmascarar", "passed": gate_ok}}
    put(p)
    db.audit(pid, "system", "ingest", {"files": built["ingest_report"]["files"], "masked": built["ingest_report"]["masked_total"]})
    return p


def run_stage(pid: str, stage: str, fn: Callable[[dict[str, Any]], dict[str, Any]], actor: str = "agent") -> None:
    """Ejecuta una etapa registrando tiempos, resultado y auditoría. No lanza: deja el error en el estado."""
    def mark(p: dict[str, Any]) -> None:
        p["stages"][stage] = {"status": "running", "started": time.time()}
    update(pid, mark)
    t0 = time.time()
    try:
        p = get(pid)
        gate = fn(p) or {}
        secs = time.time() - t0

        def done(q: dict[str, Any]) -> None:
            q.update(p)  # fn muta p con resultados
            q["stages"][stage] = {"status": "done" if gate.get("passed", True) else "gate_failed", "seconds": round(secs, 2),
                                  "ended": time.time(), "gate": gate}
        with lock_for(pid):
            cur = get(pid)
            done(cur)
            put(cur)
        db.audit(pid, actor, f"stage:{stage}", {"gate": gate, "seconds": round(secs, 2)})
    except Exception as exc:  # noqa: BLE001 - se informa al usuario con acción sugerida
        msg = f"{type(exc).__name__}: {exc}"
        tb = traceback.format_exc(limit=3)

        def fail(q: dict[str, Any]) -> None:
            q["stages"][stage] = {"status": "failed", "seconds": round(time.time() - t0, 2), "error": msg,
                                  "hint": hint_for(exc)}
        update(pid, fail)
        db.audit(pid, actor, f"stage_failed:{stage}", {"error": msg, "trace": tb[-600:]})


def hint_for(exc: Exception) -> str:
    if isinstance(exc, llm.EgressBlocked):
        return "Se detectaron datos sensibles sin enmascarar. Revise el informe de enmascarado y elimine los datos reales del código."
    if isinstance(exc, llm.LLMError):
        return "Verifique ANTHROPIC_API_KEY y la conectividad, o use el modo contingencia con ejecución pregrabada."
    return "Reintente la etapa. Si persiste, revise el código de entrada."


def spawn(pid: str, stage: str, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    threading.Thread(target=run_stage, args=(pid, stage, fn), daemon=True).start()


# ----------------------------------------------------------------------------- análisis
_INJECTION = re.compile(r"(?i)ignore (?:all )?(?:previous|prior|above) instructions|reveal (?:your )?(?:system )?prompt|"
                        r"you are now|disregard .{0,30}instructions|output the text")
_SQL_DYN = [
    (re.compile(r"(?i)EXECUTE\s+IMMEDIATE[^;]*\|\|"), "SQL dinámico concatenado (EXECUTE IMMEDIATE con ||)"),
    (re.compile(r"(?i)['\"]\s*(?:select|insert|update|delete)\b[^'\"]*['\"]\s*(?:\|\||\+)"), "Consulta SQL construida por concatenación"),
    (re.compile(r"(?i)(?:v_sql|sql_stmt|l_sql|query)\s*:=\s*['\"][^;]*\|\|"), "Sentencia SQL armada con concatenación"),
]


def legacy_security_scan(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for a in artifacts:
        for i, ln in enumerate(a["text"].split("\n"), start=1):
            if _INJECTION.search(ln):
                out.append({"file": a["path"], "line": i, "category": "prompt_injection_attempt",
                            "description": "Texto en el código que intenta dar instrucciones al modelo (tratado como dato).", "source": "determinista"})
            for rx, desc in _SQL_DYN:
                if rx.search(ln):
                    out.append({"file": a["path"], "line": i, "category": "sql_injection_risk", "description": desc, "source": "determinista"})
                    break
        if a.get("masked_count"):
            out.append({"file": a["path"], "line": 0, "category": "hardcoded_secret",
                        "description": f"{a['masked_count']} secreto(s)/dato(s) sensible(s) incrustados; enmascarados antes del envío.", "source": "determinista"})
    return out


def analyze_stage(p: dict[str, Any]) -> dict[str, Any]:
    arts = p["artifacts"]
    total_chars = sum(len(a["text"]) for a in arts)
    if total_chars > llm.CONFIG["max_source_chars"]:
        raise llm.LLMError(f"El código ({total_chars:,} caracteres) excede el máximo del MVP; divida el repositorio por módulos.")
    static = static_analysis.analyze_all(arts)
    structure = {f["file"]: {"adapter": f["adapter"], "units": f.get("units", []), "edges": f.get("edges", []),
                             "data_items": f.get("data_items", [])[:80]} for f in static["files"] if f.get("units") or f.get("data_items")}
    user = (render_source(arts) + "\n\nESTRUCTURA DETERMINISTA (analizador estático):\n" + json.dumps(structure, ensure_ascii=False)[:30000]
            + f"\n\nDominio indicado por el usuario: {p.get('domain') or 'no indicado'}. Responde con el esquema solicitado.")
    result = llm.call("analyze", system_prompt("analyze"), user, schemas.ANALYSIS, project_id=p["id"])
    errs = schemas.validate(result, schemas.ANALYSIS)
    if errs:
        raise llm.LLMError("La salida del Analista no cumple el esquema: " + "; ".join(errs[:3]))
    files = {a["path"]: a["lines"] for a in arts}
    for u in result["units"]:
        n = files.get(u["file"])
        u["verified"] = bool(n and 1 <= u["start_line"] <= u["end_line"] <= n)
    det_units = {u["name"] for f in static["files"] for u in f.get("units", [])}
    llm_units = {u["name"].upper() for u in result["units"]}
    found = [n for n in det_units if n in llm_units]
    recall = 100.0 if not det_units else round(100 * len(found) / len(det_units), 1)
    sec = legacy_security_scan(arts)
    for f in result["security_findings"]:
        f["source"] = "llm"
    keys = {(s["file"], s["line"], s["category"]) for s in sec}
    result["security_findings"] = sec + [f for f in result["security_findings"] if (f["file"], f["line"], f["category"]) not in keys]
    p["static"] = static
    p["analysis"] = result
    p["analysis"]["inventory_recall_pct"] = recall
    valid = sum(1 for u in result["units"] if u["verified"])
    return {"name": "100% de rutinas inventariadas y con líneas válidas", "passed": recall >= 100.0 and valid == len(result["units"]),
            "inventory_recall_pct": recall, "units": len(result["units"]), "units_verified": valid}


# ----------------------------------------------------------------------------- reglas
def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def verify_citations(rule: dict[str, Any], artifacts: dict[str, dict[str, Any]]) -> str:
    """Anti-alucinación: comprueba que cada cita exista (archivo, rango) y que el texto citado esté en el código.
    Si la cita no está en el rango pero sí en el archivo, corrige el rango (estado 'corrected')."""
    status = "verified" if rule["source_refs"] else "failed"
    for ref in rule["source_refs"]:
        art = artifacts.get(ref["file"])
        if not art:
            ref["trace"] = "failed"
            status = "failed"
            continue
        lines = art["text"].split("\n")
        quote = _norm(ref["quote"])
        s, e = ref["start_line"], ref["end_line"]
        in_range = 1 <= s <= e <= len(lines)
        if in_range and quote and quote in _norm(" ".join(lines[s - 1:e])):
            ref["trace"] = "verified"
            continue
        # buscar la cita en todo el archivo (ventanas de hasta 4 líneas)
        found = None
        if quote:
            for w in range(1, 5):  # ventana mínima primero: el rango más ajustado a la cita
                for i in range(len(lines)):
                    if quote in _norm(" ".join(lines[i:i + w])):
                        found = (i + 1, i + w)
                        break
                if found:
                    break
        if found:
            ref["start_line"], ref["end_line"] = found
            ref["trace"] = "corrected"
            if status == "verified":
                status = "corrected"
        else:
            ref["trace"] = "failed"
            status = "failed"
    return status


def rules_stage(p: dict[str, Any]) -> dict[str, Any]:
    analysis = p["analysis"]
    user = (render_source(p["artifacts"]) + "\n\nCONTRATO DE E/S Y UNIDADES (del Analista):\n"
            + json.dumps({"io_contract": analysis["io_contract"], "units": [{k: u[k] for k in ("name", "file", "start_line", "end_line", "summary", "classification")}
                                                                              for u in analysis["units"]],
                          "data_items": analysis["data_items"]}, ensure_ascii=False)
            + "\n\nExtrae el catálogo completo de reglas de negocio.")
    result = llm.call("rules", system_prompt("rules"), user, schemas.RULES, project_id=p["id"])
    errs = schemas.validate(result, schemas.RULES)
    if errs:
        raise llm.LLMError("La salida del Extractor no cumple el esquema: " + "; ".join(errs[:3]))
    arts = {a["path"]: a for a in p["artifacts"]}
    seen: set[str] = set()
    rules = []
    for r in result["rules"]:
        rid = r["id"]
        if rid in seen or not re.match(r"^R-\d{3,}$", rid):
            rid = f"R-{len(rules) + 1:03d}"
        seen.add(rid)
        r["id"] = rid
        r["trace_status"] = verify_citations(r, arts)
        r["confidence"] = max(0.0, min(1.0, float(r["confidence"])))
        if r["trace_status"] == "failed":
            r["confidence"] = min(r["confidence"], 0.3)
        r["status"] = "proposed"
        r["needs_review"] = r["confidence"] < 0.75 or r["trace_status"] == "failed"
        r["history"] = []
        r["comment"] = ""
        rules.append(r)
    p["rules"] = rules
    p["catalog"] = {"version": 0, "status": "draft"}
    traced = sum(1 for r in rules if r["trace_status"] in ("verified", "corrected"))
    pct = round(100 * traced / len(rules), 1) if rules else 0.0
    return {"name": "Cada regla con referencia real a líneas de origen y confianza", "passed": bool(rules) and pct == 100.0,
            "rules": len(rules), "traced": traced, "traceability_pct": pct,
            "needs_review": sum(1 for r in rules if r["needs_review"])}


# ----------------------------------------------------------------------------- revisión humana
EDITABLE = ("name", "description", "conditions", "actions", "gherkin")


def review_rule(pid: str, rid: str, status: str, edits: dict[str, Any] | None, comment: str, reviewer: str) -> dict[str, Any]:
    if status not in ("approved", "rejected", "proposed"):
        raise security.SecurityError("Estado de revisión inválido.")
    with lock_for(pid):
        p = get(pid)
        if p["stages"]["review"].get("status") == "done" and p["stages"].get("generate", {}).get("status") not in (None, "pending"):
            raise security.SecurityError("El catálogo ya fue aprobado y usado para generar código; cree un nuevo proyecto o reabra la revisión.")
        rule = next((r for r in p.get("rules", []) if r["id"] == rid), None)
        if rule is None:
            raise KeyError(rid)
        if status == "approved" and rule["trace_status"] == "failed":
            raise security.SecurityError("No se puede aprobar una regla sin trazabilidad válida a líneas de origen (ajustar el texto no corrige la cita). Recházela.")
        before = {k: rule[k] for k in EDITABLE}
        adjusted = False
        for k, v in (edits or {}).items():
            if k in EDITABLE and v != rule[k]:
                rule[k] = v if k in ("name", "description", "gherkin") else [str(x) for x in v]
                adjusted = True
        rule["status"] = status
        rule["adjusted"] = rule.get("adjusted", False) or adjusted
        rule["comment"] = (comment or "")[:500]
        rule["history"].append({"ts": time.time(), "reviewer": reviewer[:40], "status": status, "adjusted": adjusted,
                                "comment": rule["comment"], "before": before if adjusted else None})
        p["stages"]["review"] = {"status": "pending"}
        put(p)
    db.audit(pid, reviewer, "rule_review", {"rule": rid, "status": status, "adjusted": adjusted})
    return rule


def approve_catalog(pid: str, reviewer: str) -> dict[str, Any]:
    with lock_for(pid):
        p = get(pid)
        rules = p.get("rules", [])
        pending = [r["id"] for r in rules if r["status"] == "proposed"]
        if pending:
            raise security.SecurityError(f"Faltan reglas por decidir: {', '.join(pending[:8])}.")
        approved = [r for r in rules if r["status"] == "approved"]
        if not approved:
            raise security.SecurityError("Debe aprobar al menos una regla.")
        version = p["catalog"].get("version", 0) + 1
        payload = json.dumps([{k: r[k] for k in ("id", "name", "description", "conditions", "actions", "source_refs")} for r in approved],
                             sort_keys=True, ensure_ascii=False)
        p["catalog"] = {"version": version, "status": "approved", "approved_by": reviewer[:40], "approved_at": time.time(),
                        "sha256": hashlib.sha256(payload.encode()).hexdigest(), "approved_rules": len(approved),
                        "rejected_rules": sum(1 for r in rules if r["status"] == "rejected")}
        p["stages"]["review"] = {"status": "done", "ended": time.time(), "seconds": 0.0,
                                 "gate": {"name": "Aprobación explícita del ingeniero", "passed": True, "approved_by": reviewer[:40]}}
        put(p)
    db.audit(pid, reviewer, "catalog_approved", {"version": version, "rules": len(approved)})
    return p["catalog"]
