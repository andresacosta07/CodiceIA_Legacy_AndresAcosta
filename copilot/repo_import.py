"""Importación de código desde un repositorio Git PÚBLICO, solo lectura (ADR-017).

No se ejecuta `git`: se descarga por HTTPS el archivo comprimido (ZIP) de la rama/etiqueta indicada desde un
conjunto fijo de forjas conocidas. El repositorio de origen nunca se modifica (no hay clone, pull ni push) y no se
escribe nada en disco: el ZIP se procesa en memoria con las mismas defensas que una carga manual
(`security.extract_repo_zip`). Controles anti-SSRF: solo https, hosts de una lista cerrada, sin credenciales, puerto,
consulta ni fragmento en la URL, redirecciones solo a hosts de la lista y resolución DNS a IP públicas.
"""
from __future__ import annotations

import ipaddress
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from . import security

MAX_ARCHIVE_BYTES = 40 * 1024 * 1024        # tamaño máximo del archivo comprimido descargado
TIMEOUT_S = 20                              # por operación de red
DEADLINE_S = 60                             # tiempo total de la descarga
USER_AGENT = "copiloto-legacy-import/1.0"

# host público -> plantilla del archivo comprimido ({o} propietario, {r} repositorio, {ref} rama o etiqueta)
FORGES: dict[str, str] = {
    "github.com": "https://codeload.github.com/{o}/{r}/zip/{ref}",
    "gitlab.com": "https://gitlab.com/{o}/{r}/-/archive/{ref}/{r}.zip",
    "bitbucket.org": "https://bitbucket.org/{o}/{r}/get/{ref}.zip",
    "codeberg.org": "https://codeberg.org/{o}/{r}/archive/{ref}.zip",
}
REDIRECT_HOSTS = set(FORGES) | {"codeload.github.com"}
_SEG = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
_REF = re.compile(r"^[A-Za-z0-9._][A-Za-z0-9._/\-]{0,99}$")


@dataclass
class RepoSource:
    host: str
    owner: str
    repo: str
    ref: str
    url: str = ""
    files: list[tuple[str, bytes]] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {"host": self.host, "repo": f"{self.owner}/{self.repo}", "ref": self.ref, **self.stats}


def parse_repo_url(raw: str) -> tuple[str, str, str]:
    """Valida la URL del repositorio y devuelve (host, propietario, repositorio). Lanza SecurityError si no es admisible."""
    raw = (raw or "").strip()
    if not raw:
        raise security.SecurityError("Escriba la URL del repositorio (por ejemplo https://github.com/organización/repositorio).")
    if len(raw) > 300 or any(ord(c) < 33 for c in raw):
        raise security.SecurityError("La URL del repositorio no es válida.")
    if not raw.lower().startswith("https://"):
        raise security.SecurityError("Solo se admiten URL https:// de repositorios públicos (no ssh, git://, file:// ni http://).")
    try:
        u = urllib.parse.urlsplit(raw)
        port = u.port
    except ValueError as exc:
        raise security.SecurityError("La URL del repositorio no es válida.") from exc
    host = (u.hostname or "").lower()
    if u.username or u.password or port is not None or u.query or u.fragment:
        raise security.SecurityError("La URL no debe incluir usuario, contraseña, puerto, parámetros ni «#». Los repositorios privados no se admiten.")
    if host not in FORGES:
        raise security.SecurityError("Repositorio no admitido. Hosts permitidos: " + ", ".join(sorted(FORGES)) + ".")
    segs = [s for s in u.path.split("/") if s]
    if len(segs) >= 3 and segs[2] in ("tree", "blob", "-"):      # URL copiada del navegador: se ignora la ruta extra
        segs = segs[:2]
    if len(segs) != 2:
        raise security.SecurityError("La URL debe tener la forma https://host/propietario/repositorio.")
    owner, repo = segs[0], re.sub(r"\.git$", "", segs[1])
    for s in (owner, repo):
        if not _SEG.match(s) or s in (".", ".."):
            raise security.SecurityError("El propietario o el nombre del repositorio contienen caracteres no permitidos.")
    return host, owner, repo


def check_ref(ref: str) -> str:
    ref = (ref or "").strip() or "HEAD"
    if not _REF.match(ref) or ".." in ref or "//" in ref or ref.endswith("/") or ref.endswith(".lock"):
        raise security.SecurityError("La rama o etiqueta no es válida (use letras, números, «.», «_», «-» y «/»).")
    return ref


def archive_url(host: str, owner: str, repo: str, ref: str) -> str:
    return FORGES[host].format(o=owner, r=repo, ref=urllib.parse.quote(ref, safe="/"))


def _assert_public(host: str) -> None:
    """Anti-SSRF: el nombre debe resolver solo a direcciones IP públicas."""
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise security.SecurityError("No se pudo resolver el servidor del repositorio. Revise su conexión a internet.") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            raise security.SecurityError("El servidor del repositorio resuelve a una dirección no pública; importación bloqueada.")


class _Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        u = urllib.parse.urlsplit(newurl)
        if u.scheme != "https" or (u.hostname or "").lower() not in REDIRECT_HOSTS or u.port not in (None, 443):
            raise security.SecurityError("El repositorio redirige a un destino no permitido; importación bloqueada.")
        _assert_public(u.hostname)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _download(url: str) -> bytes:
    """Descarga acotada (tamaño y tiempo). Aislada en una función para poder sustituirla en las pruebas."""
    host = urllib.parse.urlsplit(url).hostname or ""
    _assert_public(host)
    opener = urllib.request.build_opener(_Redirects)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/zip, */*"})
    t0, buf = time.monotonic(), bytearray()
    try:
        with opener.open(req, timeout=TIMEOUT_S) as resp:
            while True:
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                buf += chunk
                if len(buf) > MAX_ARCHIVE_BYTES:
                    raise security.SecurityError("El repositorio es demasiado grande (máx. 40 MB comprimido). Pruebe con una rama más pequeña o suba un ZIP con la carpeta del código.")
                if time.monotonic() - t0 > DEADLINE_S:
                    raise security.SecurityError("La descarga del repositorio tardó demasiado. Reintente más tarde.")
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403, 404):
            raise security.SecurityError("No se encontró el repositorio o la rama. Compruebe la URL; solo se admiten repositorios públicos.") from exc
        if exc.code == 429:
            raise security.SecurityError("El servidor del repositorio limitó las solicitudes. Espere un momento y reintente.") from exc
        raise security.SecurityError(f"El servidor del repositorio respondió con un error ({exc.code}).") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise security.SecurityError("No se pudo descargar el repositorio. Revise su conexión a internet y reintente.") from exc
    return bytes(buf)


def fetch(url: str, ref: str = "", subdir: str = "") -> RepoSource:
    """Descarga y filtra el código fuente de un repositorio público. No modifica el origen ni escribe en disco."""
    host, owner, repo = parse_repo_url(url)
    ref = check_ref(ref)
    if subdir.strip():
        security.safe_name(subdir)                  # rechaza «..», rutas absolutas, etc. ANTES de tocar la red
    target = archive_url(host, owner, repo, ref)
    data = _download(target)
    if data[:2] != b"PK":
        raise security.SecurityError("El servidor no devolvió un archivo comprimido. Compruebe la URL y la rama.")
    files, stats = security.extract_repo_zip(data, subdir)
    return RepoSource(host, owner, repo, ref, target, files, stats)
