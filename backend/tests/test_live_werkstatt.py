import json

from app.services.werkstatt import ergebnis, sprache, vorschau
from app.services.chat_service import werkstatt_anhaengen, werkstatt_fertig


def test_folien_vorschau_normalisiert_und_kopiert():
    folien = [
        {"titel": "TON 618", "untertitel": "Quasar"},
        {"title": "Fakten", "bullets": ["66 Mrd. Sonnenmassen", "  10 Mrd. Lichtjahre"], "bild_suche": "quasar"},
        {"layout": "two_columns", "title": "Vergleich", "items": [{"titel": "A", "bullets": ["eins"]}, {"titel": "B", "bullets": ["zwei"]}]},
    ]
    roh = json.dumps(folien)
    daten = vorschau("create_pptx", {"title": "TON 618", "theme": "ocean", "slides": folien})
    assert json.dumps(folien) == roh
    assert daten["art"] == "folien"
    assert daten["farben"]["primary"] == "#065A82"
    assert daten["folien"][0]["layout"] == "title"
    assert daten["folien"][1]["punkte"][0] == "66 Mrd. Sonnenmassen:"
    assert daten["folien"][1]["punkte"][1].startswith("  ")
    assert daten["folien"][1]["bild"] == "quasar"
    assert daten["folien"][2]["items"][1]["titel"] == "B"


def test_folien_als_text_und_unbekanntes_theme():
    daten = vorschau("create_pptx", {"title": "X", "theme": "gibtsnicht", "slides": json.dumps([{"title": "Eins"}])})
    assert daten["folien"][0]["titel"] == "Eins"
    assert daten["farben"]["primary"] == "#1E2761"


def test_pptx_und_docx_aenderungen():
    p = vorschau("edit_pptx", {"path": "C:/a.pptx", "aktionen": [{"aktion": "ersetzen", "suchen": "alt", "ersetzen": "neu"}, {"aktion": "text", "folie": "2", "element": 1, "text": "Hallo"}, {"aktion": "folie_neu", "nach": 3, "title": "Neu", "bullets": ["x"]}]})
    assert p["art"] == "folien_aenderung"
    assert p["aktionen"][0] == {"art": "ersetzen", "titel": "Suchen und ersetzen", "alt": "alt", "neu": "neu"}
    assert p["aktionen"][1]["folie"] == 2 and p["aktionen"][1]["text"] == "Hallo"
    assert p["aktionen"][2]["folie_inhalt"]["titel"] == "Neu"
    d = vorschau("edit_docx", {"path": "b.docx", "aktionen": json.dumps([{"aktion": "einfuegen", "nach": 2, "text": "Absatz", "stil": "h2"}, {"aktion": "tabelle", "nach": 1, "zeilen": [["a", "b"], ["1", "2"]]}])})
    assert d["art"] == "dokument_aenderung"
    assert d["aktionen"][0]["stil"] == "h2"
    assert d["aktionen"][1]["tabelle"] == [["a", "b"], ["1", "2"]]


def test_dokument_tabelle_und_code_aus_datei_erstellen():
    dok = vorschau("datei_erstellen", {"art": "docx", "titel": "Brief", "inhalt": "# Brief\n## Teil\n- Punkt\n1. Erstens\n\n\nText"})
    assert dok["art"] == "dokument" and dok["pfad"] == "Brief.docx"
    assert [b["typ"] for b in dok["bloecke"]] == ["h2", "punkt", "nummer", "leer", "absatz"]
    tab = vorschau("datei_erstellen", {"art": "xlsx", "titel": "Liste", "inhalt": [["A", "B"], ["1", "2"]]})
    assert tab["art"] == "tabelle" and tab["zeilen"][1] == ["1", "2"]
    code = vorschau("datei_erstellen", {"art": "py", "dateiname": "x.py", "inhalt": "print(1)"})
    assert code == {"art": "code", "pfad": "x.py", "sprache": "python", "inhalt": "print(1)"}


def test_code_diff_terminal_und_harness_namen():
    assert vorschau("write_file", {"path": "a/b.tsx", "content": "x"})["sprache"] == "tsx"
    assert vorschau("append_file", {"path": "log.txt", "content": "y"})["anhaengen"] is True
    assert vorschau("create", {"path": "c.rs", "content": ""})["art"] == "code"
    assert vorschau("edit", {"path": "d.py", "old": "a", "new": "b"})["art"] == "diff"
    assert vorschau("run_cmd", {"command": "dir"})["shell"] == "cmd"
    assert vorschau("verify", {"command": "pytest"})["pruefung"] is True
    assert vorschau("run_powershell", {"command": "  "}) is None
    assert vorschau("web_search", {"query": "x"}) is None
    assert sprache("Main.KT") == "kotlin"


def test_lange_inhalte_werden_gekuerzt():
    daten = vorschau("write_file", {"path": "gross.txt", "content": "x" * 50000})
    assert len(daten["inhalt"]) < 25000


def test_ergebnisse():
    assert ergebnis("create_pptx", json.dumps({"path": "C:/x.pptx", "slides": 4})) == {"ok": True, "pfad": "C:/x.pptx", "office": True, "folien": 4}
    assert ergebnis("datei_erstellen", {"ok": True, "datei": {"path": "C:/b.md"}}) == {"ok": True, "pfad": "C:/b.md", "office": False}
    assert ergebnis("edit_pptx", json.dumps({"error": "kaputt"})) == {"ok": False, "fehler": "kaputt"}
    t = ergebnis("run_powershell", json.dumps({"exit_code": 1, "stdout": "a", "stderr": "b"}))
    assert t == {"ok": False, "exit_code": 1, "ausgabe": "a", "fehler": "b"}
    h = ergebnis("verify", {"ok": True, "exit_code": 0, "output": "fertig"})
    assert h["ok"] and h["ausgabe"] == "fertig"
    assert ergebnis("edit", {"path": "a.py", "diff": "+x"})["diff"] == "+x"
    assert ergebnis("web_search", "{}") is None
    assert ergebnis("write_file", "kein json")["ok"] is True


def test_chat_ereignisse_bekommen_werkstatt():
    laufend = {"type": "tool"}
    werkstatt_anhaengen("edit_file", {"path": "a.py", "old": "1", "new": "2"}, laufend)
    assert laufend["werkstatt"]["art"] == "diff"
    fertig = {"type": "tool"}
    werkstatt_fertig("run_cmd", json.dumps({"exit_code": 0, "stdout": "ok", "stderr": ""}), fertig)
    assert fertig["werkstatt_ergebnis"]["ausgabe"] == "ok"
    leer = {}
    werkstatt_anhaengen("web_search", {"query": "x"}, leer)
    werkstatt_fertig("web_search", "{}", leer)
    assert leer == {}
