"""Arbitraje del oráculo, reglas de código muerto en la trazabilidad y casos complementarios para reglas sin pruebas (ADR-019)."""
import pytest

GOOD = "def run(inp):\n    return {'out': 'RIGHT'}\n"
BAD = "def run(inp):\n    return {'out': 'WRONG'}\n"


def _project(rules=None):
    return {"id": "a" * 32, "artifacts": [{"path": "x.sql", "language": "plsql", "text": "BEGIN NULL; END;", "lines": 1}],
            "analysis": {"io_contract": {"inputs": [{"name": "a", "type": "string", "scale": 0}], "outputs": [{"name": "out", "type": "string", "scale": 0}]}},
            "rules": rules or [], "provided_cases": [],
            "generation": {"target": "typescript", "files": [{"path": "src/domain/a.ts", "content": "export const a = 1;"}], "autofix": []}}


@pytest.fixture()
def stubs(monkeypatch):
    from copilot import delivery, llm, verify
    calls = []
    case = {"name": "c1", "category": "x", "rule_ids": [], "input": {"a": "1"}}
    monkeypatch.setattr(delivery, "_cases_from_llm", lambda p: [case])
    monkeypatch.setattr(delivery, "_oracle", lambda p, cases: (BAD, {"ok": True, "results": [{"name": "c1", "ok": True, "output": {"out": "WRONG"}}]}))
    monkeypatch.setattr(verify, "scan_project", lambda files, target: {"findings": [], "blocking": 0, "by_category": {}, "rule_tags": {}, "max_cc": 1, "layers": []})
    monkeypatch.setattr(verify, "run_ts_cases", lambda files, cases: {"ok": True, "results": [{"name": c["name"], "ok": True, "output": {"out": "RIGHT"}} for c in cases]})
    monkeypatch.setattr(verify, "run_ts_tests", lambda files, src: {"ok": True, "tests": 1, "passed": 1, "failed": 0, "line_coverage": 99.0, "branch_coverage": 99.0})

    def fake_call(stage, system, user, schema=None, **kw):
        calls.append(stage)
        if stage == "autofix":
            return {"files": [], "explanation": "No cambié el código: el legacy (línea 9) exige ese resultado; el oráculo discrepa."}
        if stage == "oracle":
            return {"python_code": GOOD, "notes": ""}
        raise AssertionError(stage)
    monkeypatch.setattr(llm, "call", fake_call)
    return calls


def test_oracle_arbitration_resolves_a_case_where_the_code_follows_the_legacy(stubs):
    from copilot import delivery
    p = _project()
    gate = delivery.verify_stage(p)
    v = p["verification"]
    assert v["equivalence"]["pct"] == 100.0 and gate["equivalence_pct"] == 100.0
    assert stubs == ["autofix", "oracle"]                                    # una autocorrección y una segunda lectura del oráculo
    assert v["oracle_arbitration"] == [{"cases": ["c1"], "changed": ["c1"], "note": v["oracle_arbitration"][0]["note"]}]
    assert v["oracle_code"] == GOOD and v["evidence"] == "E3"


def test_arbitration_never_applies_to_client_provided_cases(stubs, monkeypatch):
    from copilot import delivery
    monkeypatch.setattr(delivery, "_oracle", lambda p, cases: (GOOD, {"ok": True, "results": [{"name": "c1", "ok": True, "output": {"out": "RIGHT"}}]}))
    p = _project()
    p["provided_cases"] = [{"name": "cliente", "input": {"a": "1"}, "expected": {"out": "OTRO"}}]   # E2: el cliente dice OTRO; el código da RIGHT
    delivery.verify_stage(p)
    v = p["verification"]
    assert v["equivalence"]["failed"] == 1 and not v["oracle_arbitration"]    # un caso E2 que falla NO se «arbitra»: sigue fallando
    assert "oracle" not in stubs


def test_dead_code_rules_do_not_count_as_orphans_but_untested_live_rules_do():
    from copilot import delivery
    rule = lambda i, name, desc="": {"id": i, "name": name, "description": desc, "status": "approved", "source_refs": [{"file": "x", "start_line": 1, "end_line": 2}]}
    p = _project([rule("R-001", "Plazo máximo"), rule("R-002", "Cálculo de IVA (no utilizado)"), rule("R-003", "Deducible 2009", "Versión obsoleta, nunca se invoca"),
                  rule("R-004", "Retención")])
    p["generation"]["scan"] = {"rule_tags": {"R-001": ["src/a.ts"], "R-004": ["src/b.ts"]}}
    p["verification"] = {"cases": [{"name": "c1", "rule_ids": ["R-001"]}]}
    t = delivery.trace_matrix(p)
    assert t["dead_code_rules"] == ["R-002", "R-003"]
    assert t["orphans"] == ["R-004"]                                         # R-004 tiene código pero ninguna prueba: sigue siendo huérfana
    assert t["complete_pct"] == 50.0                                         # 1 de 2 reglas vivas (las de código muerto no cuentan)
    assert delivery.is_dead_rule({"name": "Totalizador del lote", "description": "Suma el neto aprobado"}) is False


def test_complementary_qa_call_covers_rules_without_cases(monkeypatch):
    from copilot import delivery, llm
    rule = lambda i, n: {"id": i, "name": n, "description": "", "category": "x", "conditions": [], "actions": [], "data_items": [], "decision_table": None, "status": "approved"}
    p = _project([rule("R-001", "Estado"), rule("R-002", "Plazo"), rule("R-003", "IVA (no utilizado)")])
    calls = []

    def fake_call(stage, system, user, schema=None, **kw):
        calls.append(user)
        ids = ["R-001"] if len(calls) == 1 else ["R-002"]
        return {"cases": [{"name": f"caso_{len(calls)}", "category": "nominal", "rule_ids": ids, "rationale": "", "input": [{"name": "a", "value": "1"}]}]}
    monkeypatch.setattr(llm, "call", fake_call)
    cases = delivery._cases_from_llm(p)
    assert len(calls) == 2 and "REGLAS SIN CASOS" in calls[1]
    assert '"R-002"' in calls[1] and '"R-003"' not in calls[1]                # pide solo la regla viva sin cobertura; el código muerto no
    assert sorted(c["name"] for c in cases) == ["caso_1", "caso_2"]
