# ADR-009: Seguridad como eje transversal con criterios por fase

**Estado:** Propuesto (se acepta al iniciar F0)
**Fecha:** 2026-11-13

## Contexto
El usuario exige que el código no se filtre y que la app resista ataques, incluida la inyección SQL.

## Decisión
Cada fase incluye criterios AC-Fx-SEC-nn comprobados por security_checks.py; modelo STRIDE/OWASP en 07; SQL solo parametrizado con suite de inyección; ZAP en F6.

## Consecuencias
Mayor esfuerzo por fase, a cambio de evidencia verificable y cumplimiento de la condición de descalificación.

