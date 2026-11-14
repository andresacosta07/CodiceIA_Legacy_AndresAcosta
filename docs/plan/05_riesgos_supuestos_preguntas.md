# 05 — Riesgos, supuestos y preguntas abiertas

## 1. Riesgos

| ID | Riesgo | Tipo | Prob. | Impacto | Mitigación |
|---|---|---|---|---|---|
| RK-01 | Lenguaje legacy desconocido en la demo sin parser determinista | Técnico | Alta | Alto | Adaptador genérico (tree-sitter + LLM con salida estructurada), plugins, ensayo con muestra reservada (AC-F6-10), degradación con aviso de rigor |
| RK-02 | Sin runtime del legacy → equivalencia no ejecutada | Técnico | Alta | Alto (condición habilitante del Word) | Niveles de evidencia E1/E2/E3 (`04`), GnuCOBOL, solicitar casos esperados a organizadores, transparencia en el reporte |
| RK-03 | Alucinación de reglas o citas inexistentes | IA | Media | Alto | Verificador determinista de líneas, segundo pasaje, HITL, confianza explícita |
| RK-04 | Fuga de código/secretos al LLM o a logs | Seguridad | Media | Crítico (descalificación) | Enmascarado antes de egreso, bloqueo si hay residuo, allowlist de egreso, logs con hash, datos solo sintéticos, AC-F1-SEC-01, AC-F3-SEC-03 |
| RK-05 | Prompt injection desde comentarios del legacy | Seguridad | Media | Alto | Delimitación como datos, esquema validado, sin herramientas con efectos laterales en extracción, suite de pruebas |
| RK-06 | Inyección SQL u otros ataques a la app | Seguridad | Media | Alto | Consultas parametrizadas, Pydantic, suites SQLi/XSS/SSRF/ZIP-slip, ZAP |
| RK-07 | Ejecución de código generado/subido compromete el host | Seguridad | Baja | Crítico | Sandbox efímero sin red, usuario sin privilegios, límites; nunca se ejecuta el código subido |
| RK-08 | Código generado no compila o no converge | Técnico | Media | Alto | Autocorrección acotada, plantillas por stack, RAG de patrones, escalado a humano |
| RK-09 | Imprecisión numérica (COMP-3, redondeo) | Técnico | Media | Alto | Tipos decimales, mapeo PIC explícito, casos borde obligatorios, tolerancia 0 |
| RK-10 | Falla de conectividad/API durante la demo | Operativo | Media | Alto | Modo pregrabado, cassettes, cuotas verificadas con antelación |
| RK-11 | Costo/tokens y latencia por repos grandes | Operativo | Media | Medio | Chunking por unidad, prompt caching, modelo por etapa (Haiku/Sonnet/Opus), límites por proyecto, Batch API en F8 |
| RK-12 | Alcance excesivo para el plazo | Gestión | Alta | Alto | Demo-first, mini-pasada end-to-end en F3, F7–F9 fuera del MVP |
| RK-13 | Variabilidad de resultados entre ejecuciones | IA | Media | Medio | Temperatura baja, esquemas, replay en CI, AC-F3-08 |
| RK-14 | Incumplimiento regulatorio en uso real (confidencialidad, residencia de datos, trazabilidad) | Regulatorio | Media | Alto (post-MVP) | Despliegue privado (Bedrock/Vertex/on-prem) documentado, auditoría hash-chain, retención y borrado, F8 |
| RK-15 | IDs de modelo o capacidades cambian | Técnico | Media | Medio | `config/models.yaml`, verificación al inicio de F0 |
| RK-16 | Dependencias vulnerables o cadena de suministro | Seguridad | Media | Medio | Lockfiles, SBOM, pip-audit/npm audit, Trivy en CI |
| RK-17 | Falsos negativos del enmascarador | Seguridad | Media | Alto | Múltiples detectores, golden con secretos sintéticos, bloqueo y revisión manual de lo dudoso |

## 2. Supuestos

Ver `00_contexto_y_requerimientos.md` §4 (S-01 a S-07). Adicionales:

| ID | Supuesto | Impacto |
|---|---|---|
| S-08 | La demo usa un equipo con Docker y salida a Internet hacia el proveedor LLM | Si no, solo modo pregrabado |
| S-09 | Un usuario no involucrado está disponible para la prueba de usabilidad (Word, criterio 9) | Si no, se pierde evidencia del criterio |
| S-10 | Los criterios de evaluación del Word son los vigentes | Cambios obligan a replantear ponderación de esfuerzo |

## 3. Decisiones que requieren tu aprobación

1. Alcance demo-first y hoja de ruta F7–F9 (decidido).
2. Stack Python + FastAPI + React/TS (decidido).
3. Adaptador genérico como estrategia para lenguaje desconocido (propuesto; ADR-002).
4. Niveles de evidencia E1/E2/E3 para la equivalencia (propuesto; ADR-006).
5. Modelos por etapa y verificación de IDs (propuesto; ADR-007).
6. Orquestador propio frente a LangGraph (propuesto; ADR-003).

## 4. Preguntas abiertas (priorizadas)

| Prio | ID | Pregunta | Por qué importa |
|---|---|---|---|
| P0 | P-01 | Con código legacy desconocido el día de la demo, ¿se puede ejecutar el legacy (compilador/runtime) o los organizadores darán casos de entrada/salida esperados? Si no, ¿se acepta equivalencia E3 (derivada) declarada como tal? | Condición habilitante del Word: sin equivalencia demostrada, criterios 3–7 ≤ 3/5 |
| P0 | P-02 | ¿Fecha límite de la demo y tamaño/roles del equipo? | Calibra el recorte de F4–F6 |
| P0 | P-03 | ¿Hay API de Claude garantizada en la demo (límites, créditos, red)? ¿Se permite Bedrock/Vertex? | Define el modo pregrabado y el despliegue |
| P1 | P-04 | ¿Destinos obligatorios: Java y TypeScript, o también C# (mencionado en el Word)? | Alcance de F4/F7 |
| P1 | P-05 | ¿El portal web es suficiente o se espera extensión de IDE/bot? | Capa de experiencia |
| P1 | P-06 | ¿Qué lenguajes legacy esperan los organizadores (COBOL, PL/SQL, RPG, Java)? ¿Pueden dar una muestra previa? | Prioriza adaptadores deterministas |
| P1 | P-07 | ¿Hay un caso de negocio preferido (amortización francesa, siniestros, tarifación de vida)? | Guion de demo y golden |
| P2 | P-08 | ¿Hay estándares de codificación del cliente (para el RAG)? | Guardrails y calidad |
| P2 | P-09 | ¿SonarQube es obligatorio o basta Semgrep/SpotBugs/ruff? | Complejidad de CI |
| P2 | P-10 | ¿Qué supuestos de costo/tiempo manual usamos para la comparación (horas por rutina, tarifa)? | Informe ejecutivo y criterio "Innovador" |
| P2 | P-11 | ¿Repositorio Git remoto y proveedor de CI (GitHub Actions por defecto)? | Integración de aceptación en CI |


---

## Actualización (estado real)

### Respuestas del usuario a las preguntas abiertas
| ID | Respuesta |
|---|---|
| P-01 oráculo con código desconocido | El código será **desconocido**; no se puede ejecutar el legacy → niveles E2/E3 declarados (E1 inexistente) |
| P-02 plazo y equipo | **Una sola persona**; entrega **hoy a las 2 pm** (inicio ~9:34 am) |
| P-03 API de Claude en la demo | Se creyó haber crédito, pero finalmente **no hay clave ni presupuesto** → modo local sin API |
| P-04 destinos | «Lo que el Word menciona» (Java, TypeScript, C#); en la práctica solo **TypeScript** ejecutado; Java/C# solo con API |
| P-05 interfaz | A criterio del equipo → portal web; «buena app y demo» |

### Riesgos nuevos
| ID | Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|---|
| RK-18 | Sin clave de API no hay modo `live`; sin IA, no hay lenguajes distintos de COBOL | Alta | Alto | Motor local determinista (ADR-011) y extensión `claude-code` (Claude vía suscripción, sin clave de API; ADR-015) para otros lenguajes; declarar el límite; mostrar la muestra COBOL si el código de la demo no es soportado |
| RK-19 | Calidad del motor local limitada al **subconjunto COBOL** (sin OCCURS/REDEFINES, VARYING, SORT, STRING, PIC editadas…) | Alta | Alto | `UnsupportedConstruct` con línea; mensaje que indica la necesidad de API; no se ignora nada en silencio |
| RK-20 | Modo `live` (API con clave) y modelo local (Ollama) **no probados en vivo** (`claude-code` sí se probó con una corrida real) | Alta | Medio | Pruebas con proveedor simulado y servidor simulado; probar `live` en cuanto haya clave; el modelo local solo redacta y tiene fallback |
| RK-21 | Placeholder de clave en `.env` hacía creer que había clave real | Media | Alto | Corregido: claves de menos de 30 caracteres o con «REEMPLACE» se ignoran; `.env` queda sin clave |
| RK-22 | Las reglas rechazadas no se excluyen del código en modo local (transpila el programa completo) | Media | Medio | Se declara en los supuestos del código generado |
| RK-23 | Criterio de usuario externo sin evidencia | Alta | Medio | `AC-F6-MANUAL-01` queda `MANUAL-PENDIENTE`, nunca aprobado en silencio |
| RK-24 | Código de la demo en otro lenguaje o con construcciones fuera del subconjunto | Media | Alto | Plan de contingencia con la muestra, capturas/video (ver `docs/GUION_DEMO.md`) |

| RK-25 | **Dato sensible a Anthropic en modo `claude-code`:** el código ya enmascarado sale hacia Anthropic a través de la sesión de Claude Code del usuario | Media | Alto (con código real) | Enmascarado y compuerta de salida previos; solo datos sintéticos en demo y pruebas; el modo es **explícito** (`auto` nunca lo elige) y rotulado; revisar la política de la organización/contrato antes de usarlo con código real; `local` no envía nada a ninguna red |
| RK-26 | **Dependencia de la sesión del CLI `claude` y de los límites de la suscripción** (sesión expirada, límite del plan, CLI ausente del `PATH`) | Media | Medio | Mensajes de error con acción sugerida; el selector deshabilita el modo si no hay CLI; contingencia con `local` o `replay` (las corridas `claude-code` graban cassettes); tiempo de ~6 min por corrida → demo principal con `local`/`replay` |
| RK-27 | Variabilidad de las salidas de Claude entre corridas y **una sola corrida real** (COBOL) como evidencia; otros lenguajes (PL/SQL, RPG, Java) sin probar con `claude-code` | Alta | Medio | Verificadores deterministas (esquemas, citas, guardrails, equivalencia con tolerancia 0, autocorrección ≤ 2); declarar el límite; ensayar con el código de la demo antes |

RK-04 (fuga de secretos): mitigado y probado (suite de enmascarado y compuerta de salida); en `claude-code` el riesgo residual es RK-25. RK-10 (falla de conectividad): el modo local no usa red; `claude-code` y `live` sí (mitigación en RK-26).
