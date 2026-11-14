# 02 — Plan de construcción por fases

## Estado real por fase

El plan original (fases 0–9, por sesiones) se **compactó** para una entrega en un día con una sola persona. La implementación real está en un único ejecutor `scripts/acceptance/run_acceptance.py` (no existen `fase_<N>.py` separados). Las secciones de abajo describen el **diseño original**; este cuadro describe lo construido.

| Fase | Estado | Evidencia (pruebas / AC) | No implementado |
|---|---|---|---|
| F0 Fundaciones | Implementada (compactada) | AC-F0-01..06; 57 pruebas en `tests/` (el script exige ≥ 51) | CI/CD, SBOM, gitleaks/Semgrep/Trivy externos, `req_coverage` (AC-F0-09) |
| F1 Ingesta y seguridad | Implementada | AC-F1-01, 02, 03, SEC-01..04; `test_security.py`, `test_units.py`, `test_repo_import.py` | Clonado Git (en su lugar: descarga del ZIP de repos públicos, ADR-017; sin probar en vivo), repos privados, RBAC |
| F2 Descubrimiento | Implementada | AC-F2-01, 02, SEC-01; adaptador COBOL + genérico | Adaptadores deterministas de PL/SQL, RPG y Java |
| F3 Reglas + HITL | Implementada | AC-F3-01..03, SEC-01; `test_e2e.py`, `test_local_engine.py` | Segundo pasaje de verificación; Gherkin/DMN ejecutables |
| F4 Código + guardrails | Implementada (TypeScript) | AC-F4-01, 02, SEC-01; escaneo de capas, float, SAST ligero, CC | ArchUnit/dependency-cruiser/SpotBugs reales; Java/C# solo con API y sin compilar; OpenAPI sin lint |
| F5 Equivalencia | Implementada (TypeScript) | AC-F5-01..03; 67/67 casos y cobertura 93,7 %/83,3 % en la corrida de referencia local | Legacy ejecutado (E1); mutation testing |
| F6 Entrega y demo | Implementada | AC-F6-01, 02, SEC-01, 03; `AC-F6-MANUAL-01` **pendiente** de evidencia firmada | Docker, ZAP, Trivy, borrado/retención avanzados |
| F7 Rúbrica Visión de Cliente | Implementada (nueva) | AC-F7-01..10 en el script (depende de `docs/MANUAL_DE_USUARIO.md` y `docs/RUBRICA_Y_EVIDENCIAS.md`); **AC-F7-11** (modo `claude-code`, `tests/test_modes.py`) definido y respaldado por pruebas, pendiente de registrarse en el script; corrida real con Claude vía suscripción (ADR-015) | Prueba con usuario externo (evidencia); `claude-code` con lenguajes distintos de COBOL; modo `live` con API |
| Hoja de ruta original F7–F9 (lenguajes, producción, piloto) | No iniciadas | — | PL/SQL/RPG/Java, C#, RBAC/SSO, WORM, Bedrock/Vertex, piloto con código real |

Nota de numeración: en el diseño original F7–F9 eran la hoja de ruta (extensión de lenguajes, producción, piloto). La **F7 implementada** es la fase de aceptación de la rúbrica; la extensión de lenguajes queda pospuesta y no se ha iniciado.

---

## Diseño original

Alcance: **F0–F6 = MVP demostrable** (cumple el Word). **F7–F9 = hoja de ruta.** Metodología guiada por aceptación: al inicio de cada fase se escribe `scripts/acceptance/fase_<N>.py` (criterios en rojo) y la fase termina solo cuando pasa al 100 % y la regresión `--todas` sigue en verde (ver `06`). Los criterios `AC-Fx-SEC-nn` son de seguridad (ver `07`).

Complejidad: S < M < L < XL. Una "sesión" = una sesión de Claude Code; cada fase indica sesiones estimadas.

Mapeo con las 8 fases del flujo del Word: F1 → flujo 1; F2 → flujo 2; F3 → flujo 3–4; F4 → flujo 5–6; F5 → flujo 7; F6 → flujo 8.

Convención de verificación: `check:` indica la función en `scripts/acceptance/lib/` que lo comprueba. Umbrales numéricos vienen del Word.

---

## Fase 0 — Fundaciones (M, 2–3 sesiones)

**Objetivo:** esqueleto ejecutable con CI, convenciones, el mecanismo de aceptación y el golden dataset base.
**Entra:** monorepo (`apps/api`, `apps/web`, `packages/core`, `plugins/`, `prompts/`, `schemas/`, `scripts/acceptance/`, `golden/`, `docs/`), Docker Compose (api, web, postgres), CI, `CLAUDE.md` definitivo, `run_acceptance.py`, `config/models.yaml` con verificación de IDs, golden dataset inicial, SAST/secretos/dependencias en CI, SBOM.
**No entra:** lógica de negocio de la app.
**Requerimientos:** R-31, R-45 (base), R-46, R-50, R-51.
**Tareas:**
1. Verificar IDs de modelo vigentes (skill `claude-api`) y fijarlos en `config/models.yaml`.
2. Crear estructura del monorepo, `pyproject.toml`, `package.json`, lockfiles, pre-commit (ruff, mypy, gitleaks).
3. Escribir `scripts/acceptance/` (ejecutor, reportes MD/JSON, checks base, `fase_0.py`) **primero**.
4. `docker-compose.yml` con healthchecks; endpoint `/health` y página web mínima.
5. CI (GitHub Actions) con matriz Windows/Linux: lint, tests, SAST (Semgrep, Bandit), gitleaks, pip-audit/npm audit, SBOM CycloneDX, `run_acceptance --todas`.
6. Golden dataset v0 (`golden/`): `cobol_amortizacion_francesa` (con COMP-3, redondeo, signos), `plsql_liquidacion_siniestro` y `rpg_o_java_legacy_muestra`, más muestras **maliciosas** (prompt injection en comentarios, ZIP-slip) y con **secretos sintéticos**. Todo sintético.
7. Redactar `CLAUDE.md` desde `CLAUDE.md.draft`; ADR-001..010 pasan a Aceptados.
**Entregables:** repo que levanta con `docker compose up`, CI verde, reporte de aceptación F0.
**Dependencias:** ninguna. **Riesgos:** Docker en Windows; IDs de modelo cambiantes.

| ID | Criterio | Req. | Comprobación automática | Umbral |
|---|---|---|---|---|
| AC-F0-01 | Estructura del monorepo y archivos obligatorios presentes | R-50 | check: `files_exist` | 100 % |
| AC-F0-02 | `docker compose up` levanta y `/health` responde 200 | R-37 | check: `compose_smoke` | 200 en ≤ 60 s |
| AC-F0-03 | Lint y tipos (ruff, mypy, eslint, tsc) sin errores | R-31 | check: `run_cmd` | 0 errores |
| AC-F0-04 | Tests de base en verde y cobertura inicial | R-31 | check: `coverage` | ≥ 80 % líneas del código existente |
| AC-F0-05 | `config/models.yaml` válido contra su esquema; IDs presentes | R-45 | check: `json_schema` | válido |
| AC-F0-06 | Golden dataset válido: manifiesto, 0 datos reales marcados, esquemas JSON válidos | R-46 | check: `golden_manifest` | 100 % |
| AC-F0-07 | El ejecutor genera `.md` y `.json` y devuelve exit ≠ 0 ante fallo (test del propio ejecutor con un criterio forzado a fallar) | R-31 | check: `runner_selftest` | exit ≠ 0 |
| AC-F0-08 | Ejecutor funciona en Windows y Linux | R-31 | matriz CI | ambos verdes |
| AC-F0-SEC-01 | 0 secretos en el repo (los secretos sintéticos del golden están en allowlist firmada) | R-46, R-51 | check: `gitleaks` | 0 |
| AC-F0-SEC-02 | Semgrep/Bandit sin hallazgos altos/críticos; pip-audit/npm audit sin críticas | R-31, R-51 | check: `sast`, `deps_audit` | 0 críticas |
| AC-F0-SEC-03 | SBOM CycloneDX generado y válido; lockfiles presentes | R-51 | check: `sbom` | válido |

---

## Fase 1 — Ingesta y gestión de proyectos (M, 3–4 sesiones)

**Objetivo:** cargar código legacy de forma segura, normalizado y sin secretos.
**Entra:** proyectos y artefactos; carga por archivo, pegado, ZIP y Git; detección de lenguaje/dialecto/codificación (EBCDIC); resolución de copybooks/includes; **enmascarado de secretos/PII**; parámetros opcionales (destino, dominio, estilo); UI de carga con estados y errores con acción sugerida; auditoría y registro de LLM_CALL (base).
**No entra:** análisis estático (F2), llamadas al LLM de negocio.
**Requerimientos:** R-01–R-05, R-44 (parcial), R-45 (base), R-47, R-51.
**Tareas:**
1. Modelo de datos y migraciones (Alembic); roles de BD de mínimo privilegio.
2. Uploader seguro: límites, validación de tipo, anti-ZIP-slip/ZIP-bomb, rutas canonizadas, directorio aislado.
3. Cliente Git seguro (https, anti-SSRF, sin hooks/submódulos, timeout).
4. Detector de lenguaje/dialecto/codificación (heurísticas + LLM de bajo costo como desempate).
5. Enmascarador: detectores (gitleaks/patrones propios para cadenas de conexión, IBAN, documentos de identidad, correos), mapa reversible local, bloqueo si queda residuo.
6. Normalizador: resolución de copybooks/includes, verificación de completitud.
7. API REST + UI (carga, inventario, informe de enmascarado, vista de errores).
8. Auditoría hash-chain y esquema.
**Entregables:** subir un ZIP del golden y ver inventario normalizado y reporte de enmascarado.
**Dependencias:** F0. **Riesgos:** falsos negativos del enmascarador; EBCDIC variado.

| ID | Criterio | Req. | Comprobación | Umbral |
|---|---|---|---|---|
| AC-F1-01 | Ingesta de archivo, pegado, ZIP y Git sobre el golden: inventario completo | R-01, R-02 | check: `e2e_api` | 100 % de archivos |
| AC-F1-02 | Detección correcta de lenguaje/dialecto sobre el golden | R-02, R-05 | check: `golden_metric(language_detection)` | ≥ 95 % |
| AC-F1-03 | EBCDIC detectado y convertido; round-trip sin pérdida | R-05 | check: `ebcdic_roundtrip` | 100 % |
| AC-F1-04 | Copybooks/includes resueltos; completitud reportada | R-05 | check: `golden_metric(include_resolution)` | 100 % |
| AC-F1-05 | Parámetros opcionales (destino, dominio, estilo) persistidos y validados | R-03 | check: `e2e_api` | válido |
| AC-F1-06 | Entradas inválidas (vacío, binario, tamaño excesivo, codificación rota) devuelven error 4xx con mensaje y acción sugerida, sin pérdida ni exposición de datos | R-47, R-44 | check: `invalid_inputs` | 100 % |
| AC-F1-07 | Pruebas unitarias/integración; cobertura | R-31 | check: `coverage` | ≥ 80 % líneas / ≥ 70 % ramas |
| AC-F1-SEC-01 | Enmascarado: 0 secretos/PII residuales en lo enviable al LLM (golden con secretos sintéticos) | R-04, R-46 | check: `mask_residual` | 0 |
| AC-F1-SEC-02 | Suite ZIP-slip, ZIP-bomb, path traversal, nombres maliciosos | R-51 | check: `upload_attacks` | 100 % bloqueados |
| AC-F1-SEC-03 | Suite SSRF en clonado Git (169.254.x, localhost, redes privadas, esquemas `file://`, redirecciones) | R-51 | check: `ssrf_suite` | 100 % bloqueados |
| AC-F1-SEC-04 | Suite de inyección SQL (payloads en todos los parámetros de la API) sin alteración de datos ni errores SQL expuestos | R-51 | check: `sqli_suite` | 0 explotables |
| AC-F1-SEC-05 | Código subido nunca se ejecuta; logs sin código fuente ni secretos | R-51 | check: `log_redaction` | 0 fugas |
| AC-F1-SEC-06 | Auditoría hash-chain verificable; manipular un evento se detecta | R-45 | check: `audit_chain` | detecta 100 % |

---

## Fase 2 — Análisis estático y descubrimiento (L, 4–5 sesiones)

**Objetivo:** estructura verificada, grafo, métricas y mapa de riesgo; base para que el LLM no trabaje sobre texto plano.
**Entra:** interfaz `LanguageAdapter` y registro de plugins; adaptador **COBOL determinista** (divisiones, secciones, párrafos, PERFORM/CALL, COPY, EXEC SQL, FD/archivos, PIC/COMP-3); adaptador **genérico** (tree-sitter donde exista gramática + LLM con salida estructurada para validar), probado con PL/SQL/RPG/Java de muestra; unidades de análisis; grafo de dependencias; métricas (LOC, CC, código muerto, duplicidad); clasificación negocio vs. infraestructura; mapa de riesgo; **detección de patrones inseguros del legacy (SQL dinámico concatenado)**; UI con grafo y métricas.
**No entra:** extracción de reglas (F3).
**Requerimientos:** R-06–R-11, R-49, R-50, R-51 (hallazgos del legacy), R-09, R-44.
**Tareas:** 1) contrato `LanguageAdapter` + schemas; 2) adaptador COBOL; 3) adaptador genérico y mecanismo de validación cruzada AST↔LLM; 4) grafo (networkx) + métricas; 5) clasificador de lógica; 6) mapa de riesgo; 7) reglas de seguridad sobre legacy; 8) vistas UI (grafo, tabla de rutinas, riesgos); 9) agente Analista (resúmenes por unidad con Haiku).
**Entregables:** inventario, grafo y mapa de riesgo del golden visibles en la UI y exportables en JSON.
**Dependencias:** F1. **Riesgos:** lenguaje desconocido el día de la demo → el adaptador genérico debe degradar con gracia y avisar de menor rigor.

| ID | Criterio | Req. | Comprobación | Umbral |
|---|---|---|---|---|
| AC-F2-01 | 100 % de rutinas/párrafos/procedimientos y dependencias del golden inventariados | R-11, R-07 | check: `golden_metric(inventory_recall)` | 100 % |
| AC-F2-02 | Grafo de dependencias coincide con el grafo de referencia del golden | R-07 | check: `graph_diff` | precisión/recall ≥ 95 % |
| AC-F2-03 | Métricas (LOC, CC) coinciden con referencia; código muerto detectado | R-08 | check: `metrics_ref` | CC exacta; muerto ≥ 90 % |
| AC-F2-04 | Puntos de entrada identificados | R-07 | check: `golden_metric(entry_points)` | 100 % |
| AC-F2-05 | Clasificación negocio/infraestructura | R-09 | check: `golden_metric(logic_classification)` | ≥ 85 % |
| AC-F2-06 | Adaptador genérico procesa un lenguaje sin soporte determinista (PL/SQL/RPG/Java del golden) y marca el nivel de rigor | R-02, R-50 | check: `adapter_generic` | produce unidades válidas JSON-Schema |
| AC-F2-07 | Mapa de riesgo generado y válido contra esquema | R-10 | check: `json_schema` | válido |
| AC-F2-08 | Plugins: un adaptador de prueba se registra sin tocar el núcleo | R-50 | check: `plugin_contract` | pasa |
| AC-F2-09 | Cobertura y linters | R-31 | check: `coverage` | ≥ 80 / 70 % |
| AC-F2-SEC-01 | SQL dinámico concatenado / EXEC SQL inseguro en el golden detectado como hallazgo | R-51 | check: `legacy_sqli_findings` | recall 100 % en muestras etiquetadas |
| AC-F2-SEC-02 | Parsers resistentes a entradas hostiles (fuzz corto, recursión, archivos enormes) sin caída ni consumo ilimitado | R-51 | check: `parser_fuzz` | 0 caídas; límite de tiempo/memoria |

---

## Fase 3 — Extracción de reglas y validación humana (L, 4–5 sesiones)

**Objetivo:** catálogo de reglas formal, trazable, con confianza, revisado y aprobado por humanos. Incluye una **mini-pasada end-to-end sin pulir hasta F4** para detectar problemas de generalización cuanto antes.
**Entra:** agente Extractor (Opus para complejidad, Sonnet por defecto), chunking semántico, esquema `business_rule.schema.json` (ID, descripción de negocio, condiciones, acciones, datos, `source_refs`, confianza, supuestos, estado), salidas en tabla de decisión y Gherkin, **verificador anti-alucinación** (cada cita existe y cubre lo descrito), segundo pasaje sobre baja confianza, UI de revisión lado a lado (aprobar/ajustar/rechazar + comentario), catálogo versionado, orquestador con punto HITL, registro de prompts, defensa de prompt injection.
**No entra:** generación de código.
**Requerimientos:** R-12–R-17, R-41 (parcial), R-45, R-48, R-49, R-51.
**Tareas:** 1) esquemas y plantillas de prompt versionadas; 2) orquestador (máquina de estados, gates, HITL); 3) Extractor con chunking y contexto jerárquico; 4) verificadores; 5) generación de tablas de decisión y Gherkin; 6) UI de revisión; 7) versionado del catálogo; 8) mini-pasada end-to-end sobre el golden; 9) suite de prompt injection.
**Entregables:** catálogo aprobado y versionado del golden, exportable (JSON/MD/Gherkin).
**Dependencias:** F2. **Riesgos:** alucinación de reglas; costo de tokens; variabilidad entre ejecuciones.

| ID | Criterio | Req. | Comprobación | Umbral |
|---|---|---|---|---|
| AC-F3-01 | Todas las reglas validan contra JSON Schema | R-12, R-13 | check: `json_schema` | 100 % |
| AC-F3-02 | Trazabilidad: toda regla cita líneas que existen y contienen los elementos descritos | R-14 | check: `rule_traceability` | 100 % |
| AC-F3-03 | Recall/precisión de reglas frente a reglas de referencia del golden | R-12 | check: `golden_metric(rule_f1)` | recall ≥ 90 %, precisión ≥ 85 % (modo con grabaciones, determinista) |
| AC-F3-04 | Toda regla tiene confianza y supuestos; las de baja confianza están marcadas para revisión | R-15 | check: `rule_fields` | 100 % |
| AC-F3-05 | Revisión: aprobar/ajustar/rechazar persistido con comentario y revisor | R-16 | check: `e2e_api` | funciona |
| AC-F3-06 | No se puede avanzar a F4 sin aprobación explícita registrada | R-16, R-41 | check: `gate_blocks` | bloquea |
| AC-F3-07 | Catálogo versionado; cada cambio genera nueva versión inmutable | R-17 | check: `catalog_versioning` | válido |
| AC-F3-08 | Reproducibilidad: dos ejecuciones sobre el mismo golden producen catálogos equivalentes | R-48 | check: `reproducibility` | ≥ 90 % de reglas coinciden |
| AC-F3-09 | Gherkin y tablas de decisión generados y parseables | R-13 | check: `gherkin_parse` | 100 % |
| AC-F3-10 | Mini-pasada end-to-end sobre el golden ejecuta hasta código generado (sin pulir) | R-41 | check: `e2e_smoke` | completa |
| AC-F3-SEC-01 | Prompt injection: comentarios maliciosos en el golden no alteran el esquema de salida, no filtran el prompt de sistema ni ejecutan herramientas | R-51 | check: `prompt_injection_suite` | 0 éxitos de ataque |
| AC-F3-SEC-02 | Ningún prompt registrado contiene secretos; solo hashes y referencias | R-04, R-45 | check: `prompt_log_audit` | 0 fugas |
| AC-F3-SEC-03 | El egreso a red solo va al endpoint del proveedor (test con captura) | R-04 | check: `egress_allowlist` | 100 % |

---

## Fase 4 — Diseño y transformación al stack destino (XL, 6–8 sesiones)

**Objetivo:** del catálogo aprobado a código moderno compilable, con arquitectura limpia validada y autocorrección.
**Entra:** agentes Arquitecto (modelo DDD, puertos/adaptadores, patrones, OpenAPI, ADRs) y Desarrollador; `TargetGenerator` Java 21 + Spring Boot 3 (primero) y TypeScript/NestJS (después); mapeo PIC/COMP-3 → `BigDecimal`/decimal con escala y modo de redondeo; reestructuración de GO TO; RAG de estándares/patrones/mapeos de tipos; sandbox; ciclo de autocorrección acotado (máx. N iteraciones, escalado a humano); guardrails (ver `03`).
**No entra:** pruebas completas (F5).
**Requerimientos:** R-18–R-26, R-31, R-41–R-43, R-51.
**Tareas:** 1) sandbox de ejecución sin red; 2) plantillas y guardrails Java (ArchUnit, Checkstyle, SpotBugs) y TS (dependency-cruiser, eslint); 3) agente Arquitecto + modelo de dominio + OpenAPI; 4) agente Desarrollador y bucle de autocorrección; 5) RAG; 6) UI de vista comparativa legacy vs. moderno con trazabilidad regla↔método; 7) destino TypeScript.
**Entregables:** proyecto Java (y TS) compilable con ADRs, OpenAPI y reporte de guardrails.
**Dependencias:** F3. **Riesgos:** calidad del código generado; bucle de autocorrección que no converge; costo.

| ID | Criterio | Req. | Comprobación | Umbral |
|---|---|---|---|---|
| AC-F4-01 | El código generado compila (Java/TS) en el sandbox | R-26 | check: `sandbox_build` | éxito |
| AC-F4-02 | ArchUnit/dependency-cruiser: 0 violaciones de la regla de dependencias; sin lógica de negocio en controladores/repositorios | R-24, R-18 | check: `arch_rules` | 0 violaciones |
| AC-F4-03 | Complejidad ciclomática por método | R-26 | check: `cyclomatic` | ≤ 10 |
| AC-F4-04 | Linters/análisis estático | R-31 | check: `lint_generated` | 0 bloqueantes/críticos |
| AC-F4-05 | Mapeo numérico: PIC/COMP-3 → tipos decimales con escala; sin `double`/`float` en cálculos financieros | R-23 | check: `no_float_money` | 0 usos |
| AC-F4-06 | Sin GO TO/saltos obsoletos en código generado | R-23 | check: `no_goto` | 0 |
| AC-F4-07 | OpenAPI válido (lint) y modelo de dominio presente | R-18, R-19 | check: `openapi_lint` | válido |
| AC-F4-08 | ADRs generados en formato correcto | R-20 | check: `adr_format` | ≥ 1 por decisión |
| AC-F4-09 | Cada método de dominio referencia reglas (`@Rule("R-xx")` o comentario) y cada regla aprobada se implementa | R-14, R-21 | check: `rule_to_code_trace` | 100 % |
| AC-F4-10 | Autocorrección converge o escala a humano en ≤ N iteraciones | R-25 | check: `autofix_loop` | ≤ N |
| AC-F4-11 | Segundo destino TypeScript pasa los mismos gates | R-22 | check: `sandbox_build_ts` | éxito |
| AC-F4-SEC-01 | SAST sobre código generado (Semgrep, FindSecBugs, npm audit): 0 críticas; sin SQL concatenado, secretos ni path traversal | R-31, R-51 | check: `sast_generated` | 0 |
| AC-F4-SEC-02 | Sandbox: sin red, usuario sin privilegios, límites de recursos (test de escape básico) | R-43, R-51 | check: `sandbox_isolation` | pasa |
| AC-F4-SEC-03 | Consultas del código generado parametrizadas (prueba de inyección sobre el servicio generado) | R-51 | check: `generated_sqli` | 0 explotables |

---

## Fase 5 — Pruebas unitarias y de equivalencia (XL, 5–6 sesiones)

**Objetivo:** demostrar que el código moderno se comporta igual que el legacy.
**Entra:** agente QA; pruebas unitarias por regla (JUnit 5/Mockito, Jest/Vitest) con aserciones y datos realistas; escenarios BDD ejecutables; **pruebas de caracterización/golden master** y **diferenciales**; generador de casos borde (redondeos, COMP-3, signos, truncamientos, fechas); **oráculo legacy** (GnuCOBOL en sandbox para COBOL; en otros lenguajes, casos esperados aportados + oráculo derivado de reglas aprobadas con marca explícita de nivel de evidencia; ver P-01); cobertura JaCoCo/Istanbul; mutation testing opcional (PIT/Stryker); reporte de equivalencia.
**Requerimientos:** R-27–R-32, R-35, R-29, R-48.
**Tareas:** 1) infraestructura del oráculo; 2) generador de casos y casos borde; 3) agente QA; 4) runner diferencial y comparador (con tolerancia 0 en decimales); 5) cobertura y umbrales; 6) mutation (opcional); 7) reporte de equivalencia en UI.
**Entregables:** `equivalence_report.json/md`, cobertura y suite ejecutable en vivo.
**Dependencias:** F4. **Riesgos:** sin oráculo ejecutable del legacy; pruebas triviales; casos borde incompletos.

| ID | Criterio | Req. | Comprobación | Umbral |
|---|---|---|---|---|
| AC-F5-01 | Equivalencia legacy vs. moderno sobre el golden | R-27, R-28 | check: `equivalence_report` | 100 % de casos aprobados |
| AC-F5-02 | Diferencias en cálculos y redondeos | R-28 | check: `equivalence_report` | 0 |
| AC-F5-03 | Cobertura generada | R-30 | check: `coverage_generated` | ≥ 80 % líneas / ≥ 70 % ramas |
| AC-F5-04 | Pruebas no triviales: toda prueba tiene ≥ 1 aserción explícita; ninguna vacía; datos del dominio | R-29 | check: `test_quality_lint` | 100 % |
| AC-F5-05 | Cada regla aprobada tiene ≥ 1 prueba unitaria y ≥ 1 escenario BDD | R-29, R-34 | check: `rule_to_test_trace` | 100 % |
| AC-F5-06 | Casos borde presentes: redondeo, COMP-3, signos, truncamiento, fechas | R-27 | check: `edge_cases_present` | todas las categorías aplicables |
| AC-F5-07 | Nivel de evidencia del oráculo registrado en el reporte (ejecutado / aportado / derivado) y nunca presentado como "ejecutado" si no lo fue | R-28 | check: `oracle_evidence` | correcto |
| AC-F5-08 | Mutation score (opcional) | R-32 | check: `mutation` | ≥ 60 % o `SKIP` justificado |
| AC-F5-SEC-01 | SAST y escaneo de dependencias del proyecto generado | R-31, R-51 | check: `sast_generated`, `deps_audit` | 0 críticas |
| AC-F5-SEC-02 | Los datos de prueba son sintéticos (sin patrones de PII real) | R-46 | check: `synthetic_data_only` | 0 hallazgos |

---

## Fase 6 — Documentación, trazabilidad, empaquetado y demo (L, 5–6 sesiones)

**Objetivo:** entregable completo con calidad de demo: paquete, informe, tablero, demo de 10 min y hardening previo.
**Entra:** agente Documentador (as-is/to-be, Mermaid C4/secuencia/dependencias, catálogo, diccionario de datos, mapeo legacy→nuevo, ADRs); **matriz de trazabilidad extremo a extremo** (línea → regla → código → prueba → documento) y verificación automática de integridad; informe ejecutivo de una página; tablero (reglas, equivalencia, cobertura, hallazgos, tiempo, costo); comparación cuantificada vs. manual (supuestos explícitos y parametrizables); empaquetador (repo, contenedor, README, reportes) con `docker compose up`; modo pregrabado (ejecución grabada reproducible sin API); guion de demo; **hardening de seguridad** (ZAP baseline, cabeceras, borrado de proyecto); ensayo con un lenguaje legacy no visto.
**Requerimientos:** R-20, R-33–R-40, R-44, R-45, R-48, R-51.
**Tareas:** 1) Documentador; 2) matriz de trazabilidad + verificador; 3) informe ejecutivo y comparación; 4) tablero; 5) paquete y Compose único; 6) grabación/reproducción de contingencia; 7) hardening (ZAP, cabeceras, CSP, rate limit, CSRF); 8) guion y ensayo; 9) prueba con usuario no involucrado (checklist firmado).
**Entregables:** paquete de migración completo, informe ejecutivo, guion de demo.
**Dependencias:** F5. **Riesgos:** tiempo; fallas de conectividad en demo; lenguaje inesperado.

| ID | Criterio | Req. | Comprobación | Umbral |
|---|---|---|---|---|
| AC-F6-01 | Paquete contiene: código, pruebas, docs, reportes, informe, Docker, README | R-33, R-37 | check: `package_manifest` | 100 % |
| AC-F6-02 | `docker compose up` ejecuta el flujo completo sobre el golden en un solo comando | R-37 | check: `one_command_e2e` | éxito |
| AC-F6-03 | Diagramas Mermaid válidos (render/parse) y documentación sin enlaces rotos | R-33 | check: `mermaid_lint`, `links` | 0 errores |
| AC-F6-04 | Matriz de trazabilidad completa: toda regla aprobada enlaza línea, código, prueba y documento | R-34, R-14 | check: `trace_matrix` | 100 % sin huérfanos |
| AC-F6-05 | Informe ejecutivo de una página generado (PDF/MD) con métricas reales | R-36 | check: `exec_report` | ≤ 1 página, campos presentes |
| AC-F6-06 | Comparación vs. manual con supuestos explícitos | R-40 | check: `comparison_report` | presente y válida |
| AC-F6-07 | Tablero muestra reglas, equivalencia, cobertura, hallazgos, tiempo, costo | R-35, R-39, R-45 | check: `dashboard_smoke` | todos los campos |
| AC-F6-08 | Modo pregrabado funciona sin red ni API | R-38 | check: `offline_replay` | éxito |
| AC-F6-09 | Tiempo total del flujo sobre el golden | R-39 | check: `timing` | ≤ 10 min |
| AC-F6-10 | Flujo completo con un lenguaje legacy no usado en desarrollo (muestra reservada) | R-02 | check: `unseen_language_e2e` | completa; equivalencia reportada con evidencia |
| AC-F6-11 | Checklist de usabilidad con usuario externo firmado | R-44 | check: `manual_evidence` | `MANUAL-VERIFICADO` |
| AC-F6-12 | Regresión de F0–F5 | todos | `run_acceptance --todas` | 100 % |
| AC-F6-SEC-01 | ZAP baseline contra la app levantada | R-51 | check: `zap_baseline` | 0 altos/críticos |
| AC-F6-SEC-02 | Cabeceras de seguridad (CSP, HSTS, X-Content-Type-Options, X-Frame-Options), CORS restrictivo, cookies seguras | R-51 | check: `security_headers` | todas |
| AC-F6-SEC-03 | Prueba XSS: contenido legacy hostil renderizado sin ejecución de script | R-51 | check: `xss_suite` | 0 |
| AC-F6-SEC-04 | Borrado de proyecto elimina artefactos y mapa de enmascarado (verificado) | R-51 | check: `purge_project` | 100 % |
| AC-F6-SEC-05 | Escaneo final de imágenes (Trivy), secretos y SBOM | R-51 | check: `trivy`, `gitleaks` | 0 críticas |

---

## Hoja de ruta (fuera del MVP)

**F7 — Extensión de lenguajes y destinos (L):** adaptadores deterministas PL/SQL, RPG/RPGLE, Java antiguo (EJB 2.x, Struts, JSP); destino C#. Req.: R-02, R-22, R-52. AC: recall de inventario y grafo por lenguaje ≥ 95 % sobre su golden; equivalencia 100 % por lenguaje piloto; regresión F0–F6.
**F8 — Seguridad avanzada, cumplimiento y producción (XL):** RBAC completo, auditoría inmutable (WORM), cifrado con KMS, Bedrock/Vertex, retención/borrado, observabilidad (OpenTelemetry, dashboards), Batch API, escalado a repos de millones de líneas, pentest externo. Req.: R-45, R-49, R-53. AC: pruebas de carga, 0 críticas en pentest, rotación de claves verificada.
**F9 — Piloto con código real (L):** evaluación de precisión de reglas y equivalencia con código real bajo acuerdo de confidencialidad, métricas y ajustes. Req.: R-54. AC: precisión de reglas y equivalencia sobre el piloto según umbrales acordados con el cliente.
