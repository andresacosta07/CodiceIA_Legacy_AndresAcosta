#!/usr/bin/env python3
"""Ejecutor de criterios de aceptación (ADR-004). Multiplataforma, solo biblioteca estándar.

  python scripts/acceptance/run_acceptance.py --fase 3
  python scripts/acceptance/run_acceptance.py --todas

Resultado por criterio: PASS / FAIL / SKIP / MANUAL-VERIFICADO / MANUAL-PENDIENTE.
Reportes: reports/acceptance/fase_<N>_<fecha>.md y .json. Código de salida != 0 si falla cualquier criterio.
Fases del MVP: 0 Fundaciones · 1 Ingesta+seguridad · 2 Descubrimiento · 3 Reglas+HITL · 4 Código+guardrails ·
5 Equivalencia · 6 Entrega y demo · 7 Rúbrica de Visión de Cliente y Negocio (Funcional/Interactivo/Innovador).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
PY = str(ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python"))
if not Path(PY).exists():
    PY = sys.executable
ENV = {**os.environ, "PYTHONPATH": str(ROOT), "COPILOT_LLM": "replay"}


@dataclass
class Criterion:
    id: str
    desc: str
    reqs: list[str]
    check: Callable[[], tuple[bool, str]]
    manual: bool = False


def pytest_k(expr: str, min_tests: int = 1) -> Callable[[], tuple[bool, str]]:
    def run() -> tuple[bool, str]:
        p = subprocess.run([PY, "-m", "pytest", "tests", "-q", "-k", expr, "-p", "no:cacheprovider"], cwd=ROOT, env=ENV,
                           capture_output=True, text=True, timeout=600)
        tail = (p.stdout.strip().splitlines() or ["sin salida"])[-1]
        m = re.search(r"(\d+) passed", tail)
        ok = p.returncode == 0 and bool(m) and int(m.group(1)) >= min_tests
        return ok, tail if ok else (p.stdout[-600:] + p.stderr[-300:])
    return run


def files_exist(paths: list[str]) -> Callable[[], tuple[bool, str]]:
    def run() -> tuple[bool, str]:
        missing = [p for p in paths if not (ROOT / p).exists()]
        return not missing, "todos presentes" if not missing else "faltan: " + ", ".join(missing)
    return run


def models_config() -> tuple[bool, str]:
    cfg = json.loads((ROOT / "config" / "models.json").read_text(encoding="utf-8"))
    known = {"claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-2"}
    bad = [s for s, v in cfg["stages"].items() if v["model"] not in known or v["model"] not in cfg["pricing_usd_per_mtok"]]
    return not bad, "etapas válidas: %d" % len(cfg["stages"]) if not bad else f"modelos desconocidos en {bad}"


def golden_valid() -> tuple[bool, str]:
    n = 0
    for m in (ROOT / "golden").glob("*/manifest.json"):
        man = json.loads(m.read_text(encoding="utf-8-sig"))
        for f in man["files"]:
            if not (m.parent / f).exists():
                return False, f"falta {m.parent.name}/{f}"
        n += 1
    cases = json.loads((ROOT / "golden/cobol_amortizacion/cases.json").read_text(encoding="utf-8-sig"))
    ok = n >= 3 and len(cases) >= 20 and all({"input", "expected"} <= set(c) for c in cases)
    return ok, f"{n} muestras, {len(cases)} casos aportados"


def repo_has_no_secrets() -> tuple[bool, str]:
    sys.path.insert(0, str(ROOT))
    from copilot import masking
    allow = ("golden/adversarial", "golden/cobol_amortizacion/LOANAMRT.cbl", "tests/", ".venv", "data/", "docs/plan/_requerimiento", "cassettes/", "reports/")
    hits = []
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT).as_posix()
        if not p.is_file() or any(rel.startswith(a) or f"/{a}" in f"/{rel}" for a in allow) or p.suffix not in (".py", ".js", ".ts", ".md", ".json", ".html", ".css", ".txt", ".cbl", ".sql", ".cpy", ".yml", ".yaml"):
            continue
        if rel.startswith((".venv", "node_modules")):
            continue
        for f in masking.residual_scan(p.read_text(encoding="utf-8", errors="ignore"), heuristics=False):
            hits.append(f"{rel}:{f['line']} ({f['kind']})")
    return not hits, "0 secretos (muestras sintéticas del golden en lista permitida)" if not hits else "; ".join(hits[:6])


def node_check(path: str) -> Callable[[], tuple[bool, str]]:
    def run() -> tuple[bool, str]:
        p = subprocess.run(["node", "--check", str(ROOT / path)], capture_output=True, text=True)
        return p.returncode == 0, "sintaxis válida" if p.returncode == 0 else p.stderr[-300:]
    return run


def manual(ac_id: str) -> Callable[[], tuple[bool, str]]:
    def run() -> tuple[bool, str]:
        ev = ROOT / "evidence" / f"{ac_id}.json"
        if not ev.exists():
            return False, f"sin evidencia firmada en evidence/{ac_id}.json"
        d = json.loads(ev.read_text(encoding="utf-8"))
        ok = all(d.get(k) for k in ("reviewer", "date", "checklist_completed"))
        return ok, "evidencia completa" if ok else "evidencia incompleta (reviewer/date/checklist_completed)"
    return run


def ui_has(path: str, needles: list[str]) -> Callable[[], tuple[bool, str]]:
    def run() -> tuple[bool, str]:
        text = (ROOT / path).read_text(encoding="utf-8")
        missing = [n for n in needles if n not in text]
        return not missing, "elementos de UI presentes" if not missing else "faltan en la UI: " + ", ".join(missing)
    return run


def doc_has(path: str, needles: list[str], min_chars: int = 3000) -> Callable[[], tuple[bool, str]]:
    def run() -> tuple[bool, str]:
        f = ROOT / path
        if not f.exists():
            return False, f"no existe {path}"
        text = f.read_text(encoding="utf-8")
        missing = [n for n in needles if n.lower() not in text.lower()]
        ok = not missing and len(text) >= min_chars
        return ok, f"{len(text)} caracteres, secciones completas" if ok else f"faltan secciones: {missing}" if missing else "documento demasiado corto"
    return run


def install_check() -> tuple[bool, str]:
    if not (ROOT / "iniciar.bat").exists() or not (ROOT / "iniciar_claude.bat").exists():
        return False, "faltan iniciar.bat / iniciar_claude.bat"
    p = subprocess.run([PY, str(ROOT / "run.py"), "--check"], cwd=ROOT, capture_output=True, text=True, timeout=60)
    ok = p.returncode == 0 and "[ERROR]" not in p.stdout
    return ok, "diagnóstico del equipo sin errores" if ok else (p.stdout[-400:] or p.stderr[-300:])


def cassette_replay() -> tuple[bool, str]:
    code = ("import json,tempfile,os\nfrom pathlib import Path\nfrom copilot import llm,db\n"
            "d=tempfile.mkdtemp(); os.environ['COPILOT_CASSETTES']=d; os.environ['COPILOT_LLM']='replay'; db.init(Path(d)/'x.db')\n"
            "m=llm.CONFIG['stages']['docs']['model']; h=llm._hash('docs',m,'s','u',None)\n"
            "Path(d,h+'.json').write_text(json.dumps({'result':'grabado','tokens_in':1,'tokens_out':1}))\n"
            "assert llm.call('docs','s','u',None)=='grabado'; print('REPLAY-OK')")
    p = subprocess.run([PY, "-c", code], cwd=ROOT, env=ENV, capture_output=True, text=True)
    return "REPLAY-OK" in p.stdout, "modo contingencia responde sin red ni API" if "REPLAY-OK" in p.stdout else (p.stderr[-300:] or p.stdout[-300:])


CRITERIA: dict[int, list[Criterion]] = {
    0: [
        Criterion("AC-F0-01", "Estructura del repo y plan documentado (docs/plan 00–07, ADRs)", ["R-50"], files_exist(
            ["docs/plan/00_contexto_y_requerimientos.md", "docs/plan/02_plan_por_fases.md", "docs/plan/07_seguridad_y_modelo_de_amenazas.md",
             "docs/plan/adr/ADR-001-stack-python-fastapi-react.md", "copilot/main.py", "web/index.html", "runtime/decimal.ts", "run.py", "README.md", "config/models.json"])),
        Criterion("AC-F0-02", "Modelo por etapa configurable y válido", ["R-45"], models_config),
        Criterion("AC-F0-03", "Golden dataset sintético válido (3 muestras, casos aportados)", ["R-46"], golden_valid),
        Criterion("AC-F0-04", "0 secretos en el repositorio (excepto muestras sintéticas del golden)", ["R-46", "R-51"], repo_has_no_secrets),
        Criterion("AC-F0-05", "Frontend: sintaxis JS válida", ["R-44"], node_check("web/app.js")),
        Criterion("AC-F0-06", "Suite completa de pruebas unitarias/integración en verde", ["R-31"], pytest_k("test or not test", min_tests=45)),
    ],
    1: [
        Criterion("AC-F1-01", "Detección de lenguaje, copybooks resueltos y EBCDIC", ["R-01", "R-02", "R-05"], pytest_k("language_detection or ebcdic", 2)),
        Criterion("AC-F1-02", "Entradas inválidas → error claro sin pérdida de datos", ["R-47", "R-44"], pytest_k("invalid_inputs or oversized", 2)),
        Criterion("AC-F1-SEC-01", "Enmascarado: 0 residuos; compuerta de salida bloquea secretos", ["R-04", "R-46"], pytest_k("secrets_masked or masking_preserves or logs_do_not", 3)),
        Criterion("AC-F1-SEC-02", "ZIP-slip, symlink, ZIP-bomb, límites", ["R-51"], pytest_k("zip_slip or zip_symlink", 6)),
        Criterion("AC-F1-03", "Importación desde repositorio Git público: solo lectura, URL/anti-SSRF validados, filtrado y límites", ["R-01", "R-51"], pytest_k("repo_import", 25)),
        Criterion("AC-F1-SEC-03", "Inyección SQL: payloads en rutas, campos y cabeceras; SQL solo parametrizado", ["R-51"], pytest_k("sqli or no_string_built_sql", 4)),
        Criterion("AC-F1-SEC-04", "Auditoría encadenada detecta manipulación; borrado de proyecto", ["R-45", "R-51"], pytest_k("audit_chain or project_purge", 2)),
    ],
    2: [
        Criterion("AC-F2-01", "Adaptador COBOL determinista: unidades, grafo, COMP-3, código muerto", ["R-06", "R-07", "R-08"], pytest_k("cobol_adapter", 1)),
        Criterion("AC-F2-02", "Adaptador genérico para lenguaje sin soporte determinista", ["R-02", "R-50"], pytest_k("generic_adapter", 1)),
        Criterion("AC-F2-SEC-01", "Hallazgos de seguridad del legacy: SQL dinámico y prompt injection", ["R-51"], pytest_k("plsql_dynamic or prompt_injection_flagged", 2)),
    ],
    3: [
        Criterion("AC-F3-01", "Verificador anti-alucinación de citas (verificada/corregida/fallida)", ["R-14"], pytest_k("citation_verifier", 1)),
        Criterion("AC-F3-02", "Salidas del LLM validadas por JSON Schema (estricto)", ["R-12", "R-13"], pytest_k("schema_validator or strictify", 2)),
        Criterion("AC-F3-03", "Validación humana: no se aprueban reglas sin trazabilidad ni se avanza sin aprobar el catálogo", ["R-16", "R-17"], pytest_k("full_flow", 1)),
        Criterion("AC-F3-SEC-01", "Prompt injection: código delimitado como dato no confiable", ["R-51"], pytest_k("prompt_injection_flagged", 1)),
    ],
    4: [
        Criterion("AC-F4-01", "Guardrails: regla de dependencias, sin float, SAST ligero sobre código generado", ["R-24", "R-26"], pytest_k("generated_code_scanner", 1)),
        Criterion("AC-F4-02", "Destino Java: validación estática y declarado NO ejecutado", ["R-21", "R-22"], pytest_k("java_target", 1)),
        Criterion("AC-F4-SEC-01", "Sandbox del oráculo rechaza código inseguro", ["R-43", "R-51"], pytest_k("oracle_sandbox", 1)),
    ],
    5: [
        Criterion("AC-F5-01", "Equivalencia 100 %, 0 diferencias, cobertura ≥80/70, CC ≤10 (solución de referencia)", ["R-27", "R-28", "R-30"], pytest_k("golden_reference_vs_typescript", 1)),
        Criterion("AC-F5-02", "Aritmética decimal exacta (ROUNDED/truncamiento/COMP-3)", ["R-23"], pytest_k("decimal_runtime", 1)),
        Criterion("AC-F5-03", "El comparador detecta diferencias de un centavo", ["R-28"], pytest_k("compare_detects", 1)),
        Criterion("AC-F5-04", "Arbitraje del oráculo (E2 nunca se arbitra), casos complementarios y código muerto fuera de la trazabilidad", ["R-27", "R-28", "R-35"],
                  pytest_k("test_arbitration", 4)),
    ],
    6: [
        Criterion("AC-F6-01", "Flujo completo → paquete con código, pruebas, docs, matriz de trazabilidad, informe y reportes", ["R-33", "R-34", "R-35", "R-36", "R-37"], pytest_k("full_flow", 1)),
        Criterion("AC-F6-02", "Modo contingencia (replay) responde sin red ni API", ["R-38"], cassette_replay),
        Criterion("AC-F6-SEC-01", "Cabeceras de seguridad, rate limit, sin sumideros XSS en la UI", ["R-51"], pytest_k("headers or rate_limit or dangerous_sinks or hostile_content", 4)),
        Criterion("AC-F6-03", "Guion de demo y README presentes", ["R-39"], files_exist(["README.md", "docs/GUION_DEMO.md"])),
        Criterion("AC-F6-MANUAL-01", "Usuario externo completa la tarea principal sin asistencia (checklist firmado)", ["R-44"], manual("AC-F6-MANUAL-01"), manual=True),
    ],
    # Fase 7: rúbrica de Visión de Cliente y Negocio (Funcional 33,33 % · Interactivo 33,33 % · Innovador 33,33 %)
    7: [
        Criterion("AC-F7-01", "FUNCIONAL: flujo completo sin clave (motor local) con equivalencia 100 %, cobertura ≥80/70 y trazabilidad 100 %", ["R-27", "R-28", "R-30", "R-39"],
                  pytest_k("local_full_flow", 1)),
        Criterion("AC-F7-02", "FUNCIONAL: caso representativo y casos borde (E2 independiente + E3) y el oráculo coincide con la referencia a mano", ["R-27"],
                  pytest_k("python_backend_matches or golden_reference", 2)),
        Criterion("AC-F7-03", "FUNCIONAL: entrada inválida manejada con mensaje claro, sin exponer ni guardar datos", ["R-47"], pytest_k("invalid_inputs or oversized or unsupported_construct or other_languages", 4)),
        Criterion("AC-F7-04", "INTERACTIVO: flujo guiado (stepper + ayuda «qué hago ahora») y demostración de errores en la UI", ["R-44"],
                  ui_has("web/app.js", ["helpCard", "Qué hacer ahora", "demoInvalid", "STEPS"])),
        Criterion("AC-F7-05", "INTERACTIVO: vista comparativa legacy vs. moderno con resaltado de líneas por regla", ["R-44", "R-34"],
                  ui_has("web/app.js", ["Vista comparativa legacy", "cmp-legacy", "cmp-modern", "codeView"])),
        Criterion("AC-F7-06", "INTERACTIVO: manual de usuario técnico y no técnico, arquitectura y tecnologías", ["R-37"],
                  doc_has("docs/MANUAL_DE_USUARIO.md", ["arquitectura", "tecnolog", "usuario no técnico", "usuario técnico", "solución de problemas", "guion"], 8000)),
        Criterion("AC-F7-07", "INNOVADOR: comparación cuantificada manual vs. copiloto y caso de negocio interactivo (cartera)", ["R-40"],
                  ui_has("web/app.js", ["Comparación frente al proceso manual", "Caso de negocio: de una rutina a toda la cartera", "manual_hours_estimate"])),
        Criterion("AC-F7-08", "INNOVADOR: elemento diferenciador explícito y evidencias mapeadas a la rúbrica", ["R-40"],
                  ui_has("web/app.js", ["¿Qué nos diferencia?"])),
        Criterion("AC-F7-09", "Rúbrica documentada con evidencia por criterio", ["R-39"], doc_has("docs/RUBRICA_Y_EVIDENCIAS.md", ["funcional", "interactivo", "innovador", "evidencia"], 2500)),
        Criterion("AC-F7-11", "Extensión Claude vía suscripción (Claude Code, sin clave): invocación aislada, sin API key, error handling, cambio de modo y `auto` nunca la activa", ["R-55", "R-51"],
                  pytest_k("claude_code or mode_endpoint or auto_mode", 4)),
        Criterion("AC-F7-12", "Contingencia: se reproduce sin red ni IA una corrida real de Claude grabada (equivalencia 100 %)", ["R-38", "R-55"], pytest_k("replay_of_recorded", 1)),
        Criterion("AC-F7-16", "Interfaz guiada y estándares UX: recorrido guiado, glosario ⓘ, navegación por pasos, favicon, contraste WCAG AA y accesibilidad", ["R-44", "R-56"],
                  pytest_k("test_ui_standards or contrast_meets or favicon or accessibility or guided_experience or dangerous_sinks_in_any", 5)),
        Criterion("AC-F7-17", "Guía de entrenamiento para presentar la demo (persona no técnica)", ["R-56"],
                  doc_has("docs/GUIA_ENTRENAMIENTO_DEMO.md", ["ejercicio", "preguntas", "checklist", "autoevaluación", "guion"], 9000)),
        Criterion("AC-F7-13","Instalación sencilla: iniciar.bat, diagnóstico `run.py --check` sin errores y puerto libre automático", ["R-37"], install_check),
        Criterion("AC-F7-14", "Manual técnico completo (instalación, API REST, seguridad, extensión, escalabilidad y hoja de ruta de producción)", ["R-56"],
                  doc_has("docs/MANUAL_TECNICO.md", ["escalabilidad", "hoja de ruta", "instalación", "api rest", "seguridad", "extender"], 12000)),
        Criterion("AC-F7-15", "Manual funcional no técnico completo (glosario, preguntas frecuentes, recorrido por pasos)", ["R-56"],
                  doc_has("docs/MANUAL_FUNCIONAL_NO_TECNICO.md", ["glosario", "preguntas frecuentes", "recorrido", "aprobar", "rechazar"], 5000)),
        Criterion("AC-F7-10", "Motor local: no genera Java/C# sin API y lo declara; el modelo local opcional es solo loopback y seguro", ["R-51"], pytest_k("non_typescript or enrichment_is_safe or must_be_loopback", 3)),
    ],
}


@dataclass
class Result:
    id: str
    desc: str
    reqs: list[str]
    status: str
    detail: str
    seconds: float = 0.0


def commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or "sin-git"
    except OSError:
        return "sin-git"


def run_phase(n: int, strict: bool) -> list[Result]:
    import time
    out = []
    for c in CRITERIA[n]:
        t = time.time()
        try:
            ok, detail = c.check()
            status = ("MANUAL-VERIFICADO" if ok else "MANUAL-PENDIENTE" if not strict else "FAIL") if c.manual else ("PASS" if ok else "FAIL")
        except Exception as exc:  # noqa: BLE001
            status, detail = "FAIL", f"{type(exc).__name__}: {exc}"
        r = Result(c.id, c.desc, c.reqs, status, detail, round(time.time() - t, 1))
        out.append(r)
        print(f"  [{status:>17}] {c.id}  {c.desc}  ({r.seconds}s)" + ("" if status in ("PASS", "MANUAL-VERIFICADO") else f"\n      → {detail}"))
    return out


def write_report(n: int | str, results: list[Result]) -> Path:
    d = ROOT / "reports" / "acceptance"
    d.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    data = {"fase": n, "fecha": dt.datetime.now().isoformat(timespec="seconds"), "commit": commit(),
            "resultado": "PASS" if all(r.status in ("PASS", "MANUAL-VERIFICADO", "MANUAL-PENDIENTE", "SKIP") for r in results) else "FAIL",
            "criterios": [r.__dict__ for r in results]}
    (d / f"fase_{n}_{stamp}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [f"# Reporte de aceptación — fase {n}", "", f"- Fecha: {data['fecha']}  ·  Commit: {data['commit']}  ·  Resultado: **{data['resultado']}**", "",
          "| Criterio | Estado | Requerimientos | Detalle |", "|---|---|---|---|"]
    md += [f"| {r.id} — {r.desc} | {r.status} | {', '.join(r.reqs)} | {r.detail[:120]} |" for r in results]
    path = d / f"fase_{n}_{stamp}.md"
    path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--fase", type=int, choices=sorted(CRITERIA))
    g.add_argument("--todas", action="store_true", help="regresión de todas las fases")
    ap.add_argument("--estricto", action="store_true", help="los criterios manuales pendientes cuentan como FAIL")
    a = ap.parse_args()
    phases = sorted(CRITERIA) if a.todas else [a.fase]
    allres: list[Result] = []
    for n in phases:
        print(f"\n== Fase {n} ==")
        res = run_phase(n, a.estricto)
        report = write_report(n, res)
        allres += res
        print(f"  reporte: {report.relative_to(ROOT)}")
    if a.todas:
        write_report("todas", allres)
    failed = [r for r in allres if r.status == "FAIL"]
    print(f"\n{'ACEPTACIÓN: PASS' if not failed else 'ACEPTACIÓN: FAIL'} — {len(allres) - len(failed)}/{len(allres)} criterios")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
