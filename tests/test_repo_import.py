"""Importación desde un repositorio Git público (solo lectura, sin clonar): validación de URL, anti-SSRF, límites y flujo."""
import io
import socket
import urllib.error
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
COBOL = ROOT / "golden" / "cobol_amortizacion"


def _zip(entries, top="proyecto-main/"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(top + name, data)
    return buf.getvalue()


def _repo_zip():
    return _zip({
        "src/LOANAMRT.cbl": (COBOL / "LOANAMRT.cbl").read_bytes(),
        "src/LOANREC.cpy": (COBOL / "LOANREC.cpy").read_bytes(),
        "README.md": b"# doc", "logo.png": b"\x89PNG....", "LICENSE": b"MIT",
        "node_modules/x/y.java": b"class Y {}", ".git/config": b"[core]",
        "docs/otro.cbl": b"       IDENTIFICATION DIVISION.\n       PROGRAM-ID. OTRO.\n",
    })


@pytest.fixture()
def fake_net(monkeypatch):
    from copilot import repo_import
    calls = []

    def fake_download(url):
        calls.append(url)
        return _repo_zip()
    monkeypatch.setattr(repo_import, "_download", fake_download)
    return calls


# ---------------------------------------------------------------- validación de URL
@pytest.mark.parametrize("url,expected", [
    ("https://github.com/acme/legacy-bank", ("github.com", "acme", "legacy-bank")),
    ("https://github.com/acme/legacy-bank.git", ("github.com", "acme", "legacy-bank")),
    ("  https://GitHub.com/acme/legacy-bank/  ", ("github.com", "acme", "legacy-bank")),
    ("https://github.com/acme/legacy-bank/tree/main/src", ("github.com", "acme", "legacy-bank")),
    ("https://gitlab.com/acme/cobol", ("gitlab.com", "acme", "cobol")),
])
def test_repo_url_accepted(url, expected):
    from copilot import repo_import
    assert repo_import.parse_repo_url(url) == expected


@pytest.mark.parametrize("url", [
    "", "http://github.com/a/b", "git@github.com:a/b.git", "ssh://git@github.com/a/b", "git://github.com/a/b", "file:///etc/passwd",
    "ftp://github.com/a/b", "https://localhost/a/b", "https://127.0.0.1/a/b", "https://169.254.169.254/latest/meta-data/",
    "https://[::1]/a/b", "https://evil.com/a/b", "https://github.com.evil.com/a/b", "https://github.com@evil.com/a/b",
    "https://user:token@github.com/a/b", "https://github.com:8443/a/b", "https://github.com/a/b?x=1", "https://github.com/a/b#frag",
    "https://github.com/a", "https://github.com/", "https://github.com/a/b/c/d/e", "https://github.com/../b", "https://github.com/a/..",
    "https://github.com/a/b c", "https://github.com/a/b\nHost: evil", "javascript:alert(1)",
])
def test_repo_url_rejected(url):
    from copilot import repo_import, security
    with pytest.raises(security.SecurityError):
        repo_import.parse_repo_url(url)


@pytest.mark.parametrize("ref", ["--upload-pack=calc", "../x", "a b", "-x", "a//b", "x;rm", "main.lock", "a\nb", "x" * 101])
def test_repo_ref_rejected(ref):
    from copilot import repo_import, security
    with pytest.raises(security.SecurityError):
        repo_import.check_ref(ref)


def test_repo_ref_default_and_archive_urls():
    from copilot import repo_import
    assert repo_import.check_ref("") == "HEAD" and repo_import.check_ref("feature/x-1.0") == "feature/x-1.0"
    assert repo_import.archive_url("github.com", "a", "b", "main") == "https://codeload.github.com/a/b/zip/main"
    assert repo_import.archive_url("gitlab.com", "a", "b", "dev") == "https://gitlab.com/a/b/-/archive/dev/b.zip"
    assert repo_import.archive_url("bitbucket.org", "a", "b", "dev") == "https://bitbucket.org/a/b/get/dev.zip"
    assert repo_import.archive_url("codeberg.org", "a", "b", "dev") == "https://codeberg.org/a/b/archive/dev.zip"


# ---------------------------------------------------------------- anti-SSRF
def test_dns_resolving_to_private_address_is_blocked(monkeypatch):
    from copilot import repo_import, security
    for ip in ("127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "::1"):
        monkeypatch.setattr(socket, "getaddrinfo", lambda *a, _ip=ip, **k: [(0, 0, 0, "", (_ip, 443))])
        with pytest.raises(security.SecurityError):
            repo_import._assert_public("github.com")
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(0, 0, 0, "", ("140.82.112.4", 443))])
    repo_import._assert_public("github.com")


def test_redirects_only_to_allowed_https_hosts(monkeypatch):
    from copilot import repo_import, security
    monkeypatch.setattr(repo_import, "_assert_public", lambda h: None)
    handler = repo_import._Redirects()
    for bad in ("http://codeload.github.com/a/b", "https://evil.com/x", "https://169.254.169.254/", "https://codeload.github.com:8080/x",
                "file:///etc/passwd"):
        with pytest.raises(security.SecurityError):
            handler.redirect_request(_FakeReq(), None, 302, "Found", {}, bad)
    assert handler.redirect_request(_FakeReq(), None, 302, "Found", {}, "https://codeload.github.com/a/b/zip/main") is not None


class _FakeReq:
    full_url = "https://github.com/a/b"
    data = None
    headers: dict = {}
    origin_req_host = "github.com"
    unverifiable = False

    def get_method(self):
        return "GET"

    def get_full_url(self):
        return self.full_url

    @property
    def method(self):
        return "GET"


class _Resp:
    def __init__(self, payload):
        self._b = io.BytesIO(payload)

    def read(self, n=-1):
        return self._b.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _patch_opener(monkeypatch, behavior):
    import urllib.request
    from copilot import repo_import
    monkeypatch.setattr(repo_import, "_assert_public", lambda h: None)

    class Opener:
        def open(self, req, timeout=None):
            return behavior(req)
    monkeypatch.setattr(urllib.request, "build_opener", lambda *a, **k: Opener())


def test_download_size_cap_and_http_errors(monkeypatch):
    from copilot import repo_import, security
    monkeypatch.setattr(repo_import, "MAX_ARCHIVE_BYTES", 1000)
    _patch_opener(monkeypatch, lambda req: _Resp(b"x" * 5000))
    with pytest.raises(security.SecurityError, match="demasiado grande"):
        repo_import._download("https://codeload.github.com/a/b/zip/main")
    for code, text in ((404, "No se encontró"), (403, "No se encontró"), (429, "limitó"), (500, "error")):
        def boom(req, _c=code):
            raise urllib.error.HTTPError(req.full_url, _c, "x", {}, None)
        _patch_opener(monkeypatch, boom)
        with pytest.raises(security.SecurityError, match=text):
            repo_import._download("https://codeload.github.com/a/b/zip/main")
    _patch_opener(monkeypatch, lambda req: (_ for _ in ()).throw(urllib.error.URLError("sin red")))
    with pytest.raises(security.SecurityError, match="conexión"):
        repo_import._download("https://codeload.github.com/a/b/zip/main")


# ---------------------------------------------------------------- extracción
def test_extract_keeps_only_legacy_source_and_counts_the_rest():
    from copilot import security
    files, stats = security.extract_repo_zip(_repo_zip())
    assert sorted(n for n, _ in files) == ["docs/otro.cbl", "src/LOANAMRT.cbl", "src/LOANREC.cpy"]
    assert stats["files"] == 3 and stats["skipped_other"] == 5            # README, png, LICENSE, node_modules, .git
    files, _ = security.extract_repo_zip(_repo_zip(), "src")                # subcarpeta: nombres relativos
    assert sorted(n for n, _ in files) == ["LOANAMRT.cbl", "LOANREC.cpy"]


def test_extract_rejects_hostile_archives():
    from copilot import security
    with pytest.raises(security.SecurityError):                              # ZIP-slip
        security.extract_repo_zip(_zip({"../../evil.cbl": b"x"}, top=""))
    with pytest.raises(security.SecurityError):
        security.extract_repo_zip(_zip({"a.cbl": b"x"}), "../fuera")
    with pytest.raises(security.SecurityError, match="ZIP-bomb"):            # compresión sospechosa
        security.extract_repo_zip(_zip({"bomba.cbl": b"0" * (1024 * 1024)}))
    with pytest.raises(security.SecurityError, match="no es un ZIP"):
        security.extract_repo_zip(b"PK esto no es un zip")
    with pytest.raises(security.SecurityError, match="No se encontró código"):
        security.extract_repo_zip(_zip({"README.md": b"hola", "img.png": b"x"}))
    with pytest.raises(security.SecurityError, match="No se encontró código"):
        security.extract_repo_zip(_repo_zip(), "no/existe")


def test_extract_skips_symlinks_and_oversized_files():
    from copilot import security
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        link = zipfile.ZipInfo("r-main/enlace.cbl")
        link.external_attr = (0o120777 << 16)
        zf.writestr(link, "/etc/passwd")
        zf.writestr("r-main/ok.cbl", b"       PROGRAM-ID. OK.\n")
        zf.writestr("r-main/grande.cbl", b"A" + bytes(range(256)) * (security.MAX_FILE_BYTES // 256 + 1))
    files, stats = security.extract_repo_zip(buf.getvalue())
    assert [n for n, _ in files] == ["ok.cbl"] and stats["skipped_links"] == 1 and stats["skipped_large"] == 1


def test_extract_limits_number_of_files(monkeypatch):
    from copilot import security
    monkeypatch.setattr(security, "MAX_FILES", 2)
    with pytest.raises(security.SecurityError, match="carpeta"):
        security.extract_repo_zip(_repo_zip())


# ---------------------------------------------------------------- flujo completo (red simulada)
def test_import_from_repo_creates_project_without_touching_origin(client, fake_net):
    r = client.post("/api/projects/repo", json={"url": "https://github.com/acme/legacy-bank", "ref": "main", "subdir": "src"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert fake_net == ["https://codeload.github.com/acme/legacy-bank/zip/main"]      # una sola petición GET de lectura
    assert body["source"] == {"host": "github.com", "repo": "acme/legacy-bank", "ref": "main", "files": 2,
                              "skipped_other": 0, "skipped_large": 0, "skipped_links": 0}
    p = client.get(f"/api/projects/{body['id']}").json()
    assert p["name"] == "legacy-bank" and p["ingest_report"]["files"] == 2 and p["ingest_report"]["gate_no_secrets"]
    assert any(e["action"] == "ingest:repo" for e in client.get(f"/api/projects/{body['id']}/audit").json()["events"])


def test_import_from_repo_errors_are_clear(client, fake_net):
    for payload in ({"url": "http://github.com/a/b"}, {"url": "https://evil.com/a/b"}, {"url": "https://github.com/a/b", "ref": "--x"},
                    {"url": "https://github.com/a/b", "subdir": "../x"}, {"url": "https://github.com/a/b", "subdir": "nada"}):
        r = client.post("/api/projects/repo", json=payload)
        assert r.status_code == 400 and r.json()["error"], payload
    assert fake_net.count("https://evil.com/a/b") == 0 and len(fake_net) == 1       # las rechazadas por URL/ref no salen a la red
    assert client.post("/api/projects/repo", json={}).status_code == 422
