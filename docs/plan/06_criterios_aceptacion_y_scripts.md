# 06 — Criterios de aceptación y scripts

Los criterios `AC-F<fase>-<nn>` y `AC-F<fase>-SEC-<nn>` están definidos, con requerimientos cubiertos, comprobación y umbral, en las tablas de cada fase de `02_plan_por_fases.md`. Este documento define **cómo se ejecutan**. Ninguna fase se da por terminada por inspección manual ni por afirmación del agente.

## 1. Tecnología

**Python 3.12, solo biblioteca estándar en el núcleo** (ADR-004): corre igual en Windows, Linux y macOS, ya está en CI, no requiere compilación y facilita invocar herramientas externas (`subprocess`), leer JSON, comparar y generar reportes. Los checks que necesitan herramientas externas (gitleaks, Semgrep, docker, mvn, npm) las invocan y devuelven `SKIP` con causa si faltan **solo en modo local**; en CI, una herramienta ausente es `FAIL`.

## 2. Estructura

```
scripts/acceptance/
  run_acceptance.py        # --fase N | --todas | --criterio AC-F3-02 | --ci | --offline
  fase_0.py … fase_6.py    # un módulo por fase: lista de criterios (CRITERIA)
  lib/
    runner.py              # ejecución, timeouts, captura, resultados
    report.py              # .md y .json
    checks_build.py        # compilar, lint, tipos, cobertura
    checks_arch.py         # ArchUnit, dependency-cruiser, complejidad, no_float_money, no_goto
    checks_golden.py       # métricas sobre golden/, trazabilidad, equivalencia
    checks_api.py          # smoke/e2e contra la app levantada, entradas inválidas
    security_checks.py     # gitleaks, sast, deps_audit, sqli_suite, ssrf_suite, upload_attacks,
                           # prompt_injection_suite, xss_suite, security_headers, zap_baseline, trivy
    schemas.py             # validación JSON Schema
    manual.py              # evidencia firmada → MANUAL-VERIFICADO
  security/payloads/       # payloads de SQLi, XSS, traversal, SSRF, prompt injection
reports/acceptance/        # fase_<N>_<fecha>.md / .json  (no versionado salvo releases)
```

Cada criterio se declara como dato:

```python
Criterion(
  id="AC-F3-02",
  desc="Toda regla cita líneas reales",
  reqs=["R-14"],
  check=checks_golden.rule_traceability,
  threshold={"min_pct": 100},
  mode="auto",            # auto | manual
)
```

## 3. Comportamiento

- Resultado por criterio: `PASS`, `FAIL` (con motivo y valor medido vs. umbral), `SKIP` (solo local, con causa) o `MANUAL-VERIFICADO` (existe `evidence/<AC>.json` con revisor, fecha, hash y checklist completa; si falta, es `FAIL`, nunca aprobado en silencio).
- Reportes `reports/acceptance/fase_<N>_<fecha>.md` y `.json` con fecha, **commit**, versión de herramientas, resultado por criterio, valores medidos y **requerimientos cubiertos**.
- **Código de salida ≠ 0** si falla cualquier criterio (también ante `SKIP` en `--ci`).
- `--todas` ejecuta todas las fases marcadas como completadas en `scripts/acceptance/phases.json` (regresión). Una fase solo se marca completada cuando su script pasa al 100 %.
- Verificación de cobertura de requerimientos: un chequeo meta (`AC-F0-09`, añadido en F0) comprueba que cada R-xx de `00` está referenciado por ≥ 1 criterio de su fase.
- Modo determinista: los agentes IA usan cassettes (replay) en aceptación; las métricas en vivo se reportan aparte.

## 4. Ejecución local

```powershell
# Windows (PowerShell)
python scripts/acceptance/run_acceptance.py --fase 3
python scripts/acceptance/run_acceptance.py --todas
```
```bash
# Linux / macOS
python3 scripts/acceptance/run_acceptance.py --fase 3
python3 scripts/acceptance/run_acceptance.py --todas
```

## 5. CI (GitHub Actions por defecto)

Disparador: push y pull request a la rama principal. Matriz `windows-latest` + `ubuntu-latest`. Pasos: checkout → instalar toolchains (Python, Node, JDK 21, Docker) → `python scripts/acceptance/run_acceptance.py --todas --ci` → subir `reports/acceptance/` como artefacto → el job falla si el exit code ≠ 0. Jobs de seguridad (gitleaks, Semgrep, Trivy, ZAP) se invocan desde los checks de seguridad; no se duplican fuera de la aceptación.

## 6. Regla de avance

1. Al **inicio** de la fase: escribir `fase_<N>.py` (criterios en rojo) y ver el reporte `FAIL`.
2. Implementar hasta que `run_acceptance --fase N` dé 100 %.
3. Ejecutar `run_acceptance --todas`; deben pasar todas las fases previas.
4. Adjuntar el reporte generado al cierre de la fase. Solo entonces se actualiza `phases.json`.

## 7. Trazabilidad requerimientos → fase

Cada R-xx está asignado a ≥ 1 fase en la columna "Fase" de `00`; la verificación automática es AC-F0-09. Resumen:

| Fase | Requerimientos |
|---|---|
| F0 | R-31, R-45 (base), R-46, R-50, R-51 |
| F1 | R-01–R-05, R-44, R-45, R-47, R-51 |
| F2 | R-06–R-11, R-49, R-50, R-51 |
| F3 | R-12–R-17, R-41, R-45, R-48, R-49, R-51 |
| F4 | R-18–R-26, R-31, R-41–R-43, R-51 |
| F5 | R-27–R-32, R-35, R-46, R-48, R-51 |
| F6 | R-20, R-33–R-40, R-44, R-45, R-48, R-51 |
| F7–F9 | R-52, R-53, R-54 |

## 8. Criterio adicional de F0 (completa la tabla de `02`)

| ID | Criterio | Req. | Comprobación | Umbral |
|---|---|---|---|---|
| AC-F0-09 | Todo requerimiento R-01…R-51 del MVP tiene ≥ 1 criterio asociado | todos | check: `req_coverage` | 100 % |


---

## Actualización (implementación real del script)

**Corrección a las secciones anteriores:** la implementación es **un único archivo** `scripts/acceptance/run_acceptance.py` con un diccionario `CRITERIA` por fase (no existen `fase_<N>.py` ni `lib/`). Solo biblioteca estándar; usa el Python del `.venv` si existe. Las comprobaciones de pruebas ejecutan `pytest -k <expresión>` con `COPILOT_LLM=replay` y exigen un mínimo de pruebas pasadas. Estados: `PASS`, `FAIL`, `MANUAL-VERIFICADO`, `MANUAL-PENDIENTE` (con `--estricto` cuenta como FAIL). Reportes `reports/acceptance/fase_<N>_<fecha>.md/.json` con commit; código de salida ≠ 0 si algún criterio es `FAIL`. Opciones: `--fase N` (0–7), `--todas`, `--estricto`. No implementado: ejecución en CI, `AC-F0-09` (cobertura de requerimientos), `--ci`/`--offline`.

| Fase | ID | Qué comprueba | Cómo |
|---|---|---|---|
| 0 | AC-F0-01 | Estructura del repo y plan documentado | archivos presentes |
| 0 | AC-F0-02 | `config/models.json` válido (IDs conocidos con precio) | lectura de JSON |
| 0 | AC-F0-03 | Golden dataset (≥ 3 muestras, ≥ 20 casos aportados) | manifiestos y `cases.json` |
| 0 | AC-F0-04 | 0 secretos en el repo (salvo muestras sintéticas del golden) | `masking.residual_scan` (alta confianza) |
| 0 | AC-F0-05 | Sintaxis JS del frontend | `node --check web/app.js` |
| 0 | AC-F0-06 | Suite completa en verde (≥ 45 pruebas exigidas por el script; hoy la suite tiene 57) | `pytest` |
| 1 | AC-F1-01 | Lenguaje/dialecto, copybooks y EBCDIC | pytest |
| 1 | AC-F1-02 | Entradas inválidas con error claro sin pérdida de datos | pytest |
| 1 | AC-F1-03 | Importación desde repositorio Git público (solo lectura, sin clonar): URL y anti-SSRF validados, filtrado y límites (ADR-017; red simulada, GitHub probado en vivo a mano) | pytest `repo_import` |
| 1 | AC-F1-SEC-01 | Enmascarado, compuerta de salida, logs sin código | pytest |
| 1 | AC-F1-SEC-02 | ZIP-slip, symlink, ZIP-bomb, límites | pytest |
| 1 | AC-F1-SEC-03 | Inyección SQL (rutas, campos, cabeceras) y SQL solo parametrizado | pytest |
| 1 | AC-F1-SEC-04 | Auditoría encadenada detecta manipulación; borrado de proyecto | pytest |
| 2 | AC-F2-01 | Adaptador COBOL: unidades, grafo, COMP-3, código muerto | pytest |
| 2 | AC-F2-02 | Adaptador genérico para lenguaje sin soporte determinista | pytest |
| 2 | AC-F2-SEC-01 | SQL dinámico y prompt injection detectados en el legacy | pytest |
| 3 | AC-F3-01 | Verificador anti-alucinación de citas | pytest |
| 3 | AC-F3-02 | Esquemas JSON (validador y modo estricto) | pytest |
| 3 | AC-F3-03 | No se aprueban reglas sin trazabilidad ni se avanza sin aprobar el catálogo | pytest (`full_flow`) |
| 3 | AC-F3-SEC-01 | Código legacy delimitado como dato no confiable | pytest |
| 4 | AC-F4-01 | Guardrails: dependencias, sin float, SAST ligero | pytest |
| 4 | AC-F4-02 | Destino Java: validación estática y declarado NO ejecutado | pytest |
| 4 | AC-F4-SEC-01 | El sandbox del oráculo rechaza código inseguro | pytest |
| 5 | AC-F5-01 | Equivalencia 100 %, cobertura ≥ 80/70, CC ≤ 10 (solución de referencia) | pytest |
| 5 | AC-F5-02 | Aritmética decimal exacta | pytest + Node |
| 5 | AC-F5-03 | El comparador detecta diferencias de un centavo | pytest |
| 6 | AC-F6-01 | Flujo completo → paquete con todos los artefactos | pytest |
| 6 | AC-F6-02 | Modo replay responde sin red ni API | subproceso con cassette sintética |
| 6 | AC-F6-SEC-01 | Cabeceras, rate limit, sin sumideros XSS | pytest |
| 6 | AC-F6-03 | `README.md` y `docs/GUION_DEMO.md` presentes | archivos |
| 6 | **AC-F6-MANUAL-01** | Usuario externo completa la tarea sin ayuda | **manual**: exige `evidence/AC-F6-MANUAL-01.json` con `reviewer`, `date`, `checklist_completed`; si falta → `MANUAL-PENDIENTE` |
| 7 | AC-F7-01 | FUNCIONAL: flujo completo sin clave con equivalencia 100 %, cobertura y trazabilidad | pytest (`local_full_flow`) |
| 7 | AC-F7-02 | FUNCIONAL: caso representativo y bordes; oráculo == referencia a mano | pytest |
| 7 | AC-F7-03 | FUNCIONAL: entrada inválida manejada sin exponer datos | pytest |
| 7 | AC-F7-04 | INTERACTIVO: stepper + ayuda «qué hago ahora» + demostración de errores | texto en `web/app.js` |
| 7 | AC-F7-05 | INTERACTIVO: vista comparativa legacy vs. moderno | texto en `web/app.js` |
| 7 | AC-F7-06 | INTERACTIVO: manual (arquitectura, tecnologías, técnico y no técnico, problemas, guion) | `docs/MANUAL_DE_USUARIO.md` ≥ 8000 caracteres con secciones |
| 7 | AC-F7-07 | INNOVADOR: comparación cuantificada y caso de negocio interactivo | texto en `web/app.js` |
| 7 | AC-F7-08 | INNOVADOR: elemento diferenciador | texto en `web/app.js` |
| 7 | AC-F7-09 | Rúbrica documentada con evidencia | `docs/RUBRICA_Y_EVIDENCIAS.md` ≥ 2500 caracteres con secciones |
| 7 | AC-F7-10 | Motor local no genera Java/C#; modelo local opcional solo loopback y seguro | pytest |
| 7 | AC-F7-11 | Modo `claude-code` aislado y sin clave: invocación del CLI sin herramientas ni persistencia, prompt por stdin, directorio temporal, sin `ANTHROPIC_API_KEY`; errores claros; cassette y costo 0; `POST /api/mode`; `auto` nunca elige `claude-code` | pytest (`tests/test_modes.py`, 5 pruebas, con CLI simulado) |
| 7 | AC-F7-13 | Instalación sencilla: `iniciar.bat`, diagnóstico `run.py --check` sin errores | script de aceptación (`install_check`) |
| 7 | AC-F7-14 | Manual técnico completo (instalación, API REST, seguridad, extensión, escalabilidad) | `docs/MANUAL_TECNICO.md` ≥ 12 000 caracteres con secciones |
| 7 | AC-F7-15 | Manual funcional no técnico completo | `docs/MANUAL_FUNCIONAL_NO_TECNICO.md` ≥ 5 000 caracteres con secciones |
| 7 | AC-F7-16 | Interfaz guiada y estándares UX: contraste WCAG AA en claro y oscuro (texto y botones ≥ 4,5:1), favicon y metadatos, accesibilidad básica, guía interactiva y glosario, sin sumideros XSS | `tests/test_ui_standards.py` (6 pruebas) |
| 7 | AC-F7-17 | Guía de entrenamiento presente (ejercicios, guion corto y largo, preguntas del jurado, errores comunes, checklists, autoevaluación) | `docs/GUIA_ENTRENAMIENTO_DEMO.md` ≥ 9 000 caracteres con secciones |

> **Estado de AC-F7-13 a AC-F7-17:** los cinco están registrados en `CRITERIA[7]` de `scripts/acceptance/run_acceptance.py` y pasan (aceptación completa: 47/47 criterios, con el criterio manual de usuario externo pendiente; 63 pruebas).

> **Estado de AC-F7-11 y AC-F7-12:** ambos están registrados en `CRITERIA[7]` de `scripts/acceptance/run_acceptance.py` y pasan (AC-F7-11: `tests/test_modes.py`; AC-F7-12: `tests/test_replay_recorded.py`, que reproduce sin red ni IA la corrida real de Claude grabada en `cassettes/`). Aceptación completa: 42/42 criterios, con el criterio manual de usuario externo pendiente.

Limitaciones: los criterios AC-F7-04/05/07/08 verifican la **presencia de elementos en el código de la UI**, no su comportamiento en un navegador; el criterio de usabilidad con usuario externo es manual.
