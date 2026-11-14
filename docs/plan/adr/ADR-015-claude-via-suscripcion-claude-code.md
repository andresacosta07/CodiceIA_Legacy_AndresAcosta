# ADR-015: Claude vía la suscripción de Claude Code (modo `claude-code`), sin clave de API

**Estado:** Aceptado
**Fecha:** 2026-11-13

## Contexto
El proyecto no dispone de presupuesto para una clave de la API de Claude (la suscripción Pro y la API se facturan por separado). El motor local determinista (ADR-011) funciona sin clave y sin costo, pero solo cubre un subconjunto de COBOL y solo genera TypeScript. El usuario pidió poder usar IA de Claude **sin depender de la clave de API**, como una **extensión adicional** y no como requisito. En el equipo existe el CLI `claude` (Claude Code, v2.1.322) con la sesión iniciada, que admite modo no interactivo (`-p`), salida JSON (`--output-format json`), validación por esquema (`--json-schema`), selección de modelo (`--model`) y de esfuerzo (`--effort`), y desactivación de herramientas (`--tools ""`).

## Decisión
Añadir un proveedor `claude-code` en `copilot/llm.py` (`_claude_code`):
- Cada etapa invoca `claude -p --output-format json --tools "" --no-session-persistence --model <id de config/models.json> --effort <nivel> --system-prompt <sistema> --json-schema <esquema endurecido>`; la salida estructurada se lee de `structured_output` (o de `result`) y se valida contra el esquema de la etapa.
- **Aislamiento:** sin herramientas (no puede leer/escribir archivos), sin persistencia de sesión, **prompt por stdin** (evita el límite de línea de comandos de Windows), directorio de trabajo = carpeta temporal vacía, y se **elimina `ANTHROPIC_API_KEY` del entorno hijo** para forzar el uso de la suscripción.
- Pasa por la **misma compuerta de salida** (enmascarado/`EgressBlocked`) y por los **mismos verificadores deterministas** (esquemas, citas reales, guardrails, equivalencia con tolerancia 0, autocorrección).
- **Explícito, nunca implícito:** `COPILOT_LLM=claude-code`, `py run.py --claude`, o el selector «Motor de IA» (`POST /api/mode`, `MODE_OVERRIDE`). `auto` jamás lo elige (clave → `live`; si no → `local`). `available_modes()` solo ofrece `claude-code` si `claude` está en el `PATH`.
- Procedencia (ADR-014): `llm_calls.source = claude-code`, modelo «<modelo> (suscripción)», costo 0 (incluido en la suscripción, sujeto a los límites del plan), tokens registrados; **graba cassettes**, por lo que sirven al modo `replay`.

## Consecuencias
**Positivas**
- Cualquier lenguaje legacy, destinos TypeScript, Java y C# (estos dos con validación estática, **sin compilar**), y reglas redactadas en lenguaje de negocio, sin clave ni costo de API.
- Resultado verificado en **una corrida real** (muestra COBOL con casos aportados, 346 s: analyze 32 s, rules 87 s, codegen 106 s, oracle 33 s, qa_cases 30 s, docs 53 s): 14 reglas con cita verificada (confianza 0,85–0,98), 65/65 casos equivalentes (E2+E3), 0 diferencias, cobertura 98,43 % / 94,79 %, 0 hallazgos, complejidad máxima 3, 0 autocorrecciones, trazabilidad 100 %. Es **una** corrida: los LLM varían entre ejecuciones; la garantía son los verificadores.
- Las corridas con IA producen cassettes reales para la contingencia `replay`.
- Cubierto por `tests/test_modes.py` (5 pruebas, con el CLI simulado): invocación aislada y sin clave, errores, cassette y costo 0, endpoint de modo, `auto` nunca elige `claude-code` (AC-F7-11).

**Negativas / riesgos**
- **Datos:** el código ya enmascarado sale hacia Anthropic a través de la sesión de Claude Code del usuario; revisar la política de la organización/contrato antes de usar código real (RK-25).
- **Dependencia** del CLI `claude` en el `PATH`, de la sesión iniciada y de los límites de la suscripción (RK-26); error claro con acción sugerida si falla.
- **Latencia:** ~6 min por corrida completa → la demo principal debe usar `local` o `replay`; `claude-code` se muestra con una corrida previa.
- **Alcance probado:** solo COBOL; PL/SQL, RPG y Java **no** se han probado con este modo. El modo `live` (API con clave) sigue **sin probarse**.
- Variabilidad entre corridas (RK-27); el proveedor no es determinista.

## Alternativas descartadas
1. **Ollama como modelo principal:** gratuito y sin clave, pero requiere instalar el servidor y descargar GBs de modelo, la calidad de un modelo de ~7B en salidas estructuradas largas (reglas con citas, código por capas) es incierta y no está instalado en el equipo. Se conserva solo como enriquecimiento opcional de redacción (ADR-012).
2. **API de pago (`live`) como única vía de IA:** no hay presupuesto; se mantiene disponible para quien tenga clave, pero no es requisito.
3. **Usar solo el motor local:** sin costo ni red, pero limitado a un subconjunto de COBOL y al destino TypeScript; no resuelve «código desconocido en otro lenguaje».
4. **Dejar que `auto` elija `claude-code` si encuentra el CLI:** se descartó por privacidad (enviaría código a un tercero sin decisión explícita) y por latencia.
