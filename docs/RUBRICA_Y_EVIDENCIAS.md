# Rúbrica de Visión de Cliente y Negocio — mapa de evidencias

Este documento relaciona cada criterio de la rúbrica (imagen "Criterios de Éxito Visión de Cliente y Negocio") con **evidencia concreta y verificable**: archivo o función, prueba automática, criterio de aceptación `AC-F7-xx`, forma de demostrarlo en vivo y estado honesto. **No se afirman puntajes**: la evaluación corresponde al jurado; aquí se presenta la evidencia.

Los tres criterios pesan 33,33 % cada uno y se ponderan de forma independiente (escala 1–5 por criterio). Los criterios `AC-F7-xx` se ejecutan con:

```powershell
py scripts\acceptance\run_acceptance.py --fase 7
```

---

## 1. Funcional (33,33 %)

*Resuelve el problema de punta a punta. Evidencia pedida: flujo completo en vivo, caso representativo y caso borde correctos, y una entrada inválida manejada sin exponer datos.*

| Evidencia pedida | Dónde está | Verificación automática | Cómo demostrarlo en vivo |
|---|---|---|---|
| **Flujo completo en vivo** (carga → reglas → aprobación → código → pruebas) | `copilot/pipeline.py`, `copilot/delivery.py`, `copilot/local_engine.py` (modo sin clave), `web/app.js` | `test_local_full_flow_without_api_key`, `test_full_flow` · **AC-F7-01** | Muestra COBOL → los 6 pasos → descarga del `.zip`. El selector «Motor» y la insignia indican si es motor local, Claude vía suscripción, API o pregrabado. |
| **Caso representativo** (amortización francesa en COBOL con COMP-3, `ROUNDED`, truncamiento, `GO TO`, `EXEC SQL`) | `golden/cobol_amortizacion/` | `test_python_backend_matches_hand_written_reference`, `test_golden_reference_vs_typescript_fixture` · **AC-F7-02** | Paso 5: tabla de casos (67 con motor local: 25 aportados E2 + 42 derivados E3), todos equivalentes. |
| **Casos borde correctos** (monto/plazo/puntaje en el límite, justo debajo y justo arriba; truncamiento de años; redondeo con decimales largos) | `golden/cobol_amortizacion/reference.py` y `cases.json`; generador de casos en `local_engine.stage_qa_cases` | Misma batería · tolerancia 0 (`verify.compare`; `test_compare_detects_one_cent_difference`) | Mostrar un caso en el límite (p. ej. `monto_minimo`, `plazo_361_rechazo`) y la columna "Diferencias en cálculos = 0". |
| **Entrada inválida manejada sin exponer datos** | `security.py` (`SecurityError`, límites, ZIP-slip/bomb), `repo_import.py` (URL de repositorio, anti-SSRF), `main.py` (errores sin trazas), `web/app.js` (`demoInvalid`) | `test_invalid_inputs_have_clear_errors` (verifica mensaje claro, sin "Traceback" y que no queda ningún proyecto guardado), `test_oversized_upload_rejected`, `test_zip_slip_blocked`, `test_local_engine_rejects_other_languages_clearly` · **AC-F7-03** | En el inicio: "Demostrar el manejo de entradas inválidas" → **Archivo .exe**, **Archivo binario**, **Código vacío**. Aparece un aviso con acción sugerida y no se crea ningún proyecto. |

**Cifras verificadas** (motor local, muestra COBOL con casos aportados): 11 reglas con cita verificada; 67/67 casos equivalentes; 0 diferencias numéricas; cobertura 93,67 % de líneas y 83,33 % de ramas; complejidad ciclomática máxima 10; 0 hallazgos críticos; trazabilidad 100 %.

**Estado honesto y límites:**
- La equivalencia usa evidencia E2/E3. **No se ejecuta el programa legacy** (sin runtime en el entorno); la interfaz lo declara.
- El motor local cubre un **subconjunto de COBOL**; para otros lenguajes o Java/C# se requiere la API de Claude (y Java/C# no se compilan en esta máquina).
- **Evidencia adicional con IA real (sin clave de API):** el modo `claude-code` (Claude vía la suscripción de Claude Code; selector «Motor» o `py run.py --claude`) completó **una corrida real** sobre la muestra COBOL con casos aportados, en 346 s: 14 reglas con cita verificada (confianza 0,85–0,98), **65/65** casos equivalentes (E2+E3), 0 diferencias, cobertura **98,43 % / 94,79 %**, 0 hallazgos, trazabilidad 100 %, 0 iteraciones de autocorrección. Es **una sola corrida** (los LLM varían entre ejecuciones; los verificadores deterministas son la garantía). Verificación automática del aislamiento y de la selección de modo: `tests/test_modes.py` · **AC-F7-11**.
- El modo `live` (API de pago con clave) **no se ha probado**: esa parte solo se probó con un proveedor simulado. `claude-code` solo se ha probado con COBOL (PL/SQL, RPG y Java no).
- Si el código de la demostración es desconocido y queda fuera del subconjunto, el motor local se detiene con la línea exacta; entonces hace falta una IA (`claude-code` o `live`).

---

## 2. Interactivo y fácil de usar (33,33 %)

*Navegación intuitiva y respuestas oportunas. Evidencia pedida: flujo guiado, vista legacy vs. moderno y un usuario externo que completa la tarea sin ayuda.*

| Evidencia pedida | Dónde está | Verificación automática | Cómo demostrarlo en vivo |
|---|---|---|---|
| **Flujo guiado** | Stepper de 6 pasos (`STEPS`, `renderStepper`) y recuadro **"🧭 Paso N … Qué hacer ahora"** (`helpCard`) con lenguaje no técnico; indicadores de estado por fase y banner de progreso con segundos transcurridos; errores con acción sugerida y botón **Reintentar** | **AC-F7-04** (revisa que existan `helpCard`, "Qué hacer ahora", `demoInvalid`, `STEPS`) | Recorrer los pasos leyendo solo el recuadro amarillo; avance automático al terminar cada etapa (`autoStep`). |
| **Vista comparativa legacy vs. moderno** | Paso 3 (código original con líneas resaltadas por regla) y paso 4 (original ↔ archivo moderno, con ● en los archivos que implementan la regla) | **AC-F7-05** (`Vista comparativa legacy`, `cmp-legacy`, `cmp-modern`, `codeView`) | Paso 4: elegir una regla y mostrar su línea original y su implementación. |
| **Respuestas oportunas** | Etapas en segundo plano con sondeo cada 1,5 s y contador en pantalla | `test_full_flow` / `test_local_full_flow_without_api_key` esperan la finalización por estado | Mostrar el banner "Analizando… Ns" y la transición automática. |
| **Manual para perfiles técnicos y no técnicos** | `docs/MANUAL_DE_USUARIO.md` | **AC-F7-06** (secciones de arquitectura, tecnologías, usuario técnico/no técnico, solución de problemas, guion) | Entregar el manual junto con la aplicación. |
| **Usuario externo completa la tarea sin ayuda** | **Requiere una persona real.** Plantilla y checklist abajo | **AC-F6-MANUAL-01** (manual): exige `evidence/AC-F6-MANUAL-01.json` firmado | Ver "Prueba de usabilidad" más abajo. |

#### Evidencia adicional del criterio Interactivo (guía interactiva y estándares de interfaz)

| Elemento | Dónde está | Verificación | Cómo demostrarlo |
|---|---|---|---|
| **Portada con ejemplo opcional** y tres pasos explicados | `home()` en `web/app.js` («▶ Probar con un ejemplo (opcional)») | `tests/test_ui_standards.py` (guía y elementos), AC-F7-04 | Abrir la portada; pulsar el botón. |
| **Guía interactiva** (recorrido con foco sobre la pantalla real; 6/3/4/7/3/3/5 pasos por pantalla) | `web/guide.js` (`TOURS`); botones ««?» (botón flotante)» y «▶ Recorrido de esta pantalla» | `test_guided_experience_for_non_technical_users` | ««?» (botón flotante)» en cualquier pantalla; Esc para cerrar. |
| **Ayudas «ⓘ»** (20 términos en lenguaje simple) | `GLOSS` en `web/guide.js`; `tile()` | misma prueba (≥ 15 términos) | Pulsar la ⓘ de «Equivalencia» o «Cobertura». |
| **Pasos numerados y barra «Siguiente»** con aviso «🔒 qué falta» | `renderStepper()`, `navBar()` | misma prueba (`navBar`, `Siguiente:`, `aria-current`) | Intentar abrir un paso bloqueado: «Primero complete el paso anterior». |
| **Paso 3 compacto** (progreso, filtros, ✔/✖, avance automático) | `viewRules()`, `ruleRow()` | capturas con Playwright; AC-F7-04 | Aprobar con ✔ y ver cómo salta a la siguiente. |
| **Accesibilidad y contraste WCAG AA** (≥ 4,5:1 en claro y oscuro; foco visible; `aria-live`; objetivos ≥ 42 px; modo oscuro; móvil) | `web/style.css`, `web/index.html` | `tests/test_ui_standards.py` (6 pruebas) | Mostrar el cambio automático de modo claro/oscuro del sistema. |
| **Favicon propio** | `web/favicon.svg` | `test_favicon_*` | Ver la pestaña del navegador. |
| **Entrenamiento para quien presenta** | `docs/GUIA_ENTRENAMIENTO_DEMO.md`, `docs/MANUAL_FUNCIONAL_NO_TECNICO.md` | AC-F7-17 | Seguir los ejercicios de la guía. |

*Límite honesto:* estas comprobaciones verifican estándares y presencia de elementos, no la usabilidad real; la prueba con una persona externa sigue siendo manual.

**Estado honesto:** el único punto que no se puede automatizar es la prueba con una persona ajena al desarrollo. Hasta que exista el archivo de evidencia, el script reporta `MANUAL-PENDIENTE` (y falla solo con `--estricto`); **nunca se marca como aprobado en silencio**.

### Prueba de usabilidad con un usuario externo

**Procedimiento.** Elija a alguien que no haya participado en el desarrollo (idealmente de perfil de negocio). Abra la aplicación en la pantalla de inicio y dígale únicamente: *"Cargue la muestra COBOL, apruebe las reglas, genere el código y descargue el paquete"*. No ayude; anote dudas y el tiempo.

**Checklist** (marque cada punto solo si la persona lo logró sin asistencia):

1. [ ] Cargó la muestra y pulsó **Analizar y extraer reglas →**.
2. [ ] Entendió qué significa el enmascarado (o lo leyó en el recuadro de ayuda).
3. [ ] Distinguió una regla con respaldo de una sin respaldo.
4. [ ] Aprobó, ajustó o rechazó reglas y aprobó el catálogo.
5. [ ] Encontró la vista comparativa y la usó.
6. [ ] Identificó el resultado de la equivalencia (100 % / 0 diferencias).
7. [ ] Descargó el paquete `.zip`.
8. [ ] Ante un error (p. ej. archivo inválido), entendió el mensaje y supo qué hacer.

**Plantilla de evidencia** — guarde como `evidence/AC-F6-MANUAL-01.json` (cree la carpeta `evidence/`):

```json
{
  "reviewer": "Nombre y cargo de la persona evaluadora",
  "date": "2026-11-13",
  "checklist_completed": true,
  "minutes_to_complete": 0,
  "assistance_needed": false,
  "observations": "Dudas, fricciones y mejoras observadas"
}
```

El script exige `reviewer`, `date` y `checklist_completed` con valores verdaderos/no vacíos. Complete el archivo solo si la prueba se realizó realmente.

---

## 3. Innovador (33,33 %)

*Mejora diferenciada frente al proceso manual. Evidencia pedida: comparación cuantificada (tiempo, esfuerzo o calidad), elemento diferenciador y caso de negocio.*

| Evidencia pedida | Dónde está | Verificación automática | Cómo demostrarlo en vivo |
|---|---|---|---|
| **Comparación cuantificada** (tiempo y esfuerzo) | `delivery.metrics` (horas manuales estimadas, segundos de máquina, costo de IA, tokens), `config/estimates.json`; UI "Comparación frente al proceso manual"; `informe_ejecutivo.md` en el paquete | **AC-F7-07** (`Comparación frente al proceso manual`, `manual_hours_estimate`) | Paso 6: barras manual vs. copiloto con los supuestos visibles. |
| **Comparación de calidad** | Equivalencia 100 %, 0 diferencias, cobertura, hallazgos críticos, trazabilidad 100 % (pasos 5 y 6; `reportes/`) | `test_local_full_flow_without_api_key`, **AC-F7-01** | Tablero del paso 6. |
| **Elemento diferenciador** | UI **"¿Qué nos diferencia?"**: reglas verificadas de forma determinista (anti-alucinación), equivalencia con niveles de evidencia honestos, el humano decide, seguridad por diseño, híbrido determinista + IA | **AC-F7-08** | Mostrar una regla "SIN respaldo en el código" detectada y bloqueada, y el aviso E2/E3. |
| **Caso de negocio** | UI **"Caso de negocio: de una rutina a toda la cartera"** (`businessCase`): extrapola horas, ahorro ($), porcentaje y días a N rutinas con los supuestos de `config/estimates.json` (incluye revisión humana de 20 min por rutina) | **AC-F7-07** | Cambiar "Rutinas legacy a migrar" (p. ej. 50, 500) y leer el ahorro estimado. |
| **Funciona sin clave de API** | `copilot/local_engine.py`, `copilot/cobol.py`: motor determinista sin IA; modelo local opcional `copilot/local_llm.py` | `test_local_full_flow_without_api_key`, `test_local_mode_blocks_non_typescript_targets`, `test_optional_local_model_enrichment_is_safe`, `test_local_model_host_must_be_loopback` · **AC-F7-10** | Insignia "⚙ Motor local determinista (sin IA)"; costo de IA $0 en la tabla de costos. |
| **Rúbrica documentada** | Este documento | **AC-F7-09** | — |

**Estado honesto:**
- Las cifras de ahorro **son supuestos parametrizables, no mediciones**: 25 LOC/h de análisis, 12 LOC/h de migración y pruebas, +15 % de documentación, $60/h, 8 h/día, 20 min de revisión humana por rutina. Se muestran siempre junto al resultado y se pueden cambiar en `config/estimates.json`.
- El tiempo de máquina de una rutina pequeña es de segundos con el motor local; con modelos en vivo dependerá de la latencia de la API (se mide y se muestra).
- El modelo de IA local opcional (Ollama) **no se ha probado en vivo** en esta máquina; solo con pruebas simuladas. Está desactivado por defecto.

---

## 4. Resumen de criterios de aceptación de la rúbrica

| ID | Criterio | Tipo |
|---|---|---|
| AC-F7-01 | Funcional: flujo completo sin clave, equivalencia 100 %, cobertura ≥ 80/70, trazabilidad 100 % | Automático |
| AC-F7-02 | Funcional: caso representativo y bordes; oráculo = referencia a mano | Automático |
| AC-F7-03 | Funcional: entrada inválida sin exponer ni guardar datos | Automático |
| AC-F7-04 | Interactivo: flujo guiado y demostración de errores en la UI | Automático (revisión estática de la UI) |
| AC-F7-05 | Interactivo: vista comparativa legacy vs. moderno | Automático (revisión estática de la UI) |
| AC-F7-06 | Interactivo: manual técnico y no técnico | Automático (existencia y secciones) |
| AC-F7-07 | Innovador: comparación cuantificada y caso de negocio interactivo | Automático (revisión estática de la UI) |
| AC-F7-08 | Innovador: elemento diferenciador explícito | Automático (revisión estática de la UI) |
| AC-F7-09 | Rúbrica documentada con evidencia | Automático (existencia y secciones) |
| AC-F7-10 | Motor local: límites declarados y modelo local solo loopback | Automático |
| AC-F7-11 | Modo `claude-code` aislado y sin clave: invocación sin herramientas ni persistencia, prompt por stdin, directorio temporal, sin `ANTHROPIC_API_KEY`; `POST /api/mode`; `auto` nunca lo elige (`tests/test_modes.py`) | Automático (con CLI simulado; la corrida real se hizo aparte) |
| AC-F6-MANUAL-01 | Usuario externo completa la tarea sin ayuda | **Manual** (evidencia firmada) |

Los criterios que revisan la interfaz (AC-F7-04, 05, 07, 08) comprueban que los elementos **existan en el código de la UI**; no sustituyen la demostración en vivo ni la prueba con una persona real.

---

## 5. Relación con la tabla de criterios del documento del reto

Los criterios 1 a 7 de la tabla del reto se cubren así (evidencia, no puntaje):

| Criterio del reto | Peso | Evidencia principal |
|---|---|---|
| 1. Pruebas de funcionalidad y equivalencia | 25 % | Paso 5; `reportes/equivalencia.md`; pruebas unitarias generadas con cobertura (93,67 % líneas / 83,33 % ramas en la muestra COBOL con motor local); E2/E3 declarados. |
| 2. Precisión en la extracción de reglas | 15 % | Paso 3; verificador de citas (`pipeline.verify_citations`); validación humana; catálogo versionado con SHA-256. |
| 3. Arquitectura | 15 % | Orquestación por etapas y agentes (`docs/MANUAL_DE_USUARIO.md` §2); código generado hexagonal; ADRs y OpenAPI en el paquete. |
| 4. Calidad de código | 15 % | Guardrails en `verify.scan_project` (dependencias entre capas, sin float, complejidad ≤ 10, SAST ligero); decimal exacto. |
| 5. Seguridad e IA responsable | 10 % | Enmascarado previo, compuerta de salida, ejecución aislada, auditoría encadenada, suites de seguridad (`tests/test_security.py`). |
| 6. Calidad de entregables y documentación | 10 % | Paquete `.zip` (informe ejecutivo, matriz de trazabilidad, reportes), README y este manual. |
| 7. Experiencia de usuario y demo | 10 % | Flujo guiado, guion de 10 minutos (`docs/GUION_DEMO.md`), tablero y plan de contingencia (modo local o `replay`). |

Condiciones habilitantes del reto: el flujo completo se ejecuta en la demostración; la equivalencia se demuestra con casos de borde (con la salvedad de E2/E3 explicada arriba); y solo se usan datos sintéticos, sin secretos ni credenciales reales.
