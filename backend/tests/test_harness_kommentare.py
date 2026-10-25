from __future__ import annotations

import shutil
import subprocess

import pytest

from app.services.harness import kommentare


def _teilfolge(kurz: str, lang: str) -> bool:
    rest = iter(lang)
    return all(zeichen in rest for zeichen in kurz)


def test_wunsch_wird_erkannt():
    assert kommentare.gewuenscht("code mir ALLES OHNE KOMMENTAREN")
    assert kommentare.gewuenscht("Bitte ohne Kommentare")
    assert kommentare.gewuenscht("keine Kommentare im Code")
    assert not kommentare.gewuenscht("Schreib Kommentare an jede Funktion")


JS = """const url = "https://getjon.info/a//b";
// ganze Zeile weg
const muster = /\\/\\/[a-z]+/g;
const teil = a / b / c;
const vorlage = `wert ${x / 2} und // bleibt ${"/* auch */"}`;
/* Block
   ueber Zeilen */
function f() { return /=+\\//.test(s); }
let n = 4; // am Ende weg
const s = '/* kein Kommentar */';
"""


def test_javascript_ohne_kommentare_bleibt_gueltig():
    sauber = kommentare.js(JS)
    assert "ganze Zeile" not in sauber and "Block" not in sauber and "am Ende" not in sauber
    for bleibt in ('"https://getjon.info/a//b"', "/\\/\\/[a-z]+/g", "a / b / c", "// bleibt", '"/* auch */"', "/=+\\//", "'/* kein Kommentar */'", "let n = 4;\n"):
        assert bleibt in sauber, bleibt
    assert _teilfolge(sauber.replace(" ", "").replace("\n", ""), JS.replace(" ", "").replace("\n", ""))
    assert "\n\n" not in sauber
    node = shutil.which("node")
    if node is None:
        pytest.skip("node fehlt")
    pruefung = subprocess.run([node, "--check", "-"], input="let a = 8, b = 2, c = 1, x = 2;\n" + sauber, capture_output=True, text=True, encoding="utf-8")
    assert pruefung.returncode == 0, pruefung.stderr


def test_html_mit_style_und_script():
    seite = """<!DOCTYPE html>
<html>
<head>
<!-- Kopf -->
<style>
  /* Navigation */
  .a { color: red; }
  .b::after { content: "/* bleibt */"; }
</style>
</head>
<body>
  <!-- Abschnitt -->
  <a href="https://x.de//y">Link</a>
  <script>
    // Start
    const t = 1; /* kurz */ const u = 2;
  </script>
  <script type="application/ld+json">{"a": "// bleibt"}</script>
</body>
</html>
"""
    sauber = kommentare.entfernen("index.html", seite)
    for weg in ("Kopf", "Navigation", "Abschnitt", "Start", "kurz"):
        assert weg not in sauber, weg
    for bleibt in ('content: "/* bleibt */"', 'href="https://x.de//y"', 'const t = 1;', 'const u = 2;', '{"a": "// bleibt"}', "</html>"):
        assert bleibt in sauber, bleibt
    assert _teilfolge(sauber.replace(" ", "").replace("\n", ""), seite.replace(" ", "").replace("\n", ""))
    assert kommentare.entfernen("notiz.txt", "# bleibt") == "# bleibt"
