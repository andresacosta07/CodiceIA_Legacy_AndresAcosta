"""Capa de verificación (Word 2.3): guardrails, SAST ligero, ejecución aislada, equivalencia, cobertura.

El código generado se analiza estáticamente ANTES de ejecutarse y luego se ejecuta con el modelo de permisos de
Node (--permission: sin red, sin procesos hijos, lectura solo del directorio del proyecto). El oráculo Python se
valida por AST (solo `decimal` y `math`) y se ejecuta con `python -I` y builtins restringidos.
"""
from __future__ import annotations

import ast
import json
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DECIMAL = (ROOT / "runtime" / "decimal.ts").read_text(encoding="utf-8")
DECIMAL_PATH = "src/domain/shared/decimal.ts"
NODE = shutil.which("node")

# --------------------------------------------------------------------------- guardrails
_TS_FORBIDDEN = [
    (r"\beval\s*\(", "uso de eval"), (r"\bnew\s+Function\b|\bFunction\s*\(", "uso de Function()"),
    # `require` de Node: llamada suelta o `module.require`. Un MÉTODO propio llamado require (p. ej. `parametros.require(c)`,
    # que es un patrón habitual de «obtener o fallar») NO es el require de Node: va precedido de «.» o es su declaración.
    (r"(?<![\w.$])require\s*\(", "uso de require"), (r"\b(?:module|global|self)\s*\.\s*require\b", "uso de require"),
    (r"\bimport\s*\(", "import dinámico"),
    (r"\bprocess\b", "acceso a process"), (r"\bglobalThis\b|\bReflect\.|\bimport\.meta\b", "acceso a objetos globales"),
    (r"['\"](?:node:)?(?:fs(?:/promises)?|child_process|net|tls|dns|http2?|https|dgram|os|worker_threads|vm|module|cluster|inspector)['\"]",
     "módulo de plataforma prohibido"),
    (r"\bfetch\s*\(", "acceso a red (fetch)"), (r"\bconsole\.", "uso de console"),
    (r"\bXMLHttpRequest\b|\bWebSocket\b", "acceso a red"),
]
_TS_FLOAT = [(r"\bparseFloat\s*\(", "parseFloat sobre importes"), (r"\bMath\.(?:round|ceil|pow)\s*\(", "Math.* sobre importes"),
             (r"\.toFixed\s*\(", "toFixed (aritmética flotante)"), (r"\bNumber\s*\(\s*[^)]*\.", "Number() sobre decimales")]
_JAVA_FLOAT = [(r"\b(?:double|float|Double|Float)\b", "double/float en lógica numérica")]
_CS_FLOAT = [(r"\b(?:double|float)\b", "double/float en lógica numérica")]
_SQL_CONCAT = re.compile(r"""(?i)(?:select|insert|update|delete)\s+[^;\n]*['"]\s*\+""")
_SECRET = re.compile(r"(?i)(?:password|secret|api[_-]?key|token)\s*[:=]\s*['\"][^'\"]{4,}['\"]")


def _layer(path: str, target: str) -> str | None:
    p = path.replace("\\", "/")
    for layer in ("domain", "application", "infrastructure"):
        if re.search(rf"(?:^|/){layer}(?:/|$)", p, re.I) or (target == "csharp" and re.search(rf"(?:^|/){layer.capitalize()}", p)):
            return layer
    return None


def _strip_comments(src: str) -> str:
    """Quita comentarios // y /* */ respetando cadenas (un '//' dentro de un string NO oculta código)."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in "'\"`":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            out.append(src[i:j + 1])
            i = j + 1
        elif src.startswith("//", i):
            while i < n and src[i] != "\n":
                i += 1
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("\n" * src.count("\n", i, j))
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _functions(src: str) -> list[tuple[str, str]]:
    """(nombre, cuerpo) aproximado de funciones/métodos por balanceo de llaves."""
    out: list[tuple[str, str]] = []
    rx = re.compile(r"(?m)^[ \t]*(?:export\s+)?(?:public\s+|private\s+|protected\s+|static\s+|async\s+|readonly\s+|final\s+)*"
                    r"(?:function\s+)?(?:[A-Za-z_<>\[\],.? ]+\s+)?([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?::\s*[^{;=]+)?\s*\{")
    code = _strip_comments(src)
    for m in rx.finditer(code):
        name = m.group(1)
        if name in ("if", "for", "while", "switch", "catch", "constructor", "else", "return"):
            continue
        depth, i = 0, m.end() - 1
        while i < len(code):
            if code[i] == "{":
                depth += 1
            elif code[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        out.append((name, code[m.end(): i]))
    return out


# Cabecera de la DECLARACIÓN de un método/función propia llamada require: `require(code: string): Decimal {`
_REQUIRE_DECL = re.compile(r"(?m)^[ \t]*(?:(?:export|public|private|protected|static|readonly|async)\s+)*(?:function\s+)?require\s*"
                           r"(?:<[^>\n]*>)?\([^()\n]*\)\s*(?::\s*[^{;=\n]+)?\{")


def _cc(body: str) -> int:
    body = re.sub(r"(['\"`]).*?\1", "''", body)
    return 1 + len(re.findall(r"\b(?:if|for|while|case|catch)\b|&&|\|\||\?\?|\s\?\s", body))


def scan_project(files: list[dict[str, str]], target: str) -> dict[str, Any]:
    """Guardrails + SAST ligero sobre los archivos generados. Devuelve hallazgos por categoría."""
    findings: list[dict[str, Any]] = []
    layers_seen: set[str] = set()
    rule_tags: dict[str, list[str]] = {}
    max_cc, cc_over = 0, []
    ext = {"typescript": (".ts",), "java": (".java",), "csharp": (".cs",)}[target]
    code_files = [f for f in files if f["path"].endswith(ext)]

    def add(cat: str, path: str, msg: str, sev: str = "high") -> None:
        findings.append({"category": cat, "file": path, "message": msg, "severity": sev})

    for f in code_files:
        path, src = f["path"].replace("\\", "/"), f["content"]
        code = _strip_comments(src)
        layer = _layer(path, target)
        if layer:
            layers_seen.add(layer)
        is_test = "/test" in path.lower() or ".test." in path or "Test" in posixpath.basename(path)
        # --- seguridad (SAST ligero)
        if target == "typescript":
            checked = _REQUIRE_DECL.sub("", code)
            for rx, msg in _TS_FORBIDDEN:
                if re.search(rx, checked):
                    add("security", path, f"API prohibida: {msg}", "critical")
        if _SQL_CONCAT.search(code):
            add("security", path, "SQL construido por concatenación (riesgo de inyección SQL)", "critical")
        if _SECRET.search(code):
            add("security", path, "Posible secreto en el código", "critical")
        # --- precisión numérica
        if not is_test and not path.endswith("decimal.ts"):
            pats = _TS_FLOAT if target == "typescript" else _JAVA_FLOAT if target == "java" else _CS_FLOAT
            for rx, msg in pats:
                if re.search(rx, code):
                    add("numeric", path, msg, "high")
        # --- regla de dependencias
        imports = _imports(src, target)
        for imp in imports:
            tgt = _import_layer(path, imp, target)
            if layer == "domain" and tgt in ("application", "infrastructure"):
                add("architecture", path, f"domain no puede depender de {tgt} ({imp})")
            if layer == "application" and tgt == "infrastructure":
                add("architecture", path, f"application no puede depender de infrastructure ({imp})")
            if layer in ("domain", "application") and _framework_import(imp, target):
                add("architecture", path, f"{layer} no debe depender de frameworks ({imp})")
        # --- etiquetas de regla
        for tag in re.findall(r"(?:@rule|<rule>)\s*(R-\d+)", src):
            rule_tags.setdefault(tag, []).append(path)
        # --- complejidad
        if not is_test:
            for name, body in _functions(src):
                c = _cc(body)
                max_cc = max(max_cc, c)
                if c > 10:
                    cc_over.append({"file": path, "function": name, "cc": c})
                    add("complexity", path, f"complejidad ciclomática {c} > 10 en {name}", "medium")
    for layer in ("domain", "application", "infrastructure"):
        if layer not in layers_seen:
            add("architecture", "-", f"falta la capa {layer}")
    blocking = [f for f in findings if f["severity"] in ("critical", "high")]
    return {"findings": findings, "layers": sorted(layers_seen), "max_cc": max_cc, "cc_over": cc_over,
            "rule_tags": rule_tags, "blocking": len(blocking),
            "by_category": {c: sum(1 for f in findings if f["category"] == c) for c in
                            ("security", "numeric", "architecture", "complexity")}}


def _imports(src: str, target: str) -> list[str]:
    if target == "typescript":
        return re.findall(r"(?m)^\s*(?:import|export)\s+[^;]*?from\s+['\"]([^'\"]+)['\"]", src)
    if target == "java":
        return re.findall(r"(?m)^\s*import\s+(?:static\s+)?([\w.*]+);", src)
    return re.findall(r"(?m)^\s*using\s+([\w.]+);", src)


def _import_layer(path: str, imp: str, target: str) -> str | None:
    if target == "typescript":
        if not imp.startswith("."):
            return None
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), imp))
        return _layer(resolved, target)
    low = imp.lower()
    for layer in ("infrastructure", "application", "domain"):
        if f".{layer}." in f".{low}." or low.endswith(f".{layer}"):
            return layer
    return None


def _framework_import(imp: str, target: str) -> bool:
    if target == "typescript":
        return not imp.startswith(".")
    if target == "java":
        return imp.startswith(("org.springframework", "jakarta.", "javax.persistence", "com.fasterxml"))
    return imp.startswith(("Microsoft.AspNetCore", "Microsoft.EntityFrameworkCore"))


# --------------------------------------------------------------------------- ejecución aislada (TS)
_RUNNER = """import { readFileSync } from 'node:fs';
const cases = JSON.parse(readFileSync(new URL('./__cases.json', import.meta.url), 'utf8'));
const { execute } = await import('./src/index.ts');
const out = cases.map((c) => {
  try { return { name: c.name, ok: true, output: execute(c.input) }; }
  catch (e) { return { name: c.name, ok: false, error: String((e && e.message) || e) }; }
});
process.stdout.write(JSON.stringify(out));
"""


def materialize(files: list[dict[str, str]], dest: Path) -> None:
    for f in files:
        p = (dest / f["path"]).resolve()
        if dest.resolve() not in p.parents:
            raise ValueError(f"Ruta fuera del proyecto: {f['path']}")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f["content"], encoding="utf-8")
    dec = dest / DECIMAL_PATH
    dec.parent.mkdir(parents=True, exist_ok=True)
    dec.write_text(RUNTIME_DECIMAL, encoding="utf-8")


def _node_cmd(extra_read: Path, args: list[str]) -> list[str]:
    assert NODE
    return [NODE, "--permission", f"--allow-fs-read={extra_read}", "--no-warnings", *args]


def run_ts_cases(files: list[dict[str, str]], cases: list[dict[str, Any]], timeout: int = 90) -> dict[str, Any]:
    """Ejecuta los casos contra el proyecto TS. Devuelve {ok, results|error}."""
    if not NODE:
        return {"ok": False, "error": "Node.js no está instalado; no se puede ejecutar el código TypeScript."}
    with tempfile.TemporaryDirectory(prefix="copilot_ts_") as tmp:
        d = Path(tmp)
        materialize(files, d)
        (d / "__cases.json").write_text(json.dumps([{"name": c["name"], "input": c["input"]} for c in cases]), encoding="utf-8")
        (d / "__run_cases.mjs").write_text(_RUNNER, encoding="utf-8")
        try:
            p = subprocess.run(_node_cmd(d, [str(d / "__run_cases.mjs")]), cwd=d, capture_output=True, text=True,
                               timeout=timeout, env={"PATH": str(Path(NODE).parent), "SystemRoot": "C:\\Windows"})
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Tiempo de ejecución agotado en el sandbox."}
        if p.returncode != 0:
            return {"ok": False, "error": (p.stderr or p.stdout)[-2500:]}
        try:
            return {"ok": True, "results": json.loads(p.stdout)}
        except json.JSONDecodeError:
            return {"ok": False, "error": "Salida no válida del runner: " + p.stdout[-500:]}


def gen_unit_tests(cases: list[dict[str, Any]]) -> str:
    """Pruebas unitarias node:test DETERMINISTAS (aserciones explícitas con valores esperados)."""
    lines = ["import { test } from 'node:test';", "import assert from 'node:assert/strict';",
             "import { execute } from '../src/index.ts';", ""]
    safe = lambda s: re.sub(r"[^A-Za-z0-9_\-]", "_", str(s))[:60]  # noqa: E731 - evita inyección en el archivo de pruebas
    for c in cases:
        tag = ",".join(safe(r) for r in (c.get("rule_ids") or [])) or "general"
        title = f"[{tag}] {safe(c['name'])} ({safe(c.get('category', 'caso'))})"
        lines.append(f"test({json.dumps(title)}, () => {{")
        lines.append(f"  const actual = execute({json.dumps(c['input'], ensure_ascii=False)});")
        lines.append(f"  assert.deepStrictEqual(actual, {json.dumps(c['expected'], ensure_ascii=False)});")
        lines.append("});")
        lines.append("")
    return "\n".join(lines)


def run_ts_tests(files: list[dict[str, str]], test_source: str, timeout: int = 120) -> dict[str, Any]:
    """Ejecuta las pruebas unitarias con cobertura (node:test) en el sandbox de permisos."""
    if not NODE:
        return {"ok": False, "error": "Node.js no está instalado."}
    with tempfile.TemporaryDirectory(prefix="copilot_ut_") as tmp:
        d = Path(tmp)
        materialize(files, d)
        (d / "tests").mkdir(exist_ok=True)
        (d / "tests" / "rules.test.ts").write_text(test_source, encoding="utf-8")
        args = ["--test", "--test-isolation=none", "--experimental-test-coverage",
                "--test-coverage-exclude=tests/**", "--test-coverage-exclude=src/domain/shared/decimal.ts",
                "--test-coverage-exclude=__*", str(d / "tests" / "rules.test.ts")]
        # La cobertura V8 no es compatible con --permission. Mitigación: este paso solo se ejecuta DESPUÉS de que el
        # mismo código haya pasado la ejecución restringida (run_ts_cases) y el escaneo estático; entorno vacío.
        cmd = [NODE, "--no-warnings", *args]
        try:
            p = subprocess.run(cmd, cwd=d, capture_output=True, text=True, timeout=timeout,
                               env={"PATH": str(Path(NODE).parent), "SystemRoot": "C:\\Windows", "TEMP": str(d), "TMP": str(d)})
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Tiempo agotado ejecutando pruebas."}
        out = p.stdout + "\n" + p.stderr
        total = _grab(out, r"tests\s+(\d+)")
        passed = _grab(out, r"pass\s+(\d+)")
        failed = _grab(out, r"fail\s+(\d+)")
        cov = re.search(r"all files\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)", out)
        return {"ok": p.returncode == 0, "tests": total, "passed": passed, "failed": failed,
                "line_coverage": float(cov.group(1)) if cov else None, "branch_coverage": float(cov.group(2)) if cov else None,
                "func_coverage": float(cov.group(3)) if cov else None, "log_tail": out[-2000:]}


def _grab(text: str, rx: str) -> int:
    m = re.search(r"(?m)^[ℹ#\s]*" + rx, text)
    return int(m.group(1)) if m else 0


# --------------------------------------------------------------------------- oráculo Python
_ALLOWED_IMPORTS = {"decimal", "math"}
_BANNED_NAMES = {"open", "eval", "exec", "compile", "__import__", "input", "breakpoint", "globals", "locals", "vars",
                 "getattr", "setattr", "delattr", "memoryview", "exit", "quit", "help"}

_ORACLE_RUNNER = r"""
import sys, json, builtins
src = open(sys.argv[1], encoding='utf-8').read()
inputs = json.load(open(sys.argv[2], encoding='utf-8'))
ALLOWED = {'decimal', 'math'}
real_import = builtins.__import__
def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name.split('.')[0] not in ALLOWED:
        raise ImportError('Importación no permitida: ' + name)
    return real_import(name, globals, locals, fromlist, level)
safe = {k: getattr(builtins, k) for k in ('abs','all','any','bool','dict','divmod','enumerate','float','format','repr','int','isinstance','len','list','max','min','pow','range','round','set','sorted','str','sum','tuple','zip','Exception','ValueError','ArithmeticError','ZeroDivisionError','TypeError','KeyError','RuntimeError','OverflowError','super','object','True','False','None','__build_class__')}
safe['__import__'] = safe_import
ns = {'__builtins__': safe, '__name__': 'oracle'}
exec(compile(src, 'oracle', 'exec'), ns)
out = []
for inp in inputs:
    try:
        r = ns['run'](dict(inp['input']))
        out.append({'name': inp['name'], 'ok': True, 'output': {k: str(v) for k, v in r.items()}})
    except Exception as e:
        out.append({'name': inp['name'], 'ok': False, 'error': type(e).__name__ + ': ' + str(e)})
sys.stdout.write(json.dumps(out))
"""


def validate_oracle_code(code: str) -> list[str]:
    errs: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"Sintaxis inválida: {exc}"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            errs += [f"import no permitido: {a.name}" for a in node.names if a.name.split(".")[0] not in _ALLOWED_IMPORTS]
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in _ALLOWED_IMPORTS:
                errs.append(f"import no permitido: {node.module}")
        elif isinstance(node, ast.Name) and node.id in _BANNED_NAMES:
            errs.append(f"nombre prohibido: {node.id}")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__") and node.attr != "__init__":
            # `__init__` solo se admite para `super().__init__(...)` en clases de error propias; el resto (__class__, __globals__, __dict__…) sigue vetado
            errs.append(f"atributo prohibido: {node.attr}")
    if not any(isinstance(n, ast.FunctionDef) and n.name == "run" for n in tree.body):
        errs.append("falta la función run(inp)")
    return errs


def run_oracle(code: str, cases: list[dict[str, Any]], timeout: int = 60) -> dict[str, Any]:
    errs = validate_oracle_code(code)
    if errs:
        return {"ok": False, "error": "Oráculo rechazado por la validación estática: " + "; ".join(errs[:5])}
    with tempfile.TemporaryDirectory(prefix="copilot_or_") as tmp:
        d = Path(tmp)
        (d / "oracle.py").write_text(code, encoding="utf-8")
        (d / "cases.json").write_text(json.dumps([{"name": c["name"], "input": c["input"]} for c in cases]), encoding="utf-8")
        (d / "runner.py").write_text(_ORACLE_RUNNER, encoding="utf-8")
        try:
            p = subprocess.run([sys.executable, "-I", str(d / "runner.py"), str(d / "oracle.py"), str(d / "cases.json")],
                               cwd=d, capture_output=True, text=True, timeout=timeout, env={})
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Tiempo agotado ejecutando el oráculo."}
        if p.returncode != 0:
            return {"ok": False, "error": (p.stderr or "")[-1500:]}
        return {"ok": True, "results": json.loads(p.stdout)}


# --------------------------------------------------------------------------- comparación
def _same(a: str, b: str, ftype: str) -> tuple[bool, bool]:
    """(equivalente, formato_igual)."""
    if a == b:
        return True, True
    if ftype in ("decimal", "integer"):
        try:
            return Decimal(a) == Decimal(b), False
        except InvalidOperation:
            return False, False
    return False, False


def compare(expected: dict[str, dict[str, str]], actual: dict[str, dict[str, Any]], io_contract: dict[str, Any],
            evidence: dict[str, str]) -> dict[str, Any]:
    """Compara salidas esperadas (oráculo o casos aportados) con las del código moderno, campo a campo, tolerancia 0."""
    types = {f["name"]: f["type"] for f in io_contract.get("outputs", [])}
    rows, diffs, fmt_notes = [], 0, 0
    for name, exp in expected.items():
        act = actual.get(name)
        if act is None or not act.get("ok"):
            rows.append({"name": name, "equivalent": False, "evidence": evidence.get(name, "E3"),
                         "diffs": [{"field": "*", "expected": exp, "actual": (act or {}).get("error", "sin resultado")}]})
            diffs += 1
            continue
        out = act["output"]
        case_diffs = []
        for field, ev in exp.items():
            av = out.get(field)
            ok, same_fmt = _same(str(ev), str(av), types.get(field, "string"))
            if not ok:
                case_diffs.append({"field": field, "expected": ev, "actual": av})
            elif not same_fmt:
                fmt_notes += 1
        if case_diffs:
            diffs += 1
        rows.append({"name": name, "equivalent": not case_diffs, "evidence": evidence.get(name, "E3"), "diffs": case_diffs})
    total = len(rows)
    passed = sum(1 for r in rows if r["equivalent"])
    return {"total": total, "passed": passed, "failed": total - passed, "pct": round(100 * passed / total, 2) if total else 0.0,
            "numeric_differences": diffs, "format_notes": fmt_notes, "cases": rows}
