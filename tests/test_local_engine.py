"""Motor local determinista (sin IA): flujo completo, equivalencia contra casos de referencia independientes y límites."""
import json
from pathlib import Path

import pytest

from conftest import wait_stage

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def local(monkeypatch):
    monkeypatch.setenv("COPILOT_LLM", "local")
    monkeypatch.delenv("COPILOT_OLLAMA_MODEL", raising=False)


def _sample(client, name="cobol_amortizacion", with_cases=True, target="typescript"):
    return client.post("/api/projects/sample", json={"name": name, "with_cases": with_cases, "target": target}).json()["id"]


def test_local_full_flow_without_api_key(client, local):
    pid = _sample(client)
    client.post(f"/api/projects/{pid}/start")
    p = wait_stage(client, pid, "rules")
    assert p["stages"]["rules"]["status"] == "done"            # 100 % de reglas con cita verificada
    assert len(p["rules"]) >= 9 and all(r["trace_status"] == "verified" for r in p["rules"])
    cats = {r["category"] for r in p["rules"]}
    assert {"validation", "decision", "calculation"} <= cats
    assert any(r["decision_table"]["rows"] for r in p["rules"])  # tabla de decisión del EVALUATE
    units = {u["name"]: u["classification"] for u in p["analysis"]["units"]}
    assert units["READ-REQUEST"] == "infrastructure" and units["VALIDATE-INPUT"] == "business"
    assert [i["name"] for i in p["analysis"]["io_contract"]["inputs"]] == ["principal", "term_months", "credit_score", "customer_age"]

    assert client.post(f"/api/projects/{pid}/rules/approve-verified").json()["approved"] == len(p["rules"])
    client.post(f"/api/projects/{pid}/approve")
    client.post(f"/api/projects/{pid}/continue")
    p = wait_stage(client, pid, "package", timeout=180)
    for s in ("generate", "verify", "docs", "package"):
        assert p["stages"][s]["status"] == "done", (s, p["stages"][s])
    v = p["verification"]
    e = v["equivalence"]
    assert e["pct"] == 100.0 and e["numeric_differences"] == 0 and e["total"] >= 40
    assert "E2" in v["evidence"] and "E3" in v["evidence"]       # casos aportados (independientes) + oráculo derivado
    assert sum(1 for c in e["cases"] if c["evidence"] == "E2") == 25
    assert v["unit_tests"]["line_coverage"] >= 80 and v["unit_tests"]["branch_coverage"] >= 70
    scan = p["generation"]["scan"]
    assert scan["blocking"] == 0 and scan["max_cc"] <= 10 and set(scan["layers"]) == {"domain", "application", "infrastructure"}
    assert p["trace"]["complete_pct"] == 100.0 and v["rules_untested"] == []
    src = " ".join(f["content"] for f in p["generation"]["files"])
    assert "goto" not in src.lower() and "double" not in src and "parseFloat" not in src   # flujo explícito, sin float
    assert "return 'ERROR-EXIT';" in src                                                    # GO TO → valor de flujo
    llm_rows = client.get(f"/api/projects/{pid}").json()["llm"]["stages"]
    assert llm_rows and all(r["source"] == "local" and r["cost_usd"] == 0 for r in llm_rows)   # procedencia rotulada, costo 0


def test_python_backend_matches_hand_written_reference(local):
    """El oráculo derivado (traductor Python) coincide con la referencia escrita a mano en los 25 casos."""
    from copilot import ingest, local_engine as le, verify
    from copilot.cobol import parse_program
    r = ingest.build_artifacts([(f, (ROOT / "golden/cobol_amortizacion" / f).read_bytes()) for f in ("LOANAMRT.cbl", "LOANREC.cpy")])
    prog = parse_program(r["artifacts"])
    code = le.PyGen(prog, le.io_model(prog), {}).code()
    cases = json.loads((ROOT / "golden/cobol_amortizacion/cases.json").read_text(encoding="utf-8-sig"))
    res = verify.run_oracle(code, cases)
    assert res["ok"]
    for c, out in zip(cases, res["results"]):
        assert out["ok"] and out["output"] == c["expected"], (c["name"], out)


def test_local_engine_rejects_other_languages_clearly(client, local):
    pid = _sample(client, "plsql_siniestro", with_cases=False)
    client.post(f"/api/projects/{pid}/start")
    import time
    time.sleep(1.5)
    st = client.get(f"/api/projects/{pid}").json()["stages"]["analyze"]
    assert st["status"] == "failed" and "Motor local" in st["error"] and "API de Claude" in st["error"]
    assert st["hint"]


def test_local_engine_unsupported_construct_reports_line(local):
    from copilot import local_engine as le
    from copilot.cobol import UnsupportedConstruct
    src = ("       IDENTIFICATION DIVISION.\n       PROGRAM-ID. T.\n       DATA DIVISION.\n       WORKING-STORAGE SECTION.\n"
           "       01 X PIC 9(3).\n       PROCEDURE DIVISION.\n       MAIN-PARA.\n           SORT X\n           GOBACK.\n")
    user = '<legacy_source file="t.cbl" language="cobol">\n' + "\n".join(f"{i:>4}| {ln}" for i, ln in enumerate(src.split("\n"), 1)) + "\n</legacy_source>"
    with pytest.raises(UnsupportedConstruct) as exc:
        le.stage_analyze(user)
    assert "t.cbl:8" in str(exc.value) and "SORT" in str(exc.value)


def test_local_mode_blocks_non_typescript_targets(client, local):
    pid = _sample(client, target="java")
    client.post(f"/api/projects/{pid}/start")
    wait_stage(client, pid, "rules")
    client.post(f"/api/projects/{pid}/rules/approve-verified")
    client.post(f"/api/projects/{pid}/approve")
    client.post(f"/api/projects/{pid}/continue")
    import time
    time.sleep(2)
    st = client.get(f"/api/projects/{pid}").json()["stages"]["generate"]
    assert st["status"] == "failed" and "TypeScript" in st["error"]


def test_status_reports_local_mode(client, local):
    s = client.get("/api/status").json()
    assert s["mode"] == "local" and s["has_key"] is False


def test_optional_local_model_enrichment_is_safe(monkeypatch):
    from copilot import local_llm
    rules = [{"id": "R-001", "description": "x", "conditions": ["principal < 1000"], "actions": ["rechazar"]}]
    monkeypatch.setattr(local_llm, "available", lambda: True)
    monkeypatch.setenv("COPILOT_OLLAMA_MODEL", "demo")
    monkeypatch.setattr(local_llm, "_post", lambda *a, **k: {"message": {"content": json.dumps({"rules": [
        {"id": "R-001", "description": "El monto solicitado debe estar entre mil y quinientos mil."},
        {"id": "R-999", "description": "Regla inventada por el modelo que debe ignorarse."},
        {"id": "R-001", "description": "corta"}]})}})
    out = local_llm.rewrite_rule_descriptions(rules)
    assert list(out) == ["R-001"] and "mil" in out["R-001"]
    monkeypatch.setattr(local_llm, "_post", lambda *a, **k: (_ for _ in ()).throw(OSError("sin servidor")))
    assert local_llm.rewrite_rule_descriptions(rules) == {} and local_llm.executive_summary("x") is None
    monkeypatch.setattr(local_llm, "available", lambda: False)
    assert local_llm.rewrite_rule_descriptions(rules) == {}


def test_local_model_host_must_be_loopback(monkeypatch):
    from copilot import local_llm
    monkeypatch.setattr(local_llm, "HOST", "http://evil.example.com:11434")
    with pytest.raises(RuntimeError):
        local_llm._post("/api/chat", {}, 1)
