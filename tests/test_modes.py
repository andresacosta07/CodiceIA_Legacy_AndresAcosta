"""Modos de IA: local · claude-code (suscripción, sin clave) · live · replay. Sin llamar a ningún modelo real."""
import json
import subprocess

import pytest

from copilot import llm


@pytest.fixture(autouse=True)
def reset_mode():
    llm.MODE_OVERRIDE = None
    yield
    llm.MODE_OVERRIDE = None


class _Done:
    def __init__(self, out, rc=0, err=""):
        self.stdout, self.returncode, self.stderr = out, rc, err


def test_claude_code_invocation_is_isolated_and_keyless(monkeypatch):
    seen = {}

    def fake_run(cmd, **kw):
        seen.update(cmd=cmd, kw=kw)
        return _Done(json.dumps({"is_error": False, "structured_output": {"a": "x"}, "usage": {"input_tokens": 5, "cache_read_input_tokens": 7, "output_tokens": 3}}))
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(llm, "claude_cli", lambda: "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-" + "x" * 40)
    out, tin, tout = llm._claude_code("docs", "claude-sonnet-5-5", "low", "SISTEMA", "USUARIO <legacy_source>", {"type": "object", "properties": {"a": {"type": "string"}}})
    cmd, kw = seen["cmd"], seen["kw"]
    assert out == {"a": "x"} and (tin, tout) == (12, 3)
    assert cmd[cmd.index("--tools") + 1] == "" and "--no-session-persistence" in cmd and "--json-schema" in cmd
    assert kw["input"] == "USUARIO <legacy_source>"             # el código viaja por stdin, no por la línea de comandos
    assert "ANTHROPIC_API_KEY" not in kw["env"]                 # fuerza la suscripción, nunca la clave
    assert "CodigoLegacy" not in kw["cwd"] and "copilot_cc_" in kw["cwd"]   # directorio temporal vacío, sin acceso al proyecto


def test_claude_code_errors_are_reported(monkeypatch):
    monkeypatch.setattr(llm, "claude_cli", lambda: "claude")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Done(json.dumps({"is_error": True, "result": "limite alcanzado"}), rc=1))
    with pytest.raises(llm.LLMError, match="limite alcanzado"):
        llm._claude_code("docs", "m", "low", "s", "u", None)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Done("no es json"))
    with pytest.raises(llm.LLMError, match="no devolvió JSON"):
        llm._claude_code("docs", "m", "low", "s", "u", None)
    monkeypatch.setattr(llm, "claude_cli", lambda: None)
    with pytest.raises(llm.LLMError, match="CLI de Claude Code"):
        llm._claude_code("docs", "m", "low", "s", "u", None)


def test_call_in_claude_code_mode_records_cassette_and_logs_zero_cost(monkeypatch, tmp_path):
    from copilot import db
    db.init(tmp_path / "t.db")
    monkeypatch.setenv("COPILOT_CASSETTES", str(tmp_path / "cass"))
    llm.PROVIDER = None
    llm.MODE_OVERRIDE = "claude-code"
    monkeypatch.setattr(llm, "_claude_code", lambda *a, **k: ({"overview_md": "x"}, 100, 50))
    from copilot import schemas
    monkeypatch.setattr(schemas, "validate", lambda *a, **k: [])
    res = llm.call("docs", "s", "u", {"type": "object", "properties": {"overview_md": {"type": "string"}}}, project_id="p")
    assert res == {"overview_md": "x"}
    assert list((tmp_path / "cass").glob("*.json"))                 # grabado para el modo contingencia
    row = db._c().execute("SELECT model, cost_usd, source FROM llm_calls").fetchone()
    assert row[1] == 0.0 and row[2] == "claude-code" and "suscripción" in row[0]


def test_mode_endpoint_switches_and_rejects_unavailable(client, monkeypatch):
    monkeypatch.delenv("COPILOT_LLM", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(llm, "claude_cli", lambda: "claude")
    s = client.post("/api/mode", json={"mode": "claude-code"}).json()
    assert s["mode"] == "claude-code" and s["available_modes"]["claude-code"] is True and s["available_modes"]["live"] is False
    assert client.post("/api/mode", json={"mode": "live"}).status_code == 400          # sin clave
    assert client.post("/api/mode", json={"mode": "inventado"}).status_code == 400
    assert client.post("/api/mode", json={"mode": "local"}).json()["mode"] == "local"
    monkeypatch.setattr(llm, "claude_cli", lambda: None)
    assert client.post("/api/mode", json={"mode": "claude-code"}).status_code == 400   # CLI no instalado


def test_auto_mode_never_uses_claude_code_implicitly(monkeypatch):
    monkeypatch.delenv("COPILOT_LLM", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(llm, "claude_cli", lambda: "claude")
    assert llm.mode() == "local"        # la extensión con IA es opcional: se elige de forma explícita
