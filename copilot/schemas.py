"""Esquemas JSON de las salidas de los agentes (se validan en el servidor, además de forzarse en la API)."""
from __future__ import annotations

from typing import Any

S = {"type": "string"}
I = {"type": "integer"}
N = {"type": "number"}


def arr(item: dict[str, Any]) -> dict[str, Any]:
    return {"type": "array", "items": item}


def obj(**props: Any) -> dict[str, Any]:
    return {"type": "object", "properties": props}


IO_FIELD = obj(name=S, type={"type": "string", "enum": ["string", "integer", "decimal", "boolean", "date"]},
               scale=I, description=S)

ANALYSIS = obj(
    language=S, dialect=S, domain_summary=S,
    units=arr(obj(name=S, kind=S, file=S, start_line=I, end_line=I, summary=S,
                  classification={"type": "string", "enum": ["business", "infrastructure", "mixed"]},
                  calls=arr(S), data_read=arr(S), data_written=arr(S))),
    entry_points=arr(S),
    data_items=arr(obj(name=S, legacy_type=S, modern_type=S, scale=I, description=S)),
    io_contract=obj(description=S, inputs=arr(IO_FIELD), outputs=arr(IO_FIELD)),
    risks=arr(obj(unit=S, level={"type": "string", "enum": ["low", "medium", "high"]}, reason=S)),
    security_findings=arr(obj(file=S, line=I, category=S, description=S)),
)

RULES = obj(rules=arr(obj(
    id=S, name=S, description=S,
    category={"type": "string", "enum": ["validation", "calculation", "decision", "rounding", "limit", "other"]},
    conditions=arr(S), actions=arr(S), data_items=arr(S),
    source_refs=arr(obj(file=S, start_line=I, end_line=I, quote=S)),
    confidence=N, assumptions=arr(S), gherkin=S,
    decision_table=obj(columns=arr(S), rows=arr(arr(S))),
)))

FILE = obj(path=S, content=S)
CODEGEN = obj(
    design=obj(summary=S, domain_model=arr(obj(name=S, kind=S, responsibility=S)),
               ports=arr(obj(name=S, direction=S, description=S)), patterns=arr(S),
               adrs=arr(obj(title=S, context=S, decision=S, consequences=S))),
    files=arr(FILE), openapi_yaml=S, assumptions=arr(S),
)
AUTOFIX = obj(files=arr(FILE), explanation=S)
ORACLE = obj(python_code=S, notes=S)
QA_CASES = obj(cases=arr(obj(name=S, category=S, rule_ids=arr(S), rationale=S,
                              input=arr(obj(name=S, value=S)))))
DOCS = obj(overview_md=S, data_dictionary=arr(obj(name=S, legacy_type=S, modern_type=S, description=S)),
           architecture_mermaid=S, sequence_mermaid=S, glossary=arr(obj(term=S, definition=S)),
           executive_summary=S, assumptions=arr(S))


def validate(data: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Validador mínimo (tipos, required, enum) para no depender de jsonschema."""
    errs: list[str] = []
    t = schema.get("type")
    if t == "object":
        if not isinstance(data, dict):
            return [f"{path}: se esperaba objeto"]
        for k, sub in schema.get("properties", {}).items():
            if k not in data:
                errs.append(f"{path}.{k}: falta")
            else:
                errs += validate(data[k], sub, f"{path}.{k}")
    elif t == "array":
        if not isinstance(data, list):
            return [f"{path}: se esperaba arreglo"]
        for i, it in enumerate(data):
            errs += validate(it, schema["items"], f"{path}[{i}]")
    elif t == "string":
        if not isinstance(data, str):
            errs.append(f"{path}: se esperaba cadena")
        elif "enum" in schema and data not in schema["enum"]:
            errs.append(f"{path}: valor fuera de enum")
    elif t == "integer":
        if not isinstance(data, int) or isinstance(data, bool):
            errs.append(f"{path}: se esperaba entero")
    elif t == "number":
        if not isinstance(data, (int, float)) or isinstance(data, bool):
            errs.append(f"{path}: se esperaba número")
    return errs
