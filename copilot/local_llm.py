"""Enriquecimiento OPCIONAL con un modelo de IA local (Ollama), sin clave de API ni salida a Internet.

Activación: tener Ollama instalado y en ejecución y definir  COPILOT_OLLAMA_MODEL=<modelo>  (p. ej. qwen2.5:7b).
Alcance deliberadamente acotado: el modelo local SOLO redacta textos (descripciones de reglas en lenguaje de negocio y el
resumen ejecutivo). La lógica, las citas, el código y las pruebas siguen saliendo del motor determinista; si el modelo falla,
devuelve algo inválido o no está disponible, se conserva el texto determinista.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

HOST = os.environ.get("COPILOT_OLLAMA_HOST", "http://127.0.0.1:11434")


def model() -> str | None:
    return os.environ.get("COPILOT_OLLAMA_MODEL") or None


def _post(path: str, body: dict[str, Any], timeout: float) -> dict[str, Any]:
    from urllib.parse import urlparse
    if urlparse(HOST).scheme != "http" or urlparse(HOST).hostname not in ("127.0.0.1", "localhost"):
        raise RuntimeError("Solo se permite un servidor de modelo local (loopback).")
    req = urllib.request.Request(HOST + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (host restringido a loopback)
        return json.loads(r.read().decode())


def available() -> bool:
    if not model():
        return False
    from urllib.parse import urlparse
    if urlparse(HOST).scheme != "http" or urlparse(HOST).hostname not in ("127.0.0.1", "localhost"):
        return False
    try:
        with urllib.request.urlopen(HOST + "/api/tags", timeout=1.5) as r:  # noqa: S310
            return r.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _chat(system: str, user: str, schema: dict[str, Any], timeout: float = 180.0) -> dict[str, Any] | None:
    try:
        res = _post("/api/chat", {"model": model(), "stream": False, "format": schema, "options": {"temperature": 0},
                                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}, timeout)
        return json.loads(res["message"]["content"])
    except (urllib.error.URLError, OSError, ValueError, KeyError, RuntimeError, TypeError):
        return None


_SYS = ("Eres un analista de negocio bancario. Reescribes textos técnicos en español claro para personas no técnicas. "
        "No inventes reglas, cifras ni condiciones: conserva exactamente los valores y umbrales. Responde solo con JSON.")


def rewrite_rule_descriptions(rules: list[dict[str, Any]]) -> dict[str, str]:
    """{id: descripción} solo para reglas válidas; ignora cualquier id desconocido o texto vacío/excesivo."""
    if not available():
        return {}
    schema = {"type": "object", "properties": {"rules": {"type": "array", "items": {"type": "object", "properties": {
        "id": {"type": "string"}, "description": {"type": "string"}}, "required": ["id", "description"]}}}, "required": ["rules"]}
    payload = [{"id": r["id"], "tecnico": r["description"], "condiciones": r["conditions"], "acciones": r["actions"]} for r in rules]
    out = _chat(_SYS, "Reescribe la descripción de cada regla en 1-2 frases de negocio (mismos valores):\n" + json.dumps(payload, ensure_ascii=False), schema)
    by_id = {r["id"]: r for r in rules}
    good: dict[str, str] = {}
    nums = lambda s: set(re.findall(r"\d[\d.,]*\d|\d", s))  # noqa: E731
    for item in (out or {}).get("rules", []):
        if not (isinstance(item, dict) and item.get("id") in by_id and isinstance(item.get("description"), str) and 15 <= len(item["description"]) <= 500):
            continue
        r = by_id[item["id"]]
        original = " ".join([r["description"], *r["conditions"], *r["actions"]])
        if nums(item["description"]) <= nums(original):  # el modelo no puede introducir cifras nuevas ni alterar umbrales
            good[item["id"]] = item["description"].strip()
    return good


def executive_summary(context: str) -> str | None:
    if not available():
        return None
    schema = {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}
    out = _chat(_SYS, "Redacta un resumen ejecutivo de máximo 110 palabras sobre esta migración (valor de negocio y riesgo mitigado):\n" + context, schema)
    s = (out or {}).get("summary")
    return s.strip() if isinstance(s, str) and 40 <= len(s) <= 1200 else None
