# ADR-007: Modelo de IA por etapa, configurable y verificado

**Estado:** Propuesto (se acepta al iniciar F0)
**Fecha:** 2026-11-13

## Contexto
El prompt propone Haiku/Sonnet/Opus/Fable según la etapa; los IDs deben verificarse en la documentación oficial.

## Decisión
config/models.yaml mapea etapa → modelo, con validación por esquema y verificación de IDs al inicio de F0. Nada de IDs fijos en código.

## Consecuencias
Permite cambiar modelo sin redeploy y medir costo por etapa; requiere pruebas de compatibilidad.

