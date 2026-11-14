"""Contingencia: reproduce SIN red ni IA la corrida real de Claude grabada en cassettes/ (muestra COBOL con casos aportados)."""
from pathlib import Path

import pytest

from conftest import wait_stage

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(not list((ROOT / "cassettes").glob("*.json")), reason="no hay cassettes grabados (haga una corrida con Claude)")
def test_replay_of_recorded_claude_run(client, monkeypatch):
    monkeypatch.setenv("COPILOT_LLM", "replay")
    monkeypatch.setenv("COPILOT_CASSETTES", str(ROOT / "cassettes"))
    pid = client.post("/api/projects/sample", json={"name": "cobol_amortizacion", "with_cases": True}).json()["id"]
    client.post(f"/api/projects/{pid}/start")
    p = wait_stage(client, pid, "rules")
    assert p["stages"]["rules"]["status"] == "done" and len(p["rules"]) >= 9
    assert client.post(f"/api/projects/{pid}/rules/approve-verified").json()["approved"] == len(p["rules"])
    client.post(f"/api/projects/{pid}/approve")
    client.post(f"/api/projects/{pid}/continue")
    p = wait_stage(client, pid, "package", timeout=60)
    assert all(p["stages"][s]["status"] == "done" for s in ("generate", "verify", "docs", "package"))
    e = p["verification"]["equivalence"]
    assert e["pct"] == 100.0 and e["numeric_differences"] == 0
    rows = client.get(f"/api/projects/{pid}").json()["llm"]["stages"]
    assert rows and all(r["source"] == "replay" for r in rows)           # procedencia rotulada: respuestas grabadas, sin IA en esta ejecución
