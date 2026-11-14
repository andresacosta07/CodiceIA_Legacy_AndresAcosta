"""Enmascarado de secretos y PII ANTES de cualquier envío al LLM (ADR-005).

Invariante clave: el enmascarado NO cambia el número de líneas, para conservar la
trazabilidad a líneas de origen. Solo se sustituyen fragmentos dentro de cada línea.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict

_SECRET_WORDS = r"(?<![A-Za-z])(?:PASS(?:WORD|WD)?|PWD|SECRET|TOKEN|API[-_]?KEY|APIKEY|CLAVE|CREDENTIAL|PRIVATE[-_]?KEY)(?![A-Za-z])"

# (tipo, regex, grupo a enmascarar)
_PATTERNS: list[tuple[str, re.Pattern[str], int]] = [
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), 0),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), 0),
    ("api_key_sk", re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}\b"), 0),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b"), 0),
    ("conn_string_creds", re.compile(r"\b[a-z][a-z0-9+.\-]*://[^\s:/@'\"]+:([^\s@'\"]+)@", re.I), 1),
    ("conn_string_pwd", re.compile(r"(?i)\b(?:pwd|password)\s*=\s*([^;\s'\"]+)"), 1),
    ("jdbc_url", re.compile(r"(?i)jdbc:[a-z0-9]+:[^\s'\"]+"), 0),
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), 0),
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"), 0),
    ("national_id", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), 0),
]
_LITERAL = re.compile(r"""(['"])((?:(?!\1).){3,})\1""")
_SECRET_LINE = re.compile(r"(?i)" + _SECRET_WORDS)
_CARD = re.compile(r"\b(?:\d[ \-]?){13,19}\b")
_ASSIGN = re.compile(r"(?i)(" + _SECRET_WORDS + r"[A-Za-z0-9_\-]*\s*[:=]\s*)([^\s,;'\"]{4,})")


@dataclass
class Finding:
    kind: str
    line: int
    token: str


def _luhn(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        total += d
        alt = not alt
    return total % 10 == 0


def mask_text(text: str, heuristics: bool = True) -> tuple[str, list[dict]]:
    """Devuelve (texto_enmascarado, hallazgos). Conserva el número de líneas.

    `heuristics=False` aplica solo patrones de alta confianza (claves, JWT, credenciales en URLs, correos, IBAN, tarjetas
    Luhn…); se usa en la compuerta de salida, donde el texto incluye JSON/prompts y las heurísticas por línea darían falsos positivos.
    """
    findings: list[Finding] = []
    counter = 0
    out_lines: list[str] = []

    def token(kind: str, line_no: int) -> str:
        nonlocal counter
        counter += 1
        t = f"<SECRET_{counter:03d}>"
        findings.append(Finding(kind, line_no, t))
        return t

    for n, line in enumerate(text.split("\n"), start=1):
        cur = line
        for kind, rx, grp in _PATTERNS:
            def repl(m: re.Match[str], kind=kind, grp=grp, n=n) -> str:
                if grp and m.group(grp).startswith("<SECRET_"):
                    return m.group(0)  # ya enmascarado
                tok = token(kind, n)
                if grp == 0:
                    return tok
                s, e = m.span(grp)
                return m.group(0)[: s - m.start()] + tok + m.group(0)[e - m.start():]
            cur = rx.sub(repl, cur)
        # literales entre comillas en líneas que mencionan PASSWORD/SECRET/TOKEN...
        if heuristics and _SECRET_LINE.search(cur):
            cur = _LITERAL.sub(
                lambda m, n=n: m.group(1) + token("secret_literal", n) + m.group(1)
                if "<SECRET_" not in m.group(2) else m.group(0), cur)
            cur = _ASSIGN.sub(
                lambda m, n=n: m.group(1) + token("secret_assignment", n)
                if "<SECRET_" not in m.group(2) else m.group(0), cur)
        # tarjetas (Luhn) para evitar falsos positivos con importes
        def card_repl(m: re.Match[str], n=n) -> str:
            digits = re.sub(r"\D", "", m.group(0))
            if 13 <= len(digits) <= 19 and _luhn(digits):
                return token("card_number", n)
            return m.group(0)
        cur = _CARD.sub(card_repl, cur)
        out_lines.append(cur)
    return "\n".join(out_lines), [asdict(f) for f in findings]


def residual_scan(text: str, heuristics: bool = True) -> list[dict]:
    """Escaneo independiente tras enmascarar: debe devolver [] para permitir el envío."""
    _, found = mask_text(text, heuristics=heuristics)
    return found
