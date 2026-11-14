"""Controles de seguridad de entrada: cargas, ZIP, identificadores, límites, cabeceras, rate limit."""
from __future__ import annotations

import io
import posixpath
import re
import stat
import time
import uuid
import zipfile
from collections import defaultdict, deque

MAX_FILE_BYTES = 2 * 1024 * 1024          # por archivo
MAX_TOTAL_BYTES = 20 * 1024 * 1024        # descomprimido total
MAX_FILES = 300
MAX_ZIP_RATIO = 200                       # anti ZIP-bomb
ALLOWED_EXT = {".cbl", ".cob", ".cobol", ".cpy", ".copy", ".jcl", ".sql", ".pks", ".pkb", ".plsql", ".pls",
               ".rpg", ".rpgle", ".sqlrpgle", ".java", ".txt", ".prc", ".fnc", ".trg", ".bms", ".json", ".csv"}


class SecurityError(ValueError):
    """Entrada rechazada por una política de seguridad. El mensaje es seguro para mostrar."""


_UUID = re.compile(r"^[0-9a-f]{32}$")


def valid_id(value: str) -> str:
    if not isinstance(value, str) or not _UUID.match(value):
        raise SecurityError("Identificador de proyecto inválido.")
    return value


def new_id() -> str:
    return uuid.uuid4().hex


def safe_name(name: str) -> str:
    """Normaliza una ruta de archivo: sin '..', sin absolutas, sin caracteres de control."""
    name = (name or "").replace("\\", "/").strip()
    if not name or "\x00" in name or any(ord(c) < 32 for c in name):
        raise SecurityError("Nombre de archivo inválido.")
    norm = posixpath.normpath(name)
    if norm.startswith("/") or norm.startswith("../") or norm == ".." or re.match(r"^[A-Za-z]:", norm):
        raise SecurityError(f"Ruta no permitida en el archivo: {name[:60]!r}")
    if len(norm) > 200:
        raise SecurityError("Ruta de archivo demasiado larga.")
    return norm


def check_extension(name: str) -> None:
    ext = posixpath.splitext(name.lower())[1]
    if ext and ext not in ALLOWED_EXT:
        raise SecurityError(f"Tipo de archivo no admitido: {ext}. Suba código fuente legacy en texto.")


def is_archive_junk(name: str) -> bool:
    """Basura que los sistemas operativos añaden a los ZIP (macOS «__MACOSX/._x.cbl», .DS_Store, Thumbs.db): no es código."""
    parts = name.split("/")
    base = parts[-1]
    return "__MACOSX" in parts or base.startswith("._") or base in (".DS_Store", "Thumbs.db", "desktop.ini")


def extract_zip(data: bytes) -> list[tuple[str, bytes]]:
    """Extrae un ZIP EN MEMORIA (nunca al disco) con defensas ZIP-slip / ZIP-bomb / symlink."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise SecurityError("El archivo ZIP está dañado o no es un ZIP válido.") from exc
    infos = [i for i in zf.infolist() if not i.is_dir()]
    if len(infos) > MAX_FILES:
        raise SecurityError(f"El ZIP contiene demasiados archivos (máx. {MAX_FILES}).")
    total = 0
    out: list[tuple[str, bytes]] = []
    for info in infos:
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise SecurityError("El ZIP contiene enlaces simbólicos, no permitidos.")
        name = safe_name(info.filename)
        if is_archive_junk(name):
            continue
        if info.file_size > MAX_FILE_BYTES:
            raise SecurityError(f"Archivo demasiado grande dentro del ZIP: {name}")
        if info.compress_size and info.file_size / max(info.compress_size, 1) > MAX_ZIP_RATIO:
            raise SecurityError("Relación de compresión sospechosa (posible ZIP-bomb).")
        total += info.file_size
        if total > MAX_TOTAL_BYTES:
            raise SecurityError("El contenido descomprimido excede el límite permitido.")
        with zf.open(info) as fh:
            blob = fh.read(MAX_FILE_BYTES + 1)
        if len(blob) > MAX_FILE_BYTES:
            raise SecurityError(f"Archivo demasiado grande dentro del ZIP: {name}")
        check_extension(name)
        out.append((name, blob))
    return out


REPO_EXT = ALLOWED_EXT - {".txt", ".json", ".csv"}          # en un repositorio solo se toma código fuente (no ruido)
REPO_SKIP_DIRS = {".git", ".github", "node_modules", "vendor", "__pycache__"}
MAX_REPO_ENTRIES = 20000


def extract_repo_zip(data: bytes, subdir: str = "") -> tuple[list[tuple[str, bytes]], dict[str, int]]:
    """Extrae EN MEMORIA el código fuente legacy de un archivo comprimido de repositorio.

    A diferencia de `extract_zip` (una carga explícita del usuario), un repositorio trae muchos archivos ajenos:
    aquí se OMITEN (y se cuentan) los de otro tipo, los muy grandes, los enlaces simbólicos y los directorios de
    herramientas; los omitidos nunca se descomprimen. Rutas peligrosas (ZIP-slip) o compresión sospechosa abortan todo.
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise SecurityError("El archivo descargado del repositorio no es un ZIP válido.") from exc
    infos = [i for i in zf.infolist() if not i.is_dir()]
    if len(infos) > MAX_REPO_ENTRIES:
        raise SecurityError("El repositorio tiene demasiados archivos. Indique la carpeta con el código legacy.")
    parts = [i.filename.replace("\\", "/").split("/") for i in infos]
    strip = 1 if parts and all(len(p) > 1 and p[0] == parts[0][0] for p in parts) else 0   # carpeta raíz «repo-rama/»
    prefix = safe_name(subdir).strip("/") + "/" if subdir.strip() else ""
    out: list[tuple[str, bytes]] = []
    skipped = {"other": 0, "large": 0, "links": 0}
    total = 0
    for info, p in zip(infos, parts):
        name = safe_name("/".join(p[strip:]))
        if prefix:
            if not name.startswith(prefix):
                continue
            name = name[len(prefix):]
        if stat.S_ISLNK(info.external_attr >> 16):
            skipped["links"] += 1
            continue
        if REPO_SKIP_DIRS & set(name.split("/")[:-1]) or posixpath.splitext(name.lower())[1] not in REPO_EXT:
            skipped["other"] += 1
            continue
        if info.file_size > MAX_FILE_BYTES:
            skipped["large"] += 1
            continue
        if info.compress_size and info.file_size / max(info.compress_size, 1) > MAX_ZIP_RATIO:
            raise SecurityError("Relación de compresión sospechosa en el repositorio (posible ZIP-bomb).")
        with zf.open(info) as fh:
            blob = fh.read(MAX_FILE_BYTES + 1)
        if len(blob) > MAX_FILE_BYTES:
            skipped["large"] += 1
            continue
        total += len(blob)
        if len(out) >= MAX_FILES or total > MAX_TOTAL_BYTES:
            raise SecurityError("El repositorio tiene más código del permitido (300 archivos / 20 MB). Indique la carpeta con el código legacy.")
        out.append((name, blob))
    if not out:
        raise SecurityError("No se encontró código fuente legacy en el repositorio"
                            + (f" dentro de «{prefix.rstrip('/')}»" if prefix else "")
                            + " (extensiones admitidas: " + ", ".join(sorted(REPO_EXT)) + ").")
    return out, {"files": len(out), "skipped_other": skipped["other"], "skipped_large": skipped["large"], "skipped_links": skipped["links"]}


def check_blob(name: str, blob: bytes) -> None:
    if len(blob) > MAX_FILE_BYTES:
        raise SecurityError(f"{name}: supera el tamaño máximo ({MAX_FILE_BYTES // 1024} KB).")
    if not blob.strip():
        raise SecurityError(f"{name}: el archivo está vacío.")


# ---- rate limit simple en memoria (por IP) ----
_hits: dict[str, deque[float]] = defaultdict(deque)


def rate_limited(key: str, limit: int = 240, window: float = 60.0) -> bool:
    now = time.monotonic()
    q = _hits[key]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        return True
    q.append(now)
    return False


SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                               "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
