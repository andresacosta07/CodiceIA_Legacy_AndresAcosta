# ADR-018: Perfil de modelos «rápido» opcional (velocidad vs. profundidad del análisis)

**Estado:** Aceptado (opcional; el perfil estándar sigue siendo el predeterminado)
**Fecha:** 2026-11-13

## Contexto
Con `claude-code` una corrida completa del paquete PL/SQL de siniestros tardaba ≈ 14 min (estándar). Midiendo las llamadas (`llm_calls`), el tiempo es casi todo **texto generado**: ≈ 120 tokens/s con Opus y 180–200 con Sonnet. Etapas más largas (corrida estándar): generación de código ≈ 280–300 s, reglas (Opus) ≈ 186–241 s, casos de prueba ≈ 177–212 s, documentación ≈ 58–72 s, oráculo ≈ 60–90 s, análisis ≈ 40 s. Además, el oráculo se llamaba dos veces por un defecto del sandbox (corregido), sumando ≈ 60 s.

## Decisión
1. Se añade un **perfil rápido opcional**: `config/models.fast.json` sobrescribe solo algunas etapas (análisis y código con esfuerzo `low`; reglas y oráculo con Sonnet en lugar de Opus; casos de prueba y documentación con Haiku). Se activa con `COPILOT_PROFILE=fast` o `py run.py --rapido`; la API de estado informa `profile`.
2. **El perfil estándar no cambia** (`config/models.json`): el modelo forma parte del hash de las grabaciones (cassettes), así que cambiar el estándar invalidaría las grabaciones y `test_replay_recorded`. El perfil rápido graba las suyas.
3. Una prueba (`tests/test_profiles.py`) verifica que el estándar queda intacto, que solo se sobrescriben etapas existentes y que solo se usan modelos con precio conocido.

## Medición (mismo ZIP de demo de 4 archivos, 559 LOC, TypeScript, `claude-code`)
| | Estándar (Opus en reglas y oráculo) | Rápido |
|---|---|---|
| Reglas extraídas | 29 (29 con cita verificada) | 22 (21 verificadas, **1 con cita fallida → compuerta de reglas `gate_failed`**); en otra corrida, 18 (todas verificadas) |
| Unidades / riesgos / hallazgos de seguridad del legacy | 29 / 11 / 4 | 17 / 6 / 2 |
| Funciones sin uso documentadas como código muerto | Sí (4 reglas «no utilizado») | No |
| Análisis + reglas (corridas simultáneas, no comparables en tiempo) | 265 s | 120 s |
| Corrida completa (rápido, a solas) | ≈ 14,6 min (ZIP de 6 archivos, con el defecto del oráculo) | **581 s (9,7 min)**: equivalencia 100 % (40 casos, E3), cobertura 96,9 % líneas / 90,9 % ramas, 0 hallazgos críticos, trazabilidad 100 %, sin autocorrección |

## Consecuencias
- **Ganancia real:** ≈ 30–40 % menos tiempo total; el tramo que más baja es reglas (Opus → Sonnet) y generación de código (esfuerzo `low`).
- **Costo en profundidad:** menos reglas, menos riesgos y hallazgos de seguridad, y no documenta el código muerto; la compuerta de citas puede fallar y exigir rechazar una regla a mano. Las citas se verifican de forma determinista y el humano aprueba, por lo que el riesgo es de **omisión**, no de invención.
- **Haiku en casos de prueba no mejoró el tiempo** (≈ 200 s; generó más texto que Sonnet). El cuello de botella restante son los casos de prueba (≈ 24–40 casos con todas las entradas) y la generación de código.
- **Resultados no deterministas:** dos corridas rápidas dieron 18 y 22 reglas; una sola medición no basta para afirmar una cifra.
- **Recomendación:** para la demostración en vivo, usar «Pregrabado» con una corrida estándar previa; usar el perfil rápido solo si se acepta la menor profundidad. Una variante intermedia (análisis y reglas como en el estándar; solo código, oráculo y documentación más rápidos) **no se midió**.
