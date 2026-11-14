# Guion de demostración (≤ 10 minutos)

**Narrativa:** «Un banco tiene un cálculo de cuotas escrito en COBOL en 1998, sin documentación y con personas que se jubilan. Lo convertimos en conocimiento
verificado y en código moderno con evidencia de que se comporta igual, en minutos y no en semanas, con el humano decidiendo.»

## 0. Preparación previa (checklist, 15 min antes)
- [ ] `py run.py` levantado; abrir http://127.0.0.1:8000 y comprobar el selector **«Motor»** (arriba a la derecha): **«⚙ Motor local determinista (sin IA)»** (por defecto sin clave), **«◆ Con IA»** (si `claude` está en PATH con sesión; se arranca con `py run.py --claude` o se elige en el selector), **«● IA en vivo (API)»** (con clave) o **«■ Contingencia (pregrabado)»**.
- [ ] **Decidir el motor de la demo.** Recomendado: **demo principal con `local` (segundos) o `replay`**, y mostrar Claude con una corrida **previa** (una corrida completa en `claude-code` tarda **~6 min**: no cabe en vivo dentro de 10 min). Haga antes una corrida `claude-code` con la muestra COBOL para **grabar cassettes** y confirme que el modo `replay` la reproduce.
- [ ] Probar la muestra COBOL completa una vez (paso 1→6) y borrar ese proyecto, o dejarlo como respaldo en el selector de proyectos.
- [ ] `.\.venv\Scripts\python -m pytest tests -q` → 63 pasan; `py scripts\acceptance\run_acceptance.py --todas` → resultado PASS (el criterio manual sale «MANUAL-PENDIENTE»).
- [ ] Tener a mano el código que entreguen los organizadores. **En modo local solo funciona si es COBOL de formato fijo dentro del subconjunto**; si es otro lenguaje, cambie el «Motor» a **Claude vía suscripción** (o API) — **no probado con lenguajes distintos de COBOL**; si no hay IA disponible, usar la muestra y explicarlo con honestidad. Recuerde que en `claude-code` el código ya enmascarado sale hacia Anthropic: confirmar que es aceptable.
- [ ] Capturas/video de una corrida completa guardados (contingencia nivel 3).
- [ ] Navegador a pantalla completa, zoom 100 %, sin otras pestañas con datos reales. Solo datos sintéticos.

## 1. Guion minuto a minuto

> **Novedades de la interfaz (úselas):** (1) en la portada, el botón grande **«▶ Probar con un ejemplo (opcional)»** carga la muestra COBOL con los casos aportados (E2) en un solo clic; (2) el botón **««?» (botón flotante)»** (cabecera) y **«▶ Recorrido de esta pantalla»** (tarjeta amarilla) enmarcan cada zona y la explican en lenguaje simple; (3) la **barra inferior «Siguiente: … →»** lleva de un paso al siguiente y avisa con «🔒» qué falta; (4) el **«Motor»** de la cabecera se cambia antes de empezar un proyecto. Para aprender a manejarla: [GUIA_ENTRENAMIENTO_DEMO.md](GUIA_ENTRENAMIENTO_DEMO.md).

| Min | Qué pulsar | Qué mostrar | Qué decir |
|---|---|---|---|
| 0:00–1:00 | Pantalla inicial; abrir el selector **«Motor»** y mostrar las opciones | Título, el selector y qué motor está activo | «El problema: caja negra, semanas de análisis, riesgo de regresión. Esto lo convierte en reglas explícitas, código moderno y pruebas de equivalencia.» Decir con claridad qué motor está activo y **por qué**: «sin IA, determinista y en segundos» (`local`), o «con Claude a través de mi suscripción, sin clave de API» (`claude-code`, ~6 min, ya ejecutado antes). **No cambiar de motor en mitad de un proyecto.** |
| 1:00–2:00 | **Demostrar el manejo de entradas inválidas** → botones «Archivo .exe», «Archivo binario», «Código vacío» | Aviso con mensaje claro y acción sugerida; nada se guarda | «Primero lo que pasa cuando algo sale mal: se rechaza con un mensaje claro, sin guardar ni exponer datos.» (Criterio *Funcional*: entrada inválida.) |
| 2:00–3:00 | **«▶ Probar con un ejemplo (opcional)»** (carga la muestra COBOL con los casos aportados E2; equivale a «Usar esta muestra» con la casilla E2 marcada) | **Paso 1 · Ingesta**: tabla de archivos, lenguaje, codificación; informe de enmascarado: la contraseña incrustada pasó a `<SECRET_001>`; compuerta «0 residuos» | «Antes de que nada salga a una IA, los secretos se ocultan. Si quedara uno, el envío se bloquea.» |
| 3:00–3:45 | «Analizar y extraer reglas →» (después, la barra inferior **«Siguiente: … →»**) | **Paso 2 · Descubrimiento**: LOC, párrafos, grafo PERFORM/GO TO, código muerto (`UNUSED-AUDIT-LOG`), negocio vs. infraestructura, riesgos, contrato de E/S | «Un analizador estático determinista da el mapa verificable; la lógica de negocio queda separada de la de plataforma (archivos, SQL de auditoría).» |
| 3:45–5:30 | Paso 3: clic en una regla; «Aprobar todas las verificadas»; probar **Ajustar** una descripción; **Rechazar** una; «Aprobar catálogo y generar código →» | Lista compacta (una línea por regla) con barra de progreso y filtros (Todas / Pendientes / Aprobadas / Rechazadas); código legacy a la izquierda con las líneas resaltadas; detalle de la regla seleccionada (condición/acción, Gherkin, tabla de decisión). Aprobar con ✔ / rechazar con ✖: la lista avanza sola a la siguiente pendiente | «Cada regla cita líneas reales y un verificador lo comprueba; una regla sin respaldo no se puede aprobar. **Aquí decide el ingeniero**: nada pasa al código sin su aprobación.» (Criterio *Funcional*: aprobación de reglas.) |
| 5:30–6:30 | Paso 4 | Capas domain/application/infrastructure, ADRs; selector de regla → vista comparativa **legacy ↔ moderno** | «Arquitectura hexagonal; cada método lleva la etiqueta de la regla que implementa.» (Criterio *Interactivo*: vista comparativa.) |
| 6:30–8:00 | Paso 5 | Tiles: equivalencia 100 %, 0 diferencias, cobertura, 0 hallazgos; tabla de casos con evidencia E2/E3 | «**Caso borde**: fíjense en `plazo_361_rechazo`, los umbrales de puntaje y el truncamiento de años; tolerancia cero en cálculos y redondeos.» Explicar E2 (casos aportados, independientes) y E3 (oráculo derivado de un segundo traductor): **no se ejecutó el COBOL**. |
| 8:00–9:30 | Paso 6 | Tablero; «¿Qué nos diferencia?»; comparación manual vs. copiloto; **calculadora «de una rutina a toda la cartera»** (cambiar 50 → 200 rutinas); matriz de trazabilidad; botón de descarga del `.zip` | «Estimado manual: horas; copiloto: segundos más revisión humana. Los supuestos son parametrizables y están a la vista, no son mediciones.» (Criterio *Innovador*.) |
| 9:30–10:00 | — | Cierre | «De semanas a minutos, con control humano, evidencia verificable y seguridad desde el diseño.» |

## 2. Versión para público no técnico
Usar solo las columnas «Qué pulsar» y «Qué decir» y apoyarse en la tarjeta amarilla **«🧭 ¿Qué hacer ahora?»** que aparece en cada paso. Frases clave: «el programa antiguo es una caja negra», «aquí están las reglas escritas en palabras», «usted aprueba o rechaza», «comprobamos 67 casos y da lo mismo en el sistema nuevo» (cifra de la corrida de referencia; confirmar en pantalla), «ahorro estimado para 200 programas». Evitar siglas (AST, COMP-3, E2/E3) salvo que pregunten.

### Cómo mostrar el modo con Claude (sin clave de API)
- **Qué decir:** «La misma aplicación, el mismo recorrido y los mismos verificadores; solo cambia quién “piensa”. Con el motor local es un programa determinista; con Claude vía suscripción es una IA que sirve para cualquier lenguaje, a costa de ~6 minutos y de enviar el código ya enmascarado a Anthropic.»
- **Cómo mostrarlo en 10 minutos:** (a) abrir el proyecto de una corrida `claude-code` **ya hecha** (selector de proyectos) y recorrer sus pasos 3 a 6, o (b) elegir «■ Contingencia (pregrabado)» y repetir el flujo con las respuestas grabadas de esa corrida. Resultado real de una corrida (muestra COBOL con casos aportados, 346 s): **14 reglas** con cita verificada (confianza 0,85–0,98), **65/65** casos equivalentes (E2+E3), 0 diferencias, cobertura **98,43 % / 94,79 %**, 0 hallazgos, trazabilidad 100 %. Aclarar que es **una corrida** y que los verificadores deterministas son la garantía, no la IA.
- **Contraste útil:** el motor local encontró 11 reglas (más agrupadas en cálculos) y Claude 14 (más granulares y en lenguaje de negocio): ambas pasan las mismas compuertas.
- **No prometer:** otros lenguajes (PL/SQL, RPG, Java) en `claude-code` **no están probados** en esta máquina.

## 3. Notas para técnicos
- Parser COBOL de subconjunto (`copilot/cobol.py`), reglas desde el AST (`local_engine.extract_rules`), dos transpiladores independientes (TypeScript y Python) y un `Decimal` propio (BigInt escalado, `ROUNDED`=HALF_UP, truncamiento, truncado de PIC, división a 30 decimales, potencia exacta).
- El TypeScript se ejecuta con `node --permission` (sin red/archivos/procesos); el oráculo Python se valida por AST y corre con `python -I`. La cobertura corre sin `--permission` (incompatible) pero solo tras pasar la ejecución restringida y el escaneo estático.
- El flujo `PERFORM/GO TO/fall-through` se resuelve con valores de flujo explícitos; el código muerto no se migra.
- Seguridad: SQL parametrizado + suite de inyección, ZIP-slip/bomb, CSP, rate limit, auditoría con hash encadenado.

## 4. Cómo explicar la arquitectura multiagente
Seis agentes especializados, coordinados por un **orquestador con estado** (`copilot/pipeline.py`, `copilot/delivery.py`) con compuertas de calidad por etapa y un **punto de aprobación humana (HITL)** entre reglas y código:
**Analista** (estructura/riesgos/contrato de E/S) → **Extractor de reglas** (catálogo con citas y confianza) → *aprobación humana* → **Arquitecto** + **Desarrollador** (diseño y código) → **QA/Tester** (casos, oráculo, pruebas) → **Documentador** (docs, matriz de trazabilidad, informe).
Entre agentes hay **verificadores deterministas** (citas reales, esquemas JSON, guardrails de arquitectura, equivalencia con tolerancia 0), de modo que la IA no se evalúa a sí misma.
Los «agentes» se ejecutan según el modo: con **Claude vía suscripción** (`claude-code`, sin clave de API) o con clave de API (`live`) son llamadas a Claude (Sonnet/Opus según etapa, `config/models.json`); sin IA son las mismas etapas implementadas por el motor local determinista (`copilot/local_engine.py`); en `replay` se reproducen respuestas grabadas. Los verificadores son idénticos en todos los modos. En `claude-code` cada etapa invoca el CLI `claude -p` sin herramientas, sin persistencia de sesión, con el prompt por stdin y en un directorio temporal vacío.
**Sobre los subagentes de Claude Code:** durante el *desarrollo* de este prototipo se usaron subagentes de Claude Code para redactar documentación y revisar el código en paralelo. Eso es distinto de los seis agentes de la aplicación y no forma parte del producto en ejecución.

## 5. Cómo se cubre la rúbrica (Funcional · Interactivo · Innovador, 33,33 % cada uno)
| Criterio | Evidencia en la demo | Dónde se comprueba |
|---|---|---|
| **Funcional** | Flujo completo de la carga al paquete; caso representativo (COBOL amortización) y **casos borde** (umbrales, truncamiento, redondeo); **entrada inválida** con los botones de la pantalla inicial; aprobación de reglas | AC-F7-01, AC-F7-02, AC-F7-03 |
| **Interactivo y fácil de usar** | Flujo guiado (stepper de 6 pasos + tarjeta «qué hacer ahora»); vista comparativa legacy ↔ moderno; manual de usuario. *Usuario externo sin ayuda:* requiere evidencia firmada | AC-F7-04, 05, 06; AC-F6-MANUAL-01 (pendiente hasta tener la evidencia) |
| **Innovador** | Comparación cuantificada manual vs. copiloto; **calculadora de cartera**; «¿Qué nos diferencia?» (reglas verificadas, evidencia honesta, humano decide, seguro por diseño, híbrido determinista + IA) | AC-F7-07, 08, 09 |

## 6. Preguntas frecuentes (respuestas honestas)
- **¿Es IA?** En modo `local` **no**: es un motor determinista (parser + reglas + transpiladores). Con **Claude vía suscripción** (`claude-code`, sin clave de API) o con clave de API (`live`) las etapas las hacen modelos de Claude. Con Ollama opcional un modelo local solo redacta textos. El selector «Motor» y la insignia dicen siempre qué modo está activo.
- **¿Necesita clave de API?** No: el modo `claude-code` usa la sesión de Claude Code del usuario (suscripción); el modo `live` sí requiere clave de API (de pago, no probado aquí).
- **¿A dónde va mi código en modo Claude?** El código **ya enmascarado** va a Anthropic a través de la sesión de Claude Code; el motor local no envía nada a ninguna red. Revise la política de su organización antes de usarlo con código real.
- **¿Por qué tarda ~6 minutos en modo Claude?** Son seis etapas con modelos grandes; por eso la demo principal usa `local` o `replay`.
- **¿Los resultados de Claude son siempre iguales?** No: un LLM puede variar entre ejecuciones; por eso cada salida pasa por esquemas, verificación de citas, guardrails y equivalencia con tolerancia 0.
- **¿Ejecuta el COBOL original?** **No**: no hay runtime COBOL. La equivalencia se demuestra con casos aportados (E2) y con un oráculo derivado por un segundo traductor (E3); el reporte lo declara y no presenta E3 como ejecución del legacy.
- **¿Y Java o C#?** Solo con IA (`claude-code` o `live`), y se generan con validación estática pero **no se compilan** aquí. En modo local el selector los deshabilita.
- **¿Funciona con cualquier lenguaje?** En modo `local`, solo COBOL de formato fijo dentro del subconjunto (si no, falla con la línea). Con IA (`claude-code`/`live`), diseñado para cualquier lenguaje, aunque **solo se probó COBOL** (PL/SQL, RPG y Java no se han probado) y el modo `live` con API **no se ha probado**.
- **¿Qué pasa si falla internet?** Modo `local` no usa red ni API. `claude-code`, `live` y Ollama remoto dependen de servicios (Ollama local solo usa loopback); en ese caso cambie a `local` o `replay`.
- **¿Qué hace si la IA inventa una regla?** El verificador compara la cita con el código; una regla sin respaldo se marca y no se puede aprobar.
- **¿Es seguro con código real?** Hay enmascarado y controles, pero la demo y las pruebas usan solo datos sintéticos; no hay RBAC completo ni despliegue privado (hoja de ruta).

## 7. Plan de contingencia (tres niveles)
1. **Modo local sin red** (`COPILOT_LLM=local`, o simplemente sin clave): funciona offline con la muestra COBOL. Es el plan por defecto.
2. **Replay**: `COPILOT_LLM=replay py run.py` (o «■ Contingencia» en el selector) reproduce respuestas grabadas; solo útil si antes se hizo una corrida con IA (`claude-code` o `live`), que graba `cassettes/`. Si hizo la corrida `claude-code` con la muestra COBOL, ya tiene cassettes de una corrida real; **confírmelo antes de la demo**.
   - Si falla la sesión de Claude o se agota el límite de la suscripción durante la demo: cambie el selector a `local` o `replay`.
3. **Capturas/video**: tener grabada una corrida completa y las capturas de los 6 pasos para mostrar si la aplicación no arranca.
