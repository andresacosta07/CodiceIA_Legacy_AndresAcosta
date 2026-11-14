"""Estándares de interfaz moderna: contraste WCAG AA, favicon, accesibilidad básica, guía para no técnicos y ausencia de sumideros XSS."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


def _tokens(block: str) -> dict[str, str]:
    out = {}
    for name, val in re.findall(r"--([a-z0-9]+):(#[0-9a-fA-F]{3,6})\b", block):
        out[name] = "#" + "".join(c * 2 for c in val[1:]) if len(val) == 4 else val   # #fff → #ffffff
    return out


def _palettes():
    css = (WEB / "style.css").read_text(encoding="utf-8")
    light = _tokens(re.search(r":root\{([^}]*)\}", css).group(1))
    dark = _tokens(re.search(r':root\[data-theme="dark"\]\{([^}]*)\}', css).group(1))
    auto = _tokens(re.search(r'prefers-color-scheme:dark\)\{:root:not\(\[data-theme="light"\]\)\{([^}]*)\}', css).group(1))
    assert auto == dark, "el modo oscuro automático y el manual deben tener la misma paleta"
    return light, dark


def _lum(h: str) -> float:
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _cr(a: str, b: str) -> float:
    hi, lo = sorted([_lum(a), _lum(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_text_and_button_contrast_meets_wcag_aa_in_light_and_dark():
    light, dark = _palettes()
    for name, pal in (("claro", light), ("oscuro", dark)):
        pairs = [("ink", "bg"), ("ink", "card"), ("mute", "card"), ("mute", "bg"), ("mute", "line"), ("ok", "okbg"), ("warn", "warnbg"), ("bad", "badbg")]
        for a, b in pairs:
            assert _cr(pal[a], pal[b]) >= 4.5, f"{name}: {a} sobre {b} = {_cr(pal[a], pal[b]):.2f}"
        for btn in ("btn", "okbtn", "badbtn"):          # texto blanco de los botones
            assert _cr("#ffffff", pal[btn]) >= 4.5, f"{name}: blanco sobre {btn} = {_cr('#ffffff', pal[btn]):.2f}"


def test_favicon_and_head_metadata():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert '<html lang="es">' in html and 'name="viewport"' in html and 'name="theme-color"' in html
    assert 'rel="icon"' in html and "/favicon.svg" in html
    svg = (WEB / "favicon.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg") and "viewBox" in svg


def test_favicon_is_served_and_pages_have_security_headers(client):
    r = client.get("/favicon.svg")
    assert r.status_code == 200 and "svg" in r.headers["content-type"]
    assert client.get("/guide.js").status_code == 200 and client.get("/").status_code == 200
    assert "default-src 'self'" in client.get("/").headers["content-security-policy"]


def test_accessibility_basics_present():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "style.css").read_text(encoding="utf-8")
    assert 'class="skip"' in html and 'aria-live' in html and 'aria-label="Pasos del proceso"' in html
    assert ":focus-visible" in css and "prefers-reduced-motion" in css and "prefers-color-scheme:dark" in css
    assert "@media (max-width:720px)" in css                      # adaptable a móvil
    assert re.search(r"body\{[^}]*font:16px", css)                # tamaño base legible (16 px)
    assert "min-height:42px" in css                               # objetivos táctiles de tamaño adecuado


def test_guided_experience_for_non_technical_users():
    guide = (WEB / "guide.js").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    for tour in ("home:", "ingest:", "analyze:", "rules:", "code:", "verify:", "package:"):
        assert tour in guide, f"falta el recorrido guiado de {tour}"
    assert len(re.findall(r"^\s{2}\w+: \['", guide, re.M)) >= 15       # glosario en lenguaje simple (≥ 15 términos)
    for needle in ("navBar", "Siguiente:", "infoBtn", "startTour", "Probar con un ejemplo", "Recorrido de esta pantalla", "aria-current"):
        assert needle in guide + app, needle
    assert 'id="btn-guide"' in (WEB / "index.html").read_text(encoding="utf-8")


def test_no_dangerous_sinks_in_any_script():
    for f in ("app.js", "guide.js"):
        js = (WEB / f).read_text(encoding="utf-8")
        for bad in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
            assert bad not in js, f"{f}: {bad}"
