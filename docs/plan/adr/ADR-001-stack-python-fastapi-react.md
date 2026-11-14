# ADR-001: Stack de la app — Python + FastAPI + React/TypeScript

**Estado:** Propuesto (se acepta al iniciar F0)
**Fecha:** 2026-11-13

## Contexto
El Word no restringe el stack. Se necesita un prototipo con SDK de IA, parsers y agentes, y una UI de revisión rica.

## Decisión
Backend Python 3.12 + FastAPI + Pydantic; frontend React + TypeScript (Vite); PostgreSQL; Docker Compose.

## Consecuencias
Ecosistema de IA maduro y desarrollo rápido. Dos lenguajes en el repo (Python y TS). Se descartan NestJS (parsers y SDK de agentes menos maduros) y Spring Boot (pesado para un prototipo).


## Ajuste en la implementación
El frontend se implementó en **JavaScript vanilla** (sin React/Vite ni build), sin innerHTML. Backend Python + FastAPI sin cambios. Ver ADR-013.
