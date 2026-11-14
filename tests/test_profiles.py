"""Perfil de modelos rápido (ADR-018): opcional, no altera el estándar y solo usa modelos conocidos."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _stages(profile: str) -> dict:
    env = {"COPILOT_PROFILE": profile, "SystemRoot": "C:\\Windows", "PATH": ""}
    code = "import json; from copilot import llm; print(json.dumps({'p': llm.PROFILE, 's': llm.CONFIG['stages']}))"
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env={**env, "PYTHONPATH": str(ROOT)}, capture_output=True, text=True, timeout=60)
    return json.loads(out.stdout)


def test_fast_profile_overrides_only_listed_stages_and_standard_is_untouched():
    std, fast = _stages(""), _stages("fast")
    base = json.loads((ROOT / "config" / "models.json").read_text(encoding="utf-8"))["stages"]
    over = json.loads((ROOT / "config" / "models.fast.json").read_text(encoding="utf-8"))["stages"]
    assert std["p"] == "standard" and std["s"] == base                       # el perfil estándar no cambia (cassettes y pruebas intactos)
    assert fast["p"] == "fast"
    for stage, cfg in fast["s"].items():
        assert cfg == {**base[stage], **over.get(stage, {})}, stage            # lo no listado se hereda
    pricing = json.loads((ROOT / "config" / "models.json").read_text(encoding="utf-8"))["pricing_usd_per_mtok"]
    assert all(c["model"] in pricing for c in over.values())                 # solo modelos con precio conocido
    assert all(c["effort"] in ("low", "medium", "high", "xhigh", "max") for c in over.values())
    assert set(over) <= set(base)                                            # no inventa etapas
