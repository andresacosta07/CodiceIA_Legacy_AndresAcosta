# ADR-003: Orquestador propio con máquina de estados + Claude Agent SDK

**Estado:** Propuesto (se acepta al iniciar F0)
**Fecha:** 2026-11-13

## Contexto
El Word exige agentes especializados coordinados por un orquestador con estado y puntos de aprobación humana; la aceptación exige reproducibilidad y gates.

## Decisión
Orquestador propio (máquina de estados persistida en PostgreSQL) que invoca agentes basados en Claude Agent SDK/SDK de Anthropic con plantillas de prompt versionadas y salida JSON Schema.

## Consecuencias
Control explícito de gates, HITL, auditoría y costos. Se descarta LangChain/LangGraph como núcleo (abstracción opaca, más difícil de auditar). Se mantiene la posibilidad de usar MCP para herramientas.

