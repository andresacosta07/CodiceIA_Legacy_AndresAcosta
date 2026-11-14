"""Un solo comando:  py run.py   (Windows: doble clic en iniciar.bat)

Hace todo: comprueba requisitos, crea .venv e instala dependencias si faltan, levanta la app y abre el navegador.

Opciones:
  --check        solo diagnostica el equipo (Python, Node, Claude Code, clave de API, puerto) y sale
  --claude       arranca con «Claude vía suscripción» (CLI de Claude Code, sin clave de API)
  --rapido       perfil de modelos RÁPIDO (config/models.fast.json: Sonnet/Haiku en lugar de Opus; más veloz, menos margen de calidad)
  --no-browser   no abre el navegador
El motor de IA también se cambia desde la interfaz (selector «Motor de IA»).
"""
from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
MIN_NODE = 24


def node_version() -> int | None:
    node = shutil.which("node")
    if not node:
        return None
    try:
        out = subprocess.run([node, "-v"], capture_output=True, text=True, timeout=10).stdout
        return int(re.match(r"v(\d+)", out.strip()).group(1))  # type: ignore[union-attr]
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        return None


def port_free(host: str, port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) != 0


def preflight() -> list[tuple[str, str, str]]:
    """(requisito, estado OK/AVISO/ERROR, detalle accionable)."""
    rows = []
    v = sys.version_info
    rows.append(("Python", "OK" if v >= (3, 10) else "ERROR", f"{v.major}.{v.minor}.{v.micro}" + ("" if v >= (3, 10) else " — se requiere 3.10 o superior (python.org)")))
    nv = node_version()
    if nv is None:
        rows.append(("Node.js", "AVISO", f"no instalado — sin Node no se puede ejecutar ni probar el código TypeScript generado (instale Node {MIN_NODE}+ desde nodejs.org)"))
    else:
        rows.append(("Node.js", "OK" if nv >= MIN_NODE else "AVISO", f"v{nv}" + ("" if nv >= MIN_NODE else f" — se recomienda {MIN_NODE}+ (permisos y pruebas con cobertura)")))
    rows.append(("Claude Code (opcional)", "OK" if shutil.which("claude") else "INFO",
                 "disponible: se puede usar «Claude vía suscripción»" if shutil.which("claude") else "no instalado: solo estarán «Sin IA» y «Pregrabado»"))
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY")) or any(
        l.startswith("ANTHROPIC_API_KEY=sk-ant-") and "REEMPLACE" not in l.upper() for l in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines()) if (ROOT / ".env").exists() else bool(os.environ.get("ANTHROPIC_API_KEY"))
    rows.append(("Clave de API (opcional)", "OK" if has_key else "INFO", "configurada" if has_key else "no configurada: no es necesaria"))
    rows.append(("Datos de ejemplo", "OK" if (ROOT / "golden" / "cobol_amortizacion").exists() else "ERROR", "muestras sintéticas presentes" if (ROOT / "golden").exists() else "falta la carpeta golden/"))
    rows.append(("Respuestas pregrabadas", "OK" if list((ROOT / "cassettes").glob("*.json")) else "INFO",
                 "hay una corrida real de Claude grabada (modo contingencia)" if list((ROOT / "cassettes").glob("*.json")) else "no hay (haga una corrida con Claude para grabarla)"))
    return rows


def print_preflight(rows: list[tuple[str, str, str]]) -> bool:
    icons = {"OK": "[ OK  ]", "AVISO": "[AVISO]", "INFO": "[ info]", "ERROR": "[ERROR]"}
    print("\n  Comprobación del equipo\n  -----------------------")
    for name, st, detail in rows:
        print(f"  {icons[st]} {name}: {detail}")
    print()
    return all(st != "ERROR" for _, st, _ in rows)


def main() -> int:
    rows = preflight()
    ok = print_preflight(rows)
    if "--check" in sys.argv:
        return 0 if ok else 1
    if not ok:
        print("  Corrija los errores indicados y vuelva a ejecutar.")
        return 1
    if not PY.exists():
        print("  Creando entorno virtual (solo la primera vez)…")
        venv.create(VENV, with_pip=True)
    if subprocess.run([str(PY), "-c", "import fastapi, uvicorn, anthropic"], capture_output=True).returncode != 0:
        print("  Instalando dependencias (solo la primera vez, requiere Internet)…")
        subprocess.check_call([str(PY), "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")])
    if "--claude" in sys.argv:  # extensión: Claude vía suscripción (Claude Code), sin clave de API
        os.environ["COPILOT_LLM"] = "claude-code"
    if "--rapido" in sys.argv:  # perfil de modelos rápido (ADR-018)
        os.environ["COPILOT_PROFILE"] = "fast"
    host = os.environ.get("COPILOT_HOST", "127.0.0.1")
    port = int(os.environ.get("COPILOT_PORT", "8000"))
    while not port_free(host, port) and port < 8100:
        print(f"  El puerto {port} está ocupado; se prueba el siguiente…")
        port += 1
    url = f"http://{host}:{port}"
    print(f"  Copiloto de Modernización → {url}   (Ctrl+C para detener)\n")
    if "--no-browser" not in sys.argv and not os.environ.get("COPILOT_NO_BROWSER"):
        threading.Timer(3.0, lambda: webbrowser.open(url)).start()
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    cmd = [str(PY), "-m", "uvicorn", "copilot.main:app", "--host", host, "--port", str(port), "--log-level", "warning"]
    try:
        return subprocess.call(cmd, env=env)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
