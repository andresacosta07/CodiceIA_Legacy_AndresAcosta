# ADR-010: Sandbox efímero sin red para compilar y probar

**Estado:** Propuesto (se acepta al iniciar F0)
**Fecha:** 2026-11-13

## Contexto
El código generado y el oráculo se ejecutan en el sistema; no debe comprometer el host ni exfiltrar datos.

## Decisión
Contenedor efímero por ejecución, sin red, usuario sin privilegios, FS de solo lectura salvo /work, límites de recursos, imagen fijada por digest. El código subido nunca se ejecuta.

## Consecuencias
Aislamiento sólido; las dependencias deben pre-cargarse en la imagen (sin descarga en ejecución).


## Ajuste en la implementación
Sin Docker, el aislamiento se resolvió con escaneo estático + **
ode --permission** (sin red, procesos ni escritura) para la equivalencia; el oráculo Python con validación por AST y python -I. La cobertura corre sin --permission (incompatible) con mitigaciones. Ver ADR-013.
