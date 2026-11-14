# ADR-005: Enmascaramiento previo al LLM, allowlist de egreso y despliegue privado

**Estado:** Propuesto (se acepta al iniciar F0)
**Fecha:** 2026-11-13

## Contexto
El código fuente es un activo sensible y el Word descalifica por datos reales o secretos.

## Decisión
Todo texto enviado al LLM pasa por el enmascarador; si queda residuo se bloquea. Egreso solo al endpoint del proveedor. Logs con hash. Opción de Bedrock/Vertex/on-premise documentada y completada en F8.

## Consecuencias
Menor riesgo de fuga; costo de falsos positivos del enmascarador; el mapa reversible debe protegerse.

