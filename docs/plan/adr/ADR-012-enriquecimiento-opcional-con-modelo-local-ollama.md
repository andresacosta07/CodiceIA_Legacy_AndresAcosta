# ADR-012: Enriquecimiento opcional con un modelo de IA local (Ollama), solo redacción

**Estado:** Aceptado
**Fecha:** 2026-11-13

## Contexto
El usuario pidió poder usar un modelo de IA económico sin clave de API para que el modo local no quede tan limitado. Un modelo pequeño local no es fiable para extraer reglas, generar código ni citar líneas.

## Decisión
`copilot/local_llm.py` usa Ollama **solo si** está instalado y en ejecución y se define `COPILOT_OLLAMA_MODEL`. Alcance deliberadamente acotado: reescribir en lenguaje de negocio las **descripciones** de las reglas y el **resumen ejecutivo** (salida JSON con esquema). Lógica, condiciones, acciones, citas, código y pruebas siguen siendo deterministas.
- **Solo loopback** (`127.0.0.1`/`localhost`); cualquier otro host lanza `RuntimeError`.
- Validación estricta de la salida: ids existentes, longitudes acotadas; lo demás se ignora.
- **Fallback:** si no hay servidor, hay error o la salida es inválida, se conserva el texto determinista. Cuando se aplica, la regla registra en sus supuestos el modelo usado.

## Consecuencias
- Aporta lenguaje más natural sin clave y sin enviar datos fuera del equipo.
- **No se ha probado contra un Ollama real en este equipo** (hardware compatible, pero no instalado); está cubierto con pruebas con servidor simulado (`test_optional_local_model_enrichment_is_safe`, `test_local_model_host_must_be_loopback`).
- Un modelo pequeño puede redactar mal; por eso solo toca textos y se puede revisar/ajustar en la validación humana.
