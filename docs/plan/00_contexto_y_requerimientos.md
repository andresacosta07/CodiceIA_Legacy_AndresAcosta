# 00 — Contexto y requerimientos

Fuentes leídas: `docs/RetoHackathon_ Modernización_Descubrimiento_CódigoLegacy.docx` (texto en `_requerimiento_extraido.md`), `docs/Diagrama Conceptual de referencia.jpg`, `PROMPT_PLAN_Modernizacion_Legacy.md`. No existen README, `CLAUDE.md` ni código previo.

## 1. Resumen de lo entendido

El reto pide un **prototipo funcional con calidad de demo para cliente** del sector financiero/asegurador: el **Copiloto de Modernización y Descubrimiento de Código Legacy**. Ingiere código legacy (COBOL, PL/SQL, RPG, Java antiguo), descubre y formaliza reglas de negocio con trazabilidad, las somete a validación humana, genera código moderno (Java 21/Spring Boot 3, Node/TypeScript; C# mencionado), pruebas, documentación y un paquete reproducible con un solo comando.

El Word define un flujo de **8 fases con quality gates**, una arquitectura por capas con **orquestación multiagente** (Analista, Extractor, Arquitecto, Desarrollador, QA, Documentador), capa de análisis estático, RAG, sandbox de verificación y gobierno/observabilidad. La evaluación prioriza evidencia verificable: equivalencia funcional (25 %), extracción de reglas (15 %), arquitectura (15 %), calidad de código (15 %), seguridad e IA responsable (10 %), entregables (10 %), UX/demo (10 %) y criterios de visión de negocio (funcional, interactivo, innovador).

**Decisiones del usuario:** alcance demo-first (F0–F6 = MVP; F7–F9 = hoja de ruta); app en Python + FastAPI + React/TS; el código legacy de la demo lo proveen los organizadores y puede ser de **cualquier lenguaje**, por lo que el diseño es agnóstico al lenguaje; seguridad y no filtración del código como eje transversal (incluye inyección SQL y ataques a la app).

**Condiciones habilitantes del Word que se tratan como bloqueantes:** flujo completo ejecutado en la demo; sin equivalencia demostrada los criterios 3–7 se limitan a 3/5; datos reales o secretos = descalificación.

## 2. Capacidades

C1–C8 del prompt (ingesta, descubrimiento, reglas, traducción, guardrails, documentación, pruebas, validación humana/trazabilidad) más las derivadas del Word:
C9 diseño de arquitectura destino (DDD, OpenAPI, Strangler Fig) · C10 ciclo de autocorrección · C11 informe ejecutivo y comparación cuantificada · C12 empaquetado de un solo comando y modo pregrabado · C13 SAST y dependencias vulnerables · C14 mutation testing (opcional) · C15 seguridad transversal (ver `07`).

## 3. Matriz de requerimientos

Prioridad MoSCoW: M=Must, S=Should, C=Could, W=Won't (ahora). Tipo: F=funcional, NF=no funcional. "Fase" = fase de construcción (`02`).

| ID | Descripción | Fuente (Word) | MoSCoW | Tipo | Cap. | Fase |
|---|---|---|---|---|---|---|
| R-01 | Ingesta por interfaz (portal web) de fragmentos/rutinas/repos: archivo, pegado, ZIP, Git | 3.1 | M | F | C1 | F1 |
| R-02 | Tipos de entrada: COBOL, PL/SQL, RPG, Java legado (cualquier lenguaje legacy) | 3.1 | M | F | C1 | F1, F2 (COBOL+genérico), F7 |
| R-03 | Parámetros opcionales: stack destino, dominio funcional, estilo de arquitectura | 3.1 | S | F | C1/C4 | F1 |
| R-04 | Detección y enmascaramiento de secretos, credenciales, cadenas de conexión y PII antes de enviar a modelos | 3.1, 4 | M | F/NF | C15 | F1 |
| R-05 | Normalización: lenguaje/dialecto, copybooks/includes, EBCDIC/ASCII, completitud | 3.1 | M | F | C1 | F1 |
| R-06 | AST/representación intermedia para análisis determinista | 3.2, 2.3 | M | F | C2 | F2 |
| R-07 | Grafo de dependencias y flujo de control (rutinas, tablas, archivos, cursores, puntos de entrada) | 3.2 | M | F | C2 | F2 |
| R-08 | Métricas: LOC, complejidad ciclomática, código muerto, duplicidades | 3.2 | M | F | C2 | F2 |
| R-09 | Clasificación lógica de negocio vs. infraestructura legacy | 3.2, 2.2 | M | F | C2/C3 | F2, F3 |
| R-10 | Mapa de riesgo de migración (complejidad, criticidad, acoplamiento) | 3.2 | S | F | C2 | F2 |
| R-11 | Quality gate F-flujo 2: 100 % rutinas y dependencias inventariadas | 3 | M | NF | C2 | F2 |
| R-12 | Extracción de reglas (variables, condiciones, matrices de decisión, fórmulas) | 3.3 | M | F | C3 | F3 |
| R-13 | Formalización: condición/acción, tablas de decisión, Gherkin (DMN opcional) | 3.3, prompt C3 | M | F | C3 | F3 |
| R-14 | Trazabilidad de cada regla a líneas exactas de origen (100 %) | 3.3, 3.7 | M | NF | C3/C8 | F3 |
| R-15 | Nivel de confianza por regla; supuestos y ambigüedades explícitos | 3.3, 2.4 | M | F | C3 | F3 |
| R-16 | Validación humana: vista lado a lado, aprobar/ajustar/rechazar con comentarios | 3.4, 4 | M | F | C8 | F3 |
| R-17 | Catálogo aprobado y versionado como especificación (Spec-Driven) | 3.4, 3.9 | M | F | C8 | F3 |
| R-18 | Diseño destino: modelo DDD, puertos/adaptadores, patrones (Strategy/Factory/Specification) | 3.5 | M | F | C9 | F4 |
| R-19 | Contratos OpenAPI y estrategia Strangler Fig | 3.5 | S | F | C9 | F4 |
| R-20 | ADRs de decisiones de diseño del código generado | 3.5, 3.8 | M | F | C6/C9 | F4, F6 |
| R-21 | Traducción a Java 21 + Spring Boot 3 desde reglas aprobadas | 3.6, 1 | M | F | C4 | F4 |
| R-22 | Traducción a Node.js/TypeScript (segundo destino); C# opcional | 3.1, 3.6 | S | F | C4 | F4 (TS), F7 (C#) |
| R-23 | Eliminar GO TO/flujo obsoleto; precisión numérica PIC/COMP-3 → decimal exacto con escala y redondeo | 3.6, 4 | M | F | C4/C7 | F4 |
| R-24 | Guardrails: Clean Code, SOLID, excepciones canónicas, tipado fuerte, desacoplamiento | 3.6, 2.4 | M | F | C5 | F4 |
| R-25 | Ciclo de autocorrección (compilar, analizar, corregir) | 3.6 | M | F | C10 | F4 |
| R-26 | Compilación exitosa, 0 hallazgos críticos; complejidad ciclomática ≤ 10 por método | 3.7 | M | NF | C5 | F4 |
| R-27 | Pruebas de caracterización (golden master) y diferenciales legacy vs. moderno | 3.7 | M | F | C7 | F5 |
| R-28 | Equivalencia: 100 % casos aprobados, 0 diferencias en cálculos/redondeos | 3.7, 5 | M | NF | C7 | F5 |
| R-29 | Pruebas unitarias JUnit5/Mockito/Jest no triviales, con aserciones y datos realistas; BDD desde reglas | 3.7, 4 | M | F | C7 | F5 |
| R-30 | Cobertura ≥ 80 % líneas y ≥ 70 % ramas | 3.7 | M | NF | C7 | F5 |
| R-31 | Análisis estático y SAST (SonarQube o equivalente), dependencias vulnerables | 3.7 | M | NF | C13 | F0, F4, F5 |
| R-32 | Mutation testing (PIT/Stryker) | 3.7 | C | NF | C14 | F5 (opcional) |
| R-33 | Documentación técnica y funcional: catálogo, matriz de trazabilidad línea→método, supuestos, diagramas, ADRs | 3.8 | M | F | C6 | F6 |
| R-34 | Trazabilidad extremo a extremo: línea legacy → regla → código → prueba → documento | prompt C8, 3.8 | M | F | C8 | F6 |
| R-35 | Reportes de verificación (equivalencia, cobertura, calidad y seguridad) | 3.8 | M | F | C11 | F5, F6 |
| R-36 | Informe ejecutivo de una página con ahorro estimado | 2.5, 3.8 | M | F | C11 | F6 |
| R-37 | Empaquetado: repositorio, contenedor y README; ejecución con un solo comando | 2.5, 3.8 | M | NF | C12 | F6 |
| R-38 | Plan de contingencia (ejecución pregrabada) ante fallas de conectividad | 2.5 | M | NF | C12 | F6 |
| R-39 | Demo ≤ 10 min con guion, ejecución en vivo y tablero de resultados | 2.5, 5 | M | F | C12 | F6 |
| R-40 | Comparación cuantificada vs. proceso manual (tiempo/esfuerzo/calidad) | 5 (Innovador) | M | F | C11 | F6 |
| R-41 | Orquestación multiagente con estado y puntos de aprobación humana (6 agentes) | 2.3 | M | F | C9 | F3–F6 |
| R-42 | Capa RAG: estándares, patrones, glosario banca/seguros, mapeos de tipos | 2.3 | S | F | C4 | F4 |
| R-43 | Sandbox de verificación aislado (compilar, probar, comparar) | 2.3 | M | NF | C13 | F4 |
| R-44 | UI: flujo guiado, vista comparativa legacy vs. moderno, progreso por fase, errores con acción sugerida | 2.3, 5 | M | F | — | F1–F6 |
| R-45 | Observabilidad: registro de prompts y decisiones, versiones, tokens/costo/tiempo por ejecución | 2.3 | M | NF | C15 | F1 (base), F6, F8 |
| R-46 | Solo datos sintéticos; sin secretos ni datos reales (descalificatorio) | 4, 5 | M | NF | C15 | F0 en adelante |
| R-47 | Manejo controlado de entrada inválida sin pérdida ni exposición de datos | 5 (Funcional) | M | NF | C15 | F1 |
| R-48 | Reproducibilidad y resultados consistentes entre ejecuciones | 2.4 | M | NF | — | F3, F6 |
| R-49 | Escalabilidad: unidades de análisis y gestión de ventana de contexto | prompt §4 | S | NF | C2/C3 | F2, F3 |
| R-50 | Extensibilidad por plugins (parsers y generadores) | prompt §4 | M | NF | — | F0, F2 |
| R-51 | Seguridad de la app: SQLi, XSS, uploads, SSRF, prompt injection, no filtración del código | pedido del usuario; 4, 5 | M | NF | C15 | F0–F6 (`07`) |
| R-52 | Hoja de ruta: PL/SQL, RPG, Java antiguo, C# | prompt §3, 3.1 | W | F | C1 | F7 |
| R-53 | Producción: RBAC completo, auditoría inmutable, Bedrock/Vertex, retención, Batch API | prompt §4 | W | NF | C15 | F8 |
| R-54 | Piloto con código real y métricas de precisión | prompt §3 | W | NF | — | F9 |

Todos los requerimientos tienen al menos una fase asignada (verificado en `06`).

## 4. Supuestos

| ID | Supuesto | Impacto si es falso |
|---|---|---|
| S-01 | El código de la demo vendrá de los organizadores, en cualquier lenguaje legacy | Si es un lenguaje sin soporte determinista, se depende del adaptador genérico LLM; baja el rigor del grafo |
| S-02 | Hay acceso a la API de Claude durante desarrollo y demo | Sin él, solo funciona el modo pregrabado |
| S-03 | Se puede ejecutar Docker en los equipos de desarrollo y demo | Sin Docker, no hay "un solo comando"; plan B con scripts locales |
| S-04 | Solo se usan datos sintéticos | Datos reales = descalificación |
| S-05 | Los IDs de modelo del prompt (`claude-haiku-5-5`, etc.) son vigentes | Se verifican al iniciar F0 y se parametrizan |
| S-06 | Portal web es suficiente como capa de experiencia (el Word admite portal, IDE o bot) | Si se exige IDE, cambia F1–F6 |
| S-07 | Para COBOL se puede usar GnuCOBOL como oráculo ejecutable | Para otros lenguajes el oráculo es distinto (ver `05`, P-01) |

## 5. Contradicciones Word vs. prompt (prevalece el Word)

1. Prototipo de demo (Word) vs. producto hasta producción (prompt) → alcance demo-first; F7–F9 en hoja de ruta.
2. Flujo de 8 fases del Word vs. 10 fases de construcción del prompt → las fases de construcción implementan las 8 del flujo (tabla en `02`).
3. El Word exige orquestación multiagente, RAG, sandbox y diseño de arquitectura destino; el prompt no los nombra → añadidos (R-18, R-41–R-43).
4. El prompt fija COBOL como piloto; el Word (y el usuario) dejan el lenguaje abierto → diseño agnóstico, COBOL como primer adaptador determinista.
5. El Word menciona C# como destino; el prompt solo Java/TS → C# como opcional en F7.
6. El Word exige informe ejecutivo, modo pregrabado y comparación vs. manual; el prompt no → añadidos (R-36, R-38, R-40).

## 6. Preguntas abiertas

Ver `05_riesgos_supuestos_preguntas.md` (priorizadas).


---

## Actualización de alcance (estado real)

**Decisiones del usuario posteriores al plan original**
- **Sin clave de API ni presupuesto para ella** (la suscripción Pro no incluye crédito de API): la solución debe funcionar con los recursos actuales, a costo 0.
- Para no quedar limitado, se pidió además poder usar un modelo de IA económico/local sin clave: se implementó como mejora **opcional** (Ollama, solo redacción).
- Entrega **hoy a las 2 pm**, equipo de **una persona**; el código legacy de la demo es **desconocido** (lo entregarán los organizadores).
- Se añadió la **rúbrica de Visión de Cliente y Negocio** (imagen del reto): Funcional 33,33 % · Interactivo y fácil de usar 33,33 % · Innovador 33,33 %, con la evidencia que cada una pide (flujo completo en vivo, caso representativo y borde, entrada inválida sin exponer datos; flujo guiado, vista legacy vs. moderno y un usuario externo sin ayuda; comparación cuantificada, elemento diferenciador y caso de negocio).
- Se pidió además poder usar **IA de Claude sin depender de la clave de API, como extensión adicional**: se implementó el modo `claude-code` (Claude vía la suscripción de Claude Code, `py run.py --claude` o selector «Motor de IA»; ADR-015). Una corrida real con la muestra COBOL (346 s): 14 reglas verificadas, 65/65 casos equivalentes, cobertura 98,43 % / 94,79 %.
- Se pidió mantener **toda la documentación y los entregables actualizados** ante cada cambio, un **manual de usuario** (arquitectura, tecnologías, técnico y no técnico) y un **guion de demo** que lo explique todo; también el **uso de subagentes** (durante el desarrollo, para documentación y revisión en paralelo).

**Supuestos nuevos**

| ID | Supuesto | Impacto si es falso |
|---|---|---|
| S-11 | No habrá clave de API durante el desarrollo ni (probablemente) en la demo | Con clave se activa el modo `live` (no probado en vivo) |
| S-12 | El código de la demo, si es COBOL de formato fijo dentro del subconjunto soportado, lo procesa el motor local; cualquier otro lenguaje o construcción falla con un mensaje claro | Sin IA no hay demo con otros lenguajes; con `claude-code` (si hay CLI `claude` con sesión) se intenta, sin haberse probado más que con COBOL |
| S-15 | El CLI `claude` está en el `PATH` con la sesión iniciada y dentro de los límites de la suscripción; el código enmascarado puede salir hacia Anthropic | Si no, el modo `claude-code` no está disponible (el selector lo deshabilita) y se usa `local` o `replay` |
| S-13 | La rúbrica de Visión de Cliente (3 × 33,33 %) se evalúa sobre lo mostrado en vivo y lo incluido en el paquete | Define el contenido de la fase 7 |
| S-14 | Un usuario no involucrado en el desarrollo completará la tarea sin ayuda (evidencia firmada en `evidence/AC-F6-MANUAL-01.json`) | Hoy el criterio está `MANUAL-PENDIENTE` |

**Requerimientos añadidos**

| ID | Descripción | Fuente | MoSCoW | Tipo | Fase | Estado |
|---|---|---|---|---|---|---|
| R-55 | Operar sin clave de API y a costo 0: motor local determinista (parser COBOL de subconjunto, reglas desde el AST, transpiladores TS y Python, casos por valores frontera) | Decisión del usuario | M | F/NF | F7 | Implementado (solo COBOL subconjunto y destino TypeScript); `local_engine.py`, `cobol.py`; pruebas `test_local_engine.py` |
| R-56 | Guía de usuario e in-app para personas no técnicas (tarjeta «qué hacer ahora» por paso, demostración de entradas inválidas, manual de usuario) | Rúbrica «Interactivo» | M | F | F7 | Ayuda in-app y demostración de entradas inválidas: implementado (`web/app.js`); manual: `docs/MANUAL_DE_USUARIO.md`; usuario externo: pendiente de evidencia |
| R-57 | Caso de negocio cuantificado interactivo (calculadora de ahorro por cartera de rutinas, supuestos parametrizables) y elemento diferenciador explícito | Rúbrica «Innovador» | M | F | F7 | Implementado (`businessCase`, «¿Qué nos diferencia?»; `config/estimates.json`) |
| R-58 | Extensión opcional con IA **sin clave de API**: Claude vía el CLI de Claude Code con la suscripción del usuario, aislado, explícito (nunca por `auto`) y con selector de motor en la UI | Decisión del usuario | S | F/NF | F7 | Implementado (`llm._claude_code`, `POST /api/mode`, `py run.py --claude`; ADR-015; `tests/test_modes.py`); una corrida real con COBOL; sin probar con otros lenguajes |

Nota: R-52..R-54 (PL/SQL/RPG/Java, producción, piloto real) siguen sin implementar.
