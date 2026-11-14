"""Servidor de DESARROLLO con el proveedor LLM simulado (solo para ver la UI sin gastar API). No usar en la demo."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
import uvicorn  # noqa: E402

from copilot import db, llm  # noqa: E402
import fake_llm  # noqa: E402

db.init(Path(tempfile.mkdtemp()) / "dev.db")
llm.PROVIDER = fake_llm.provider
from copilot.main import app  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
