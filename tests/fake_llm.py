"""Proveedor LLM simulado SOLO PARA PRUEBAS (no es la salida del modelo real). Respuestas escritas a mano para el caso COBOL."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FX = ROOT / "tests" / "fixtures" / "ts_solution"
GOLD = ROOT / "golden" / "cobol_amortizacion"

IO = {
    "description": "Evalúa una solicitud de préstamo y calcula tasa, cuota, seguro y totales.",
    "inputs": [
        {"name": "principal", "type": "decimal", "scale": 2, "description": "Monto solicitado"},
        {"name": "term_months", "type": "integer", "scale": 0, "description": "Plazo en meses"},
        {"name": "credit_score", "type": "integer", "scale": 0, "description": "Puntaje crediticio"},
        {"name": "customer_age", "type": "integer", "scale": 0, "description": "Edad del cliente"},
    ],
    "outputs": [
        {"name": "status", "type": "string", "scale": 0, "description": "APPROVED o REJECTED"},
        {"name": "error_code", "type": "string", "scale": 0, "description": "Código de rechazo"},
        {"name": "annual_rate", "type": "decimal", "scale": 4, "description": "Tasa anual"},
        {"name": "monthly_payment", "type": "decimal", "scale": 2, "description": "Cuota mensual"},
        {"name": "insurance", "type": "decimal", "scale": 2, "description": "Seguro mensual"},
        {"name": "total_interest", "type": "decimal", "scale": 2, "description": "Interés total"},
        {"name": "total_paid", "type": "decimal", "scale": 2, "description": "Total pagado"},
    ],
}

RULE_DEFS = [
    ("R-001", "Monto permitido", "validation", "IF LR-PRINCIPAL < 1000.00 OR LR-PRINCIPAL > 500000.00",
     "El monto debe estar entre 1,000.00 y 500,000.00; si no, se rechaza con E01."),
    ("R-002", "Plazo permitido", "validation", "IF LR-TERM-MONTHS < 6 OR LR-TERM-MONTHS > 360",
     "El plazo debe estar entre 6 y 360 meses; si no, se rechaza con E02."),
    ("R-003", "Edad máxima al vencimiento", "limit", "IF WS-MATURITY-AGE > 75",
     "Edad + años enteros del plazo (truncados) no puede superar 75; si no, E03."),
    ("R-004", "Tasa según puntaje", "decision", "WHEN LR-CREDIT-SCORE >= 750",
     "Tasa 8.99 % (>=750), 12.99 % (>=650), 18.99 % (>=550); menor a 550 se rechaza con E04."),
    ("R-005", "Promoción", "decision", "IF LR-CREDIT-SCORE >= 800 AND LR-TERM-MONTHS <= 60",
     "Puntaje >= 800 y plazo <= 60 reduce la tasa en 0.25 puntos."),
    ("R-006", "Recargo por plazo largo", "decision", "IF LR-TERM-MONTHS > 120",
     "Plazo mayor a 120 meses suma 0.50 puntos a la tasa."),
    ("R-007", "Cuota francesa", "calculation", "COMPUTE WS-RATE-MONTHLY ROUNDED = LR-ANNUAL-RATE / 12",
     "Tasa mensual a 9 decimales, factor (1+i)^n a 9 decimales y cuota redondeada a 2 decimales."),
    ("R-008", "Seguro por edad", "calculation", "WHEN LR-CUSTOMER-AGE < 40",
     "Seguro mensual: 0.035 % (<40), 0.055 % (<60), 0.095 % (>=60) del monto, redondeado a 2 decimales."),
    ("R-009", "Totales truncados", "calculation", "COMPUTE LR-TOTAL-INTEREST =",
     "Interés total y total pagado se truncan a 2 decimales (sin ROUNDED)."),
]

RULE_MAP = {"R-AMOUNT": "R-001", "R-TERM": "R-002", "R-AGE": "R-003", "R-RATE": "R-004", "R-PROMO": "R-005",
            "R-SURCHARGE": "R-006", "R-ROUNDING": "R-007", "R-INSURANCE": "R-008"}


def _find_line(text: str, quote: str) -> int:
    for i, ln in enumerate(text.split("\n"), start=1):
        if quote in ln:
            return i
    return 1


def provider(stage: str, system: str, user: str, schema: dict | None) -> Any:
    src = (GOLD / "LOANAMRT.cbl").read_text(encoding="utf-8")
    n = src.count("\n") + 1
    if stage == "analyze":
        from copilot import static_analysis as sa
        art = {"path": "LOANAMRT.cbl", "language": "cobol", "text": src}
        det = sa.CobolAdapter().analyze(art)
        infra = {"READ-REQUEST", "WRITE-AUDIT", "ERROR-EXIT", "UNUSED-AUDIT-LOG"}
        units = [{"name": "LOANAMRT", "kind": "program", "file": "LOANAMRT.cbl", "start_line": 1, "end_line": n,
                  "summary": "Programa de cálculo de cuota de préstamo.", "classification": "mixed", "calls": [], "data_read": [], "data_written": []}]
        for u in det["units"]:
            units.append({"name": u["name"], "kind": "paragraph", "file": "LOANAMRT.cbl", "start_line": u["start_line"], "end_line": u["end_line"],
                          "summary": f"Párrafo {u['name']}", "classification": "infrastructure" if u["name"] in infra else "business",
                          "calls": [], "data_read": [], "data_written": []})
        return {"language": "COBOL", "dialect": "IBM Enterprise COBOL", "domain_summary": "Cálculo de cuota de préstamo por amortización francesa.",
                "units": units, "entry_points": ["MAIN-PARA"],
                "data_items": [{"name": "LR-PRINCIPAL", "legacy_type": "PIC S9(9)V99 COMP-3", "modern_type": "Decimal(scale 2)", "scale": 2, "description": "Monto"}],
                "io_contract": IO, "risks": [{"unit": "CALC-PAYMENT", "level": "high", "reason": "Aritmética con escalas intermedias"}],
                "security_findings": []}
    if stage == "rules":
        rules = []
        for rid, name, cat, quote, desc in RULE_DEFS:
            line = _find_line(src, quote)
            if rid == "R-006":
                line += 5  # línea incorrecta a propósito: el verificador debe corregirla
            rules.append({"id": rid, "name": name, "description": desc, "category": cat, "conditions": [quote], "actions": [desc],
                          "data_items": ["LR-PRINCIPAL"], "source_refs": [{"file": "LOANAMRT.cbl", "start_line": line, "end_line": line, "quote": quote}],
                          "confidence": 0.93, "assumptions": [], "gherkin": f"Escenario: {name}\n  Dado un caso aplicable\n  Cuando se evalúa\n  Entonces {desc}",
                          "decision_table": {"columns": [], "rows": []}})
        rules.append({"id": "R-010", "name": "Descuento por nómina (alucinada)", "description": "Regla inexistente en el código.", "category": "decision",
                      "conditions": ["IF LR-PAYROLL-FLAG = 'Y'"], "actions": ["Reducir tasa"], "data_items": [],
                      "source_refs": [{"file": "LOANAMRT.cbl", "start_line": 10, "end_line": 10, "quote": "IF LR-PAYROLL-FLAG = 'Y'"}],
                      "confidence": 0.9, "assumptions": [], "gherkin": "Escenario: x", "decision_table": {"columns": [], "rows": []}})
        return {"rules": rules}
    if stage == "codegen":
        files = [{"path": str(p.relative_to(FX)).replace("\\", "/"), "content": p.read_text(encoding="utf-8")} for p in FX.rglob("*") if p.is_file()]
        return {"design": {"summary": "Arquitectura hexagonal: dominio puro con reglas como funciones/specifications.",
                           "domain_model": [{"name": "LoanRequest", "kind": "value object", "responsibility": "Entrada validada"}],
                           "ports": [{"name": "AuditPort", "direction": "out", "description": "Auditoría"}], "patterns": ["Specification", "Strategy"],
                           "adrs": [{"title": "Decimal exacto", "context": "COMP-3 requiere precisión.", "decision": "Usar Decimal con escala.", "consequences": "Sin errores de punto flotante."}]},
                "files": files, "openapi_yaml": "openapi: 3.0.3\ninfo: {title: Loan, version: 1.0.0}\npaths: {}\n", "assumptions": ["Redondeo COBOL ROUNDED = mitad hacia arriba."]}
    if stage == "oracle":
        code = (GOLD / "reference.py").read_text(encoding="utf-8").split("if __name__")[0]
        code = code.replace("    import json\n", "")
        return {"python_code": code, "notes": "Referencia independiente."}
    if stage == "qa_cases":
        ref = json.loads(json.dumps([]))
        import importlib.util
        spec = importlib.util.spec_from_file_location("ref", GOLD / "reference.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        cases = []
        for name, rule, inp in mod.CASES:
            ids = [RULE_MAP[rule]] + (["R-009"] if name.startswith(("nominal", "monto_maximo")) else [])
            cases.append({"name": name, "category": "nominal", "rule_ids": ids, "rationale": "caso", "input": [{"name": k, "value": v} for k, v in inp.items()]})
        return {"cases": cases}
    if stage == "docs":
        return {"overview_md": "El programa LOANAMRT calcula la cuota (R-007).", "data_dictionary": [{"name": "principal", "legacy_type": "S9(9)V99 COMP-3", "modern_type": "Decimal", "description": "Monto"}],
                "architecture_mermaid": "flowchart LR\n  API --> UseCase --> Domain", "sequence_mermaid": "sequenceDiagram\n  Cliente->>API: solicitud\n  API->>Dominio: evaluar",
                "glossary": [{"term": "COMP-3", "definition": "Decimal empaquetado"}], "executive_summary": "Se migró el cálculo de préstamos con equivalencia verificada.", "assumptions": ["Datos sintéticos."]}
    raise AssertionError(f"etapa inesperada {stage}")
