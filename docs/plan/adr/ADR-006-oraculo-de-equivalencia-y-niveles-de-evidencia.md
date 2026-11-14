# ADR-006: Oráculo de equivalencia con niveles de evidencia E1/E2/E3

**Estado:** Propuesto (se acepta al iniciar F0)
**Fecha:** 2026-11-13

## Contexto
Con código legacy desconocido puede no haber runtime para ejecutarlo; la equivalencia es la condición habilitante del Word.

## Decisión
Tres niveles: E1 ejecutado (GnuCOBOL u otro runtime), E2 casos aportados, E3 derivado de reglas aprobadas por implementación independiente. El reporte declara el nivel por caso y nunca presenta E3 como E1.

## Consecuencias
Honestidad verificable ante auditoría. Si solo hay E3, la fuerza probatoria es menor (ver P-01).

