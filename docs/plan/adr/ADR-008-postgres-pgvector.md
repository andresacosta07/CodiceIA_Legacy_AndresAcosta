# ADR-008: PostgreSQL con pgvector para datos, cola y RAG

**Estado:** Propuesto (se acepta al iniciar F0)
**Fecha:** 2026-11-13

## Contexto
Se necesita almacén relacional, auditoría, cola simple y búsqueda semántica para RAG.

## Decisión
PostgreSQL 16 con pgvector; cola con SKIP LOCKED; migraciones con Alembic.

## Consecuencias
Menos componentes. Límite de escala de la cola, aceptable para MVP; migrable a Redis/RabbitMQ en F8.


## Ajuste en la implementación
Se usó **SQLite** (consultas parametrizadas, auditoría con hash encadenado) en lugar de PostgreSQL + pgvector; no hay cola SKIP LOCKED ni RAG. Ver ADR-013.
