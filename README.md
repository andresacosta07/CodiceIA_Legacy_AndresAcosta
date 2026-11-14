# Copiloto de Modernización y Descubrimiento de Código Legacy

Prototipo con calidad de demo: ingiere código legacy, descubre y formaliza **reglas de negocio con trazabilidad a líneas de origen**,
las somete a **validación humana**, genera código moderno con **arquitectura limpia**, demuestra **equivalencia funcional** y entrega
un paquete (código, pruebas, documentación, reportes e informe ejecutivo).

## ¿Qué manual uso?
| Si la audiencia es… | Use |
|---|---|
| Personas **funcionales / de negocio / auditoría / directivos** (sin conocimientos técnicos) | [Manual funcional (no técnico)](docs/MANUAL_FUNCIONAL_NO_TECNICO.md) |
| **Ingenieros, arquitectos, DevOps, seguridad** | [Manual técnico](docs/MANUAL_TECNICO.md) |
| **Mezcla de ambos** (jurado, comité, demo general) | [Manual combinado](docs/MANUAL_DE_USUARIO.md) |

**Más documentación:** [Guion de la demo](docs/GUION_DEMO.md) · [Rúbrica y evidencias](docs/RUBRICA_Y_EVIDENCIAS.md) · [Plan y arquitectura](docs/plan/) · [Convenciones](CLAUDE.md)

**Lenguaje principal:** Python (backend FastAPI) + JavaScript (interfaz). El código que **genera** la solución es **TypeScript** (Node.js); la entrada que analiza es **COBOL** (y otros con el motor Claude).

**Aprender a usarla:** [Guía de entrenamiento (30 minutos)](docs/GUIA_ENTRENAMIENTO_DEMO.md). La propia interfaz incluye una **guía interactiva** (botón ««?» (botón flotante)» y «▶ Recorrido de esta pantalla»), ayudas «ⓘ» con lenguaje simple y una barra «Siguiente» que indica qué falta para avanzar.

## Ejecutar (un solo comando)

- **Windows:** doble clic en **`iniciar.bat`** (o `iniciar_claude.bat` para Claude vía suscripción). Abre el navegador solo.
- **Terminal:** `py run.py` (Windows; el alias «python» de la Tienda no sirve) · `python3 run.py` (Linux/macOS).
- **Diagnóstico del equipo:** `py run.py --check` (Python, Node, Claude Code, clave, datos de ejemplo, pregrabado).
- Opciones: `--claude` (Claude vía suscripción, sin clave de API) · `--rapido` (perfil de modelos más veloz pero menos profundo, ADR-018) · `--no-browser`. El motor de IA también se cambia desde el selector «Motor».

### ¿Qué cuenta o clave necesito para usar la IA? (léalo antes de compartir o instalar)
**Este repositorio no incluye ninguna clave, sesión ni suscripción de nadie.** Quien lo descargue usa **la suya propia**; la suscripción de quien lo publicó no viaja con el código (la sesión de `claude` vive en el perfil de cada usuario, fuera del proyecto, y `.env` está en `.gitignore`).

| Quiero… | Qué necesito | Cómo |
|---|---|---|
| Probar sin cuenta y sin internet (solo COBOL de formato fijo, subconjunto) | Nada | Motor **«Sin IA»** (por defecto) |
| Repetir una corrida ya grabada | Nada | Motor **«Pregrabado»** (usa `cassettes/`; solo reproduce lo grabado con el mismo ZIP y los mismos pasos) |
| Analizar cualquier lenguaje con IA usando una suscripción | **Su propia suscripción de Claude** y la herramienta Claude Code instalada, con sesión iniciada (ejecutar `claude` una vez) | `py run.py --claude` o elegir «Con IA» en el selector |
| Usar la API de pago | **Su propia clave** `ANTHROPIC_API_KEY` en un archivo `.env` local (copie `.env.example`) | Modo `live` (**no probado en vivo**) |

- La suscripción es personal y está sujeta a los términos y límites de su plan: no comparta su sesión ni su clave.
- **Solo está implementada la IA de Claude.** Otras IA (OpenAI, Gemini, etc.) **no** están integradas; Ollama (local) es opcional y solo redacta textos.
- En los modos `claude-code` y `live`, el código **ya enmascarado** sale hacia Anthropic: use solo datos sintéticos salvo que su organización lo autorice.

Requisitos: Python 3.10+ y Node.js 24 o superior (ejecuta y prueba el TypeScript generado). No requiere Docker. La primera vez crea `.venv` e instala dependencias (necesita Internet; ~1 min). Si el puerto 8000 está ocupado usa el siguiente libre.

## Cuatro modos de IA (variable `COPILOT_LLM`, o selector «Motor» en la interfaz)

| Modo | Cuándo se usa | Qué hace |
|---|---|---|
| **`local`** | `COPILOT_LLM=local`, o `auto` **sin clave (es el modo por defecto sin clave)** | **Motor determinista, sin IA, sin red y con costo 0.** Parser de un subconjunto de COBOL (`copilot/cobol.py`), extracción de reglas desde el AST, transpiladores a TypeScript y a Python, casos de prueba por valores frontera. **Solo COBOL (subconjunto) y solo destino TypeScript.** |
| **`claude-code`** (extensión con IA, **sin clave de API**) | `py run.py --claude`, `COPILOT_LLM=claude-code`, o elegirlo en el selector «Motor». **Siempre explícito**: `auto` nunca lo elige. | Claude trabaja a través del CLI `claude` (Claude Code) con **su suscripción**, no con la API de pago. Cualquier lenguaje legacy; destinos TypeScript, Java y C#. Costo 0 en la app (incluido en la suscripción, sujeto a los límites del plan). Graba cassettes. Ver abajo. |
| **`live`** | `COPILOT_LLM=live`, o `auto` con `ANTHROPIC_API_KEY` válida en el entorno o en `.env` | Llama a la API de Claude por etapa (modelos en `config/models.json`), graba cada respuesta en `cassettes/`. **No se ha probado en vivo** (no hubo clave de API). |
| **`replay`** | `COPILOT_LLM=replay` | Reproduce respuestas grabadas en `cassettes/` (contingencia sin red). Las cassettes las generan los modos `claude-code` o `live`: requiere una corrida previa con alguno de ellos. |

`COPILOT_LLM=auto` (por defecto): clave → `live`; sin clave → `local`. Una clave de ejemplo o incompleta en `.env` (menos de 30 caracteres o que contenga «REEMPLACE») se ignora y cuenta como «sin clave». La procedencia (`local` / `claude-code` / `live` / `replay`) queda registrada por etapa y se rotula en la UI y en los reportes. El modo se puede cambiar en caliente desde la UI (`POST /api/mode`); solo se ofrecen los modos disponibles.

### Claude vía suscripción de Claude Code (sin clave de API) — extensión opcional
Requisitos: el comando `claude` en el `PATH` y la **sesión iniciada** (`claude` interactivo una vez). Arranque: `py run.py --claude` (fija `COPILOT_LLM=claude-code`) o elegir «◆ Claude vía suscripción» en el selector.
- **Aislamiento:** cada etapa invoca `claude -p --output-format json --tools "" --no-session-persistence --model <id> --effort <nivel> --system-prompt … --json-schema …`; el prompt va por stdin, el directorio de trabajo es una carpeta temporal vacía y se elimina `ANTHROPIC_API_KEY` del entorno del proceso hijo para forzar la suscripción. La compuerta de enmascarado se aplica igual antes de enviar y la salida pasa por los mismos verificadores deterministas (esquemas, citas reales, guardrails, equivalencia).
- **Resultado real (una corrida con la muestra COBOL y casos aportados, 346 s en total):** analyze 32 s, rules 87 s (Opus 5.5), codegen 106 s, oracle 33 s, qa_cases 30 s, docs 53 s. 14 reglas, todas con cita verificada (confianza 0,85–0,98) · 65/65 casos equivalentes (E2+E3), 0 diferencias · cobertura 98,43 % líneas / 94,79 % ramas · 0 hallazgos · complejidad máxima 3 · 0 iteraciones de autocorrección · trazabilidad 100 %. **Es una sola corrida:** la salida de un LLM puede variar; por eso la garantía son los verificadores deterministas.
- **Frente al motor local:** cualquier lenguaje, Java/C# generables (validación estática, **sin compilar**) y reglas en lenguaje de negocio; pero **~6 min por corrida**, depende de la sesión del CLI y de los límites de la suscripción, y **el código ya enmascarado sale hacia Anthropic** (revise la política de su organización).
- **No probado:** otros lenguajes distintos de COBOL (PL/SQL, RPG, Java) en esta máquina.

### Modelo de IA local opcional (Ollama) — sin clave
Si tiene [Ollama](https://ollama.com) instalado y en ejecución, defina `COPILOT_OLLAMA_MODEL=<modelo>` (p. ej. `qwen2.5:7b`). En modo `local` ese modelo **solo redacta textos**
(descripciones de reglas en lenguaje de negocio y el resumen ejecutivo); lógica, citas, código y pruebas siguen siendo deterministas. Solo se admite un servidor en loopback
(`127.0.0.1`/`localhost`); si no responde o devuelve algo inválido se conserva el texto determinista. **Cubierto por pruebas unitarias con el servidor simulado; no probado contra un Ollama real en este equipo.**

## Flujo (8 fases del reto → 6 pasos de la UI)
1. **Ingesta**: archivo, ZIP, pegado o **repositorio Git público** (solo lectura, ADR-017); lenguaje/dialecto/EBCDIC; copybooks; **enmascarado de secretos/PII** (compuerta: 0 residuos).
2. **Descubrimiento**: analizador estático COBOL determinista (o heurístico) + Analista: unidades, grafo, métricas, código muerto, riesgos, contrato de E/S.
3. **Reglas + validación humana**: Extractor, esquemas validados, **verificador anti-alucinación de citas**, confianza; el ingeniero aprueba/ajusta/rechaza.
4. **Código**: Arquitecto/Desarrollador; TypeScript ejecutado; Java/C# (solo con API) con validación estática, **sin compilar**.
5. **Equivalencia**: casos de borde con oráculo independiente (E3) y/o casos aportados (E2), tolerancia 0; pruebas unitarias con cobertura; autocorrección (modo `live`).
6. **Entrega**: documentación, matriz de trazabilidad, informe ejecutivo, comparación con el proceso manual, caso de negocio interactivo, paquete `.zip`.

## Resultado de referencia (muestra COBOL `cobol_amortizacion`, modo `local`, con casos aportados)
11 reglas con cita verificada · 67/67 casos equivalentes (25 E2 independientes + 42 E3), 0 diferencias · cobertura 93,7 % líneas / 83,3 % ramas · 0 hallazgos críticos · complejidad máxima 10 · trazabilidad 100 %. (Medido en una corrida; las pruebas exigen ≥ 80 % / ≥ 70 %.)

## Seguridad (detalle en `docs/plan/07_seguridad_y_modelo_de_amenazas.md`)
- Enmascarado antes de cualquier envío al modelo + compuerta de salida que **bloquea** si queda un secreto. Solo datos sintéticos.
- SQLite con **consultas parametrizadas** (suite de inyección SQL); ZIP-slip/ZIP-bomb/symlinks; validación estricta; cabeceras CSP/X-Frame; rate limit; UI sin `innerHTML`.
- El código subido **nunca se ejecuta**; el generado se analiza estáticamente y se ejecuta con `node --permission` (sin red/archivos/procesos); el oráculo Python se valida por AST y se ejecuta con `python -I`.
- El código legacy se envía delimitado como dato no confiable (prompt injection); auditoría encadenada por hash; borrado de proyecto verificable.

## Pruebas y aceptación
```powershell
.\.venv\Scripts\python -m pytest tests -q                     # 121 pruebas
py scripts\acceptance\run_acceptance.py --fase 7           # una fase (0–7)
py scripts\acceptance\run_acceptance.py --todas            # regresión (código de salida != 0 si falla algo)
```
Reportes en `reports/acceptance/`. Fases 0–6 = MVP; fase 7 = rúbrica de Visión de Cliente y Negocio. El criterio manual `AC-F6-MANUAL-01` (usuario externo) queda
`MANUAL-PENDIENTE` hasta que exista `evidence/AC-F6-MANUAL-01.json` firmado; con `--estricto` cuenta como FAIL.

## Límites conocidos
- El **motor local** solo entiende un subconjunto de COBOL de formato fijo (sin OCCURS/REDEFINES, PERFORM VARYING, SORT, STRING…); ante algo fuera del subconjunto falla con la línea indicada. Para otros lenguajes (PL/SQL, RPG, Java) o destinos Java/C# se requiere la API de Claude.
- **No se ejecuta el legacy** (no hay runtime): la equivalencia declara su nivel de evidencia (E2 casos aportados / E3 oráculo derivado de un segundo traductor) y nunca presenta E3 como ejecución del legacy.
- Java y C# se generan (solo con IA: `claude-code` o `live`) y se validan estáticamente, pero **no se compilan** aquí.
- En modo `claude-code` el código **enmascarado** sale hacia Anthropic a través de su sesión de Claude Code; el modo `local` no envía nada a ninguna red.
- Las reglas rechazadas en revisión no se excluyen del código en modo `local` (transpila el programa completo; se declara en los supuestos).
- Sin conexión a Git, RAG, PostgreSQL ni Docker (ver «planeado vs implementado» en `docs/plan/01_arquitectura_solucion.md`).
