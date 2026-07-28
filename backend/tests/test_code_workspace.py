from __future__ import annotations

import pytest

from app.services.coding import (
    active_file_context,
    mentioned_files_context,
    workspace_summary,
)
from app.services.tools import CODING_TOOLS, ToolBox


@pytest.fixture()
def projekt(tmp_path):
    (tmp_path / "index.html").write_text("<h1>Hallo</h1>", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.js").write_text("const a = 1;", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "geheim.js").write_text("x", encoding="utf-8")
    return tmp_path


def test_workspace_summary_zeigt_unterordner_ohne_muell(projekt):
    text = workspace_summary(projekt)
    assert "index.html" in text
    assert "app.js" in text
    assert "geheim.js" not in text


def test_aktive_datei_kommt_mit_inhalt_in_den_prompt(projekt):
    text = active_file_context(str(projekt), str(projekt / "index.html"))
    assert "index.html" in text
    assert "<h1>Hallo</h1>" in text


def test_aktive_datei_ausserhalb_wird_ignoriert(projekt, tmp_path_factory):
    fremd = tmp_path_factory.mktemp("fremd") / "geheim.txt"
    fremd.write_text("privat", encoding="utf-8")
    assert active_file_context(str(projekt), str(fremd)) == ""


def test_genannte_datei_wird_aufgeloest(projekt):
    text = mentioned_files_context(projekt, "schreib mir in index.html eine Navigation")
    assert str(projekt / "index.html") in text
    assert "<h1>Hallo</h1>" in text


def test_genannte_datei_im_unterordner(projekt):
    text = mentioned_files_context(projekt, "pack die Funktion in app.js")
    assert str(projekt / "src" / "app.js") in text


def test_ohne_dateiname_kein_block(projekt):
    assert mentioned_files_context(projekt, "mach das schoener") == ""


def test_coding_schema_nur_projekt_werkzeuge():
    tools = ToolBox().schema("licht an und musik", coding=True)
    namen = {t["function"]["name"] for t in tools}
    assert namen == CODING_TOOLS
    assert "smarthome_control" not in namen
    assert "send_mail" not in namen


def test_shell_darf_den_ordner_nicht_verlassen(projekt):
    box = ToolBox(root=str(projekt))
    box._guard_command("cd src && npm test")
    box._guard_command("npm run build")
    for befehl in ["cd .. && dir", "pushd ../..", "Set-Location -Path C:\\Windows"]:
        with pytest.raises(PermissionError):
            box._guard_command(befehl)


def test_dateizugriff_ausserhalb_blockiert(projekt, tmp_path_factory):
    box = ToolBox(root=str(projekt))
    fremd = tmp_path_factory.mktemp("fremd") / "notiz.txt"
    fremd.write_text("privat", encoding="utf-8")
    ergebnis = box._execute("read_file", {"path": str(fremd)})
    assert "blockiert" in ergebnis
