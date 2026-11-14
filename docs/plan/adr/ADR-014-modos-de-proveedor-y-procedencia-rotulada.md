# ADR-014: Modos de proveedor (live / local / replay) y procedencia rotulada

**Estado:** Aceptado
**Fecha:** 2026-11-13

## Contexto
La aplicación puede obtener las salidas de los agentes de tres fuentes de distinta naturaleza. El usuario final y el evaluador deben saber siempre cuál se usó; no se debe presentar una salida determinista o grabada como si fuera IA en vivo.

## Decisión
- `COPILOT_LLM` ∈ {`auto`, `live`, `local`, `replay`}. `auto`: clave de API válida → `live`; si no → `local`. Una clave de ejemplo o incompleta en `.env` (< 30 caracteres o con «REEMPLACE») se ignora.
- `live`: API de Claude con salidas JSON Schema, graba cassettes en `cassettes/` (clave por hash del prompt).
- `local`: motor determinista (ADR-011), con enriquecimiento opcional de redacción (ADR-012).
- `replay`: solo cassettes; error claro si falta una.
- Todas pasan por la **misma compuerta de salida** (enmascarado) y los **mismos verificadores** (esquemas, citas, guardrails, equivalencia).
- Procedencia: cada llamada se registra en `llm_calls` con `source` (`live`/`local`/`replay`/`provider`); en modo local el modelo se guarda como «motor local (sin IA)» y el costo es 0. La UI muestra una insignia del modo activo («● IA en vivo (Claude)», «⚙ Motor local determinista (sin IA)», «■ Contingencia (pregrabado)») y el tablero de costos muestra la fuente por etapa. `provider` es el hook de pruebas (`tests/fake_llm.py`, no es un modelo).

## Ajuste posterior (ADR-015)
Se añadió un **cuarto modo, `claude-code`** (Claude vía el CLI de Claude Code con la suscripción del usuario, sin clave de API). `COPILOT_LLM` ∈ {`auto`, `local`, `claude-code`, `live`, `replay`}; `auto` **nunca** elige `claude-code`. El modo se puede cambiar en caliente (`POST /api/mode`, selector «Motor de IA»; `MODE_OVERRIDE` tiene prioridad sobre la variable de entorno). Procedencia: `source=claude-code`, modelo rotulado «<modelo> (suscripción)», costo 0; graba cassettes como `live`. La insignia/selector añaden «◆ Claude vía suscripción (sin clave de API)».

## Consecuencias
- Transparencia ante la evaluación; reproducibilidad en CI y contingencia.
- En modo local el selector de destino deshabilita Java y C#, y la etapa de generación falla con un mensaje claro si se fuerzan.
- Las cassettes de un modelo real las generan `claude-code` o `live`: `replay` solo es útil tras una corrida con alguno de ellos (hay una corrida real con `claude-code` sobre la muestra COBOL; confirmar que `cassettes/` la contiene antes de depender de `replay`).
