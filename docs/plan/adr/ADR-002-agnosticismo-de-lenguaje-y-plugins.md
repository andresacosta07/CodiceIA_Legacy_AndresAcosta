# ADR-002: Diseño agnóstico al lenguaje con LanguageAdapter y plugins

**Estado:** Propuesto (se acepta al iniciar F0)
**Fecha:** 2026-11-13

## Contexto
El código de la demo lo entregan los organizadores y puede ser de cualquier lenguaje legacy; el Word pide reducir la dependencia exclusiva del LLM.

## Decisión
Interfaz LanguageAdapter con registro de plugins. Adaptador genérico (tree-sitter donde exista gramática + LLM con salida estructurada validada) como fallback; adaptador COBOL determinista primero. Se declara el nivel de rigor (determinista/híbrido/LLM) por artefacto.

## Consecuencias
Cubre lenguajes no previstos con menor rigor declarado. Mayor trabajo de validación cruzada AST↔LLM. Extensible sin tocar el núcleo (R-50).

