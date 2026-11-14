"""Pruebas unitarias de componentes deterministas."""
import json
import subprocess
from pathlib import Path

from copilot import ingest, pipeline, schemas, static_analysis as sa, verify

ROOT = Path(__file__).resolve().parent.parent
COB = (ROOT / "golden/cobol_amortizacion/LOANAMRT.cbl").read_bytes()
CPY = (ROOT / "golden/cobol_amortizacion/LOANREC.cpy").read_bytes()


def test_language_detection_and_includes():
    r = ingest.build_artifacts([("LOANAMRT.cbl", COB), ("LOANREC.cpy", CPY)])
    langs = {a["path"]: a["language"] for a in r["artifacts"]}
    assert langs == {"LOANAMRT.cbl": "cobol", "LOANREC.cpy": "cobol-copybook"}
    assert r["ingest_report"]["includes"]["complete"]
    miss = ingest.build_artifacts([("LOANAMRT.cbl", COB)])
    assert miss["ingest_report"]["includes"]["missing"][0]["copybook"] == "LOANREC"


def test_ebcdic_detected_and_roundtrip():
    text = COB.decode("utf-8").replace("\n", "\n")
    blob = text.encode("cp037")
    r = ingest.build_artifacts([("LOANAMRT.cbl", blob)])
    a = r["artifacts"][0]
    assert a["encoding"].startswith("EBCDIC") and a["language"] == "cobol" and "PROCEDURE DIVISION" in a["text"]


def test_cobol_adapter_structure():
    r = ingest.build_artifacts([("LOANAMRT.cbl", COB), ("LOANREC.cpy", CPY)])
    res = sa.analyze_all(r["artifacts"])
    names = {u["name"] for f in res["files"] for u in f.get("units", [])}
    assert {"MAIN-PARA", "VALIDATE-INPUT", "DETERMINE-RATE", "CALC-PAYMENT", "WRITE-AUDIT"} <= names
    assert res["dead_units"] == ["UNUSED-AUDIT-LOG"] and res["tables"] == ["LOAN_AUDIT"]
    kinds = {(e["from"], e["to"], e["kind"]) for e in res["edges"]}
    assert ("MAIN-PARA", "VALIDATE-INPUT", "PERFORM") in kinds and ("MAIN-PARA", "ERROR-EXIT", "GO TO") in kinds
    cpy = next(f for f in res["files"] if f["file"] == "LOANREC.cpy")
    principal = next(d for d in cpy["data_items"] if d["name"] == "LR-PRINCIPAL")
    assert principal["usage"] == "COMP-3" and principal["scale"] == 2 and principal["int_digits"] == 9 and principal["signed"]


def test_generic_adapter_on_unknown_language():
    r = ingest.build_artifacts([("x.sql", (ROOT / "golden/plsql_siniestro/PKG_SINIESTROS.sql").read_bytes())])
    res = sa.analyze_all(r["artifacts"])
    assert res["rigor"] == "heuristico" and res["loc"] > 10 and res["max_cyclomatic"] >= 3


def test_citation_verifier():
    art = {"a.cbl": {"text": "L1\n   IF X > 5\n   MOVE 1 TO Y\nL4"}}
    ok = {"source_refs": [{"file": "a.cbl", "start_line": 2, "end_line": 2, "quote": "IF X > 5"}]}
    moved = {"source_refs": [{"file": "a.cbl", "start_line": 4, "end_line": 4, "quote": "if  X > 5"}]}
    fake = {"source_refs": [{"file": "a.cbl", "start_line": 2, "end_line": 2, "quote": "IF Z = 9"}]}
    nofile = {"source_refs": [{"file": "zz.cbl", "start_line": 1, "end_line": 1, "quote": "x"}]}
    assert pipeline.verify_citations(ok, art) == "verified"
    assert pipeline.verify_citations(moved, art) == "corrected" and moved["source_refs"][0]["start_line"] == 2
    assert pipeline.verify_citations(fake, art) == "failed" and pipeline.verify_citations(nofile, art) == "failed"
    assert pipeline.verify_citations({"source_refs": []}, art) == "failed"


def test_schema_validator():
    assert schemas.validate({"cases": []}, schemas.QA_CASES) == []
    assert schemas.validate({}, schemas.QA_CASES)
    assert schemas.validate({"cases": [{"name": 1}]}, schemas.QA_CASES)


def test_strictify_adds_required_and_no_additional():
    s = schemas.__dict__["ANALYSIS"]
    from copilot import llm
    st = llm.strictify(s)
    assert st["additionalProperties"] is False and set(st["required"]) == set(st["properties"])
    assert st["properties"]["units"]["items"]["additionalProperties"] is False


def test_compare_detects_one_cent_difference():
    contract = {"outputs": [{"name": "monthly_payment", "type": "decimal"}, {"name": "status", "type": "string"}]}
    exp = {"c1": {"monthly_payment": "2075.35", "status": "APPROVED"}, "c2": {"monthly_payment": "10.00", "status": "APPROVED"}}
    act = {"c1": {"ok": True, "output": {"monthly_payment": "2075.35", "status": "APPROVED"}},
           "c2": {"ok": True, "output": {"monthly_payment": "10.01", "status": "APPROVED"}}}
    r = verify.compare(exp, act, contract, {})
    assert r["passed"] == 1 and r["failed"] == 1 and r["numeric_differences"] == 1 and r["pct"] == 50.0


def test_decimal_runtime_matches_cobol_semantics():
    src = f"""import {{ Decimal }} from '../runtime/decimal.ts';
const out = [
  Decimal.of('2.345').setScale(2, 'HALF_UP').toString(), Decimal.of('2.345').setScale(2, 'DOWN').toString(),
  Decimal.of('-2.345').setScale(2, 'HALF_UP').toString(), Decimal.of('2.5').setScale(0, 'HALF_EVEN').toString(),
  Decimal.of('1').dividedBy('3', 5, 'HALF_UP').toString(), Decimal.of('12345.678').truncateToPic(3, 1).toString(),
  Decimal.of('1.1').plus('2.2').toString(), Decimal.of('0.1').times('0.2').toString(), Decimal.of('1.015').pow(3).toString(),
];
console.log(JSON.stringify(out));"""
    f = ROOT / "data" / "_dec_probe.mts"
    f.parent.mkdir(exist_ok=True)
    f.write_text(src, encoding="utf-8")
    try:
        out = subprocess.run([verify.NODE, str(f)], capture_output=True, text=True, timeout=30)
    finally:
        f.unlink(missing_ok=True)
    assert json.loads(out.stdout) == ["2.35", "2.34", "-2.35", "2", "0.33333", "345.6", "3.3", "0.02", "1.045678375"]


def test_golden_reference_vs_typescript_fixture():
    """La solución TS de referencia es equivalente (25 casos, tolerancia 0) y cumple los umbrales del Word."""
    fx = ROOT / "tests/fixtures/ts_solution"
    files = [{"path": str(p.relative_to(fx)).replace("\\", "/"), "content": p.read_text(encoding="utf-8")} for p in fx.rglob("*") if p.is_file()]
    cases = json.loads((ROOT / "golden/cobol_amortizacion/cases.json").read_text(encoding="utf-8-sig"))
    run = verify.run_ts_cases(files, cases)
    assert run["ok"], run
    cmp = verify.compare({c["name"]: c["expected"] for c in cases}, {r["name"]: r for r in run["results"]},
                         {"outputs": [{"name": k, "type": "decimal"} for k in cases[0]["expected"]]}, {})
    assert cmp["pct"] == 100.0 and cmp["numeric_differences"] == 0
    scan = verify.scan_project(files, "typescript")
    assert scan["blocking"] == 0 and scan["max_cc"] <= 10
    ut = verify.run_ts_tests(files, verify.gen_unit_tests([{**c, "rule_ids": []} for c in cases]))
    assert ut["ok"] and ut["line_coverage"] >= 80 and ut["branch_coverage"] >= 70
