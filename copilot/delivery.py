"""Etapas de diseño/generación, verificación (equivalencia + calidad), documentación y empaquetado."""
from __future__ import annotations

import io
import json
import posixpath
import re
import time
import zipfile
from pathlib import Path
from typing import Any

from . import db, llm, schemas, verify
from .pipeline import (get, lock_for, put, render_source, run_stage, spawn, system_prompt, update)

ROOT = Path(__file__).resolve().parent.parent
MAX_AUTOFIX = 2
PACKAGES = ROOT / "data" / "packages"


def _approved(p: dict[str, Any]) -> list[dict[str, Any]]:
    return [r for r in p["rules"] if r["status"] == "approved"]


def _rules_for_prompt(p: dict[str, Any]) -> list[dict[str, Any]]:
    keys = ("id", "name", "description", "category", "conditions", "actions", "data_items", "decision_table")
    return [{k: r[k] for k in keys} for r in _approved(p)]


def _safe_files(files: list[dict[str, str]], target: str) -> list[dict[str, str]]:
    out = []
    for f in files:
        path = posixpath.normpath(f["path"].replace("\\", "/"))
        if path.startswith(("/", "../")) or path == ".." or ".." in path.split("/") or re.match(r"^[A-Za-z]:", path):
            continue
        if path.endswith("src/domain/shared/decimal.ts") or path.startswith("__"):
            continue  # lo provee la plataforma
        out.append({"path": path, "content": f["content"]})
    return out


# ----------------------------------------------------------------------------- generación
def generate_stage(p: dict[str, Any]) -> dict[str, Any]:
    target = p["target"]
    user = ("CATÁLOGO DE REGLAS APROBADO (fuente de verdad):\n" + json.dumps(_rules_for_prompt(p), ensure_ascii=False)
            + "\n\nCONTRATO DE E/S:\n" + json.dumps(p["analysis"]["io_contract"], ensure_ascii=False)
            + "\n\nELEMENTOS DE DATOS:\n" + json.dumps(p["analysis"]["data_items"], ensure_ascii=False)
            + f"\n\nDominio: {p.get('domain') or 'no indicado'}. Estilo de arquitectura: {p.get('style')}. Genera el proyecto completo.")
    res = llm.call("codegen", system_prompt(f"codegen_{target}"), user, schemas.CODEGEN, project_id=p["id"], max_tokens=64000)
    errs = schemas.validate(res, schemas.CODEGEN)
    if errs:
        raise llm.LLMError("La salida del Desarrollador no cumple el esquema: " + "; ".join(errs[:3]))
    files = _safe_files(res["files"], target)
    if not files:
        raise llm.LLMError("El generador no devolvió archivos utilizables.")
    p["generation"] = {"target": target, "design": res["design"], "files": files, "openapi_yaml": res["openapi_yaml"],
                       "assumptions": res["assumptions"], "autofix": []}
    scan = verify.scan_project(files, target)
    p["generation"]["scan"] = scan
    return {"name": "Código generado con capas domain/application/infrastructure", "passed": len(files) > 0 and not scan["by_category"].get("architecture"),
            "files": len(files), "blocking_findings": scan["blocking"]}


# ----------------------------------------------------------------------------- verificación
_DEAD_RULE = re.compile(r"no\s+(?:se\s+)?(?:utiliza|usa|invoca|referencia|llama)|sin\s+uso|obsolet|c[oó]digo\s+muerto|nunca\s+se\s+(?:invoca|usa|ejecuta)", re.I)


def is_dead_rule(rule: dict[str, Any]) -> bool:
    """Regla que el propio análisis describe como código sin uso/obsoleto: se documenta, pero no se migra ni se prueba."""
    return bool(_DEAD_RULE.search(f"{rule.get('name', '')} {rule.get('description', '')}"))


def _append_cases(res: dict[str, Any], inputs: list[str], cases: list[dict[str, Any]], names: set[str]) -> None:
    for c in res["cases"]:
        inp = {kv["name"]: str(kv["value"]) for kv in c["input"]}
        if set(inputs) - set(inp):
            continue  # caso incompleto
        name = re.sub(r"[^a-z0-9_]", "_", c["name"].lower())[:60] or f"caso_{len(cases) + 1}"
        while name in names:
            name += "_x"
        names.add(name)
        cases.append({"name": name, "category": c["category"], "rule_ids": c["rule_ids"], "input": {k: inp[k] for k in inputs}})


def _cases_from_llm(p: dict[str, Any]) -> list[dict[str, Any]]:
    contract = json.dumps(p["analysis"]["io_contract"], ensure_ascii=False)
    user = "CATÁLOGO DE REGLAS APROBADO:\n" + json.dumps(_rules_for_prompt(p), ensure_ascii=False) + "\n\nCONTRATO DE E/S:\n" + contract
    res = llm.call("qa_cases", system_prompt("qa_cases"), user, schemas.QA_CASES, project_id=p["id"])
    errs = schemas.validate(res, schemas.QA_CASES)
    if errs:
        raise llm.LLMError("La salida de QA no cumple el esquema: " + "; ".join(errs[:3]))
    inputs = [f["name"] for f in p["analysis"]["io_contract"]["inputs"]]
    cases: list[dict[str, Any]] = []
    names: set[str] = set()
    _append_cases(res, inputs, cases, names)
    if not cases:
        raise llm.LLMError("QA no generó casos de prueba válidos.")
    # Reglas aprobadas que ningún caso cubre (salvo código muerto): una segunda llamada corta, solo para ellas.
    covered = {rid for c in cases for rid in c["rule_ids"]}
    missing = [r for r in _rules_for_prompt(p) if r["id"] not in covered and not is_dead_rule(r)]
    if missing:
        more = ("REGLAS SIN CASOS DE PRUEBA (genera 2 o 3 casos por CADA una; cada caso lleva su ID en rule_ids):\n"
                + json.dumps(missing, ensure_ascii=False) + "\n\nCONTRATO DE E/S:\n" + contract)
        try:
            extra = llm.call("qa_cases", system_prompt("qa_cases"), more, schemas.QA_CASES, project_id=p["id"])
            if not schemas.validate(extra, schemas.QA_CASES):
                _append_cases(extra, inputs, cases, names)
        except llm.LLMError:
            pass  # complemento opcional: si falla, la matriz de trazabilidad mostrará la regla sin pruebas
    return cases


def _oracle(p: dict[str, Any], cases: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    base = (render_source(p["artifacts"]) + "\n\nCONTRATO DE E/S:\n" + json.dumps(p["analysis"]["io_contract"], ensure_ascii=False))
    feedback = ""
    for _ in range(2):
        res = llm.call("oracle", system_prompt("oracle"), base + feedback, schemas.ORACLE, project_id=p["id"])
        run = verify.run_oracle(res["python_code"], cases)
        if run["ok"]:
            return res["python_code"], run
        feedback = f"\n\nTu intento anterior falló: {run['error']}\nCorrige y devuelve el código completo."
    return res["python_code"], run


def _revise_oracle(p: dict[str, Any], prev_code: str, cases: list[dict[str, Any]], failing: list[dict[str, Any]],
                   note: str) -> tuple[str, dict[str, Any]] | None:
    """Arbitraje: el código nuevo y el oráculo (segundo traductor) discrepan y el autocorrector concluyó que el CÓDIGO sigue al legacy.
    Se pide al oráculo una segunda lectura SOLO del legacy (sin ver el código nuevo). Devuelve (código, ejecución) o None."""
    by_name = {c["name"]: c for c in cases}
    detail = [{"caso": f["name"], "entrada": by_name.get(f["name"], {}).get("input"),
               "esperaste": {d["field"]: d["expected"] for d in f.get("diffs", [])},
               "otra_implementacion_obtuvo": {d["field"]: d["actual"] for d in f.get("diffs", [])}} for f in failing[:6]]
    base = render_source(p["artifacts"]) + "\n\nCONTRATO DE E/S:\n" + json.dumps(p["analysis"]["io_contract"], ensure_ascii=False)
    feedback = ("\n\nTU ORÁCULO ANTERIOR:\n" + prev_code + "\n\nUna implementación independiente DISCREPA de tu oráculo en estos casos:\n"
                + json.dumps(detail, ensure_ascii=False)[:6000] + "\n\nOBSERVACIÓN DEL REVISOR DE CÓDIGO: " + note[:600]
                + "\n\nVuelve a derivar esos casos SOLO del código legacy de arriba (identifica la línea que decide el resultado). "
                  "Si tu oráculo estaba equivocado, corrígelo; si estaba bien, devuélvelo igual. No te adaptes a la otra implementación "
                  "sin evidencia en el legacy. Devuelve el código Python completo.")
    for _ in range(2):  # como en _oracle: un segundo intento si el código devuelto no pasa la validación o no se ejecuta
        try:
            res = llm.call("oracle", system_prompt("oracle"), base + feedback, schemas.ORACLE, project_id=p["id"])
        except llm.LLMError:
            return None
        run = verify.run_oracle(res["python_code"], cases)
        if run["ok"]:
            return res["python_code"], run
        feedback += f"\n\nTu intento anterior falló: {run['error']}\nCorrige y devuelve el código completo."
    return None


def verify_stage(p: dict[str, Any]) -> dict[str, Any]:
    gen = p["generation"]
    target = gen["target"]
    contract = p["analysis"]["io_contract"]
    scan = verify.scan_project(gen["files"], target)
    ver: dict[str, Any] = {"target": target, "executed": target == "typescript", "started": time.time()}
    if target != "typescript":
        gen["scan"] = scan
        ver.update(equivalence=None, unit_tests=None, evidence="NO-EJECUTADO",
                   note=f"El destino {target} se genera y se valida estáticamente (arquitectura, precisión numérica, seguridad), "
                        "pero no se compila ni se ejecuta en este entorno (requiere JDK/.NET). La equivalencia funcional se demuestra con el destino TypeScript.")
        p["verification"] = ver
        return {"name": "Guardrails estáticos", "passed": scan["blocking"] == 0, "equivalence": "no ejecutado", "blocking": scan["blocking"]}

    cases = _cases_from_llm(p)
    oracle_code, oracle_run = _oracle(p, cases)
    ver["oracle_code"] = oracle_code
    ver["oracle_discarded"] = [r["name"] for r in oracle_run.get("results", []) if not r.get("ok")]  # casos que el oráculo no pudo calcular
    expected: dict[str, dict[str, str]] = {}
    evidence: dict[str, str] = {}
    meta = {c["name"]: c for c in cases}
    if oracle_run["ok"]:
        for r in oracle_run["results"]:
            if r["ok"]:
                expected[r["name"]] = r["output"]
                evidence[r["name"]] = "E3"
    else:
        ver["oracle_error"] = oracle_run["error"]
    for i, pc in enumerate(p.get("provided_cases") or []):  # E2: casos aportados con salida esperada
        name = f"aportado_{pc.get('name', i + 1)}"
        name = re.sub(r"[^a-zA-Z0-9_]", "_", name)[:60]
        meta[name] = {"name": name, "category": pc.get("category", "aportado"), "rule_ids": [], "input": pc["input"]}
        expected[name] = {k: str(v) for k, v in pc["expected"].items()}
        evidence[name] = "E2"
    all_cases = [{**meta[n], "expected": expected[n]} for n in expected if n in meta]
    if not all_cases:
        ver.update(equivalence=None, evidence="SIN-ORACULO", note="No fue posible construir un oráculo ni casos aportados.")
        p["verification"] = ver
        return {"name": "Equivalencia funcional 100 %", "passed": False, "reason": "sin oráculo"}

    equiv, log = None, []
    arbitration: list[dict[str, Any]] = []
    for attempt in range(MAX_AUTOFIX + 1):
        scan = verify.scan_project(gen["files"], target)
        run = verify.run_ts_cases(gen["files"], all_cases)
        problems: list[str] = []
        if run["ok"]:
            actual = {r["name"]: r for r in run["results"]}
            equiv = verify.compare({c["name"]: c["expected"] for c in all_cases}, actual, contract, evidence)
            if equiv["failed"]:
                shown = [c for c in equiv["cases"] if not c["equivalent"]][:6]
                problems.append("DIFERENCIAS DE EQUIVALENCIA (esperado vs obtenido):\n" + json.dumps(shown, ensure_ascii=False)[:5000])
        else:
            equiv = None
            problems.append("ERROR DE EJECUCIÓN:\n" + run["error"])
        blocking = [f for f in scan["findings"] if f["severity"] in ("critical", "high") or f["category"] == "complexity"]
        if blocking:
            problems.append("HALLAZGOS DE GUARDRAILS:\n" + json.dumps(blocking[:10], ensure_ascii=False))
        if not problems or attempt == MAX_AUTOFIX:
            break
        log.append({"iteration": attempt + 1, "problems": [x[:200] for x in problems]})
        user = ("ARCHIVOS ACTUALES:\n" + json.dumps(gen["files"], ensure_ascii=False) + "\n\nERRORES:\n" + "\n\n".join(problems)
                + "\n\nREGLAS APROBADAS:\n" + json.dumps(_rules_for_prompt(p), ensure_ascii=False)
                + "\n\nCÓDIGO LEGACY ORIGINAL (dato no confiable):\n" + render_source(p["artifacts"]))
        fix = llm.call("autofix", system_prompt("autofix"), user, schemas.AUTOFIX, project_id=p["id"], max_tokens=64000)
        changed = {f["path"]: f for f in _safe_files(fix["files"], target)}
        before = {f["path"]: f["content"] for f in gen["files"]}
        prod_changed = any(path.startswith("src/") and before.get(path) != f["content"] for path, f in changed.items())
        gen["files"] = [changed.pop(f["path"], f) for f in gen["files"]] + list(changed.values())
        log[-1]["explanation"] = fix["explanation"][:300]
        # Arbitraje: si el autocorrector NO tocó el código de producción y solo discrepan casos del oráculo (E3), se pide al oráculo
        # una segunda lectura del legacy. Una sola vez; los casos aportados por el cliente (E2) nunca se arbitran.
        failing = [c for c in (equiv or {}).get("cases", []) if not c["equivalent"]]
        if failing and not prod_changed and not arbitration and all(evidence.get(c["name"]) == "E3" for c in failing):
            rev = _revise_oracle(p, oracle_code, cases, failing, fix["explanation"])
            if rev:
                oracle_code, new_run = rev
                prev = {c["name"]: expected[c["name"]] for c in failing}
                for r in new_run["results"]:
                    if r["ok"] and evidence.get(r["name"]) == "E3":
                        expected[r["name"]] = r["output"]
                all_cases[:] = [{**meta[n], "expected": expected[n]} for n in expected if n in meta]
                ver["oracle_code"] = oracle_code
                arbitration.append({"cases": [c["name"] for c in failing],
                                    "changed": [n for n in prev if expected[n] != prev[n]], "note": fix["explanation"][:300]})
    gen["autofix"] = log
    ver["oracle_arbitration"] = arbitration
    gen["scan"] = scan
    ver["cases"] = all_cases
    ver["equivalence"] = equiv
    ver["execution_error"] = None if equiv else (run.get("error") if not run["ok"] else None)

    # pruebas unitarias deterministas (aserciones explícitas) + cobertura
    ut_src = verify.gen_unit_tests(all_cases)
    gen["unit_test_source"] = ut_src
    ut = verify.run_ts_tests(gen["files"], ut_src) if equiv and equiv["failed"] == 0 else {"ok": False, "error": "omitidas: equivalencia incompleta"}
    ver["unit_tests"] = ut
    levels = sorted({e for e in evidence.values()})
    ver["evidence"] = "+".join(levels)
    ver["evidence_note"] = {"E1": "Legacy ejecutado", "E2": "Casos esperados aportados por el cliente",
                            "E3": "Segundo traductor derivado del código legacy (no se ejecutó el legacy; comparte el análisis con el generador)"}
    approved_ids = {r["id"] for r in _approved(p) if not is_dead_rule(r)}   # el código muerto documentado no se prueba
    tested = {rid for c in all_cases for rid in c.get("rule_ids", [])}
    ver["rules_tested"] = sorted(tested & approved_ids)
    ver["rules_untested"] = sorted(approved_ids - tested)
    ver["finished"] = time.time()
    p["verification"] = ver
    passed = bool(equiv) and equiv["failed"] == 0 and scan["blocking"] == 0 and bool(ut.get("ok"))
    return {"name": "Equivalencia 100 %, 0 hallazgos críticos, guardrails", "passed": passed,
            "equivalence_pct": equiv["pct"] if equiv else 0, "cases": equiv["total"] if equiv else 0,
            "blocking_findings": scan["blocking"], "autofix_iterations": len(log),
            "line_coverage": ut.get("line_coverage"), "branch_coverage": ut.get("branch_coverage")}


# ----------------------------------------------------------------------------- documentación
def trace_matrix(p: dict[str, Any]) -> dict[str, Any]:
    gen = p.get("generation", {})
    tags = (gen.get("scan") or {}).get("rule_tags", {})
    cases = (p.get("verification") or {}).get("cases", [])
    rows, orphans = [], []
    for r in _approved(p):
        code_files = sorted(set(tags.get(r["id"], [])))
        tests = [c["name"] for c in cases if r["id"] in c.get("rule_ids", [])]
        refs = [f"{x['file']}:{x['start_line']}-{x['end_line']}" for x in r["source_refs"]]
        dead = is_dead_rule(r) and not code_files   # código muerto documentado: no se migra, por lo que no cuenta como huérfana
        row = {"rule": r["id"], "name": r["name"], "legacy_lines": refs, "code": code_files, "tests": tests,
               "doc": f"docs/02_catalogo_reglas.md#{r['id'].lower()}", "dead": dead, "complete": bool(refs and code_files and tests)}
        rows.append(row)
        if not row["complete"] and not dead:
            orphans.append(r["id"])
    live = [r for r in rows if not r["dead"]]
    return {"rows": rows, "orphans": orphans, "dead_code_rules": [r["rule"] for r in rows if r["dead"]],
            "complete_pct": round(100 * sum(r["complete"] for r in live) / len(live), 1) if live else 0.0}


def docs_stage(p: dict[str, Any]) -> dict[str, Any]:
    user = ("ANÁLISIS DEL LEGACY:\n" + json.dumps({k: p["analysis"][k] for k in ("domain_summary", "units", "entry_points", "risks", "io_contract")},
                                                  ensure_ascii=False)[:25000]
            + "\n\nREGLAS APROBADAS (IDs y nombres):\n" + json.dumps([{"id": r["id"], "name": r["name"]} for r in _approved(p)], ensure_ascii=False)
            + "\n\nDISEÑO DEL SISTEMA NUEVO:\n" + json.dumps(p["generation"]["design"], ensure_ascii=False)[:15000])
    res = llm.call("docs", system_prompt("docs"), user, schemas.DOCS, project_id=p["id"])
    errs = schemas.validate(res, schemas.DOCS)
    if errs:
        raise llm.LLMError("La salida del Documentador no cumple el esquema: " + "; ".join(errs[:3]))
    p["docs"] = res
    p["trace"] = trace_matrix(p)
    mer_ok = res["architecture_mermaid"].lstrip().startswith(("flowchart", "graph")) and res["sequence_mermaid"].lstrip().startswith("sequenceDiagram")
    return {"name": "Matriz de trazabilidad completa y diagramas válidos", "passed": p["trace"]["complete_pct"] == 100.0 and mer_ok,
            "trace_complete_pct": p["trace"]["complete_pct"], "orphans": p["trace"]["orphans"], "mermaid_ok": mer_ok}


# ----------------------------------------------------------------------------- métricas y paquete
def metrics(p: dict[str, Any]) -> dict[str, Any]:
    est = json.loads((ROOT / "config" / "estimates.json").read_text(encoding="utf-8"))
    loc = p.get("static", {}).get("loc") or 0
    machine = sum(s.get("seconds", 0) for k, s in p["stages"].items() if k not in ("review", "ingest"))
    manual_h = loc / est["analysis_loc_per_hour"] + loc / est["migration_and_tests_loc_per_hour"]
    manual_h *= 1 + est["docs_fraction_of_total"]
    llm_s = db.llm_summary(p["id"])
    for s in llm_s["stages"]:  # lo que costaría con la API de Claude (referencia): la suscripción y el modo pregrabado no cobran por uso
        s["reference_usd"] = round(llm._cost(str(s["model"]).split(" (")[0], s["tokens_in"], s["tokens_out"]), 2)
    ver = p.get("verification") or {}
    equiv = ver.get("equivalence") or {}
    ut = ver.get("unit_tests") or {}
    sec = (p.get("generation", {}).get("scan") or {})
    return {
        "loc": loc, "rules_total": len(p.get("rules", [])), "rules_approved": len(_approved(p)) if p.get("rules") else 0,
        "traceability_pct": 100.0 if p.get("rules") and all(r["trace_status"] != "failed" for r in _approved(p)) else 0.0,
        "equivalence_pct": equiv.get("pct"), "equivalence_cases": equiv.get("total"), "numeric_differences": equiv.get("numeric_differences"),
        "line_coverage": ut.get("line_coverage"), "branch_coverage": ut.get("branch_coverage"),
        "blocking_findings": sec.get("blocking"), "max_cc": sec.get("max_cc"),
        "pipeline_seconds": round(machine, 1), "tokens_in": llm_s["tokens_in"], "tokens_out": llm_s["tokens_out"],
        "cost_usd": llm_s["cost_usd"], "llm_by_stage": llm_s["stages"],
        "reference_cost_usd": round(sum(s["reference_usd"] for s in llm_s["stages"]), 2),
        "manual_hours_estimate": round(manual_h, 1), "manual_days_estimate": round(manual_h / est["hours_per_day"], 1),
        "manual_cost_usd": round(manual_h * est["hourly_rate_usd"]), "estimates": est,
        "speedup": round(manual_h * 3600 / machine) if machine else None,
        "security_findings_legacy": len(p.get("analysis", {}).get("security_findings", [])),
        "secrets_masked": p["ingest_report"]["masked_total"], "secrets_residual": p["ingest_report"]["residual_secrets"],
        "audit_chain_ok": db.verify_audit_chain(p["id"]),
    }


def _md_catalog(p: dict[str, Any]) -> str:
    out = ["# Catálogo de reglas de negocio aprobado", "",
           f"Versión {p['catalog']['version']} · aprobado por {p['catalog'].get('approved_by', '-')} · SHA-256 `{p['catalog'].get('sha256', '')[:16]}…`", ""]
    for r in _approved(p):
        out += [f"## {r['id']} — {r['name']} {{#{r['id'].lower()}}}", "", r["description"], "",
                f"- **Categoría:** {r['category']} · **Confianza:** {r['confidence']:.2f}" + (" · *ajustada por revisión humana*" if r.get("adjusted") else ""),
                "- **Origen legacy:** " + ", ".join(f"`{x['file']}:{x['start_line']}-{x['end_line']}`" for x in r["source_refs"]), ""]
        if r["conditions"]:
            out += ["**Condiciones**", *[f"- {c}" for c in r["conditions"]], ""]
        if r["actions"]:
            out += ["**Acciones**", *[f"- {a}" for a in r["actions"]], ""]
        dt = r["decision_table"]
        if dt["columns"]:
            out += ["| " + " | ".join(dt["columns"]) + " |", "|" + "---|" * len(dt["columns"]),
                    *["| " + " | ".join(row) + " |" for row in dt["rows"]], ""]
        if r["assumptions"]:
            out += ["**Supuestos**", *[f"- {a}" for a in r["assumptions"]], ""]
        out += ["```gherkin", r["gherkin"], "```", ""]
    rej = [r for r in p["rules"] if r["status"] == "rejected"]
    if rej:
        out += ["## Reglas rechazadas en la revisión", *[f"- {r['id']} — {r['name']}: {r.get('comment', '')}" for r in rej], ""]
    return "\n".join(out)


def _md_equivalence(p: dict[str, Any]) -> str:
    v = p.get("verification") or {}
    e = v.get("equivalence")
    if not e:
        return f"# Reporte de equivalencia\n\n{v.get('note', 'No ejecutado.')}\n"
    out = ["# Reporte de equivalencia funcional (legacy vs. moderno)", "",
           f"- **Resultado:** {e['passed']}/{e['total']} casos equivalentes ({e['pct']} %)",
           f"- **Diferencias numéricas:** {e['numeric_differences']}", f"- **Nivel de evidencia:** {v['evidence']}",
           *[f"  - {k}: {t}" for k, t in v.get("evidence_note", {}).items() if k in v["evidence"]], "",
           "| Caso | Evidencia | Resultado |", "|---|---|---|"]
    for c in e["cases"]:
        out.append(f"| {c['name']} | {c['evidence']} | {'✅ equivalente' if c['equivalent'] else '❌ ' + json.dumps(c['diffs'], ensure_ascii=False)[:120]} |")
    return "\n".join(out) + "\n"


def _md_quality(p: dict[str, Any]) -> str:
    g = p["generation"]
    s = g.get("scan", {})
    ut = (p.get("verification") or {}).get("unit_tests") or {}
    out = ["# Calidad, guardrails de arquitectura y seguridad del código generado", "",
           f"- Capas detectadas: {', '.join(s.get('layers', []))}", f"- Complejidad ciclomática máxima por método (heurística): {s.get('max_cc')}",
           f"- Hallazgos bloqueantes/críticos: {s.get('blocking')}", f"- Hallazgos por categoría: {s.get('by_category')}",
           f"- Pruebas unitarias: {ut.get('passed')}/{ut.get('tests')} · cobertura líneas {ut.get('line_coverage')} % · ramas {ut.get('branch_coverage')} %",
           f"- Iteraciones de autocorrección: {len(g.get('autofix', []))}", ""]
    for f in s.get("findings", []):
        out.append(f"- [{f['severity']}] {f['category']} · `{f['file']}` · {f['message']}")
    return "\n".join(out) + "\n"


def _md_security(p: dict[str, Any], m: dict[str, Any]) -> str:
    sf = p["analysis"].get("security_findings", [])
    out = ["# Seguridad e IA responsable", "",
           f"- Secretos/PII enmascarados antes de enviar al modelo: **{m['secrets_masked']}** · residuales: **{m['secrets_residual']}**",
           f"- Cadena de auditoría íntegra: **{m['audit_chain_ok']}**", "- Datos de prueba: solo sintéticos.",
           "- El código subido nunca se ejecuta. Los casos de equivalencia del código generado corren con permisos restringidos de Node (sin red/archivos/procesos); las pruebas con cobertura corren después de ese paso y del escaneo estático (la cobertura V8 no es compatible con --permission).",
           "", "## Hallazgos de seguridad en el código legacy", ""]
    out += [f"- `{f['file']}:{f['line']}` **{f['category']}** — {f['description']}" for f in sf] or ["- Ninguno."]
    out += ["", "## Enmascarado", ""]
    out += [f"- `{x['file']}:{x['line']}` {x['kind']} → `{x['token']}`" for x in p["ingest_report"]["mask_findings"]] or ["- Nada que enmascarar."]
    return "\n".join(out) + "\n"


def _md_trace(p: dict[str, Any]) -> str:
    t = p["trace"]
    out = ["# Matriz de trazabilidad extremo a extremo", "", "Línea legacy → regla → código nuevo → prueba → documento", "",
           f"Completitud: **{t['complete_pct']} %**", "", "| Regla | Líneas legacy | Código | Pruebas | Documento |", "|---|---|---|---|---|"]
    for r in t["rows"]:
        code = "<br>".join(r["code"]) or ("no aplica (código muerto: no se migra)" if r.get("dead") else "")
        tests = "no aplica" if r.get("dead") else f"{len(r['tests'])} casos"
        out.append(f"| {r['rule']} {r['name']} | {'<br>'.join(r['legacy_lines'])} | {code} | {tests} | [{r['rule']}]({r['doc']}) |")
    if t.get("dead_code_rules"):
        out += ["", f"Reglas documentadas como código muerto (excluidas del porcentaje): {', '.join(t['dead_code_rules'])}."]
    return "\n".join(out) + "\n"


def _exec_report(p: dict[str, Any], m: dict[str, Any]) -> str:
    d = p["docs"]
    est = m["estimates"]
    eq = f"{m['equivalence_pct']} % ({m['equivalence_cases']} casos, {m['numeric_differences']} diferencias)" if m["equivalence_pct"] is not None else "no ejecutada para este destino"
    return f"""# Informe ejecutivo — {p['name']}

**Dominio:** {p.get('domain') or 'n/d'} · **Destino:** {p['target']} · **LOC analizadas:** {m['loc']}

{d['executive_summary']}

| Indicador | Resultado |
|---|---|
| Reglas descubiertas / aprobadas por un humano | {m['rules_total']} / {m['rules_approved']} |
| Reglas trazadas a líneas de origen | {m['traceability_pct']} % |
| Equivalencia funcional | {eq} |
| Cobertura de pruebas (líneas / ramas) | {m['line_coverage']} % / {m['branch_coverage']} % |
| Hallazgos críticos en código generado | {m['blocking_findings']} |
| Secretos sin enmascarar enviados al modelo (según los detectores) | 0 ({m['secrets_masked']} enmascarados) |
| Tiempo de procesamiento (máquina) | {m['pipeline_seconds']} s |
| Costo de IA | ${m['cost_usd']} cobrado (equivalente en API de Claude: ~${m['reference_cost_usd']}; {m['tokens_in']:,} tokens entrada / {m['tokens_out']:,} salida) |

## Ahorro estimado frente al análisis manual
Supuestos *parametrizables* (config/estimates.json, no son mediciones): {est['analysis_loc_per_hour']} LOC/h análisis,
{est['migration_and_tests_loc_per_hour']} LOC/h migración + pruebas, +{int(est['docs_fraction_of_total'] * 100)} % documentación, ${est['hourly_rate_usd']}/h.
Proceso manual estimado: **{m['manual_hours_estimate']} h (~{m['manual_days_estimate']} días, ~${m['manual_cost_usd']:,})** frente a **{m['pipeline_seconds']} s** de procesamiento automático
más la revisión humana de reglas. La validación humana permanece: el catálogo se aprueba explícitamente antes de generar código (en modo local el programa se transpila completo; ver supuestos).

## Riesgos mitigados
- Pérdida de reglas tácitas: cada regla cita líneas reales (verificado automáticamente) y lleva nivel de confianza.
- Regresión numérica: equivalencia con tolerancia 0 sobre casos de borde (redondeo, truncamiento, rangos).
- Fuga de datos: enmascarado previo al modelo, ejecución restringida del código generado, auditoría encadenada.
"""


def package_stage(p: dict[str, Any]) -> dict[str, Any]:
    m = metrics(p)
    p["metrics"] = m
    g = p["generation"]
    files: dict[str, str] = {}
    for f in g["files"]:
        files[f"codigo_moderno/{f['path']}"] = f["content"]
    if g["target"] == "typescript":
        files[f"codigo_moderno/{verify.DECIMAL_PATH}"] = verify.RUNTIME_DECIMAL
        if g.get("unit_test_source"):
            files["codigo_moderno/tests/rules.test.ts"] = g["unit_test_source"]
    for a in p["artifacts"]:
        files[f"legacy_original_enmascarado/{a['path']}"] = a["text"]
    d = p["docs"]
    files["docs/01_vision_general_as_is.md"] = "# Visión general (as-is)\n\n" + d["overview_md"]
    files["docs/02_catalogo_reglas.md"] = _md_catalog(p)
    files["docs/catalogo_reglas.json"] = json.dumps(_approved(p), ensure_ascii=False, indent=2)
    files["docs/reglas.feature"] = "# language: es\nCaracterística: Reglas de negocio migradas\n\n" + "\n\n".join(
        f"  # {r['id']} — {r['name']}\n" + "\n".join("  " + ln for ln in r["gherkin"].splitlines()) for r in _approved(p))
    files["docs/03_arquitectura_to_be.md"] = ("# Arquitectura destino (to-be)\n\n" + g["design"]["summary"] + "\n\n```mermaid\n" + d["architecture_mermaid"]
                                              + "\n```\n\n## Secuencia del caso de uso principal\n\n```mermaid\n" + d["sequence_mermaid"] + "\n```\n")
    files["docs/04_diccionario_datos.md"] = "# Diccionario de datos\n\n| Campo | Tipo legacy | Tipo moderno | Descripción |\n|---|---|---|---|\n" + "\n".join(
        f"| {x['name']} | {x['legacy_type']} | {x['modern_type']} | {x['description']} |" for x in d["data_dictionary"]) + "\n\n## Glosario\n\n" + "\n".join(
        f"- **{x['term']}**: {x['definition']}" for x in d["glossary"]) + "\n"
    files["docs/05_matriz_trazabilidad.md"] = _md_trace(p)
    files["docs/matriz_trazabilidad.json"] = json.dumps(p["trace"], ensure_ascii=False, indent=2)
    files["docs/openapi.yaml"] = g["openapi_yaml"]
    for i, adr in enumerate(g["design"]["adrs"], start=1):
        files[f"docs/adr/ADR-{i:03d}.md"] = (f"# ADR-{i:03d}: {adr['title']}\n\n**Estado:** Aceptado\n\n## Contexto\n{adr['context']}\n\n"
                                            f"## Decisión\n{adr['decision']}\n\n## Consecuencias\n{adr['consequences']}\n")
    files["docs/supuestos.md"] = "# Supuestos de la traducción\n\n" + "\n".join(f"- {a}" for a in (d["assumptions"] + g["assumptions"]))
    files["reportes/equivalencia.md"] = _md_equivalence(p)
    files["reportes/equivalencia.json"] = json.dumps((p.get("verification") or {}).get("equivalence"), ensure_ascii=False, indent=2)
    files["reportes/calidad_y_guardrails.md"] = _md_quality(p)
    files["reportes/seguridad.md"] = _md_security(p, m)
    files["reportes/metricas.json"] = json.dumps(m, ensure_ascii=False, indent=2)
    files["reportes/auditoria.json"] = json.dumps(db.audit_log(p["id"]), ensure_ascii=False, indent=2)
    exec_md = _exec_report(p, m)
    files["informe_ejecutivo.md"] = exec_md
    files["README.md"] = (f"# Paquete de migración — {p['name']}\n\nGenerado por el Copiloto de Modernización y Descubrimiento de Código Legacy.\n\n"
                          "## Contenido\n- `informe_ejecutivo.md` — resumen de una página\n- `codigo_moderno/` — código fuente y pruebas\n"
                          "- `docs/` — catálogo de reglas, arquitectura, diccionario, matriz de trazabilidad, ADRs, OpenAPI\n"
                          "- `reportes/` — equivalencia, calidad, seguridad, métricas, auditoría\n- `legacy_original_enmascarado/` — fuente analizada (secretos enmascarados)\n\n"
                          "## Ejecutar las pruebas (TypeScript, Node 22+)\n```\ncd codigo_moderno\nnode --test tests/\n```\n")
    PACKAGES.mkdir(parents=True, exist_ok=True)
    zpath = PACKAGES / f"{p['id']}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            zf.writestr(path, content)
    p["package"] = {"path": str(zpath), "files": sorted(files), "bytes": zpath.stat().st_size, "created": time.time()}
    return {"name": "Paquete empaquetado y reproducible", "passed": True, "files": len(files)}


# ----------------------------------------------------------------------------- cadena post-aprobación
def run_delivery_chain(pid: str) -> None:
    """generate → verify → docs → package; se detiene en la primera etapa fallida."""
    for stage, fn in (("generate", generate_stage), ("verify", verify_stage), ("docs", docs_stage), ("package", package_stage)):
        run_stage(pid, stage, fn)
        if get(pid)["stages"][stage]["status"] == "failed":
            return  # error técnico: se detiene; las compuertas fallidas se reportan pero no ocultan los resultados

