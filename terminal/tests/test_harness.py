from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jon_harness import netz, speicher
from jon_harness.agent import Agent, Sitzung
from jon_harness.anbieter import KATALOG, Jon, Verbindung
from jon_harness.werkzeuge import Werkzeugkasten, ausfuehren, befehl_gefaehrlich, befehl_sicher


@pytest.fixture(autouse=True)
def eigener_ordner(tmp_path, monkeypatch):
    monkeypatch.setenv("JON_HARNESS_DIR", str(tmp_path / "harness"))
    monkeypatch.setenv("JON_HARNESS_OHNE_JON", "1")
    monkeypatch.setenv("JON_HARNESS_OHNE_FREI", "1")
    for name in list(__import__("os").environ):
        if name.endswith("_API_KEY") or (name.startswith("JON_") and name.endswith("_KEY")):
            monkeypatch.delenv(name, raising=False)


def test_schluessel_werden_verschluesselt_gespeichert(tmp_path):
    einstellungen = speicher.Einstellungen()
    einstellungen.schluessel_setzen("nvidia", "nvapi-geheim-123")
    roh = (tmp_path / "harness" / "einstellungen.json").read_text(encoding="utf-8")
    assert "nvapi-geheim-123" not in roh
    assert speicher.Einstellungen().schluessel("nvidia") == "nvapi-geheim-123"
    assert len(einstellungen.get("geraet")) == 20


def test_dateien_lesen_schreiben_bearbeiten(tmp_path):
    kasten = Werkzeugkasten(tmp_path)
    assert ausfuehren(kasten, "datei_schreiben", {"pfad": "app.py", "inhalt": "def a():\n    return 1\n"}).ok
    gelesen = ausfuehren(kasten, "datei_lesen", {"pfad": "app.py"})
    assert "return 1" in gelesen.text and gelesen.text.lstrip().startswith("1")
    bearbeitet = ausfuehren(kasten, "datei_bearbeiten", {"pfad": "app.py", "alt": "return 1", "neu": "return 2"})
    assert bearbeitet.ok and "+1" in bearbeitet.kurz
    assert (tmp_path / "app.py").read_text(encoding="utf-8") == "def a():\n    return 2\n"
    fehlt = ausfuehren(kasten, "datei_bearbeiten", {"pfad": "app.py", "alt": "gibt es nicht", "neu": "x"})
    assert not fehlt.ok
    assert "zurückgesetzt" in kasten.rueckgaengig()
    assert "return 1" in (tmp_path / "app.py").read_text(encoding="utf-8")


def test_bearbeiten_toleriert_einrueckung_und_tabs(tmp_path):
    (tmp_path / "a.py").write_text("if x:\n\tdo()   \n", encoding="utf-8")
    kasten = Werkzeugkasten(tmp_path)
    kasten.datei_lesen("a.py")
    assert ausfuehren(kasten, "datei_bearbeiten", {"pfad": "a.py", "alt": "if x:\n    do()", "neu": "if y:\n    go()"}).ok
    assert (tmp_path / "a.py").read_text(encoding="utf-8").startswith("if y:")


def test_ueberschreiben_nur_nach_lesen(tmp_path):
    (tmp_path / "x.txt").write_text("alt", encoding="utf-8")
    kasten = Werkzeugkasten(tmp_path)
    assert not ausfuehren(kasten, "datei_schreiben", {"pfad": "x.txt", "inhalt": "neu"}).ok
    kasten.datei_lesen("x.txt")
    assert ausfuehren(kasten, "datei_schreiben", {"pfad": "x.txt", "inhalt": "neu"}).ok


def test_suchen_und_finden(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.ts").write_text("const zahl = 42\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.ts").write_text("const zahl = 1\n", encoding="utf-8")
    kasten = Werkzeugkasten(tmp_path)
    gefunden = ausfuehren(kasten, "dateien_finden", {"muster": "**/*.ts"})
    assert "src/main.ts" in gefunden.text and "node_modules" not in gefunden.text
    treffer = ausfuehren(kasten, "text_suchen", {"muster": r"zahl\s*=\s*42"})
    assert "src/main.ts:1" in treffer.text


def test_befehl_ausfuehren(tmp_path):
    kasten = Werkzeugkasten(tmp_path)
    ergebnis = ausfuehren(kasten, "befehl", {"befehl": "echo hallo-jon"})
    assert ergebnis.ok and "hallo-jon" in ergebnis.text


def test_befehle_einstufen():
    assert befehl_sicher("git status")
    assert befehl_sicher("npm run test")
    assert not befehl_sicher("git status; rm -rf /")
    assert befehl_gefaehrlich("rm -rf ~/")
    assert befehl_gefaehrlich("Stop-Computer -Force")
    assert not befehl_gefaehrlich("npm install")


def test_fehlertext_ist_verstaendlich():
    assert "API-Schlüssel" in netz.fehlertext(401, '{"error": {"message": "invalid key"}}')
    assert netz.fehlertext(429, '{"detail": "Kontingent aufgebraucht"}') == "Kontingent aufgebraucht"


class _Antwort:
    def __init__(self, zeilen):
        self._zeilen = zeilen

    def zeilen(self):
        yield from self._zeilen

    def schliessen(self):
        pass


def _sse(*ereignisse):
    return [f"data: {json.dumps(e)}" for e in ereignisse] + ["data: [DONE]"]


def test_agent_fuehrt_werkzeuge_aus_und_antwortet(tmp_path, monkeypatch):
    (tmp_path / "README.md").write_text("Hallo Projekt", encoding="utf-8")
    verbindung = Verbindung(speicher.Einstellungen(), Jon())
    antworten = [
        _sse({"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "a1", "function": {"name": "datei_lesen", "arguments": "{\"pfad\": \"README.md\"}"}}]}}]}),
        _sse({"choices": [{"delta": {"content": "Im README steht Hallo Projekt."}}]}, {"usage": {"prompt_tokens": 10, "completion_tokens": 5}, "choices": []}),
    ]
    gesehen = []

    def strom(kennung, modell, nachrichten, werkzeuge, denken=None, max_tokens=8192, temperatur=0.4):
        gesehen.append([n["role"] for n in nachrichten])
        return _Antwort(antworten.pop(0)), True

    monkeypatch.setattr(verbindung, "strom", strom)
    agent = Agent(verbindung, Werkzeugkasten(tmp_path), Sitzung(tmp_path), "felworks", "x", "vorsichtig")
    antwort = agent.runde("Was steht im README?", still=True)
    assert antwort == "Im README steht Hallo Projekt."
    assert gesehen[1][-1] == "tool"
    assert agent.sitzung.tokens_ein == 10


def test_agent_textmodus_ohne_funktionsaufrufe(tmp_path, monkeypatch):
    (tmp_path / "a.txt").write_text("Inhalt A", encoding="utf-8")
    verbindung = Verbindung(speicher.Einstellungen(), Jon())
    verbindung.ohne_werkzeuge.add("ollama|klein")
    antworten = [
        _sse({"choices": [{"delta": {"content": "Ich schaue nach.\n```werkzeug\n{\"name\": \"datei_lesen\", \"args\": {\"pfad\": \"a.txt\"}}\n```"}}]}),
        _sse({"choices": [{"delta": {"content": "Da steht Inhalt A."}}]}),
    ]

    def strom(kennung, modell, nachrichten, werkzeuge, denken=None, max_tokens=8192, temperatur=0.4):
        assert werkzeuge is None
        assert "WERKZEUGE OHNE FUNKTIONSAUFRUFE" in nachrichten[0]["content"]
        return _Antwort(antworten.pop(0)), False

    monkeypatch.setattr(verbindung, "strom", strom)
    agent = Agent(verbindung, Werkzeugkasten(tmp_path), Sitzung(tmp_path), "ollama", "klein")
    assert agent.runde("Was steht in a.txt?", still=True) == "Da steht Inhalt A."
    assert any("Inhalt A" in str(n.get("content")) for n in agent.sitzung.nachrichten if n["role"] == "user")


def test_abgelehnte_aktion_wird_gemeldet(tmp_path, monkeypatch):
    verbindung = Verbindung(speicher.Einstellungen(), Jon())
    antworten = [
        _sse({"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "b1", "function": {"name": "befehl", "arguments": "{\"befehl\": \"npm install\"}"}}]}}]}),
        _sse({"choices": [{"delta": {"content": "Okay, lasse ich."}}]}),
    ]
    monkeypatch.setattr(verbindung, "strom", lambda *a, **k: (_Antwort(antworten.pop(0)), True))
    monkeypatch.setattr("builtins.input", lambda *a: "n")
    agent = Agent(verbindung, Werkzeugkasten(tmp_path), Sitzung(tmp_path), "felworks", "x", "vorsichtig")
    assert agent.runde("installier", still=True) == "Okay, lasse ich."
    werkzeug = next(n for n in agent.sitzung.nachrichten if n["role"] == "tool")
    assert "abgelehnt" in werkzeug["content"]


def test_strom_faellt_ohne_denkschalter_und_werkzeuge_zurueck(monkeypatch):
    verbindung = Verbindung(speicher.Einstellungen(), Jon())
    monkeypatch.setattr(verbindung.felworks, "token", lambda neu=False: "t")
    monkeypatch.setattr(verbindung.felworks, "erreichbar", lambda: True)
    gesendet = []

    def anfrage(methode, url, daten=None, kopf=None, zeit=60, strom=False, **k):
        gesendet.append(dict(daten))
        if len(gesendet) == 1:
            raise netz.NetzFehler("x", 400, "unknown field chat_template_kwargs")
        if len(gesendet) == 2:
            raise netz.NetzFehler("x", 400, "tools are not supported for this model")
        return "ok"

    monkeypatch.setattr(netz, "anfrage", anfrage)
    antwort, mit = verbindung.strom("felworks", "nvidia/nemotron-3-ultra-550b-a55b", [{"role": "user", "content": "hi"}], [{"type": "function"}])
    assert antwort == "ok" and mit is False
    assert "chat_template_kwargs" in gesendet[0] and "chat_template_kwargs" not in gesendet[1]
    assert "tools" in gesendet[1] and "tools" not in gesendet[2]


def test_katalog_hat_alle_wichtigen_anbieter():
    for kennung in ("felworks", "jon", "nvidia", "openai", "anthropic", "gemini", "deepseek", "openrouter", "groq", "mistral", "xai", "ollama", "lmstudio"):
        assert kennung in KATALOG
    assert not KATALOG["felworks"].braucht_schluessel


def test_nebenbei_erkennt_btw_und_nachauftraege():
    from jon_harness.nebenbei import auftrag_aus, frage_aus, ist_btw

    assert ist_btw("/btw wie weit bist du?") and ist_btw("  /nebenbei: was ist das?")
    assert not ist_btw("/hilfe")
    assert frage_aus("/btw: wie weit bist du?") == "wie weit bist du?"
    assert auftrag_aus("danach: schreib Tests") == "schreib Tests"
    assert auftrag_aus("schreib Tests") == "schreib Tests"


def test_nebenbei_merkt_vor_und_beantwortet_im_hintergrund(capsys):
    from jon_harness.nebenbei import Nebenbei

    fragen = []

    def beantworten(frage):
        fragen.append(frage)
        return "Ich bin gleich fertig, noch **zwei** Dateien."

    nebenbei = Nebenbei(beantworten)
    nebenbei._zeile("danach: schreib noch Tests")
    nebenbei._zeile("/btw wie weit bist du?")
    for faden in nebenbei._fragen:
        faden.join(timeout=5)
    assert fragen == ["wie weit bist du?"]
    assert nebenbei.naechste() == "schreib noch Tests"
    assert nebenbei.naechste() is None
    ausgabe = capsys.readouterr().out
    assert "vorgemerkt für danach" in ausgabe
    assert "Nebenbei" in ausgabe and "zwei Dateien" in ausgabe and "**" not in ausgabe


def test_zwischenfrage_kennt_den_verlauf_ohne_ihn_zu_aendern(tmp_path, monkeypatch):
    verbindung = Verbindung(speicher.Einstellungen(), Jon())
    gesehen = {}

    def strom(kennung, modell, nachrichten, werkzeuge, denken=None, max_tokens=8192, temperatur=0.4):
        gesehen.update(nachrichten=nachrichten, werkzeuge=werkzeuge, denken=denken)
        return _Antwort(_sse({"choices": [{"delta": {"content": "Ich baue gerade die Startseite."}}]})), False

    monkeypatch.setattr(verbindung, "strom", strom)
    agent = Agent(verbindung, Werkzeugkasten(tmp_path), Sitzung(tmp_path), "felworks", "x", "vorsichtig")
    agent.sitzung.nachrichten = [{"role": "user", "content": "Baue eine Startseite"}, {"role": "assistant", "content": "", "tool_calls": [{"id": "a", "type": "function", "function": {"name": "datei_schreiben", "arguments": "{}"}}]}]
    vorher = json.dumps(agent.sitzung.nachrichten)
    assert agent.zwischenfrage("woran arbeitest du?") == "Ich baue gerade die Startseite."
    assert json.dumps(agent.sitzung.nachrichten) == vorher
    assert gesehen["werkzeuge"] is None and gesehen["denken"] is False
    inhalt = gesehen["nachrichten"][-1]["content"]
    assert "Baue eine Startseite" in inhalt and "datei_schreiben" in inhalt and "ZWISCHENFRAGE: woran arbeitest du?" in inhalt


def test_terminal_zeigt_die_gedanken_live(tmp_path, monkeypatch, capsys):
    verbindung = Verbindung(speicher.Einstellungen(), Jon())
    gesehen = {}

    def strom(kennung, modell, nachrichten, werkzeuge, denken=None, max_tokens=8192, temperatur=0.4):
        gesehen["denken"] = denken
        return _Antwort(_sse({"choices": [{"delta": {"reasoning_content": "Der Nutzer will wissen, was 2+2 ist. Das ist einfach.\n"}}]}, {"choices": [{"delta": {"content": "Das ergibt 4."}}]})), True

    monkeypatch.setattr(verbindung, "strom", strom)
    agent = Agent(verbindung, Werkzeugkasten(tmp_path), Sitzung(tmp_path), "felworks", "x", "vorsichtig")
    assert agent.runde("Was ist 2+2?") == "Das ergibt 4."
    ausgabe = capsys.readouterr().out
    assert gesehen["denken"] is True
    assert "Jon denkt nach" in ausgabe and "Das ist einfach." in ausgabe
    assert ausgabe.index("Das ist einfach.") < ausgabe.index("Das ergibt 4.")


def test_updater_ersetzt_den_harness_nur_mit_passender_pruefsumme(tmp_path, monkeypatch):
    import hashlib

    from jon_harness import aktualisieren, netz

    alt = tmp_path / "jon-harness.pyz"
    alt.write_bytes(b"alte Version")
    neu_inhalt = b"neue Version"
    summe = hashlib.sha256(neu_inhalt).hexdigest()

    class Antwort:
        def __init__(self, daten):
            self.daten = daten

        def text(self):
            return self.daten.decode()

        def inhalt(self):
            return self.daten

    liste = {"text": f"{summe}  jon-harness.pyz\nabc  jon-harness.exe\n"}

    def anfrage(methode, url, *a, **k):
        return Antwort(liste["text"].encode() if url.endswith("SHA256SUMS.txt") else neu_inhalt)

    monkeypatch.setattr(netz, "anfrage", anfrage)
    assert aktualisieren.pruefsumme("jon-harness.pyz") == summe
    assert aktualisieren.aktualisieren((alt, "jon-harness.pyz")) == alt
    assert alt.read_bytes() == neu_inhalt
    liste["text"] = "0000  jon-harness.pyz\n"
    alt.write_bytes(b"bleibt")
    try:
        aktualisieren.aktualisieren((alt, "jon-harness.pyz"))
        raise AssertionError("falsche Pruefsumme muss abbrechen")
    except aktualisieren.UpdateFehler as fehler:
        assert "Prüfsumme" in str(fehler)
    assert alt.read_bytes() == b"bleibt"
    assert not (tmp_path / "jon-harness.pyz.neu").exists()


def test_updater_ersetzt_eine_laufende_exe_ueber_umbenennen(tmp_path, monkeypatch):
    import hashlib

    from jon_harness import aktualisieren, netz

    exe = tmp_path / "jon-harness.exe"
    exe.write_bytes(b"MZ" + b"a" * 1_100_000)
    neu_inhalt = b"MZ" + b"b" * 1_100_000

    class Antwort:
        def __init__(self, daten):
            self.daten = daten

        def text(self):
            return self.daten.decode()

        def inhalt(self):
            return self.daten

    summen = f"{hashlib.sha256(neu_inhalt).hexdigest()}  jon-harness.exe\n".encode()
    monkeypatch.setattr(netz, "anfrage", lambda methode, url, *a, **k: Antwort(summen if url.endswith("SHA256SUMS.txt") else neu_inhalt))
    aktualisieren.aktualisieren((exe, "jon-harness.exe"))
    assert exe.read_bytes() == neu_inhalt
    assert (tmp_path / "jon-harness.exe.alt").read_bytes()[:3] == b"MZa"
    monkeypatch.setattr(aktualisieren, "eigene_datei", lambda: (exe, "jon-harness.exe"))
    aktualisieren.aufraeumen()
    assert not (tmp_path / "jon-harness.exe.alt").exists()


class _Json:
    def __init__(self, daten):
        self._daten = daten

    def json(self):
        return self._daten


def test_felworks_weg_dann_weicht_jonh_auf_ollama_aus(tmp_path, monkeypatch, capsys):
    import argparse

    from jon_harness import start

    aufrufe = []

    def anfrage(methode, url, daten=None, kopf=None, zeit=60, **rest):
        aufrufe.append((url, zeit))
        if "ts.net" in url:
            raise netz.NetzFehler("Keine Verbindung zu felworks: timed out")
        if url.endswith("11434/v1/models"):
            return _Json({"data": [{"id": "nomic-embed-text"}, {"id": "qwen3:8b"}]})
        raise netz.NetzFehler("Keine Verbindung", 0)

    monkeypatch.setattr(netz, "anfrage", anfrage)
    werte = argparse.Namespace(frage=[], einmal=True, weiter=False, anbieter="felworks", modell=None, ordner=str(tmp_path), auto=False, alles=False, ohne_jon=True, version=False)
    terminal = start.Terminal(werte)
    assert (terminal.agent.anbieter, terminal.agent.modell) == ("ollama", "qwen3:8b")
    assert "FelWorks ist gerade nicht erreichbar" in terminal._ersatz_hinweis
    gesehen = []

    def strom(kennung, modell, nachrichten, werkzeuge, denken=None, max_tokens=8192, temperatur=0.4):
        gesehen.append((kennung, modell))
        return _Antwort(_sse({"choices": [{"delta": {"content": "Hallo aus Ollama."}}]})), True

    monkeypatch.setattr(terminal.verbindung, "strom", strom)
    assert terminal.ausfuehren("Sag hallo") == "Hallo aus Ollama."
    assert gesehen == [("ollama", "qwen3:8b")]
    assert all(zeit <= 8 for url, zeit in aufrufe if "ts.net" in url)
    assert "Ollama" in capsys.readouterr().out
    assert [n["role"] for n in terminal.agent.sitzung.nachrichten].count("user") == 1


def test_ohne_ausweg_sagt_jonh_klar_was_zu_tun_ist(tmp_path, monkeypatch, capsys):
    import argparse

    from jon_harness import start

    def anfrage(methode, url, daten=None, kopf=None, zeit=60, **rest):
        raise netz.NetzFehler("Keine Verbindung", 0)

    monkeypatch.setattr(netz, "anfrage", anfrage)
    werte = argparse.Namespace(frage=[], einmal=True, weiter=False, anbieter="felworks", modell=None, ordner=str(tmp_path), auto=False, alles=False, ohne_jon=True, version=False)
    terminal = start.Terminal(werte)
    assert terminal.ausfuehren("Sag hallo") == ""
    ausgabe = capsys.readouterr().out
    assert "FelWorks ist gerade nicht erreichbar" in ausgabe and "Ollama" in ausgabe and "/api" in ausgabe


def test_abgeschnittene_datei_wird_gerettet_und_angehaengt(tmp_path, monkeypatch):
    voll = json.dumps({"pfad": "index.html", "inhalt": "<!DOCTYPE html>\n<html>\n<body>\n<h1>Jon für dich</h1>\n<p>Teil</p>\n"}, ensure_ascii=False)
    abgeschnitten = voll[: voll.index("<p>Teil")]
    antworten = [
        _sse({"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "a1", "function": {"name": "datei_schreiben", "arguments": abgeschnitten}}]}}]}),
        _sse({"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "a2", "function": {"name": "datei_anhaengen", "arguments": json.dumps({"pfad": "index.html", "inhalt": "<p>Teil</p>\n</body>\n</html>\n"})}}]}}]}),
        _sse({"choices": [{"delta": {"content": "Die Website ist fertig."}}]}),
    ]
    gesehen = []

    def strom(kennung, modell, nachrichten, werkzeuge, denken=None, max_tokens=8192, temperatur=0.4):
        gesehen.append(json.loads(json.dumps(nachrichten)))
        return _Antwort(antworten.pop(0)), True

    verbindung = Verbindung(speicher.Einstellungen(), Jon())
    monkeypatch.setattr(verbindung, "strom", strom)
    agent = Agent(verbindung, Werkzeugkasten(tmp_path), Sitzung(tmp_path), "felworks", "x", "alles")
    assert agent.runde("Bau mir eine Website") == "Die Website ist fertig."
    inhalt = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert inhalt.startswith("<!DOCTYPE html>") and inhalt.endswith("</html>\n") and inhalt.count("<h1>") == 1
    werkzeug_antwort = next(n for n in gesehen[1] if n["role"] == "tool")
    assert "abgeschnitten" in werkzeug_antwort["content"] and "datei_anhaengen" in werkzeug_antwort["content"]
    aufruf = next(n for n in gesehen[1] if n.get("tool_calls"))
    assert json.loads(aufruf["tool_calls"][0]["function"]["arguments"])["pfad"] == "index.html"


def test_jonh_entfernt_kommentare_auf_wunsch(tmp_path, monkeypatch):
    antworten = [
        _sse({"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "a1", "function": {"name": "datei_schreiben", "arguments": json.dumps({"pfad": "spiel.js", "inhalt": "// Start\nconst ziel = 'https://getjon.info';\n"})}}]}}]}),
        _sse({"choices": [{"delta": {"content": "Fertig."}}]}),
    ]

    def strom(kennung, modell, nachrichten, werkzeuge, denken=None, max_tokens=8192, temperatur=0.4):
        return _Antwort(antworten.pop(0)), True

    verbindung = Verbindung(speicher.Einstellungen(), Jon())
    monkeypatch.setattr(verbindung, "strom", strom)
    agent = Agent(verbindung, Werkzeugkasten(tmp_path), Sitzung(tmp_path), "felworks", "x", "alles")
    assert agent.runde("Programmier mir ein Spiel ohne Kommentare") == "Fertig."
    assert (tmp_path / "spiel.js").read_text(encoding="utf-8") == "const ziel = 'https://getjon.info';\n"


def test_unzensiert_nur_mit_lokalem_modell(tmp_path):
    from jon_harness import prompt

    verbindung = Verbindung(speicher.Einstellungen(), Jon())
    lokal = Agent(verbindung, Werkzeugkasten(tmp_path), Sitzung(tmp_path), "ollama", "dolphin-mistral")
    wolke = Agent(verbindung, Werkzeugkasten(tmp_path), Sitzung(tmp_path), "nvidia", "meta/muse-glimmer-30b")
    assert "UNZENSIERT-MODUS" not in lokal._system()["content"]
    lokal.unzensiert = wolke.unzensiert = True
    assert "UNZENSIERT-MODUS" in lokal._system()["content"]
    assert "UNZENSIERT-MODUS" not in wolke._system()["content"]
    assert prompt.lokal("jon", "ollama/llama3") and not prompt.lokal("ollama", "gpt-oss:120b-cloud")


def test_ohne_felworks_und_ohne_schluessel_nimmt_jonh_den_freien_dienst(tmp_path, monkeypatch):
    import argparse

    from jon_harness import start
    from jon_harness.anbieter import KATALOG

    monkeypatch.delenv("JON_HARNESS_OHNE_FREI", raising=False)

    def anfrage(methode, url, daten=None, kopf=None, zeit=60, **rest):
        raise netz.NetzFehler("Keine Verbindung", 0)

    monkeypatch.setattr(netz, "anfrage", anfrage)
    werte = argparse.Namespace(frage=[], einmal=True, weiter=False, anbieter=None, modell=None, ordner=str(tmp_path), auto=False, alles=False, ohne_jon=True, version=False)
    terminal = start.Terminal(werte)
    assert terminal.agent.anbieter == "frei"
    assert KATALOG["frei"].braucht_schluessel is False
    assert terminal.verbindung.bereit("frei")


def test_werkzeugname_mit_steuerzeichen_wird_bereinigt(tmp_path, monkeypatch):
    verbindung = Verbindung(speicher.Einstellungen(), Jon())
    antworten = [
        _sse({"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "c1", "function": {"name": "datei_lesen<|channel|>commentary", "arguments": "{\"pfad\": \"a.txt\"}"}}]}}]}),
        _sse({"choices": [{"delta": {"content": "Gelesen."}}]}),
    ]
    (tmp_path / "a.txt").write_text("Inhalt", encoding="utf-8")
    monkeypatch.setattr(verbindung, "strom", lambda *a, **k: (_Antwort(antworten.pop(0)), True))
    agent = Agent(verbindung, Werkzeugkasten(tmp_path), Sitzung(tmp_path), "frei", "openai-fast", "auto")
    assert agent.runde("lies a.txt", still=True) == "Gelesen."
    aufruf = next(n for n in agent.sitzung.nachrichten if n.get("tool_calls"))
    assert aufruf["tool_calls"][0]["function"]["name"] == "datei_lesen"
