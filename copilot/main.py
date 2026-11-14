"""API FastAPI del Copiloto. Seguridad: validación estricta, cabeceras, rate limit, errores sin detalles internos."""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db, delivery, llm, pipeline, repo_import, security

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "golden"
MAX_BODY = 25 * 1024 * 1024

app = FastAPI(title="Copiloto de Modernización y Descubrimiento de Código Legacy", docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def guard(request: Request, call_next):
    host = request.client.host if request.client else "?"
    if security.rate_limited(host):
        return JSONResponse({"error": "Demasiadas solicitudes. Espere un momento e intente de nuevo."}, status_code=429)
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > MAX_BODY:
        return JSONResponse({"error": "La solicitud excede el tamaño máximo permitido (25 MB)."}, status_code=413)
    try:
        response = await call_next(request)
    except Exception:  # noqa: BLE001 - nunca exponer trazas
        return JSONResponse({"error": "Error interno. Reintente; si persiste, revise el registro del servidor."}, status_code=500,
                            headers=security.SECURITY_HEADERS)
    for k, v in security.SECURITY_HEADERS.items():
        response.headers.setdefault(k, v)
    return response


@app.exception_handler(security.SecurityError)
async def _sec(_: Request, exc: security.SecurityError):
    return JSONResponse({"error": str(exc), "hint": "Corrija la entrada y vuelva a intentarlo."}, status_code=400,
                        headers=security.SECURITY_HEADERS)


@app.exception_handler(KeyError)
async def _nf(_: Request, exc: KeyError):
    return JSONResponse({"error": "Recurso no encontrado."}, status_code=404, headers=security.SECURITY_HEADERS)


def reviewer(request: Request) -> str:
    return re.sub(r"[^A-Za-z0-9_.\- ]", "", request.headers.get("x-reviewer", "reviewer"))[:40] or "reviewer"


def project_view(pid: str) -> dict[str, Any]:
    p = pipeline.get(security.valid_id(pid))
    p["llm"] = db.llm_summary(pid)
    p["metrics"] = delivery.metrics(p) if p.get("rules") else {}
    return p


# ------------------------------------------------------------------ estado y muestras
@app.get("/api/status")
def status() -> dict[str, Any]:
    st = llm.status()
    return {**st, "version": "1.0.0"}


class ModeReq(BaseModel):
    mode: str = Field(max_length=20)


@app.post("/api/mode")
def set_mode(req: ModeReq) -> dict[str, Any]:
    """Cambia el proveedor de IA en caliente: local (sin IA) · claude-code (suscripción, sin clave) · live (API) · replay."""
    try:
        llm.set_mode(req.mode)
    except llm.LLMError as exc:
        raise security.SecurityError(str(exc)) from exc
    return llm.status()


def _samples() -> list[dict[str, Any]]:
    out = []
    for m in sorted(GOLDEN.glob("*/manifest.json")):
        out.append(json.loads(m.read_text(encoding="utf-8-sig")))
    return out


@app.get("/api/samples")
def samples() -> list[dict[str, Any]]:
    return _samples()


class SampleReq(BaseModel):
    name: str = Field(max_length=60)
    target: str = "typescript"
    with_cases: bool = False


@app.post("/api/projects/sample")
def create_from_sample(req: SampleReq) -> dict[str, Any]:
    man = next((s for s in _samples() if s["name"] == req.name), None)
    if man is None:
        raise KeyError(req.name)
    d = GOLDEN / man["name"]
    files = [(f, (d / f).read_bytes()) for f in man["files"]]
    cases = None
    if req.with_cases and (d / "cases.json").exists():
        cases = _parse_cases((d / "cases.json").read_bytes())
    p = pipeline.new_project(man["title"], "Créditos / amortización" if "amort" in man["name"] else "Seguros", req.target, "hexagonal", files, cases)
    return {"id": p["id"]}


def _parse_cases(blob: bytes) -> list[dict[str, Any]]:
    try:
        data = json.loads(blob.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise security.SecurityError("El archivo de casos no es JSON válido.") from exc
    if not isinstance(data, list) or len(data) > 500:
        raise security.SecurityError("Los casos aportados deben ser una lista (máx. 500).")
    out = []
    for i, c in enumerate(data):
        if not isinstance(c, dict) or not isinstance(c.get("input"), dict) or not isinstance(c.get("expected"), dict):
            raise security.SecurityError(f"Caso {i + 1} inválido: requiere 'input' y 'expected'.")
        out.append({"name": str(c.get("name", i + 1))[:40], "category": str(c.get("category", "aportado"))[:30],
                    "input": {str(k)[:40]: str(v)[:60] for k, v in c["input"].items()},
                    "expected": {str(k)[:40]: str(v)[:60] for k, v in c["expected"].items()}})
    return out


# ------------------------------------------------------------------ proyectos
@app.post("/api/projects")
async def create_project(files: list[UploadFile] = File(default=[]), code_text: str = Form(""), code_name: str = Form("pegado.cbl"),
                         name: str = Form(""), domain: str = Form(""), target: str = Form("typescript"), style: str = Form("hexagonal"),
                         cases_json: str = Form("")) -> dict[str, Any]:
    collected: list[tuple[str, bytes]] = []
    provided: list[dict[str, Any]] | None = None
    for f in files:
        blob = await f.read(security.MAX_TOTAL_BYTES + 1)
        if len(blob) > security.MAX_TOTAL_BYTES:
            raise security.SecurityError("El archivo excede el tamaño máximo permitido.")
        fname = security.safe_name(f.filename or "")
        if fname.lower().endswith(".zip"):
            collected += security.extract_zip(blob)
        elif re.search(r"cases.*\.json$", fname.lower()):
            provided = _parse_cases(blob)
        else:
            security.check_extension(fname)
            collected.append((fname, blob))
    if code_text.strip():
        if len(code_text) > security.MAX_FILE_BYTES:
            raise security.SecurityError("El código pegado excede el tamaño máximo permitido.")
        pname = security.safe_name(code_name or "pegado.txt")
        security.check_extension(pname)
        collected.append((pname, code_text.encode("utf-8")))
    if cases_json.strip():
        provided = _parse_cases(cases_json.encode("utf-8"))
    p = pipeline.new_project(name, domain, target, style, collected, provided)
    return {"id": p["id"]}


class RepoReq(BaseModel):
    url: str = Field(max_length=300)
    ref: str = Field("", max_length=100)
    subdir: str = Field("", max_length=200)
    name: str = Field("", max_length=80)
    domain: str = Field("", max_length=120)
    target: str = "typescript"
    style: str = "hexagonal"


@app.post("/api/projects/repo")
def create_from_repo(req: RepoReq) -> dict[str, Any]:
    """Importa el código de un repositorio Git público (solo lectura, sin clonar; ADR-017)."""
    src = repo_import.fetch(req.url, req.ref, req.subdir)
    p = pipeline.new_project(req.name or src.repo, req.domain, req.target, req.style, src.files, None)
    db.audit(p["id"], "system", "ingest:repo", src.summary())
    return {"id": p["id"], "source": src.summary()}


def _project_summary(p: dict[str, Any]) -> dict[str, Any]:
    """Estado legible de un proyecto para agruparlo en la lista: actual, en cola, finalizado o con error."""
    st = {k: v.get("status") for k, v in p.get("stages", {}).items()}
    rules = p.get("rules") or []
    decided = sum(1 for r in rules if r.get("status") != "proposed")
    if any(s == "failed" for s in st.values()):
        group, label = "error", "Con error"
    elif any(s == "running" for s in st.values()):
        group, label = "actual", "Procesando…"
    elif st.get("package") == "done":
        group, label = "finalizado", "Finalizado"
    elif st.get("review") == "done":
        group, label = "actual", "Generando entrega"
    elif st.get("rules") in ("done", "gate_failed"):
        group, label = "actual", f"Esperando su decisión · {decided}/{len(rules)} reglas"
    elif st.get("analyze") == "pending":
        group, label = "cola", "En cola · sin iniciar"
    else:
        group, label = "actual", "En análisis"
    return {"group": group, "label": label, "target": p.get("target"), "language": (p.get("ingest_report") or {}).get("languages", [])}


@app.get("/api/projects")
def list_projects() -> list[dict[str, Any]]:
    out = []
    for item in db.list_projects():
        p = db.load_project(item["id"])
        out.append({**item, **(_project_summary(p) if p else {"group": "cola", "label": ""})})
    return out


@app.get("/api/projects/{pid}")
def get_project(pid: str) -> dict[str, Any]:
    return project_view(pid)


@app.delete("/api/projects/{pid}")
def delete_project(pid: str) -> dict[str, Any]:
    security.valid_id(pid)
    zpath = delivery.PACKAGES / f"{pid}.zip"
    if zpath.exists():
        zpath.unlink()
    try:  # purga también el fuente guardado en la caché del motor local
        from . import local_engine
        p = db.load_project(pid)
        if p and p.get("analysis"):
            (local_engine.CACHE / f"{local_engine._key(p['analysis']['io_contract'])}.json").unlink(missing_ok=True)
    except (OSError, KeyError):
        pass
    return {"deleted": db.delete_project(pid)}


def _start_chain(pid: str) -> None:
    def chain() -> None:
        pipeline.run_stage(pid, "analyze", pipeline.analyze_stage)
        if pipeline.get(pid)["stages"]["analyze"]["status"] in ("done", "gate_failed"):
            pipeline.run_stage(pid, "rules", pipeline.rules_stage)
    threading.Thread(target=chain, daemon=True).start()


@app.post("/api/projects/{pid}/start")
def start(pid: str) -> dict[str, Any]:
    p = pipeline.get(security.valid_id(pid))
    if not p["stages"]["ingest"]["gate"]["passed"]:
        raise security.SecurityError("La ingesta no superó la compuerta de secretos; revise el informe de enmascarado.")
    if any(p["stages"][s]["status"] == "running" for s in ("analyze", "rules")):
        return {"started": False}
    _start_chain(pid)
    return {"started": True}


class ReviewReq(BaseModel):
    status: str
    edits: dict[str, Any] | None = None
    comment: str = Field(default="", max_length=500)


@app.post("/api/projects/{pid}/rules/{rid}/review")
def review(pid: str, rid: str, req: ReviewReq, request: Request) -> dict[str, Any]:
    security.valid_id(pid)
    if not re.match(r"^R-\d{3,}$", rid):
        raise security.SecurityError("Identificador de regla inválido.")
    return pipeline.review_rule(pid, rid, req.status, req.edits, req.comment, reviewer(request))


@app.post("/api/projects/{pid}/rules/approve-verified")
def approve_verified(pid: str, request: Request) -> dict[str, Any]:
    p = pipeline.get(security.valid_id(pid))
    n = 0
    for r in p["rules"]:
        if r["status"] == "proposed" and r["trace_status"] in ("verified", "corrected"):
            pipeline.review_rule(pid, r["id"], "approved", None, "Aprobada en lote tras revisión (trazabilidad verificada)", reviewer(request))
            n += 1
    return {"approved": n}


@app.post("/api/projects/{pid}/approve")
def approve(pid: str, request: Request) -> dict[str, Any]:
    return pipeline.approve_catalog(security.valid_id(pid), reviewer(request))


@app.post("/api/projects/{pid}/continue")
def continue_delivery(pid: str) -> dict[str, Any]:
    p = pipeline.get(security.valid_id(pid))
    if p["stages"]["review"].get("status") != "done":
        raise security.SecurityError("Primero debe aprobar el catálogo de reglas (validación humana).")
    if any(p["stages"][s]["status"] == "running" for s in ("generate", "verify", "docs", "package")):
        return {"started": False}
    threading.Thread(target=delivery.run_delivery_chain, args=(pid,), daemon=True).start()
    return {"started": True}


@app.get("/api/projects/{pid}/audit")
def audit(pid: str) -> dict[str, Any]:
    security.valid_id(pid)
    return {"chain_ok": db.verify_audit_chain(pid), "events": db.audit_log(pid)}


@app.get("/api/projects/{pid}/download")
def download(pid: str):
    security.valid_id(pid)
    z = delivery.PACKAGES / f"{pid}.zip"
    if not z.exists():
        raise KeyError(pid)
    return FileResponse(z, media_type="application/zip", filename=f"paquete_migracion_{pid[:8]}.zip")


app.mount("/", StaticFiles(directory=str(ROOT / "web"), html=True), name="web")
