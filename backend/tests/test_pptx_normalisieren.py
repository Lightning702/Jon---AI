from __future__ import annotations

from app.services.pptx_normalisieren import folien


def test_powerpoint_layoutnamen_und_objekte_werden_verstanden():
    ergebnis = folien([
        {"layout": "title_only", "title": "AKW – Radioaktivität", "objects": [
            {"type": "textbox", "text": "Von Anna B.  Ben C.  Clara D."},
            {"type": "image", "bild_suche": "radiation warning symbol"},
        ]},
        {"layout": "title_and_content", "title": "Woher?", "bullets": ["Kernspaltung", "Neutronen"]},
        {"layout": "two_column", "title": "Vergleich", "left_title": "A", "left_bullets": ["x"], "right_title": "B", "right_bullets": ["y"]},
        {"layout": "section_header", "title": "Teil 2"},
        {"layout": "schema", "title": "Ablauf", "steps": ["Neutron: trifft Kern", "Spaltung: zwei Kerne"]},
    ])
    assert [f["layout"] for f in ergebnis] == ["title", "bullets", "two_columns", "closing", "timeline"]
    assert ergebnis[0]["bild_suche"] == "radiation warning symbol"
    assert "Anna B." in ergebnis[0]["subtitle"]
    assert [s["titel"] for s in ergebnis[2]["items"]] == ["A", "B"]
    assert ergebnis[4]["items"][0] == {"titel": "Neutron", "text": "trifft Kern"}


def test_hintergrundbild_und_quellzeilen():
    ergebnis = folien([
        {"layout": "title", "title": "T", "background": {"bild_suche": "nuclear plant"}},
        {"layout": "bullets", "title": "Fakten", "bullets": ["Punkt eins", "Punkt zwei", "Quelle: BASE 2024"]},
    ])
    assert ergebnis[0]["bild_suche"] == "nuclear plant"
    assert ergebnis[1]["bullets"] == ["Punkt eins", "Punkt zwei"]
    assert ergebnis[1]["quelle"] == "BASE 2024"


def test_unterpunkte_werden_zu_spalten_statt_zerstueckelt():
    punkte = []
    for art in ("Alpha", "Beta", "Gamma", "Neutronen"):
        punkte += [f"{art}:", "  – Entstehung: x", "  – Reichweite: y", "  – Abschirmung: z", ""]
    ergebnis = folien([{"layout": "bullets", "title": "Strahlungsarten", "bullets": punkte}])
    assert [f["layout"] for f in ergebnis] == ["two_columns", "two_columns"]
    assert [s["titel"] for s in ergebnis[0]["items"]] == ["Alpha", "Beta"]
    assert ergebnis[1]["items"][1]["bullets"] == ["Entstehung: x", "Reichweite: y", "Abschirmung: z"]


def test_volle_folien_werden_gleichmaessig_geteilt_und_nie_leer():
    ergebnis = folien([
        {"layout": "bullets", "title": "Viel", "bullets": [f"Punkt {i} mit etwas Text" for i in range(10)]},
        {"layout": "diagram", "title": "Leer", "beschreibung": "Beschreibung als Inhalt"},
    ])
    assert [len(f["bullets"]) for f in ergebnis[:2]] == [5, 5]
    assert ergebnis[0]["title"] == "Viel (1/2)"
    assert ergebnis[2]["bullets"] == ["Beschreibung als Inhalt"]


def test_quellenfolien_bleiben_listen():
    ergebnis = folien([{"layout": "bullets", "title": "Quellen", "bullets": ["BASE:", "  – https://www.base.bund.de", "BfS:", "  – https://www.bfs.de"]}])
    assert ergebnis[0]["layout"] == "bullets"
    assert "– https://www.bfs.de" in ergebnis[0]["bullets"]


def test_tabelle_aus_kopf_und_verrutschten_zeilen():
    ergebnis = folien([{"layout": "table", "title": "Vergleich", "headers": ["Eigenschaft", "Alpha", "Beta"], "rows": [["Ladung", "+2", "-1", "Masse", "4 u", "klein"]]}])
    assert ergebnis[0]["layout"] == "table"
    assert ergebnis[0]["tabelle"] == [["Eigenschaft", "Alpha", "Beta"], ["Ladung", "+2", "-1"], ["Masse", "4 u", "klein"]]


def test_emojis_und_abschnittsfolien_mit_inhalt():
    ergebnis = folien([{"layout": "section_header", "title": "Abgleich ✅", "bullets": ["✅ Folie 1: ok", "✅ Folie 2: ok"]}])
    assert ergebnis[0]["layout"] == "bullets"
    assert ergebnis[0]["title"] == "Abgleich"
    assert ergebnis[0]["bullets"] == ["Folie 1: ok", "Folie 2: ok"]


def test_titel_aus_textfeld_mit_zeilenumbruch_und_praesentationstitel():
    ergebnis = folien([{"layout": "blank", "objects": [{"type": "textbox", "text": "AKW\nRadioaktivität"}, {"type": "textbox", "text": "Von Anna B."}]}], "AKW – Radioaktivität")
    assert ergebnis[0]["layout"] == "title"
    assert ergebnis[0]["title"] == "AKW – Radioaktivität"
    assert ergebnis[0]["subtitle"] == "Von Anna B."


def test_bildname_aus_kaputter_url_und_relevanz():
    from app.services.bildquelle import ersatzadressen, name_aus_url, passt

    url = "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Ionizing_radiation_symbol.svg/1024px-Ionizing_radiation_symbol.svg.png"
    assert name_aus_url(url) == "Ionizing radiation symbol"
    assert any("/960px-" in a for a in ersatzadressen(url))
    assert passt("Alfa beta gamma radiation penetration.svg", "alpha beta gamma radiation penetration")
    assert not passt("L1 plasma station magnetosheath.png", "radiation shielding gamma neutron")
