# ADR-011: Motor local determinista sin IA para operar sin clave de API

**Estado:** Aceptado
**Fecha:** 2026-11-13

## Contexto
No hay clave de API ni presupuesto para ella (la suscripción Pro no incluye crédito de API) y la entrega es hoy. La aplicación debe seguir siendo funcional y demostrable a costo 0. El código de la demo es desconocido.

## Decisión
Implementar un **motor local determinista** que cumple los mismos contratos (esquemas) que los agentes y se activa cuando no hay clave (`COPILOT_LLM=auto` → `local`):
- `copilot/cobol.py`: parser de un **subconjunto de COBOL de formato fijo** → AST (MOVE, COMPUTE [ROUNDED], ADD, SUBTRACT, MULTIPLY, DIVIDE, IF/ELSE, EVALUATE, PERFORM [THRU/UNTIL/N TIMES], GO TO, GOBACK, copybooks; infraestructura OPEN/CLOSE/READ/WRITE/DISPLAY/EXEC SQL aislada). Lo no soportado lanza `UnsupportedConstruct` con la línea.
- `copilot/local_engine.py`: análisis (unidades, clasificación, riesgos, contrato de E/S), reglas desde el AST con cita literal (verificada por el mismo verificador de citas), código TypeScript con arquitectura limpia (flujo `PERFORM`/`GO TO`/fall-through como valores de flujo; código muerto no migrado), **segundo traductor a Python** que actúa como oráculo derivado (evidencia **E3**), casos de prueba por valores frontera y documentación.
- `runtime/decimal.ts`: `Decimal` exacto con `toPic` (ROUNDED = HALF_UP, truncamiento, truncado de PIC); divisiones intermedias a 30 decimales truncadas; potencia entera exacta.
- Procedencia rotulada (ADR-014).

## Consecuencias
- Funciona sin red y con costo 0; resultados reproducibles. Corrida de referencia: 67/67 casos equivalentes (25 E2 independientes escritos a mano + 42 E3).
- **Límites:** solo COBOL (subconjunto) y solo destino TypeScript; Java/C# y otros lenguajes requieren la API. Las descripciones de reglas salen de comentarios del código o de plantillas. Las reglas rechazadas en revisión no se excluyen del código (transpila el programa completo; se declara en los supuestos).
- E3 comparte el AST con el transpilador TypeScript: un error de parseo sería común a ambos; por eso se exige además la referencia independiente E2 escrita a mano.
- El legacy **no se ejecuta** (no hay runtime COBOL).

## Límites conocidos tras la revisión independiente (motor local)
Un subagente de Claude Code revisó el código en modo solo lectura. Se corrigieron: inyección vía nombres/categorías en el archivo de pruebas generado, comentarios `//` dentro de cadenas que ocultaban código en el escáner, lista ampliada de módulos prohibidos, mezcla entre proyectos en la caché del motor local (ahora la clave incluye el hash del fuente), exponentes fraccionarios (ahora se rechazan), enmascarado por límites de palabra (`PASSED` ya no se enmascara), validación estricta del host del modelo local, cifras nuevas del modelo local (se descarta el texto) y nombres de método de párrafo (prefijo `para`).

**Siguen abiertos (declarados, no ocultos):**
- Las entradas/salidas se infieren por uso: un campo que se lee y luego se actualiza (acumulador) se trata como salida y arranca en 0; revise el contrato de E/S en el paso 2.
- El «oráculo» (segundo traductor) comparte parser y análisis con el generador: es evidencia E3 de consistencia, no una ejecución del legacy. Los casos que el oráculo no puede calcular se descartan y se listan en `verification.oracle_discarded`.
- Semántica alfanumérica simplificada (sin relleno de blancos de COBOL en comparaciones).
- El enmascarado puede alterar literales de negocio parecidos a secretos; la compuerta solo informa el conteo.
- Las reglas rechazadas o editadas por el revisor no modifican el código en modo local (se transpila el programa completo).
- La cobertura V8 corre sin `--permission`; no hay aislamiento de red garantizado en todas las versiones de Node; no hay autenticación (uso local de demostración, `X-Reviewer` es informativo).
- Sin límite para cargas con `Transfer-Encoding: chunked` fuera de los límites por archivo.
