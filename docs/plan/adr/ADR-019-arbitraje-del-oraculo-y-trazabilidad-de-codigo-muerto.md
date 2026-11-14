# ADR-019: Arbitraje del oráculo, casos complementarios y código muerto en la trazabilidad

**Estado:** Aceptado
**Fecha:** 2026-11-13

## Contexto
En una corrida manual con el paquete PL/SQL de siniestros (perfil estándar) las dos últimas fases quedaron en advertencia:
1. **Equivalencia 97,83 % (45/46).** El caso `parametro_faltante_factor_inflacion` falló porque el oráculo (segundo traductor, evidencia E3) esperaba «APROBADA», pero el legacy llama `fn_param_num('FACTOR_INFLACION')` siempre (línea 375) y, si falta, lanza `ORA-20010`; el TypeScript hacía exactamente eso. El autocorrector lo concluyó dos veces («no cambié el código») pero el sistema solo sabe corregir **código**, no al oráculo; quedaba atascado y las pruebas unitarias/cobertura se omitían.
2. **Trazabilidad 82,1 %.** Cinco reglas «huérfanas»: cuatro describían código sin uso/obsoleto (se documentan, no se migran) y una regla viva no tenía ningún caso de prueba.
Además, una corrida de `claude-code` sobre un ejemplo ya grabado **sobrescribió** la respuesta grabada de su etapa de análisis y dejó inconsistente el replay del ejemplo COBOL (`test_replay_recorded`).

## Decisión
1. **Arbitraje del oráculo** (`delivery._revise_oracle`): si tras una autocorrección el código de producción no cambió y solo discrepan casos E3, se pide **una sola vez** al oráculo una segunda lectura **solo del legacy** (no ve el código nuevo; recibe sus propios resultados, los de la otra implementación y la observación del autocorrector, con la instrucción de no adaptarse sin evidencia en el legacy). Si corrige, se recalculan los esperados de los casos E3 y se vuelve a comparar. **Los casos aportados por el cliente (E2) nunca se arbitran.** Queda en `verification.oracle_arbitration` (casos, cuáles cambiaron, nota). Si el oráculo mantiene su postura, la discrepancia sigue siendo un fallo visible.
2. **Casos complementarios:** si tras la generación de casos hay reglas aprobadas vivas sin ningún caso, se hace **una segunda llamada corta** de QA solo para ellas (2–3 casos por regla). Es opcional: si falla, la matriz muestra la regla sin pruebas.
3. **Código muerto en la trazabilidad:** una regla cuyo nombre/descripción dice «no utilizado», «obsoleto», «código muerto» o «nunca se invoca» **y** no tiene código generado se marca `dead` (no aplica): se documenta, no se cuenta como huérfana ni entra en el porcentaje y la matriz lo indica. Es una heurística de texto, visible y reversible rechazando/aprobando reglas.
4. **Validación del oráculo revisado:** en la primera corrida real el oráculo SÍ se corrigió («mi versión anterior estaba equivocada… la línea 375 decide»), pero el validador rechazó su código por `super().__init__` en su clase de error (`atributo prohibido: __init__`) y el sandbox no tenía `super`. Se admite `__init__` (solo ese atributo especial; `__class__`, `__globals__`, `__dict__`… siguen vetados) y los builtins `super`, `object`, `RuntimeError` y `OverflowError`; la revisión del oráculo tiene **2 intentos** (el segundo con el error). Las reglas de código muerto tampoco figuran en «reglas sin caso de prueba».
5. **Grabaciones de solo escritura única:** `claude-code` y `live` ya no sobrescriben un cassette existente.
6. **Matriz de trazabilidad en la interfaz:** tarjeta a todo el ancho, columna de estado, rutas abreviadas a `archivo:líneas` (ruta completa al pasar el cursor) y columnas numéricas sin partir. Además, las tarjetas de dos columnas ya no se desbordan sobre su vecina.

## Consecuencias
- Un desacuerdo con el oráculo deja de bloquear la entrega **cuando el legacy respalda al código**, sin debilitar E2 ni ocultar discrepancias reales (siguen visibles y auditables en el informe).
- **Riesgo asumido:** el oráculo, al ser un LLM, podría «ceder» y alinearse con un código incorrecto; se mitiga no mostrándole el código nuevo y con el límite de una revisión, pero no se elimina. La evidencia sigue siendo E3 (no se ejecuta el legacy).
- Una llamada extra de IA como máximo en cada caso (casos complementarios; revisión del oráculo).
- **Validado** repitiendo desde las grabaciones la corrida real del caso de siniestros (ZIP de 6 archivos): equivalencia 100 % (41/41, E3), cobertura 97,05 % líneas / 91,32 % ramas, 0 hallazgos críticos, trazabilidad 100 % con 4 reglas de código muerto excluidas y el arbitraje aplicado. No se repitió una corrida **en vivo** completa con IA tras el último ajuste. El ejemplo COBOL se **regrabó** con una corrida completa (15 reglas verificadas, equivalencia 100 % con 61/61 casos E2+E3, cobertura 98,6 % / 96,8 %) y `test_replay_recorded` vuelve a pasar.
