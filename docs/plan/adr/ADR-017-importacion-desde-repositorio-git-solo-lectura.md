# ADR-017: Importación de código desde un repositorio Git público, solo lectura y sin clonar

**Estado:** Aceptado
**Fecha:** 2026-11-13

## Contexto
Además de pegar código o subir un ZIP, se pidió poder indicar la URL de un repositorio Git para extraer el código **sin afectar el repositorio** (sin pull, sin escribir en él). El plan original (R-01) preveía un «cliente Git seguro» con clonado; no estaba implementado. En el equipo de desarrollo **no hay `git` instalado**, y ejecutar `git clone` sobre una URL ajena abre superficie de ataque (hooks, submódulos, filtros, protocolos `ext::`/`file://`, configuración del repositorio).

## Decisión
1. **No se ejecuta `git`.** Se descarga por HTTPS el **archivo comprimido (ZIP)** de la rama o etiqueta desde un conjunto **cerrado** de forjas: GitHub (`codeload.github.com`), GitLab, Bitbucket y Codeberg. Es una única petición GET de lectura: el repositorio de origen no se modifica y no hay clone, pull ni push.
2. **Solo repositorios públicos.** No se aceptan usuarios, contraseñas ni tokens en la URL (se rechazan); así no se manejan credenciales ni secretos.
3. **Anti-SSRF** (`copilot/repo_import.py`): solo `https://`; host dentro de la lista; sin usuario/contraseña/puerto/consulta/fragmento; propietario y repositorio con caracteres restringidos; rama/etiqueta con patrón estricto (sin `--`, `..`, espacios); redirecciones solo a hosts de la lista y a `https`; el nombre debe resolver a IP **globales** (se bloquean loopback, privadas, link-local/metadata, multicast); límite de 40 MB comprimidos y 60 s en total.
4. **Procesamiento en memoria** con `security.extract_repo_zip`: se quita la carpeta raíz del ZIP; se conservan solo extensiones de código legacy (`ALLOWED_EXT` menos `.txt/.json/.csv`); se **omiten y cuentan** (sin descomprimirlos) los demás archivos, los enlaces simbólicos, los de más de 2 MB y los directorios `.git`, `.github`, `node_modules`, `vendor`, `__pycache__`; rutas peligrosas (ZIP-slip) o compresión sospechosa abortan todo; máximo 300 archivos / 20 MB de código (si se excede, se pide indicar la carpeta). Campo opcional «Carpeta con el código» para monorepos.
5. Lo importado entra al mismo `pipeline.new_project`: se enmascaran secretos y se aplican las mismas compuertas que a una carga manual. Queda un evento de auditoría `ingest:repo` (host, repositorio, rama, conteos).
6. API: `POST /api/projects/repo` `{url, ref?, subdir?, name?, domain?, target?}`. UI: bloque «O traiga el código desde un repositorio Git» en «Cargar su código».

## Consecuencias
- Funciona sin `git` y con una superficie de ataque mucho menor que un clone; reutiliza las defensas de ZIP.
- **Limitaciones:** repositorios privados, otros servidores Git (autoalojados) y GitLab con subgrupos no se admiten; la rama por defecto se obtiene con `HEAD`. Se descarga el estado de una rama/etiqueta, no el historial.
- **No probado en vivo** (ver estado en `docs/plan/02_plan_por_fases.md`): las pruebas automáticas usan red simulada. Las plantillas de URL de GitLab, Bitbucket y Codeberg están verificadas solo por pruebas unitarias de construcción de la URL.
- Riesgo residual: reasignación de DNS entre la comprobación de IP y la conexión; se mitiga con la lista cerrada de hosts y https, y se documenta como pendiente de endurecimiento.
