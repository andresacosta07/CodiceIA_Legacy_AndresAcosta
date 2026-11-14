"""Suites de seguridad: inyección SQL, cargas maliciosas, fuga de secretos, prompt injection, XSS, cabeceras, auditoría."""
import io
import json
import re
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SQLI = ["' OR 1=1--", "'; DROP TABLE projects;--", "\" OR \"\"=\"", "1; SELECT * FROM audit", "' UNION SELECT data FROM projects--",
        "admin'/*", "1' AND SLEEP(5)--", "%27%20OR%201%3D1", "\\'; DELETE FROM audit WHERE '1'='1"]


def _count(table):
    from copilot import db
    return db._c().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608 (tabla fija, prueba)


def _sample(client):
    return client.post("/api/projects/sample", json={"name": "cobol_amortizacion"}).json()["id"]


# ---------------------------------------------------------------- inyección SQL
def test_sqli_in_path_ids_is_rejected(client):
    pid = _sample(client)
    before = (_count("projects"), _count("audit"))
    for payload in SQLI:
        for url in (f"/api/projects/{payload}", f"/api/projects/{payload}/audit", f"/api/projects/{payload}/download"):
            r = client.get(url)
            assert r.status_code in (400, 404, 422), (url, r.status_code)
            assert "sql" not in r.text.lower() and "sqlite" not in r.text.lower()
        r = client.post(f"/api/projects/{pid}/rules/{payload}/review", json={"status": "approved"})
        assert r.status_code in (400, 404, 405, 422)   # 405: la ruta no existe (p. ej. payload con '/')
        r = client.delete(f"/api/projects/{payload}")
        assert r.status_code in (400, 404, 405, 422)
    assert (_count("projects"), _count("audit")) == before  # nada se alteró


def test_sqli_in_text_fields_is_stored_as_data(client):
    for payload in SQLI:
        r = client.post("/api/projects", data={"name": payload, "domain": payload, "target": "typescript", "code_text": "MOVE 1 TO X.",
                                               "code_name": "a.cbl"}, headers={"X-Reviewer": payload})
        assert r.status_code == 200, r.text
    names = [p["name"] for p in client.get("/api/projects").json()]
    assert "' OR 1=1--" in names                      # se guardó literalmente: parametrizado
    assert _count("projects") == len(SQLI)            # la tabla sigue íntegra
    assert _count("audit") >= len(SQLI)


def test_sqli_payload_in_sample_name_and_review_fields(client):
    pid = _sample(client)
    assert client.post("/api/projects/sample", json={"name": "' OR 1=1--"}).status_code == 404
    client.post(f"/api/projects/{pid}/start")
    r = client.post(f"/api/projects/{pid}/rules/R-001/review", json={"status": "approved' OR '1'='1", "comment": SQLI[0]})
    assert r.status_code in (400, 404)


def test_no_string_built_sql_in_codebase():
    rx = re.compile(r"""(?i)(execute|executemany|executescript)\(\s*f?["'][^"']*(\{|%s|\+)""")
    for py in (ROOT / "copilot").glob("*.py"):
        for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            if rx.search(line) and "? " not in line:
                raise AssertionError(f"SQL no parametrizado en {py.name}:{i}: {line.strip()}")


# ---------------------------------------------------------------- cargas maliciosas
def _zip(entries, symlink=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries:
            z.writestr(name, data)
        if symlink:
            zi = zipfile.ZipInfo(symlink)
            zi.external_attr = (0o120777 << 16)
            z.writestr(zi, "/etc/passwd")
    return buf.getvalue()


@pytest.mark.parametrize("name", ["../../evil.cbl", "..\\..\\evil.cbl", "/etc/passwd.cbl", "C:\\Windows\\x.cbl", "a/../../b.cbl"])
def test_zip_slip_blocked(client, name):
    r = client.post("/api/projects", files={"files": ("p.zip", _zip([(name, "MOVE 1 TO X.")]))}, data={"target": "typescript"})
    assert r.status_code == 400 and "Ruta no permitida" in r.json()["error"] or r.status_code == 400


def test_zip_symlink_bomb_and_limits(client):
    assert client.post("/api/projects", files={"files": ("p.zip", _zip([("a.cbl", "X")], symlink="l.cbl"))}).status_code == 400
    bomb = _zip([("big.cbl", "A" * (1_900_000))] * 1)
    r = client.post("/api/projects", files={"files": ("b.zip", bomb)}, data={"target": "typescript"})
    assert r.status_code == 400 and "compresión" in r.json()["error"]       # ratio de ZIP-bomb
    many = _zip([(f"f{i}.cbl", f"MOVE {i} TO X.") for i in range(301)])
    assert client.post("/api/projects", files={"files": ("m.zip", many)}).status_code == 400
    assert client.post("/api/projects", files={"files": ("x.zip", b"no es un zip")}).status_code == 400


def test_invalid_inputs_have_clear_errors(client):
    for kwargs, frag in [({"data": {"target": "typescript"}}, "No se recibió"),
                         ({"files": {"files": ("a.exe", b"MZ")}}, "no admitido"),
                         ({"files": {"files": ("a.cbl", b"\x00\x01\x02\x03binary")}}, "binario"),
                         ({"files": {"files": ("a.cbl", b"   ")}}, "vacío"),
                         ({"files": {"files": ("../a.cbl", b"X")}}, "no permitida"),
                         ({"data": {"code_text": "MOVE 1 TO X.", "target": "cobol"}}, "no soportado")]:
        r = client.post("/api/projects", **kwargs)
        assert r.status_code == 400, (kwargs, r.text)
        assert frag in r.json()["error"], r.json()
        assert "Traceback" not in r.text
    assert _count("projects") == 0   # ninguna entrada inválida dejó datos


def _zip_bytes(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for n, d in entries.items():
            zf.writestr(n, d)
    return buf.getvalue()


def test_invalid_inputs_zip_with_binary_and_macos_junk(client):
    good = (ROOT / "golden" / "cobol_amortizacion" / "LOANAMRT.cbl").read_bytes()
    z = _zip_bytes({"p/LOANAMRT.cbl": good, "__MACOSX/p/._LOANAMRT.cbl": b"\x00\x05\x16\x07AppleDouble", "p/.DS_Store": b"\x00\x00\x00\x01Bud1",
                    "p/datos.cbl": b"\x00\x01\x02\x03binario"})
    r = client.post("/api/projects", files={"files": ("p.zip", z)})
    assert r.status_code == 200, r.text                                   # un binario suelto ya no aborta toda la carga
    rep = client.get(f"/api/projects/{r.json()['id']}").json()["ingest_report"]
    assert rep["files"] == 1 and rep["skipped_binary"] == ["p/datos.cbl"]   # y se informa cuál se omitió (la basura de macOS se ignora)
    only_bad = _zip_bytes({"a/datos.cbl": b"\x00\x01\x02\x03binario", "a/otro.cbl": b"\x00\x09bin"})
    r = client.post("/api/projects", files={"files": ("p.zip", only_bad)})
    assert r.status_code == 400 and "binario" in r.json()["error"] and "datos.cbl" in r.json()["error"]   # el mensaje nombra el archivo


def test_oversized_upload_rejected(client):
    r = client.post("/api/projects", files={"files": ("a.cbl", b"A" * (2 * 1024 * 1024 + 10))})
    assert r.status_code == 400


# ---------------------------------------------------------------- fugas
def test_secrets_masked_and_egress_blocked(client):
    from copilot import llm
    code = Path(ROOT / "golden/adversarial/TRAP.cbl").read_bytes()
    r = client.post("/api/projects", files={"files": ("TRAP.cbl", code)}, data={"target": "typescript"})
    p = client.get(f"/api/projects/{r.json()['id']}").json()
    text = json.dumps(p)
    for secret in ("Sup3rS3cret", "AKIAABCDEFGHIJKLMNOP", "cliente.ficticio@example.com", "ES9121000418450200051332"):
        assert secret not in text
    assert p["ingest_report"]["masked_total"] >= 4 and p["ingest_report"]["residual_secrets"] == 0
    # la compuerta de salida bloquea texto con secretos sin enmascarar
    with pytest.raises(llm.EgressBlocked):
        llm.call("analyze", "sys", "clave AKIAABCDEFGHIJKLMNOP y correo juan.perez@banco.com", None)


def test_masking_preserves_line_numbers():
    from copilot import masking
    src = "A\nMOVE 'Sup3rS3cret!' TO WS-PASSWORD\nC\npwd=abc12345;x\n4111 1111 1111 1111\n"
    out, f = masking.mask_text(src)
    assert out.count("\n") == src.count("\n") and len(f) >= 3 and "Sup3rS3cret" not in out and "4111" not in out


def test_logs_do_not_contain_source(client, fake):
    from copilot import db
    pid = _sample(client)
    client.post(f"/api/projects/{pid}/start")
    import time
    time.sleep(1.5)
    rows = db._c().execute("SELECT stage, prompt_hash FROM llm_calls").fetchall()
    assert rows and all(len(h) == 16 for _, h in rows)          # solo hash del prompt
    for (detail,) in db._c().execute("SELECT detail FROM audit").fetchall():
        assert "LOAN-REQUEST" not in detail and "PROCEDURE DIVISION" not in detail


# ---------------------------------------------------------------- prompt injection / XSS / cabeceras
def test_prompt_injection_flagged_and_source_delimited(client):
    from copilot import ingest, pipeline
    r = ingest.build_artifacts([("TRAP.cbl", (ROOT / "golden/adversarial/TRAP.cbl").read_bytes())])
    found = pipeline.legacy_security_scan(r["artifacts"])
    assert any(f["category"] == "prompt_injection_attempt" for f in found)
    rendered = pipeline.render_source(r["artifacts"])
    assert rendered.startswith("<legacy_source") and rendered.rstrip().endswith("</legacy_source>")
    assert "datos no confiables" in pipeline.system_prompt("analyze").lower() or "dato no confiable" in pipeline.system_prompt("analyze").lower()


def test_plsql_dynamic_sql_flagged():
    from copilot import ingest, pipeline
    r = ingest.build_artifacts([("PKG.sql", (ROOT / "golden/plsql_siniestro/PKG_SINIESTROS.sql").read_bytes())])
    assert any(f["category"] == "sql_injection_risk" for f in pipeline.legacy_security_scan(r["artifacts"]))


def test_frontend_has_no_dangerous_sinks():
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    for bad in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
        assert bad not in js, bad


def test_hostile_content_roundtrip_is_plain_text(client):
    payload = "<script>alert(1)</script> MOVE 1 TO X."
    r = client.post("/api/projects", data={"code_text": payload, "code_name": "x.cbl", "target": "typescript", "name": "<img src=x onerror=alert(1)>"})
    p = client.get(f"/api/projects/{r.json()['id']}").json()
    assert p["name"].startswith("<img")  # se almacena como dato; la UI usa textContent (verificado arriba)


def test_security_headers(client):
    r = client.get("/api/status")
    h = r.headers
    assert "default-src 'self'" in h["content-security-policy"] and "script-src 'self'" in h["content-security-policy"]
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY" and h["referrer-policy"] == "no-referrer"
    assert client.get("/docs").status_code in (404,) or "swagger" not in client.get("/docs").text.lower()


def test_rate_limit(client):
    from copilot import security
    codes = [client.get("/api/status").status_code for _ in range(security._hits.maxlen or 260)] if False else None
    hits = 0
    for _ in range(300):
        if client.get("/api/status").status_code == 429:
            hits += 1
    assert hits > 0


# ---------------------------------------------------------------- auditoría y código generado
def test_audit_chain_detects_tampering(client, fake):
    from copilot import db
    pid = _sample(client)
    assert db.verify_audit_chain(pid)
    db.audit(pid, "t", "x", {"a": 1})
    db.audit(pid, "t", "y", {"b": 2})
    seq = db.audit_log(pid)[0]["seq"]
    db.tamper_audit_for_test(seq)
    assert not db.verify_audit_chain(pid)


def test_generated_code_scanner_blocks_dangerous_code():
    from copilot import verify
    files = [{"path": "src/domain/a.ts", "content": "import fs from 'node:fs';\nexport const x = eval('1');\nconst q = \"SELECT * FROM t WHERE id=\" + id;\nconst p = parseFloat('1.5');\nfetch('http://x');"},
             {"path": "src/domain/b.ts", "content": "import { y } from '../infrastructure/z.ts';"},
             {"path": "src/application/c.ts", "content": "const password = 'Hunter2secret';"}]
    scan = verify.scan_project(files, "typescript")
    msgs = " ".join(f["message"] for f in scan["findings"])
    for frag in ("eval", "fetch", "concatenación", "parseFloat", "domain no puede depender", "secreto"):
        assert frag in msgs, frag
    assert scan["blocking"] >= 5


def test_generated_code_scanner_distinguishes_require_method_from_node_require():
    from copilot import verify

    def blocking_require(src):
        scan = verify.scan_project([{"path": "src/domain/a.ts", "content": src}], "typescript")
        return [f for f in scan["findings"] if "require" in f["message"]]
    ok = ("export class P {\n  require(code: string): Decimal {\n    return this.m.get(code)!;\n  }\n}\n"
          "const a = parameters.require(Codes.X);\nconst b = this.params.require('Y');")
    assert not blocking_require(ok)                                            # método propio: no es el require de Node
    for bad in ("const fs = require('fs');", "const x = require(name);", "module.require('fs');", "const r = (require)('fs'); require('os')",
                "function f() { return require(\"child_process\"); }"):
        assert blocking_require(bad), bad                                      # el require de Node sigue bloqueado


def test_oracle_sandbox_allows_classes_but_still_rejects_escapes():
    from copilot import verify
    code = ("from decimal import Decimal\nclass LegacyError(Exception):\n    pass\n"
            "def run(inp):\n    if inp.get('x') == 'bad':\n        raise LegacyError('x')\n    return {'a': Decimal('1.5')}\n")
    assert not verify.validate_oracle_code(code)
    res = verify.run_oracle(code, [{"name": "ok", "input": {"x": "1"}}, {"name": "malo", "input": {"x": "bad"}}])
    assert res["ok"] and res["results"][0]["output"] == {"a": "1.5"} and res["results"][1]["ok"] is False
    assert not verify.run_oracle("class A:\n    def m(self):\n        return open('x')\ndef run(inp):\n    return {}", [])["ok"]
    # clase de error propia con super().__init__ (habitual en oráculos): permitida y ejecutable...
    err = ("class LegacyError(Exception):\n    def __init__(self, code):\n        super().__init__(code)\n        self.code = code\n"
           "def run(inp):\n    try:\n        raise LegacyError('ORA-20010')\n    except LegacyError as e:\n        return {'code': e.code}\n")
    res = verify.run_oracle(err, [{"name": "c", "input": {}}])
    assert res["ok"] and res["results"][0]["output"] == {"code": "ORA-20010"}
    # ...pero no abre la puerta a escapes por atributos especiales
    for bad in ("def run(inp):\n    return {'a': run.__init__.__globals__}", "def run(inp):\n    return {'a': ().__init__.__class__}",
                "class A(Exception):\n    def __init__(self):\n        super().__init__.__self__.__class__\ndef run(inp):\n    return {}"):
        assert verify.validate_oracle_code(bad), bad


def test_oracle_sandbox_rejects_unsafe_code():
    from copilot import verify
    for code in ("import os\ndef run(inp): return {}", "def run(inp):\n  return {'a': open('x').read()}",
                 "def run(inp):\n  return eval('1')", "from decimal import Decimal\ndef run(inp):\n  return {'a': ().__class__}"):
        assert verify.validate_oracle_code(code), code


def test_project_purge(client):
    pid = _sample(client)
    assert client.delete(f"/api/projects/{pid}").json()["deleted"] is True
    assert client.get(f"/api/projects/{pid}").status_code == 404
    assert _count("projects") == 0 and _count("audit") == 0


# ---------------------------------------------------------------- hallazgos de la revisión independiente
def test_unit_test_generator_resists_injection_via_category_and_names():
    from copilot import verify
    src = verify.gen_unit_tests([{"name": "x'); process.exit(1); //", "category": "\\'+0);/*", "rule_ids": ["R-1'); evil("],
                                  "input": {"a": "1"}, "expected": {"b": "2"}}])
    assert "process.exit" not in src and "evil(" not in src.split("test(")[1].split("\n")[0]
    assert src.count("test(") == 1 and src.count("\n});") == 1


def test_comment_stripper_does_not_hide_code_after_slashes_in_strings():
    from copilot import verify
    scan = verify.scan_project([{"path": "src/domain/a.ts", "content": "const u = 'http://x//y'; eval('1');"},
                                {"path": "src/domain/b.ts", "content": "import { x } from 'node:fs/promises';"},
                                {"path": "src/domain/c.ts", "content": "const t = globalThis;"}], "typescript")
    msgs = " ".join(f["message"] for f in scan["findings"])
    assert "eval" in msgs and "plataforma" in msgs and "globales" in msgs


def test_masking_does_not_alter_business_words_containing_pass():
    from copilot import masking
    out, found = masking.mask_text("           MOVE 'PASSED' TO WS-STATUS\n           MOVE 'BYPASS' TO WS-X\n")
    assert "PASSED" in out and "BYPASS" in out and not found


def test_local_engine_rejects_fractional_exponent():
    from copilot import local_engine as le
    from copilot.cobol import UnsupportedConstruct
    src = ("       IDENTIFICATION DIVISION.\n       PROGRAM-ID. T.\n       DATA DIVISION.\n       WORKING-STORAGE SECTION.\n"
           "       01 REC.\n          05 R-A PIC 9(3)V99.\n          05 R-B PIC 9(5)V99.\n       PROCEDURE DIVISION.\n       MAIN-PARA.\n"
           "           COMPUTE R-B ROUNDED = (1 + R-A) ** 0.5\n           GOBACK.\n")
    user = '<legacy_source file="t.cbl" language="cobol">\n' + "\n".join(f"{i:>4}| {ln}" for i, ln in enumerate(src.split("\n"), 1)) + "\n</legacy_source>"
    analysis = le.stage_analyze(user)
    import pytest
    with pytest.raises(UnsupportedConstruct):
        le.stage_codegen(user + '\n\nCATÁLOGO DE REGLAS APROBADO (fuente de verdad):\n[]\n\nCONTRATO DE E/S:\n' + json.dumps(analysis["io_contract"]), "proyecto TypeScript")


def test_local_cache_key_depends_on_source_and_ollama_cannot_change_numbers(monkeypatch):
    from copilot import ingest, local_engine as le, local_llm
    from copilot.cobol import parse_program
    a = (ROOT / "golden/cobol_amortizacion/LOANAMRT.cbl").read_bytes()
    b = a.replace(b"0.0899", b"0.0777")
    keys = []
    for blob in (a, b):
        r = ingest.build_artifacts([("LOANAMRT.cbl", blob), ("LOANREC.cpy", (ROOT / "golden/cobol_amortizacion/LOANREC.cpy").read_bytes())])
        keys.append(le._key(le.io_model(parse_program(r["artifacts"]))["contract"]))
    assert keys[0] != keys[1]
    rules = [{"id": "R-001", "description": "Monto entre 1000 y 5000", "conditions": ["principal < 1000"], "actions": ["rechazar E01"]}]
    monkeypatch.setattr(local_llm, "available", lambda: True)
    monkeypatch.setenv("COPILOT_OLLAMA_MODEL", "demo")
    monkeypatch.setattr(local_llm, "_post", lambda *a, **k: {"message": {"content": json.dumps({"rules": [
        {"id": "R-001", "description": "El monto debe estar entre 1000 y 9999 para ser aceptado."}]})}})
    assert local_llm.rewrite_rule_descriptions(rules) == {}        # cifra nueva (9999) ? descartado
    monkeypatch.setattr(local_llm, "_post", lambda *a, **k: {"message": {"content": json.dumps({"rules": [
        {"id": "R-001", "description": "El monto debe estar entre 1000 y 5000 para ser aceptado."}]})}})
    assert "R-001" in local_llm.rewrite_rule_descriptions(rules)


def test_local_model_host_validation_is_strict(monkeypatch):
    from copilot import local_llm
    monkeypatch.setattr(local_llm, "HOST", "http://127.0.0.1.evil.example:11434")
    with pytest.raises(RuntimeError):
        local_llm._post("/api/chat", {}, 1)
