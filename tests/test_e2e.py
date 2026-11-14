"""Flujo completo de extremo a extremo con el proveedor simulado: ingesta → análisis → reglas → HITL → código → equivalencia → docs → paquete."""
import io
import zipfile

from conftest import wait_stage


def _create(client, target="typescript"):
    r = client.post("/api/projects/sample", json={"name": "cobol_amortizacion", "target": target})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_full_flow(client, fake):
    pid = _create(client)
    p = client.get(f"/api/projects/{pid}").json()
    assert p["ingest_report"]["gate_no_secrets"] is True
    assert p["ingest_report"]["masked_total"] >= 1  # la contraseña sintética fue enmascarada
    assert "Pr0d#2019" not in str(p["artifacts"])

    assert client.post(f"/api/projects/{pid}/start").json()["started"]
    p = wait_stage(client, pid, "rules")
    assert p["stages"]["analyze"]["status"] == "done"
    assert p["analysis"]["inventory_recall_pct"] == 100.0
    assert "UNUSED-AUDIT-LOG" in p["static"]["dead_units"]
    rules = {r["id"]: r for r in p["rules"]}
    assert rules["R-006"]["trace_status"] == "corrected"     # línea incorrecta corregida automáticamente
    assert rules["R-010"]["trace_status"] == "failed"        # cita alucinada detectada
    assert p["stages"]["rules"]["status"] == "gate_failed"   # no hay 100 % de trazabilidad

    # No se puede aprobar la regla alucinada ni cerrar el catálogo con reglas pendientes
    assert client.post(f"/api/projects/{pid}/rules/R-010/review", json={"status": "approved"}).status_code == 400
    assert client.post(f"/api/projects/{pid}/approve").status_code == 400
    assert client.post(f"/api/projects/{pid}/rules/approve-verified").json()["approved"] == 9
    assert client.post(f"/api/projects/{pid}/rules/R-010/review", json={"status": "rejected", "comment": "No existe en el código"}).status_code == 200
    assert client.post(f"/api/projects/{pid}/continue").status_code == 400   # sin aprobar el catálogo
    cat = client.post(f"/api/projects/{pid}/approve").json()
    assert cat["version"] == 1 and cat["approved_rules"] == 9

    assert client.post(f"/api/projects/{pid}/continue").json()["started"]
    p = wait_stage(client, pid, "package", timeout=180)
    for s in ("generate", "verify", "docs", "package"):
        assert p["stages"][s]["status"] == "done", (s, p["stages"][s])
    v = p["verification"]["equivalence"]
    assert v["pct"] == 100.0 and v["numeric_differences"] == 0 and v["total"] >= 24
    assert p["verification"]["unit_tests"]["line_coverage"] >= 80
    assert p["verification"]["unit_tests"]["branch_coverage"] >= 70
    assert p["generation"]["scan"]["blocking"] == 0
    assert p["trace"]["complete_pct"] == 100.0
    assert p["metrics"]["secrets_residual"] == 0

    z = client.get(f"/api/projects/{pid}/download")
    assert z.status_code == 200
    names = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    for needed in ("informe_ejecutivo.md", "README.md", "docs/02_catalogo_reglas.md", "docs/05_matriz_trazabilidad.md",
                   "reportes/equivalencia.md", "codigo_moderno/src/index.ts", "codigo_moderno/src/domain/shared/decimal.ts",
                   "codigo_moderno/tests/rules.test.ts", "docs/openapi.yaml"):
        assert needed in names, needed
    audit = client.get(f"/api/projects/{pid}/audit").json()
    assert audit["chain_ok"] is True and len(audit["events"]) >= 8


def test_java_target_is_static_only(client, fake):
    """Destino Java: se valida estáticamente y se declara explícitamente como NO ejecutado."""
    import fake_llm
    from copilot import llm
    base = fake_llm.provider

    def prov(stage, system, user, schema):
        if stage == "codegen":
            r = base(stage, system, user, schema)
            r["files"] = [{"path": "src/main/java/com/x/domain/Loan.java", "content": "package com.x.domain;\n/** @rule R-001 */\npublic class Loan { double x; }"},
                          {"path": "src/main/java/com/x/application/UseCase.java", "content": "package com.x.application;\nimport com.x.infrastructure.Repo;\npublic class UseCase {}"},
                          {"path": "src/main/java/com/x/infrastructure/Repo.java", "content": "package com.x.infrastructure;\npublic class Repo {}"}]
            return r
        return base(stage, system, user, schema)
    llm.PROVIDER = prov
    pid = _create(client, "java")
    client.post(f"/api/projects/{pid}/start")
    wait_stage(client, pid, "rules")
    client.post(f"/api/projects/{pid}/rules/approve-verified")
    client.post(f"/api/projects/{pid}/rules/R-010/review", json={"status": "rejected"})
    client.post(f"/api/projects/{pid}/approve")
    client.post(f"/api/projects/{pid}/continue")
    p = wait_stage(client, pid, "verify", timeout=60)
    assert p["verification"]["evidence"] == "NO-EJECUTADO"
    cats = {f["category"] for f in p["generation"]["scan"]["findings"]}
    assert "numeric" in cats and "architecture" in cats   # double + application→infrastructure detectados
    assert p["stages"]["verify"]["status"] == "gate_failed"
