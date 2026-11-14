import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from copilot import db, llm, security
    from copilot import delivery
    monkeypatch.setattr(delivery, "PACKAGES", tmp_path / "pkg")
    db.init(tmp_path / "t.db")
    security._hits.clear()
    llm.PROVIDER = None
    from copilot.main import app
    with TestClient(app) as c:
        yield c
    llm.PROVIDER = None


@pytest.fixture()
def fake(monkeypatch):
    from copilot import llm
    import fake_llm
    llm.PROVIDER = fake_llm.provider
    yield
    llm.PROVIDER = None


def wait_stage(client, pid, stage, timeout=120):
    t = time.time()
    while time.time() - t < timeout:
        p = client.get(f"/api/projects/{pid}").json()
        st = p["stages"][stage]["status"]
        if st not in ("pending", "running"):
            return p
        if any(s["status"] == "failed" for s in p["stages"].values()):
            raise AssertionError({k: v.get("error") for k, v in p["stages"].items() if v["status"] == "failed"})
        time.sleep(0.3)
    raise TimeoutError(stage)
