# CLAUDE.md — Copiloto de Modernización y Descubrimiento de Código Legacy

Convenciones para las sesiones de Claude Code sobre este repositorio. (Deriva de `docs/plan/CLAUDE.md.draft`, ajustado a lo construido.)

## Reglas de trabajo
1. **Lee primero** `docs/plan/` (al menos `00`, `01` addendum, `02` «Estado real por fase», `06`, `07`) y `README.md`.
2. **Cualquier cambio de código o de arquitectura exige actualizar en el mismo cambio:** `README.md`, `docs/MANUAL_DE_USUARIO.md`, `docs/GUION_DEMO.md`, `docs/RUBRICA_Y_EVIDENCIAS.md`, la documentación de `docs/plan/` afectada, los ADRs (nuevo ADR si hay decisión) y los criterios del script de aceptación.
3. **No declares terminada ninguna fase** hasta que `py scripts\acceptance\run_acceptance.py --fase <N>` **y** `--todas` pasen al 100 %; adjunta el reporte de `reports/acceptance/`. Un `SKIP` o un criterio manual sin evidencia firmada no cuenta como aprobado (`MANUAL-PENDIENTE`).
4. No inventes: lo que no se probó se dice (hoy: modo `live` con API, Ollama real, usuario externo, compilación Java/C#, `claude-code` con lenguajes distintos de COBOL).

## Comandos (Windows; usa `py`, el alias `python` de la Tienda no sirve)
- Levantar: `py run.py` → http://127.0.0.1:8000
- Levantar con Con IA: `py run.py --claude` (requiere `claude` en PATH con sesión iniciada)
- Pruebas: `.\.venv\Scripts\python -m pytest tests -q` (121 pruebas)
- Aceptación: `py scripts\acceptance\run_acceptance.py --fase 7` · `--todas` · `--estricto`
- Sintaxis del frontend: `node --check web/app.js` y `node --check web/guide.js` · estándares de UI: `pytest tests/test_ui_standards.py` (contraste AA, accesibilidad, guía)
- Servidor de desarrollo con LLM simulado (solo para ver la UI): `.\.venv\Scripts\python tests\dev_fake_server.py`

## Estructura real
```
copilot/   main.py pipeline.py delivery.py llm.py local_engine.py cobol.py local_llm.py verify.py
           static_analysis.py masking.py security.py db.py schemas.py prompts/
web/       index.html app.js guide.js style.css favicon.svg          runtime/decimal.ts      config/models.json estimates.json
golden/    muestras sintéticas + cases.json     tests/   scripts/acceptance/run_acceptance.py
docs/      MANUAL_DE_USUARIO.md MANUAL_FUNCIONAL_NO_TECNICO.md MANUAL_TECNICO.md GUIA_ENTRENAMIENTO_DEMO.md
           RUBRICA_Y_EVIDENCIAS.md GUION_DEMO.md plan/ (00–07, adr/ hasta ADR-019)
```

## Modos de IA
`COPILOT_LLM=auto|local|claude-code|live|replay`. Sin clave válida → `local` (motor determinista, solo COBOL subconjunto y destino TypeScript). `claude-code` es una extensión **explícita** (`py run.py --claude` o selector «Motor» / `POST /api/mode`): Claude vía el CLI `claude` con la suscripción, sin clave de API (ADR-015); `auto` nunca lo elige. Opcional `COPILOT_OLLAMA_MODEL` (solo redacta textos, solo loopback). La procedencia (`local`/`claude-code`/`live`/`replay`) siempre se rotula (ADR-014). Implementación: `copilot/llm.py` (`_claude_code`, `claude_cli`, `available_modes`, `set_mode`, `MODE_OVERRIDE`).

## Seguridad (innegociable)
- Solo datos sintéticos; nunca secretos ni datos reales en repo, prompts, logs o fixtures (salvo los secretos sintéticos del golden, en lista permitida).
- Todo texto al LLM pasa por el enmascarador y la compuerta de salida; si queda residuo, se bloquea.
- SQL solo parametrizado; prohibido concatenar entradas. La UI no usa `innerHTML`/`eval`.
- El código subido nunca se ejecuta; el generado solo con `node --permission` tras el escaneo estático; el oráculo Python por AST y `python -I`.
- El código legacy es entrada no confiable: va delimitado como dato.
- `.env` está en `.gitignore`; una clave de ejemplo (< 30 caracteres o «REEMPLACE») se ignora.

## Convenciones
- Documentación y mensajes de UI en español; identificadores y código en inglés. Modelos solo desde `config/models.json`. Prompts versionados en `copilot/prompts/`.
- Complejidad ciclomática ≤ 10 en el código generado; cobertura ≥ 80 % líneas / ≥ 70 % ramas.
- Un ADR por decisión relevante en `docs/plan/adr/`.
