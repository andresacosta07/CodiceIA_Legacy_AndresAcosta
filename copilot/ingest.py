"""Ingesta: decodificación (UTF-8/EBCDIC), detección de lenguaje, enmascarado, resolución de includes."""
from __future__ import annotations

import posixpath
import re
from typing import Any

from . import masking, security

_EXT_LANG = {
    ".cbl": "cobol", ".cob": "cobol", ".cobol": "cobol", ".cpy": "cobol-copybook", ".copy": "cobol-copybook",
    ".jcl": "jcl", ".sql": "plsql", ".pks": "plsql", ".pkb": "plsql", ".plsql": "plsql", ".pls": "plsql",
    ".prc": "plsql", ".fnc": "plsql", ".trg": "plsql",
    ".rpg": "rpg", ".rpgle": "rpg", ".sqlrpgle": "rpg", ".java": "java",
}


def decode_bytes(blob: bytes) -> tuple[str, str]:
    """Devuelve (texto, codificación). Detecta EBCDIC (cp037) por distribución de bytes."""
    if b"\x00" in blob[:4096] and not _looks_utf16(blob):
        # Puede ser EBCDIC con muchos 0x00? EBCDIC usa 0x40 (espacio) y 0xC1-0xE9 (letras)
        pass
    sample = blob[:4096]
    ebcdic_hits = sum(1 for b in sample if b == 0x40 or 0xC1 <= b <= 0xE9 or 0xF0 <= b <= 0xF9 or 0x81 <= b <= 0xA9)
    ascii_hits = sum(1 for b in sample if b == 0x20 or 0x41 <= b <= 0x7A or 0x30 <= b <= 0x39)
    if sample and ebcdic_hits / len(sample) > 0.6 and ascii_hits / len(sample) < 0.35:
        return blob.decode("cp037", errors="replace"), "EBCDIC (cp037)"
    if _looks_utf16(blob):
        return blob.decode("utf-16", errors="replace"), "UTF-16"
    if b"\x00" in blob:
        raise security.SecurityError("El archivo parece binario y no puede analizarse como código fuente.")
    for enc, label in (("utf-8-sig", "UTF-8"), ("cp1252", "Windows-1252")):
        try:
            return blob.decode(enc), label
        except UnicodeDecodeError:
            continue
    return blob.decode("latin-1"), "ISO-8859-1"


def _looks_utf16(blob: bytes) -> bool:
    return blob[:2] in (b"\xff\xfe", b"\xfe\xff")


def detect_language(name: str, text: str) -> tuple[str, str]:
    """(lenguaje, dialecto/pista). 'unknown' se resuelve luego con el LLM en la etapa de análisis."""
    ext = posixpath.splitext(name.lower())[1]
    up = text[:20000].upper()
    if "IDENTIFICATION DIVISION" in up or "PROCEDURE DIVISION" in up or re.search(r"^\s{6,7}\d{2}\s+\S+\s+PIC", up, re.M):
        return "cobol", "IBM Enterprise COBOL" if "EXEC SQL" in up or "COMP-3" in up else "COBOL"
    if re.search(r"^\s*(?:CREATE\s+(?:OR\s+REPLACE\s+)?(?:PACKAGE|PROCEDURE|FUNCTION|TRIGGER)|DECLARE\b)", up, re.M) \
            or ("BEGIN" in up and "END;" in up):
        return "plsql", "Oracle PL/SQL"
    if re.search(r"^\s*(?:DCL-S|DCL-PROC|CTL-OPT|DCL-DS)\b", up, re.M) or re.search(r"^[HFDCP]\s", up, re.M) and ext in (".rpg", ".rpgle"):
        return "rpg", "RPG IV/ILE"
    if re.search(r"\b(?:PUBLIC\s+CLASS|IMPORT\s+JAVA\.|PACKAGE\s+[A-Z.]+;)", up) and ext == ".java":
        return "java", "Java"
    if re.search(r"^//\S+\s+(?:JOB|EXEC|DD)\b", up, re.M):
        return "jcl", "IBM JCL"
    if ext in _EXT_LANG:
        return _EXT_LANG[ext], ""
    return "unknown", ""


_COPY = re.compile(r"^\s{6,}COPY\s+([A-Z0-9\-]+)", re.I | re.M)


def build_artifacts(files: list[tuple[str, bytes]]) -> dict[str, Any]:
    """Convierte archivos en artefactos normalizados y enmascarados + informe de ingesta."""
    if not files:
        raise security.SecurityError("No se recibió ningún archivo ni código. Cargue un archivo, ZIP o pegue el código.")
    artifacts: list[dict[str, Any]] = []
    all_findings: list[dict[str, Any]] = []
    skipped_binary: list[str] = []
    for name, blob in files:
        name = security.safe_name(name)
        security.check_blob(name, blob)
        try:
            text, enc = decode_bytes(blob)
        except security.SecurityError:          # archivo binario: se omite y se informa (no se aborta toda la carga)
            skipped_binary.append(name)
            continue
        text = text.replace("\r\n", "\n").replace("\r", "\n").expandtabs(8)
        lang, dialect = detect_language(name, text)
        masked, findings = masking.mask_text(text)
        residual = masking.residual_scan(masked)
        for f in findings:
            f["file"] = name
        all_findings.extend(findings)
        artifacts.append({
            "path": name, "language": lang, "dialect": dialect, "encoding": enc,
            "lines": masked.count("\n") + 1, "text": masked, "masked_count": len(findings),
            "residual_secrets": len(residual),
        })
    if not artifacts:
        names = ", ".join(skipped_binary[:5]) + (" …" if len(skipped_binary) > 5 else "")
        raise security.SecurityError(f"El archivo parece binario y no puede analizarse como código fuente: {names}.")
    includes = resolve_includes(artifacts)
    langs = sorted({a["language"] for a in artifacts if a["language"] not in ("cobol-copybook",)})
    return {
        "artifacts": artifacts,
        "ingest_report": {
            "files": len(artifacts),
            "skipped_binary": skipped_binary[:50],
            "total_lines": sum(a["lines"] for a in artifacts),
            "languages": langs,
            "masked_total": len(all_findings),
            "masked_by_kind": _count_by(all_findings, "kind"),
            "mask_findings": [{"file": f["file"], "line": f["line"], "kind": f["kind"], "token": f["token"]} for f in all_findings],
            "residual_secrets": sum(a["residual_secrets"] for a in artifacts),
            "includes": includes,
            "gate_no_secrets": all(a["residual_secrets"] == 0 for a in artifacts),
        },
    }


def _count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for i in items:
        out[i[key]] = out.get(i[key], 0) + 1
    return out


def resolve_includes(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    stems = {posixpath.splitext(posixpath.basename(a["path"]))[0].upper(): a["path"] for a in artifacts}
    resolved: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []
    for a in artifacts:
        if a["language"] != "cobol":
            continue
        for m in _COPY.finditer(a["text"]):
            name = m.group(1).upper().rstrip(".")
            (resolved if name in stems else missing).append({"from": a["path"], "copybook": name, **({"file": stems[name]} if name in stems else {})})
    return {"resolved": resolved, "missing": missing, "complete": not missing}
