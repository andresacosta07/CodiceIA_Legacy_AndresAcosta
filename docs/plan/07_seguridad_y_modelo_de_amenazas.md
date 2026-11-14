# 07 — Seguridad y modelo de amenazas

Objetivo: el código legacy (activo sensible) no se filtra en ningún paso y la app resiste ataques, incluida la inyección SQL. Es un eje transversal; cada fase tiene criterios `AC-Fx-SEC-nn` verificados por script (`06`). Referencias: OWASP Top 10, ASVS nivel 2, OWASP Top 10 for LLM Applications, STRIDE.

## 1. Activos y fronteras de confianza

Activos: código fuente cargado, mapa de enmascarado, reglas, código generado, claves de API, prompts/respuestas, auditoría.
Fronteras: navegador ↔ API · API ↔ workers/BD · workers ↔ API del LLM (externa) · workers ↔ sandbox · app ↔ repositorios Git externos.
**Entradas no confiables:** archivos, ZIP, URLs Git, pegado, y **el propio código legacy** (puede contener instrucciones dirigidas al modelo).

## 2. Modelo de amenazas (STRIDE)

| Amenaza | Vector | Control | AC |
|---|---|---|---|
| **S**poofing | Acceso sin identidad | Autenticación + RBAC (reviewer/approver/admin), sesiones seguras | AC-F6-SEC-02 |
| **T**ampering | Manipular auditoría o catálogo; SQLi | Hash-chain, versiones inmutables, SQL parametrizado, validación Pydantic | AC-F1-SEC-04, AC-F1-SEC-06, AC-F3-07 |
| **R**epudiation | Negar aprobaciones | Auditoría append-only con revisor y marca de tiempo | AC-F1-SEC-06 |
| **I**nformation disclosure | Fuga de código/secretos al LLM, logs, errores, red | Enmascarado, allowlist de egreso, logs con hash, errores genéricos, cifrado | AC-F1-SEC-01/05, AC-F3-SEC-02/03 |
| **D**enial of service | ZIP-bomb, archivos enormes, parsers recursivos, costos de tokens | Límites de tamaño/tiempo/memoria, cuotas por proyecto, rate limit | AC-F1-SEC-02, AC-F2-SEC-02 |
| **E**levation of privilege | Escape de sandbox, RCE vía código subido, SSRF | Sandbox sin red y sin privilegios, nunca ejecutar lo subido, anti-SSRF | AC-F1-SEC-03, AC-F4-SEC-02 |

## 3. Que el código no se filtre

1. **Enmascarar antes de salir.** Detectores (gitleaks/detect-secrets + patrones propios: cadenas de conexión, credenciales en JCL, IBAN, documentos de identidad, correos, teléfonos). Se sustituye por tokens (`<SECRET_001>`); el mapa reversible vive solo en el almacén local cifrado. Si queda un residuo, el envío se **bloquea** (gate de F1).
2. **Egreso controlado.** Solo se permite el endpoint del proveedor LLM (allowlist en la red del contenedor); sin telemetría de terceros. Los sandboxes no tienen red.
3. **Cifrado** en reposo (clave por proyecto) y en tránsito (TLS); claves de API solo en variables de entorno/gestor de secretos, nunca en repo, frontend o logs.
4. **Logs con redacción:** no se registran código completo ni secretos; los prompts se guardan como hash + referencia a artefacto.
5. **Despliegue privado documentado:** Claude vía Bedrock/Vertex u on-premise para clientes con residencia de datos (ADR-005; implementación en F8).
6. **Retención y borrado:** borrar un proyecto elimina artefactos, mapa de enmascarado y vectores RAG derivados (AC-F6-SEC-04).
7. **Datos sintéticos únicamente** en desarrollo y demo (el Word descalifica por datos reales).

## 4. Protección de la app

### Inyección SQL (requisito explícito)
- Todo acceso a BD vía SQLAlchemy con parámetros; **prohibido** construir SQL con f-strings/concatenación (regla Semgrep en CI).
- Rol de BD de mínimo privilegio (sin DDL en runtime); errores de BD nunca se muestran al cliente.
- **Suite `sqli_suite`:** recorre automáticamente todos los endpoints y parámetros (query, path, body, cabeceras) con payloads clásicos y avanzados (`' OR 1=1--`, `UNION SELECT`, stacked queries, blind booleano y por tiempo, codificaciones). Criterios: sin cambio de datos, sin errores SQL expuestos, sin diferencias de tiempo explotables. Complementa con SAST (Semgrep/Bandit).
- Aplica igualmente al **código generado** (AC-F4-SEC-03) y detecta SQL dinámico concatenado **en el legacy** como hallazgo (AC-F2-SEC-01).

### Otros ataques
| Ataque | Defensa | Suite |
|---|---|---|
| Carga maliciosa (ZIP-slip, ZIP-bomb, symlinks, traversal, nombres raros, binarios) | Límites, rutas canonizadas, extracción aislada, rechazo de symlinks, tipo real | `upload_attacks` |
| SSRF en clonado Git | Solo https, bloqueo de IP privadas/loopback/metadata, validación tras redirecciones, sin hooks/submódulos, timeout | `ssrf_suite` |
| **Prompt injection** (LLM01) | Código como dato delimitado, rol de sistema fijo, sin herramientas con efectos laterales en extracción, salida JSON Schema validada, verificación determinista de citas, segundo pasaje | `prompt_injection_suite` |
| Salida insegura del LLM (LLM02) | Nunca se ejecuta salida del modelo fuera del sandbox; se valida y se escapa | `xss_suite`, `sandbox_isolation` |
| XSS | Escape en UI (React), CSP estricta, sanitización del código mostrado | `xss_suite` |
| CSRF / CORS / clickjacking | Tokens/SameSite, CORS restrictivo, X-Frame-Options/CSP frame-ancestors | `security_headers` |
| Fuerza bruta / abuso | Rate limit, bloqueo progresivo, cuotas de tokens | `ratelimit` |
| Escalada de privilegios / IDOR | RBAC en cada endpoint, comprobación de pertenencia al proyecto | `authz_suite` |
| Cadena de suministro | Versiones fijadas, lockfiles, SBOM, pip-audit/npm audit/OWASP DC, Trivy | `deps_audit`, `trivy`, `sbom` |
| Consumo excesivo de recursos (LLM10) | Límites de contexto, topes de reintentos, presupuesto por proyecto | `budget_limits` |
| Fuga del prompt de sistema (LLM07) | No contiene secretos; pruebas de extracción | `prompt_injection_suite` |

### Sandbox de verificación
Contenedor efímero por ejecución; sin red; usuario sin privilegios; FS de solo lectura salvo `/work`; límites de CPU, memoria, procesos y tiempo; sin montar docker.sock; imagen mínima fijada por digest.

## 5. Seguridad del código generado

SAST (Semgrep, Bandit, SpotBugs+FindSecBugs, eslint-plugin-security), dependencias (OWASP Dependency-Check, `npm audit`), reglas propias (sin `float` monetario, sin SQL concatenado, sin secretos, sin deserialización insegura, validación de entrada en controladores, manejo canónico de excepciones sin filtrar trazas). Umbral del Word: 0 vulnerabilidades críticas y 0 secretos.

## 6. Autenticación y autorización

MVP: autenticación local (usuarios sembrados) con JWT de corta vida/cookies seguras y roles `viewer`, `reviewer`, `approver`, `admin`. Solo `approver` aprueba reglas y diseño. F8: SSO/OIDC, MFA, KMS.

## 7. Verificación continua

- Pre-commit: gitleaks, ruff, Semgrep ligero.
- CI: SAST, dependencias, SBOM, Trivy, `run_acceptance --todas`.
- F6: OWASP ZAP baseline contra la app levantada (AC-F6-SEC-01), revisión final de superficie de ataque y de egreso.
- Revisión de seguridad (`/security-review`) al cierre de F1, F3, F4 y F6.

## 8. Mapa por fase

| Fase | Controles |
|---|---|
| F0 | SAST, secretos, dependencias, SBOM en CI; reglas Semgrep anti-SQL concatenado |
| F1 | Enmascarado, uploads, SSRF, SQLi, redacción de logs, hash-chain |
| F2 | Hallazgos de seguridad del legacy, fuzz de parsers |
| F3 | Prompt injection, auditoría de prompts, allowlist de egreso |
| F4 | SAST del código generado, sandbox, SQLi del servicio generado |
| F5 | SAST/dependencias del proyecto, datos sintéticos |
| F6 | ZAP, cabeceras, XSS, borrado, Trivy, revisión final |
| F8 | RBAC/SSO/MFA, auditoría WORM, KMS, Bedrock/Vertex, pentest externo |


---

## Actualización (controles implementados vs. pendientes)

| Control | Estado | Evidencia |
|---|---|---|
| Enmascarado antes de enviar al modelo + compuerta de salida (`EgressBlocked`) | Implementado | `masking.py`, `llm.call`; `test_secrets_masked_and_egress_blocked` |
| Heurísticas de línea solo en el código fuente; en la compuerta de salida solo patrones de alta confianza | Implementado | `mask_text(heuristics=False)` |
| SQL parametrizado + suite de inyección en rutas, campos y cabeceras | Implementado | `test_sqli_*`, `test_no_string_built_sql_in_codebase` |
| ZIP-slip, symlinks, ZIP-bomb, límites de tamaño/cantidad, extensiones permitidas | Implementado | `security.py`, `test_zip_*` |
| Cabeceras CSP/X-Frame/nosniff, rate limit, sin docs de la API, errores sin trazas | Implementado | `main.py`, `test_security_headers`, `test_rate_limit` |
| UI sin `innerHTML`/`eval` (texto como nodos) | Implementado | `test_frontend_has_no_dangerous_sinks` |
| Prompt injection: fuente delimitada como dato; hallazgo determinista | Implementado (modo `live`); en modo local no hay LLM que engañar | `pipeline.legacy_security_scan`, `render_source` |
| Código subido nunca se ejecuta; generado: escaneo estático + `node --permission` (sin red/archivos/procesos) | Implementado | `verify.py` |
| Cobertura sin `--permission` (incompatible), solo tras pasar la ejecución restringida y con entorno vacío | Implementado con mitigación | ADR-013 |
| Oráculo Python: AST (solo `decimal`/`math`), `python -I`, builtins restringidos | Implementado | `test_oracle_sandbox_rejects_unsafe_code` |
| Auditoría con hash encadenado y borrado de proyecto | Implementado | `test_audit_chain_detects_tampering`, `test_project_purge` |
| **Modelo local (Ollama) solo en loopback** (`127.0.0.1`/`localhost`); si no, `RuntimeError` | Implementado | `test_local_model_host_must_be_loopback` |
| **Clave de ejemplo/incompleta en `.env` se ignora** (< 30 caracteres o contiene «REEMPLACE») y `.env` está en `.gitignore` | Implementado | `llm._load_dotenv` |
| Modo local: sin red ni envío a terceros | Implementado | `local_engine.py` |
| **Modo `claude-code`: invocación aislada y sin clave** (`claude -p --tools "" --no-session-persistence`, prompt por stdin, cwd temporal vacío, `ANTHROPIC_API_KEY` eliminada del entorno hijo); mismo enmascarado/compuerta de salida; salida validada contra esquema y por los verificadores | Implementado | `llm._claude_code`, `tests/test_modes.py` (AC-F7-11) |
| **Modo explícito:** `auto` nunca elige `claude-code`; `POST /api/mode` rechaza modos no disponibles; la procedencia se rotula (`source=claude-code`) | Implementado | `llm.mode`, `llm.set_mode`, `test_mode_endpoint_*`, `test_auto_mode_never_*` |

**Pendientes / no implementados:** RBAC/autenticación (la app asume un solo usuario local), cifrado en reposo, clonado Git (se implementó la descarga de ZIP de repos públicos con anti-SSRF, ADR-017, probada con red simulada; repos privados no se admiten), ZAP/Trivy/gitleaks/Semgrep externos, contenedor de sandbox, despliegue privado (Bedrock/Vertex), retención configurable, auditoría WORM, rate limit distribuido. El modo `live` y el modelo local real **no se han probado en vivo**.

**Aviso de privacidad de los modos con IA (`live` y `claude-code`):** el código **ya enmascarado** sale hacia Anthropic (en `live` por la API con clave; en `claude-code` a través de la sesión de Claude Code del usuario, sujeta a sus términos y a la política de la organización); el modo `local` no envía nada fuera del equipo. El CLI se ejecuta sin herramientas (no puede leer ni escribir archivos del proyecto), pero un prompt injection en el código legacy aún podría alterar el *texto* devuelto: por eso toda salida se valida contra esquema, citas reales y guardrails, y el código generado se analiza antes de ejecutarse. Riesgo residual: RK-25 y RK-26 (`05`). `claude-code` solo se probó con COBOL.
