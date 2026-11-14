# PROMPT INICIAL — MODO PLAN (Claude Code)

## App: "Modernización y Descubrimiento de Código Legacy"
### Propuesta para acelerar la extracción de reglas de negocio y la migración hacia arquitecturas modernas mediante IA

---

## 0. Cómo debes trabajar en esta sesión (LEER PRIMERO)

Estás en **modo Plan**. En esta sesión **NO escribas código de la aplicación ni modifiques archivos fuera de `/docs/plan/`**. Tu objetivo es producir un plan de construcción completo, por fases, que luego ejecutaremos fase a fase en sesiones posteriores.

Actúa como **Arquitecto de Software Principal** con experiencia en:
- Modernización de sistemas core bancarios y de seguros (mainframe IBM z/OS, IBM i/AS400, Oracle).
- Lenguajes legacy: COBOL (incl. copybooks, JCL, CICS, DB2 embebido), PL/SQL, RPG/RPGLE/ILE, Java antiguo (1.4–8, EJB 2.x, Struts, JSP).
- Stacks destino: Java 21 + Spring Boot 3.x, Node.js/TypeScript (NestJS), arquitectura limpia / hexagonal, DDD.
- Construcción de aplicaciones sobre la API de Claude (Anthropic).
- Cumplimiento en sectores regulados (trazabilidad, auditoría, protección de datos).

Reglas de trabajo:
1. **Primero lee, luego planifica.** No asumas requisitos que estén en los documentos del proyecto.
2. **Los documentos del proyecto mandan.** Si algo de este prompt contradice el documento Word de requerimientos, prevalece el Word y debes listar la contradicción en "Preguntas abiertas".
3. **No inventes.** Si falta información crítica, regístrala como supuesto explícito (con su impacto) o como pregunta para mí.
4. Escribe todo el plan **en español**. Código, nombres técnicos e identificadores pueden ir en inglés.

---

## 1. Paso obligatorio: leer el contexto del proyecto

1. Explora la carpeta **`/Docs`** del proyecto (y subcarpetas). Contiene:
   - El **documento de requerimientos en formato Word (.docx)**.
   - Documentación complementaria adjunta.
2. Para leer el `.docx`, conviértelo a texto/markdown sin alterar el original, por ejemplo:
   - `pandoc "Docs/<archivo>.docx" -t gfm -o docs/plan/_requerimiento_extraido.md`
   - o, si no hay pandoc: `python -c "import docx; ..."` (python-docx).
   Si ninguna herramienta está disponible, **detente y pídeme** que exporte el Word a PDF o Markdown.
3. Revisa también, si existen: `README`, `CLAUDE.md`, ejemplos de código legacy de muestra, y cualquier estructura de repositorio ya creada.
4. Produce `docs/plan/00_contexto_y_requerimientos.md` con:
   - Resumen de lo entendido.
   - **Matriz de requerimientos** (ID, descripción, fuente/sección del Word, prioridad MoSCoW, tipo funcional/no funcional).
   - Supuestos y preguntas abiertas.

---

## 2. Contexto de negocio (resumen ejecutivo)

En sectores altamente regulados como la banca y los seguros, los sistemas centrales (core business) siguen operando sobre código heredado (legacy) escrito en COBOL, PL/SQL, RPG o versiones desactualizadas de Java. Estos componentes contienen décadas de lógica de negocio crítica, pero no tienen documentación actualizada. Eso expone a las organizaciones a riesgos operativos, regulatorios y de pérdida de conocimiento (personal que se jubila, proveedores que desaparecen).

La app debe **acelerar y hacer verificable** la comprensión y migración de ese código mediante IA, con humanos en el ciclo para las decisiones críticas.

---

## 3. Capacidades que la app DEBE cubrir (mínimo)

| # | Capacidad | Descripción |
|---|-----------|-------------|
| C1 | **Ingesta** | Recibir fragmentos, rutinas o repositorios completos de código legacy (COBOL + copybooks + JCL, PL/SQL, RPG/RPGLE, Java antiguo). Carga por archivo, ZIP o conexión a repositorio Git. Detección automática de lenguaje, dialecto y codificación (incl. EBCDIC). |
| C2 | **Descubrimiento** | Inventario del código, grafo de dependencias (llamadas entre programas, CALL/PERFORM, paquetes, tablas, archivos, copybooks), métricas de complejidad, código muerto e identificación de puntos de entrada. |
| C3 | **Extracción y formalización de reglas de negocio** | Encontrar las reglas que hay en el código y formalizarlas en un formato estructurado y versionado (ID de regla, descripción en lenguaje de negocio, condiciones, acciones, datos involucrados, **trazabilidad a líneas de código fuente**, nivel de confianza, estado de validación humana). Considerar salida tipo tablas de decisión, Gherkin (Given/When/Then) y/o DMN. |
| C4 | **Traducción / migración** | Traducir la lógica a un stack moderno elegido por el usuario: **Java 21 + Spring Boot**, **Node.js/TypeScript** (extensible a otros). La traducción debe partir de las reglas formalizadas, no solo línea por línea. |
| C5 | **Guardrails de arquitectura limpia** | Aplicar y **validar automáticamente** arquitectura limpia/hexagonal: separación dominio / aplicación / infraestructura, regla de dependencias, sin lógica de negocio en controladores ni repositorios, puertos y adaptadores. Incluir validación automática (p. ej. ArchUnit para Java, dependency-cruiser/eslint-boundaries para TS) y estándares (linters, formateadores, SonarQube o equivalente). |
| C6 | **Documentación técnica automática** | Generar documentación del sistema legacy (as-is) y del sistema nuevo (to-be): visión general, diagramas (C4, secuencia, dependencias, en Mermaid/PlantUML), catálogo de reglas, diccionario de datos, mapeo legacy → nuevo y ADRs. |
| C7 | **Suite de pruebas** | Generar pruebas unitarias (JUnit 5/Mockito, Jest/Vitest) por regla de negocio, más **pruebas de equivalencia funcional** (golden master / pruebas de caracterización: mismas entradas → mismas salidas legacy vs. nuevo), incluyendo casos límite (redondeos, decimales empaquetados COMP-3, fechas, signos, truncamientos). |
| C8 | **Validación humana y trazabilidad** | Flujo de revisión y aprobación por expertos funcionales/técnicos para reglas y código generado. Trazabilidad de extremo a extremo: línea legacy → regla → código nuevo → prueba → documento. Registro de auditoría. |

Agrega cualquier capacidad adicional que exija el documento Word.

---

## 4. Requisitos no funcionales a considerar

- **Seguridad y cumplimiento (banca/seguros):** el código fuente es activo sensible. Plantear enmascaramiento de datos/secretos antes de enviarlos al modelo, opciones de despliegue (on-premise / nube privada / Claude vía AWS Bedrock o Google Vertex AI si aplica), cifrado, RBAC, logs de auditoría inmutables, retención de datos.
- **Escalabilidad:** repositorios de cientos de miles o millones de líneas. Procesamiento por lotes, colas, partición del código en unidades de análisis (chunking semántico por programa/sección/párrafo/procedimiento) y gestión de la ventana de contexto.
- **Calidad y confiabilidad de la IA:** salidas estructuradas (JSON Schema) validadas, puntuación de confianza, detección de alucinaciones (verificar que cada regla cite líneas reales), reintentos y verificación cruzada.
- **Costos y observabilidad:** medición de tokens/costo por proyecto y por etapa, prompt caching, uso de la Batch API donde aplique, métricas, trazas y dashboards.
- **Extensibilidad:** arquitectura de plugins para nuevos lenguajes origen (parsers) y stacks destino (generadores).

---

## 5. Estrategia de modelos de IA (Claude API)

Diseña la orquestación asignando el modelo según la etapa (configurable, no fijo en código):

| Etapa | Modelo sugerido | ID |
|-------|-----------------|----|
| Inventario, clasificación masiva, resúmenes por archivo | Claude Haiku 5.5 | `claude-haiku-5-5` |
| Traducción módulo a módulo, generación de pruebas y documentación | Claude Sonnet 5.5 | `claude-sonnet-5-5` |
| Extracción de reglas complejas, decisiones de arquitectura, revisión crítica | Claude Opus 5.5 | `claude-opus-5-5` |
| Casos excepcionales de máxima dificultad (opcional) | Claude Fable 5.2 | `claude-fable-5-2` |

Verifica los identificadores y capacidades vigentes en la documentación oficial (docs.claude.com) antes de fijarlos. Combina la IA con **análisis estático determinista** (parsers/AST, p. ej. ANTLR con gramáticas COBOL/PL/SQL, ProLeap u otros) para que el modelo trabaje sobre estructura verificada y no solo sobre texto plano. Evalúa si conviene usar el Claude Agent SDK para los flujos agénticos.

---

## 6. Entregables de ESTA sesión de planificación

Crea estos archivos en `docs/plan/`:

1. **`00_contexto_y_requerimientos.md`**: lo indicado en la sección 1.
2. **`01_arquitectura_solucion.md`**:
   - Arquitectura de la app (diagramas C4 nivel 1–3 en Mermaid).
   - Stack tecnológico propuesto para la propia app (backend, frontend, base de datos, colas, almacenamiento de artefactos, búsqueda/embeddings si aplica), **con justificación y alternativas descartadas**.
   - Pipeline de procesamiento: Ingesta → Parseo/AST → Descubrimiento → Extracción de reglas → Validación humana → Traducción → Guardrails → Pruebas → Documentación → Empaquetado.
   - Modelo de datos principal (proyecto, artefacto fuente, unidad de análisis, regla de negocio, artefacto generado, prueba, revisión, auditoría).
   - Estrategia de prompts internos de la app (plantillas versionadas, salidas JSON validadas).
3. **`02_plan_por_fases.md`**: el plan de construcción, fase a fase. Para **cada fase** incluye:
   - Objetivo y alcance (qué entra / qué no entra).
   - Requerimientos de la matriz que cubre (IDs).
   - Tareas concretas y ordenadas (pensadas para ejecutarse en una sesión de Claude Code cada una o en pocas).
   - Entregables verificables.
   - **Criterios de aceptación / "Definition of Done"** comprobables (comandos de prueba, cobertura mínima, reglas ArchUnit que deben pasar, etc.). Cada criterio lleva un ID único (`AC-F<fase>-<nn>`), indica qué requerimientos de la matriz cubre y **cómo lo comprueba el script de aceptación** (ver sección 6.1).
   - Dependencias y riesgos.
   - Estimación relativa de complejidad (S/M/L/XL).

   Secuencia orientativa (ajústala según el Word):
   - **Fase 0:** Fundaciones: repositorio, monorepo/estructura, CI/CD, convenciones, `CLAUDE.md`, guardrails base.
   - **Fase 1:** Ingesta y gestión de proyectos/artefactos.
   - **Fase 2:** Parseo y descubrimiento (inventario, grafo de dependencias, métricas). Empezar con **COBOL** como lenguaje piloto.
   - **Fase 3:** Extracción y formalización de reglas de negocio + flujo de validación humana.
   - **Fase 4:** Traducción al stack destino (Java/Spring Boot primero, luego TypeScript) con guardrails de arquitectura limpia.
   - **Fase 5:** Generación de pruebas unitarias y de equivalencia.
   - **Fase 6:** Documentación técnica automática y trazabilidad de extremo a extremo.
   - **Fase 7:** Extensión a PL/SQL, RPG y Java antiguo.
   - **Fase 8:** Seguridad, cumplimiento, observabilidad, costos y endurecimiento para producción.
   - **Fase 9:** Piloto con código real, evaluación de calidad (métricas de precisión de reglas y equivalencia) y ajustes.
4. **`03_guardrails_y_estandares.md`**: reglas de arquitectura limpia, convenciones de código, estructura de paquetes/módulos del código **generado**, y cómo se validan automáticamente.
5. **`04_estrategia_de_pruebas_y_calidad.md`**: pruebas de la propia app y del código generado; conjunto de evaluación (golden dataset) con muestras legacy de referencia para medir la calidad de la IA.
6. **`05_riesgos_supuestos_preguntas.md`**: riesgos (técnicos, regulatorios, de calidad de IA) con mitigación, supuestos y **preguntas abiertas para mí, priorizadas**.
7. **`adr/`**: ADRs iniciales (formato Michael Nygard) para las decisiones clave.
8. **`06_criterios_aceptacion_y_scripts.md`**: ver sección 6.1.
9. **Borrador de `CLAUDE.md`** (en `docs/plan/CLAUDE.md.draft`) con las convenciones que deberán seguir las sesiones de construcción posteriores: comandos de build/test, estructura, reglas de arquitectura, la instrucción de leer `docs/plan/` al inicio de cada fase y la regla de **no declarar ninguna fase terminada hasta que `scripts/acceptance/run_acceptance --fase <N>` y la regresión `--todas` pasen al 100 %**, adjuntando el reporte generado.

### 6.1 Validación de criterios de aceptación mediante script (OBLIGATORIO)

**Todos** los criterios de aceptación de **todas** las fases deben comprobarse automáticamente con un script. Ninguna fase se da por terminada por inspección manual o por afirmación del agente. En el plan debes diseñar ese mecanismo:

1. **Script de aceptación por fase:** `scripts/acceptance/fase_<N>.<ext>`, con un ejecutor común `scripts/acceptance/run_acceptance.<ext> --fase <N>` y la opción `--todas` para correr la regresión de todas las fases ya completadas.
   - Debe ser **multiplataforma** (Windows y Linux/macOS, porque el desarrollo se hace en VS Code y además corre en CI). Propón la tecnología (p. ej. Python 3 o Node.js/TypeScript) y justifícala en un ADR.
2. **Cada criterio `AC-F<fase>-<nn>` corresponde a una o más comprobaciones automáticas**, por ejemplo:
   - Compilación y build sin errores.
   - Pruebas unitarias, de integración y de equivalencia en verde.
   - Cobertura mínima (umbral numérico).
   - Reglas de arquitectura (ArchUnit / dependency-cruiser) sin violaciones.
   - Linters y análisis estático sin errores bloqueantes.
   - Endpoints o comandos de la app respondiendo lo esperado (smoke tests contra la app levantada).
   - Ejecución de extremo a extremo sobre las **muestras legacy de referencia** (golden dataset), con métricas mínimas: % de reglas con trazabilidad a líneas reales, % de equivalencia funcional, etc.
   - Existencia y validez de los artefactos generados (documentación, diagramas, esquemas JSON válidos).
   - Si un criterio no se puede automatizar del todo, el script debe al menos verificar la evidencia (archivo de aprobación firmado, checklist completado) y marcarlo como `MANUAL-VERIFICADO`, nunca como aprobado en silencio.
3. **Salida del script:**
   - Resultado en consola por criterio: `PASS` / `FAIL` / `SKIP`, con el motivo del fallo.
   - Reporte en `reports/acceptance/fase_<N>_<fecha>.md` y `.json` (fecha, commit, resultado por criterio, requerimientos cubiertos).
   - **Código de salida distinto de 0 si falla cualquier criterio**, para que bloquee el pipeline de CI.
4. **Integración en CI/CD:** el pipeline ejecuta `run_acceptance --todas` en cada push o pull request a la rama principal.
5. **Regla de avance:** una fase solo está terminada cuando su script pasa al 100 % **y** la regresión de las fases anteriores sigue en verde. El script de aceptación de cada fase se escribe **al inicio** de esa fase, antes de implementarla (enfoque guiado por aceptación).
6. Documenta todo en el entregable **`06_criterios_aceptacion_y_scripts.md`**: la tabla completa de criterios por fase (ID, descripción, requerimientos cubiertos, comprobación automática, umbral), la estructura de `scripts/acceptance/` y cómo ejecutarlo localmente y en CI.

---

## 7. Criterios de calidad del plan

Antes de darme el plan por terminado, verifica que:
- [ ] Cada requerimiento de la matriz está asignado al menos a una fase.
- [ ] Cada capacidad C1–C8 está cubierta.
- [ ] Cada fase tiene criterios de aceptación comprobables, no subjetivos.
- [ ] Cada criterio de aceptación tiene ID y una comprobación automática definida en el script de aceptación de su fase.
- [ ] El ejecutor de aceptación es multiplataforma, genera reportes y devuelve código de salida distinto de 0 si algo falla.
- [ ] Cada fase entrega algo funcional y demostrable (incremental, no "big bang").
- [ ] Están definidos el lenguaje piloto y el stack destino inicial.
- [ ] La estrategia de seguridad para código sensible está explícita.
- [ ] Están identificadas las decisiones que requieren mi aprobación.

---

## 8. Al terminar

Responde con:
1. Un resumen ejecutivo del plan (máximo 15 líneas).
2. La lista de archivos creados.
3. Las **preguntas abiertas más importantes** que necesito responder antes de iniciar la Fase 0.
4. La recomendación de qué modelo usar en Claude Code para ejecutar cada fase.

**No inicies la Fase 0 hasta que yo apruebe el plan explícitamente.**
