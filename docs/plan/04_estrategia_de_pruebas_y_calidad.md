# 04 — Estrategia de pruebas y calidad

## 1. Pruebas de la propia app

| Nivel | Herramientas | Qué cubre |
|---|---|---|
| Unitarias | pytest, Vitest | Detectores, enmascarador, adaptadores, verificadores, orquestador |
| Integración | pytest + Postgres en contenedor | API, cola, auditoría, versionado de catálogo |
| Contrato | JSON Schema, OpenAPI (schemathesis) | Salidas de agentes y API |
| E2E | Playwright | Flujo guiado de la UI sobre el golden |
| Seguridad | suites propias + Semgrep/Bandit/ZAP | Ver `07` |
| Propiedades/fuzz | hypothesis | Parsers, detección de codificación, mapeo COMP-3 |
| Rendimiento | locust (humo) | Tiempo de flujo ≤ 10 min en el golden |

**Pruebas con LLM:** dos modos. (1) **Grabado/replay** (determinista, por defecto en CI): respuestas del modelo grabadas (cassettes) con hash del prompt; (2) **en vivo** (manual o nocturno, requiere API): mide calidad real. Los criterios de aceptación usan replay para ser reproducibles; las métricas en vivo se publican aparte y con tolerancia.

## 2. Pruebas del código generado

- **Unitarias por regla** (JUnit 5/Mockito; Jest/Vitest) con aserciones explícitas y datos del dominio.
- **BDD** (Cucumber/jest-cucumber) desde los Gherkin del catálogo aprobado.
- **Caracterización/golden master:** entradas → salidas del legacy como referencia.
- **Diferenciales:** mismas entradas sobre legacy y moderno; comparación exacta de decimales y mensajes.
- **Casos borde obligatorios** (cuando aplican): redondeo (mitad hacia arriba/par), COMP-3 y signos, truncamientos por PIC, desbordamiento (SIZE ERROR), fechas (bisiestos, fin de mes), valores cero/negativos, tasas límite, entradas vacías.
- **Mutation testing** opcional (PIT/Stryker).
- **Calidad de las pruebas:** lint que rechaza pruebas sin aserciones, sin datos o con valores triviales.

## 3. Oráculo de equivalencia (decisión clave)

| Nivel de evidencia | Cuándo | Cómo |
|---|---|---|
| **E1 Ejecutado** | COBOL (GnuCOBOL en sandbox) u otro lenguaje con runtime disponible | Se compila y ejecuta el legacy con las entradas |
| **E2 Aportado** | Los organizadores o el cliente entregan entradas/salidas esperadas | Se importan como golden master |
| **E3 Derivado** | Sin runtime ni casos | Casos esperados calculados por una implementación independiente a partir de las reglas aprobadas por humanos |

El reporte declara el nivel de evidencia por caso; E3 nunca se presenta como E1 (AC-F5-07). Ver P-01 en `05`.

## 4. Golden dataset

`golden/<caso>/` con: `source/` (legacy sintético), `manifest.json` (lenguaje, dialecto, codificación, líneas, hash), `expected/` (inventario, grafo, métricas, reglas de referencia con líneas, clasificación), `cases.csv` (entradas/salidas esperadas, incluidos casos borde), `findings.json` (hallazgos de seguridad esperados), `masks.json` (secretos sintéticos y su enmascarado esperado).

Muestras iniciales (todas sintéticas):
1. `cobol_amortizacion_francesa` (COBOL con copybook, COMP-3, ROUNDED, PERFORM, EBCDIC variante).
2. `plsql_liquidacion_siniestro` (paquete PL/SQL con SQL dinámico inseguro etiquetado).
3. `rpg_tarifacion` o `java_ejb_poliza` (según disponibilidad).
4. `adversarial/` : prompt injection en comentarios, ZIP-slip, ZIP-bomb pequeño, nombres maliciosos, secretos sintéticos, EBCDIC corrupto.
5. `reserved_unseen/` : lenguaje no usado en desarrollo para el ensayo final (AC-F6-10).

Métricas de calidad de IA (sobre el golden):
- **Recall y precisión de reglas** frente a las de referencia (emparejamiento por solapamiento de líneas y semántica).
- **% de reglas con trazabilidad válida** (objetivo 100 %).
- **Tasa de alucinación** (citas inexistentes) objetivo 0 tras verificador.
- **Equivalencia funcional** (objetivo 100 %) y diferencias numéricas (objetivo 0).
- **Consistencia entre ejecuciones**, **costo y tokens por etapa**, **tasa de convergencia de autocorrección**.

## 5. Calidad y puertas

Umbrales del Word: equivalencia 100 %, cobertura ≥ 80 % líneas / ≥ 70 % ramas, 0 hallazgos críticos, CC ≤ 10, 0 vulnerabilidades críticas y 0 secretos, trazabilidad 100 %. Se verifican en los scripts de aceptación (`06`). SonarQube opcional en CI; el reporte de aceptación incluye el resumen del análisis.


---

## Actualización (estado real)

- **Suite:** 57 pruebas pytest (`tests/test_units.py`, `test_security.py`, `test_e2e.py`, `test_local_engine.py`, `test_modes.py`). Proveedores: `fake_llm.py` (respuestas escritas a mano **solo para pruebas**, no es salida de un modelo), motor local, `claude-code` (en pruebas, con el CLI simulado) y cassettes.
- **Modo grabado/replay:** implementado en `copilot/llm.py` (`COPILOT_CASSETTES`); el criterio `AC-F6-02` lo valida con una cassette sintética. Los modos `claude-code` y `live` graban cassettes; la corrida real con `claude-code` sobre la muestra COBOL graba cassettes de un modelo real (confirmar su presencia en `cassettes/` antes de la demo).
- **`tests/test_modes.py` (5 pruebas, AC-F7-11):** invocación aislada y sin clave del CLI (`--tools ""`, `--no-session-persistence`, prompt por stdin, cwd temporal, sin `ANTHROPIC_API_KEY`), errores reportados, cassette y costo 0, `POST /api/mode`, y `auto` nunca elige `claude-code`.
- **Corrida real con Claude vía suscripción (manual, una sola vez):** muestra COBOL con casos aportados, 346 s; 14 reglas con cita verificada; 65/65 casos (E2+E3), 0 diferencias; cobertura 98,43 % líneas / 94,79 % ramas; complejidad máxima 3; 0 hallazgos; 0 autocorrecciones. No es una prueba automática (depende de la sesión de Claude Code); los LLM varían entre corridas.
- **Oráculo y evidencia:** E2 = `golden/cobol_amortizacion/cases.json` (25 casos generados desde `reference.py`, escrito a mano e independiente de los transpiladores); E3 = segundo traductor (`PyGen`) en modo local, o oráculo del LLM en modo `live`. E1 (legacy ejecutado) no existe.
- **Pruebas clave del motor local:** `test_python_backend_matches_hand_written_reference` (oráculo derivado == referencia a mano en 25 casos) y `test_local_full_flow_without_api_key` (equivalencia 100 %, ≥ 40 casos, 25 E2, cobertura ≥ 80/70, CC ≤ 10, trazabilidad 100 %, costo 0, procedencia `local`).
- **Resultado medido en una corrida de referencia** (muestra COBOL, modo local, con casos aportados): 67/67 casos, 0 diferencias, cobertura 93,67 % líneas / 83,33 % ramas, complejidad máxima 10, 0 hallazgos bloqueantes. Son cifras de una corrida; las pruebas imponen solo los umbrales.
- **Cobertura:** `node --test --experimental-test-coverage` corre sin `--permission` (incompatible), solo tras pasar la ejecución restringida y el escaneo estático, con entorno vacío.
- **No cubierto:** pruebas de la UI en navegador (solo comprobación estática de sumideros peligrosos y capturas manuales), pruebas del modo `live` contra la API real, Ollama real, `claude-code` con lenguajes distintos de COBOL (PL/SQL, RPG, Java) y con Java/C# como destino, mutation testing, usuario externo.
