# ADR-004: Script de aceptación multiplataforma en Python (stdlib)

**Estado:** Propuesto (se acepta al iniciar F0)
**Fecha:** 2026-11-13

## Contexto
Los criterios deben verificarse automáticamente en Windows (VS Code) y Linux/macOS (CI).

## Decisión
scripts/acceptance/run_acceptance.py con módulos por fase, solo biblioteca estándar en el núcleo, reportes .md/.json y exit code distinto de 0 si falla.

## Consecuencias
Portabilidad y cero dependencias. Se descartan Bash/PowerShell (no portables) y Node/TS (segundo toolchain para el ejecutor).

