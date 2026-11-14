"""Persistencia SQLite. TODAS las consultas son parametrizadas (nunca se concatena entrada)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "copilot.db"
_lock = threading.RLock()
_conn: sqlite3.Connection | None = None


def init(path: Path | None = None) -> None:
    global _conn, DB_PATH
    with _lock:
        if _conn is not None:
            _conn.close()
        DB_PATH = path or DB_PATH
        if str(DB_PATH) != ":memory:":
            Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects(
              id TEXT PRIMARY KEY, name TEXT NOT NULL, created REAL NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audit(
              seq INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL, ts REAL NOT NULL,
              actor TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL,
              prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS llm_calls(
              id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, ts REAL NOT NULL, stage TEXT NOT NULL,
              model TEXT NOT NULL, prompt_hash TEXT NOT NULL, tokens_in INTEGER, tokens_out INTEGER,
              cost_usd REAL, seconds REAL, source TEXT);
            """
        )
        _conn.commit()


def _c() -> sqlite3.Connection:
    if _conn is None:
        init()
    assert _conn is not None
    return _conn


def save_project(pid: str, name: str, data: dict[str, Any]) -> None:
    with _lock:
        _c().execute(
            "INSERT INTO projects(id,name,created,data) VALUES(?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET name=excluded.name, data=excluded.data",
            (pid, name, data.get("created", time.time()), json.dumps(data, ensure_ascii=False)),
        )
        _c().commit()


def load_project(pid: str) -> dict[str, Any] | None:
    with _lock:
        row = _c().execute("SELECT data FROM projects WHERE id = ?", (pid,)).fetchone()
    return json.loads(row[0]) if row else None


def list_projects() -> list[dict[str, Any]]:
    with _lock:
        rows = _c().execute("SELECT id,name,created FROM projects ORDER BY created DESC").fetchall()
    return [{"id": r[0], "name": r[1], "created": r[2]} for r in rows]


def delete_project(pid: str) -> bool:
    """Purga el proyecto, su auditoría y sus llamadas LLM."""
    with _lock:
        cur = _c().execute("DELETE FROM projects WHERE id = ?", (pid,))
        _c().execute("DELETE FROM llm_calls WHERE project_id = ?", (pid,))
        _c().execute("DELETE FROM audit WHERE project_id = ?", (pid,))
        _c().commit()
        return cur.rowcount > 0


# ---------------- auditoría con cadena de hashes ----------------
def audit(pid: str, actor: str, action: str, detail: dict[str, Any] | None = None) -> None:
    detail_s = json.dumps(detail or {}, ensure_ascii=False, sort_keys=True)
    with _lock:
        row = _c().execute("SELECT hash FROM audit WHERE project_id = ? ORDER BY seq DESC LIMIT 1", (pid,)).fetchone()
        prev = row[0] if row else "GENESIS"
        ts = time.time()
        h = hashlib.sha256(f"{prev}|{pid}|{ts}|{actor}|{action}|{detail_s}".encode()).hexdigest()
        _c().execute(
            "INSERT INTO audit(project_id,ts,actor,action,detail,prev_hash,hash) VALUES(?,?,?,?,?,?,?)",
            (pid, ts, actor, action, detail_s, prev, h),
        )
        _c().commit()


def audit_log(pid: str) -> list[dict[str, Any]]:
    with _lock:
        rows = _c().execute(
            "SELECT seq,ts,actor,action,detail,prev_hash,hash FROM audit WHERE project_id = ? ORDER BY seq", (pid,)
        ).fetchall()
    return [dict(seq=r[0], ts=r[1], actor=r[2], action=r[3], detail=json.loads(r[4]), prev_hash=r[5], hash=r[6]) for r in rows]


def verify_audit_chain(pid: str) -> bool:
    prev = "GENESIS"
    for e in audit_log(pid):
        detail_s = json.dumps(e["detail"], ensure_ascii=False, sort_keys=True)
        h = hashlib.sha256(f"{prev}|{pid}|{e['ts']}|{e['actor']}|{e['action']}|{detail_s}".encode()).hexdigest()
        if e["prev_hash"] != prev or e["hash"] != h:
            return False
        prev = e["hash"]
    return True


def tamper_audit_for_test(seq: int) -> None:  # solo pruebas
    with _lock:
        _c().execute("UPDATE audit SET detail = ? WHERE seq = ?", ('{"tampered": true}', seq))
        _c().commit()


def log_llm(pid: str | None, stage: str, model: str, prompt_hash: str, tin: int, tout: int,
            cost: float, seconds: float, source: str) -> None:
    with _lock:
        _c().execute(
            "INSERT INTO llm_calls(project_id,ts,stage,model,prompt_hash,tokens_in,tokens_out,cost_usd,seconds,source) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)", (pid, time.time(), stage, model, prompt_hash, tin, tout, cost, seconds, source))
        _c().commit()


def llm_summary(pid: str) -> dict[str, Any]:
    with _lock:
        rows = _c().execute(
            "SELECT stage,model,SUM(tokens_in),SUM(tokens_out),SUM(cost_usd),SUM(seconds),COUNT(*),MAX(source) "
            "FROM llm_calls WHERE project_id = ? GROUP BY stage,model", (pid,)).fetchall()
    stages = [dict(stage=r[0], model=r[1], tokens_in=r[2] or 0, tokens_out=r[3] or 0, cost_usd=round(r[4] or 0, 4),
                   seconds=round(r[5] or 0, 1), calls=r[6], source=r[7]) for r in rows]
    return {"stages": stages,
            "tokens_in": sum(s["tokens_in"] for s in stages), "tokens_out": sum(s["tokens_out"] for s in stages),
            "cost_usd": round(sum(s["cost_usd"] for s in stages), 4), "calls": sum(s["calls"] for s in stages)}
