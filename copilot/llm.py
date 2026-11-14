"""Cliente LLM único de la app (ADR-003/005/007).

- Todo texto saliente pasa por la compuerta de enmascarado (EgressBlocked si queda residuo).
- Modelo por etapa desde config/models.json (nunca IDs fijos en código).
- Salidas estructuradas con JSON Schema (output_config.format) + validación + reintento.
- Modos: live (API real, graba cassettes), replay (solo cassettes; plan de contingencia sin red), auto.
- Registra tokens, costo y latencia por etapa (observabilidad).
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from . import db, masking

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config" / "models.json").read_text(encoding="utf-8"))

# Hook para pruebas: fn(stage, system, user, schema) -> dict | str
PROVIDER: Callable[[str, str, str, dict | None], Any] | None = None


class LLMError(RuntimeError):
    pass


class EgressBlocked(LLMError):
    """El texto a enviar contiene secretos/PII sin enmascarar."""


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if k.strip() == "ANTHROPIC_API_KEY" and (len(v) < 30 or "REEMPLACE" in v.upper()):
                    continue  # clave de ejemplo/incompleta: se trata como «sin clave» (modo local)
                os.environ.setdefault(k.strip(), v)


_load_dotenv()

# Perfil de modelos: «standard» (config/models.json) o «fast» (config/models.fast.json sobrescribe etapas puntuales; ADR-018).
PROFILE = "fast" if os.environ.get("COPILOT_PROFILE", "").strip().lower() in ("fast", "rapido", "rápido") else "standard"
if PROFILE == "fast":
    for _stage, _cfg in json.loads((ROOT / "config" / "models.fast.json").read_text(encoding="utf-8"))["stages"].items():
        CONFIG["stages"][_stage].update(_cfg)


MODE_OVERRIDE: str | None = None  # cambiado desde la UI (POST /api/mode); tiene prioridad sobre COPILOT_LLM
MODES = ("local", "claude-code", "live", "replay")


def claude_cli() -> str | None:
    """Ruta del CLI de Claude Code (usa la suscripción del usuario; no requiere clave de API)."""
    return shutil.which("claude")


def available_modes() -> dict[str, bool]:
    return {"local": True, "claude-code": claude_cli() is not None, "live": bool(os.environ.get("ANTHROPIC_API_KEY")), "replay": True}


def mode() -> str:
    """local (motor determinista sin IA) · claude-code (Claude vía suscripción, sin clave) · live (API de Claude) · replay (cassettes).
    'auto': clave → live, si no → local. Las extensiones con IA son opcionales y se eligen explícitamente."""
    m = (MODE_OVERRIDE or os.environ.get("COPILOT_LLM", "auto")).lower()
    if m == "auto":
        return "live" if os.environ.get("ANTHROPIC_API_KEY") else "local"
    return m


def set_mode(m: str) -> str:
    global MODE_OVERRIDE
    if m not in MODES or not available_modes()[m]:
        raise LLMError(f"Modo no disponible: {m}.")
    MODE_OVERRIDE = m
    return m


def status() -> dict[str, Any]:
    from . import local_llm
    return {"mode": mode(), "has_key": bool(os.environ.get("ANTHROPIC_API_KEY")), "local_model": local_llm.model() if local_llm.available() else None,
            "available_modes": available_modes(), "models": {k: v["model"] for k, v in CONFIG["stages"].items()}, "profile": PROFILE}


def cassette_dir() -> Path:
    return Path(os.environ.get("COPILOT_CASSETTES", str(ROOT / "cassettes")))


def strictify(schema: dict[str, Any]) -> dict[str, Any]:
    """additionalProperties:false y required=todas las propiedades, recursivamente (salidas estructuradas)."""
    s = copy.deepcopy(schema)

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"].keys())
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(s)
    return s


def _hash(stage: str, model: str, system: str, user: str, schema: dict | None) -> str:
    return hashlib.sha256("\x1f".join([stage, model, system, user, json.dumps(schema, sort_keys=True)]).encode()).hexdigest()


def _cost(model: str, tin: int, tout: int) -> float:
    p = CONFIG["pricing_usd_per_mtok"].get(model, {"in": 0, "out": 0})
    return (tin * p["in"] + tout * p["out"]) / 1_000_000


_client = None
_fallbacks_ok = True


def _client_get():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(max_retries=3)
    return _client


def _live(stage: str, model: str, effort: str, system: str, user: str, schema: dict | None, max_tokens: int) -> tuple[str, int, int]:
    global _fallbacks_ok
    import anthropic
    client = _client_get()
    params: dict[str, Any] = dict(model=model, max_tokens=max_tokens, system=system,
                                  messages=[{"role": "user", "content": user}])
    oc: dict[str, Any] = {"effort": effort}
    if schema is not None:
        oc["format"] = {"type": "json_schema", "schema": strictify(schema)}
    params["output_config"] = oc
    msg = None
    if CONFIG.get("use_server_fallbacks") and _fallbacks_ok:
        try:  # fallback por rechazo de clasificadores de seguridad (servidor)
            with client.beta.messages.stream(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **params) as s:
                msg = s.get_final_message()
        except (anthropic.BadRequestError, TypeError):
            _fallbacks_ok = False
            msg = None
    if msg is None:
        with client.messages.stream(**params) as s:
            msg = s.get_final_message()
    if msg.stop_reason == "refusal":
        raise LLMError(f"El modelo rechazó la solicitud en la etapa '{stage}' (stop_reason=refusal).")
    if msg.stop_reason == "max_tokens":
        raise LLMError(f"Respuesta truncada por max_tokens en la etapa '{stage}'.")
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    return text, msg.usage.input_tokens, msg.usage.output_tokens


def _claude_code(stage: str, model: str, effort: str, system: str, user: str, schema: dict | None, timeout: int = 900) -> tuple[Any, int, int]:
    """Llama a Claude mediante el CLI de Claude Code en modo no interactivo (suscripción del usuario, SIN clave de API).

    Aislamiento: sin herramientas (--tools ""), sin persistencia de sesión y en un directorio temporal vacío, de modo que el
    código legacy (dato no confiable) no puede provocar lecturas/escrituras. El prompt va por stdin (sin límite de línea de comandos).
    """
    exe = claude_cli()
    if not exe:
        raise LLMError("No se encontró el CLI de Claude Code (comando 'claude'). Instálelo e inicie sesión, o use el modo local.")
    cmd = [exe, "-p", "--output-format", "json", "--tools", "", "--no-session-persistence", "--model", model, "--effort", effort,
           "--system-prompt", system]
    if schema is not None:
        cmd += ["--json-schema", json.dumps(strictify(schema))]
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}  # fuerza el uso de la suscripción
    with tempfile.TemporaryDirectory(prefix="copilot_cc_") as cwd:
        try:
            p = subprocess.run(cmd, input=user, cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=timeout, env=env)
        except subprocess.TimeoutExpired as exc:
            raise LLMError(f"Claude Code excedió el tiempo en la etapa '{stage}'.") from exc
    try:
        d = json.loads(p.stdout)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Claude Code no devolvió JSON en '{stage}': {(p.stderr or p.stdout)[:300]}") from exc
    if p.returncode != 0 or d.get("is_error"):
        msg = str(d.get("result") or p.stderr)[:300]
        raise LLMError(f"Claude Code falló en '{stage}': {msg} (¿sesión iniciada con `claude` o límite de la suscripción?)")
    u = d.get("usage") or {}
    tin = int(u.get("input_tokens", 0)) + int(u.get("cache_creation_input_tokens", 0)) + int(u.get("cache_read_input_tokens", 0))
    tout = int(u.get("output_tokens", 0))
    if schema is None:
        return str(d.get("result", "")), tin, tout
    out = d.get("structured_output")
    if out is None:
        try:
            out = json.loads(d.get("result", ""))
        except (json.JSONDecodeError, TypeError) as exc:
            raise LLMError(f"Claude Code no devolvió la salida estructurada en '{stage}'.") from exc
    return out, tin, tout


def call(stage: str, system: str, user: str, schema: dict[str, Any] | None = None, *,
         project_id: str | None = None, max_tokens: int = 32000) -> Any:
    """Llama al LLM para una etapa. Devuelve dict (si hay schema) o str."""
    cfg = CONFIG["stages"][stage]
    model, effort = cfg["model"], cfg["effort"]
    residual = masking.residual_scan(system + "\n" + user, heuristics=False)
    if residual:
        raise EgressBlocked(f"Envío bloqueado en '{stage}': {len(residual)} posible(s) secreto(s)/PII sin enmascarar.")
    h = _hash(stage, model, system, user, schema)
    t0 = time.time()
    source = "provider"
    tin = tout = 0
    result: Any
    if PROVIDER is not None:
        result = PROVIDER(stage, system, user, schema)
    else:
        cass = cassette_dir() / f"{h}.json"
        m = mode()
        if m == "local":
            from . import local_engine
            from .cobol import UnsupportedConstruct
            source = "local"
            try:
                result = local_engine.provider(stage, system, user, schema)
            except UnsupportedConstruct as exc:
                raise LLMError(f"Motor local (sin IA): {exc} — Para otros lenguajes o construcciones se requiere la API de Claude.") from exc
            if schema is not None:
                from . import schemas as _s
                errs = _s.validate(result, schema)
                if errs:
                    raise LLMError("Motor local: salida inválida " + "; ".join(errs[:2]))
        elif m == "claude-code":
            source = "claude-code"
            result, tin, tout = _claude_code(stage, model, effort, system, user, schema)
            if schema is not None:
                from . import schemas as _s
                errs = _s.validate(result, schema)
                if errs:
                    raise LLMError("Claude Code: salida inválida " + "; ".join(errs[:2]))
            cassette_dir().mkdir(parents=True, exist_ok=True)  # graba para el modo contingencia (replay)
            if not cass.exists():  # nunca se pisa una grabación: una corrida nueva (otra respuesta) rompería el replay de las etapas siguientes
                cass.write_text(json.dumps({"stage": stage, "model": model, "result": result, "tokens_in": tin, "tokens_out": tout}, ensure_ascii=False), encoding="utf-8")
        elif m == "replay":
            if not cass.exists():
                raise LLMError(f"Modo contingencia (replay): no hay respuesta grabada para la etapa '{stage}'. "
                               "Configure ANTHROPIC_API_KEY para modo en vivo.")
            data = json.loads(cass.read_text(encoding="utf-8"))
            result, tin, tout, source = data["result"], data.get("tokens_in", 0), data.get("tokens_out", 0), "replay"
        else:
            source = "live"
            last_err: Exception | None = None
            result = None
            for attempt in range(2):
                text, tin, tout = _live(stage, model, effort, system, user, schema, max_tokens)
                try:
                    result = json.loads(text) if schema is not None else text
                    break
                except json.JSONDecodeError as exc:
                    last_err = exc
            if result is None:
                raise LLMError(f"La salida de '{stage}' no es JSON válido: {last_err}")
            cassette_dir().mkdir(parents=True, exist_ok=True)
            if not cass.exists():  # no se pisan grabaciones (ver claude-code)
                cass.write_text(json.dumps({"stage": stage, "model": model, "result": result,
                                            "tokens_in": tin, "tokens_out": tout}, ensure_ascii=False), encoding="utf-8")
    secs = time.time() - t0
    shown_model = "motor local (sin IA)" if source == "local" else f"{model} (suscripción)" if source == "claude-code" else model
    free = source in ("local", "claude-code", "replay")  # claude-code: incluido en la suscripción; replay: no hay gasto en esta ejecución
    db.log_llm(project_id, stage, shown_model, h[:16], tin, tout, 0.0 if free else _cost(model, tin, tout), secs, source)
    return result
