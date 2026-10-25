from __future__ import annotations

import fnmatch
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

from . import netz

UEBERSPRINGEN = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", ".idea", ".pytest_cache", ".mypy_cache", "target", ".gradle", "release", ".cache"}
LESEN_MAX = 2000
AUSGABE_MAX = 30000
SICHERE_BEFEHLE = re.compile(r"^\s*(git\s+(status|diff|log|show|branch|remote)|ls|dir|pwd|cat|type|head|tail|echo|where|which|whoami|node\s+(-v|--version)|python\s+(-V|--version)|npm\s+(-v|--version|ls|list|run\s+(test|lint|build|typecheck))|pip\s+(list|show|--version)|Get-ChildItem|Get-Content|Get-Location|Test-Path|tree)\b", re.IGNORECASE)
GEFAEHRLICH = re.compile(r"(rm\s+-rf\s+[/~]|Remove-Item[^\n]*-Recurse[^\n]*(C:\\|\$env:USERPROFILE|~)\b|format\s+[a-z]:|diskpart|Stop-Computer|Restart-Computer|shutdown\s|mkfs|dd\s+if=|reg\s+delete|Set-ExecutionPolicy|del\s+/[sq]\s+[a-z]:\\)", re.IGNORECASE)


def _s(beschreibung: str) -> dict:
    return {"type": "string", "description": beschreibung}


def _w(name: str, beschreibung: str, felder: dict, pflicht: list[str]) -> dict:
    return {"type": "function", "function": {"name": name, "description": beschreibung, "parameters": {"type": "object", "properties": felder, "required": pflicht}}}


SCHEMA = [
    _w("datei_lesen", "Liest eine Textdatei mit Zeilennummern. Lies jede Datei, bevor du sie änderst. Bei grossen Dateien mit von/bis einen Ausschnitt lesen.", {"pfad": _s("Pfad, relativ zum Arbeitsordner oder absolut"), "von": {"type": "integer"}, "bis": {"type": "integer"}}, ["pfad"]),
    _w("datei_schreiben", "Legt eine Datei neu an oder ersetzt sie komplett. Für Änderungen an bestehenden Dateien nimm datei_bearbeiten.", {"pfad": _s("Pfad"), "inhalt": _s("Vollständiger neuer Inhalt")}, ["pfad", "inhalt"]),
    _w("datei_anhaengen", "Hängt Text an eine Datei an, die du gerade angelegt hast. Grosse Dateien schreibst du in Teilen: erst datei_schreiben mit dem ersten Teil, dann datei_anhaengen mit den weiteren Teilen.", {"pfad": _s("Pfad"), "inhalt": _s("Nächster Teil des Inhalts")}, ["pfad", "inhalt"]),
    _w("datei_bearbeiten", "Ersetzt in einer Datei genau den Text alt durch neu. alt muss exakt (inklusive Einrückung) und eindeutig vorkommen, sonst mehr Kontext angeben oder alle=true.", {"pfad": _s("Pfad"), "alt": _s("Exakter vorhandener Text"), "neu": _s("Neuer Text"), "alle": {"type": "boolean"}}, ["pfad", "alt", "neu"]),
    _w("ordner_zeigen", "Zeigt Dateien und Unterordner eines Ordners (ohne node_modules, .git usw.).", {"pfad": _s("Ordner, Standard ist der Arbeitsordner"), "tiefe": {"type": "integer"}}, []),
    _w("dateien_finden", "Findet Dateien per Glob-Muster, z. B. **/*.py oder src/**/*.tsx.", {"muster": _s("Glob-Muster")}, ["muster"]),
    _w("text_suchen", "Durchsucht Dateien mit einem regulären Ausdruck und liefert Datei:Zeile: Treffer.", {"muster": _s("Regulärer Ausdruck"), "pfad": _s("Ordner oder Datei"), "dateien": _s("Glob für Dateinamen, z. B. *.ts"), "gross_klein": {"type": "boolean"}}, ["muster"]),
    _w("befehl", "Führt einen Befehl in der Shell aus (Windows: PowerShell, sonst bash) und liefert Ausgabe und Exitcode. Für Tests, Builds, git, npm, pip, Programme starten. Lange Dienste (Server) mit hintergrund=true starten.", {"befehl": _s("Der Befehl"), "zeitlimit": {"type": "integer", "description": "Sekunden, Standard 120"}, "hintergrund": {"type": "boolean"}}, ["befehl"]),
    _w("web_suche", "Sucht im Internet und liefert Titel, Adresse und Ausschnitt der besten Treffer.", {"anfrage": _s("Suchbegriffe")}, ["anfrage"]),
    _w("web_lesen", "Lädt eine Webseite oder API-Adresse und liefert den lesbaren Text.", {"url": _s("Adresse")}, ["url"]),
    _w("aufgaben", "Pflegt deine sichtbare Aufgabenliste für mehrschrittige Arbeiten. Schicke immer die ganze Liste; status: offen, aktiv oder fertig. Genau ein Eintrag ist aktiv.", {"liste": {"type": "array", "items": {"type": "object", "properties": {"text": {"type": "string"}, "status": {"type": "string", "enum": ["offen", "aktiv", "fertig"]}}, "required": ["text", "status"]}}}, ["liste"]),
    _w("nutzer_fragen", "Stellt dem Nutzer eine kurze Rückfrage, wenn eine Entscheidung wirklich nur er treffen kann. Optional mit Antwortmöglichkeiten.", {"frage": _s("Die Frage"), "optionen": {"type": "array", "items": {"type": "string"}}}, ["frage"]),
]

JON_WERKZEUG = _w("jon", "Gibt einen Auftrag an den Jon-Assistenten auf diesem PC weiter. Jon kann den Bildschirm sehen und klicken, Programme und Fenster steuern, PowerPoint, Word und Excel erstellen und bearbeiten, Telegram-Nachrichten schicken, Erinnerungen, Kalender, Musik, Smart Home und alle seine Werkzeuge nutzen. Beschreibe den Auftrag vollständig in einem Satz oder Absatz.", {"auftrag": _s("Was Jon tun soll")}, ["auftrag"])


@dataclass
class Ergebnis:
    text: str
    ok: bool = True
    kurz: str = ""
    zusatz: dict = field(default_factory=dict)


class Werkzeugkasten:
    def __init__(self, arbeitsordner: Path) -> None:
        self.arbeitsordner = arbeitsordner.resolve()
        self.gelesen: dict[str, float] = {}
        self.aufgabenliste: list[dict] = []
        self.hintergrund: list[subprocess.Popen] = []
        self.sicherungen: list[tuple[Path, str | None]] = []

    def pfad(self, eingabe: str) -> Path:
        roh = os.path.expandvars(os.path.expanduser(str(eingabe or ".").strip().strip('"')))
        pfad = Path(roh)
        if not pfad.is_absolute():
            pfad = self.arbeitsordner / pfad
        return pfad.resolve()

    def anzeigen(self, pfad: Path) -> str:
        try:
            return str(pfad.relative_to(self.arbeitsordner)).replace("\\", "/")
        except ValueError:
            return str(pfad)

    def im_arbeitsordner(self, pfad: Path) -> bool:
        return pfad == self.arbeitsordner or self.arbeitsordner in pfad.parents

    def datei_lesen(self, pfad: str, von: int | None = None, bis: int | None = None) -> Ergebnis:
        ziel = self.pfad(pfad)
        if not ziel.exists():
            return Ergebnis(f"Die Datei {self.anzeigen(ziel)} gibt es nicht.", False)
        if ziel.is_dir():
            return self.ordner_zeigen(str(ziel))
        if ziel.stat().st_size > 15_000_000:
            return Ergebnis("Die Datei ist zu gross zum Lesen.", False)
        roh = ziel.read_bytes()
        if b"\x00" in roh[:8000]:
            return Ergebnis(f"{self.anzeigen(ziel)} ist eine Binärdatei ({len(roh)} Bytes).", True, "Binärdatei")
        text = roh.decode("utf-8", errors="replace")
        zeilen = text.splitlines()
        start = max(1, int(von or 1))
        ende = min(len(zeilen), int(bis or start + LESEN_MAX - 1))
        teil = [f"{i:>6}\t{zeilen[i - 1]}" for i in range(start, ende + 1)]
        self.gelesen[str(ziel)] = ziel.stat().st_mtime
        hinweis = f"\n… {len(zeilen) - ende} weitere Zeilen, lies mit von={ende + 1}" if ende < len(zeilen) else ""
        return Ergebnis("\n".join(teil) + hinweis if teil else "(leere Datei)", True, f"{len(zeilen)} Zeilen")

    def _sichern(self, ziel: Path) -> None:
        alt = ziel.read_text(encoding="utf-8", errors="replace") if ziel.exists() else None
        self.sicherungen.append((ziel, alt))
        del self.sicherungen[:-200]

    def rueckgaengig(self) -> str:
        if not self.sicherungen:
            return "Es gibt nichts rückgängig zu machen."
        ziel, alt = self.sicherungen.pop()
        if alt is None:
            try:
                ziel.unlink()
            except OSError:
                pass
            return f"{self.anzeigen(ziel)} wieder entfernt."
        ziel.write_text(alt, encoding="utf-8")
        return f"{self.anzeigen(ziel)} auf den vorherigen Stand zurückgesetzt."

    def vorschau_schreiben(self, pfad: str, inhalt: str) -> tuple[str, str]:
        ziel = self.pfad(pfad)
        alt = ziel.read_text(encoding="utf-8", errors="replace") if ziel.exists() else ""
        return alt, inhalt

    def datei_schreiben(self, pfad: str, inhalt: str) -> Ergebnis:
        ziel = self.pfad(pfad)
        if ziel.exists() and str(ziel) not in self.gelesen and ziel.stat().st_size > 0:
            return Ergebnis(f"{self.anzeigen(ziel)} gibt es schon. Lies die Datei zuerst mit datei_lesen, bevor du sie komplett ersetzt.", False)
        self._sichern(ziel)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        neu = not ziel.exists()
        ziel.write_text(inhalt, encoding="utf-8", newline="")
        self.gelesen[str(ziel)] = ziel.stat().st_mtime
        zeilen = inhalt.count("\n") + (1 if inhalt and not inhalt.endswith("\n") else 0)
        return Ergebnis(f"{'Angelegt' if neu else 'Ersetzt'}: {self.anzeigen(ziel)} ({zeilen} Zeilen)", True, f"{zeilen} Zeilen")

    def datei_anhaengen(self, pfad: str, inhalt: str) -> Ergebnis:
        ziel = self.pfad(pfad)
        if not ziel.exists():
            return Ergebnis(f"{self.anzeigen(ziel)} gibt es noch nicht. Lege die Datei zuerst mit datei_schreiben an.", False)
        alt = ziel.read_text(encoding="utf-8", errors="replace")
        inhalt = naht_bereinigen(alt, inhalt)
        trenner = "" if not alt or alt.endswith("\n") or inhalt.startswith("\n") else "\n"
        with ziel.open("a", encoding="utf-8", newline="") as datei:
            datei.write(trenner + inhalt)
        self.gelesen[str(ziel)] = ziel.stat().st_mtime
        gesamt = (alt + trenner + inhalt).splitlines()
        ende = "\n".join(gesamt[-25:])
        return Ergebnis(f"Angehängt: {self.anzeigen(ziel)} hat jetzt {len(gesamt)} Zeilen. So endet die Datei:\n{ende}", True, f"{len(gesamt)} Zeilen")

    def vorschau_bearbeiten(self, pfad: str, alt: str, neu: str, alle: bool = False) -> tuple[str, str, str]:
        ziel = self.pfad(pfad)
        if not ziel.exists():
            return "", "", f"Die Datei {self.anzeigen(ziel)} gibt es nicht."
        text = ziel.read_text(encoding="utf-8", errors="replace")
        anzahl = text.count(alt)
        if not alt:
            return "", "", "alt darf nicht leer sein."
        if anzahl == 0:
            ersatz = _toleranter_treffer(text, alt)
            if ersatz is None:
                return "", "", f"Der Text alt kommt in {self.anzeigen(ziel)} nicht vor. Lies die Datei erneut und kopiere den Ausschnitt exakt."
            alt = ersatz
            anzahl = text.count(alt)
        if anzahl > 1 and not alle:
            return "", "", f"Der Text alt kommt {anzahl}-mal vor. Gib mehr Kontext an oder setze alle=true."
        neu_text = text.replace(alt, neu) if alle else text.replace(alt, neu, 1)
        return text, neu_text, ""

    def datei_bearbeiten(self, pfad: str, alt: str, neu: str, alle: bool = False) -> Ergebnis:
        vorher, nachher, fehler = self.vorschau_bearbeiten(pfad, alt, neu, alle)
        if fehler:
            return Ergebnis(fehler, False)
        ziel = self.pfad(pfad)
        self._sichern(ziel)
        with ziel.open("w", encoding="utf-8", newline="") as datei:
            datei.write(nachher)
        self.gelesen[str(ziel)] = ziel.stat().st_mtime
        import difflib

        plus = minus = 0
        for zeile in difflib.unified_diff(vorher.splitlines(), nachher.splitlines(), lineterm="", n=0):
            if zeile.startswith("+") and not zeile.startswith("+++"):
                plus += 1
            elif zeile.startswith("-") and not zeile.startswith("---"):
                minus += 1
        return Ergebnis(f"Geändert: {self.anzeigen(ziel)} (+{plus} −{minus})", True, f"+{plus} −{minus}")

    def ordner_zeigen(self, pfad: str = ".", tiefe: int = 2) -> Ergebnis:
        wurzel = self.pfad(pfad or ".")
        if not wurzel.is_dir():
            return Ergebnis(f"{self.anzeigen(wurzel)} ist kein Ordner.", False)
        zeilen: list[str] = []
        tiefe = max(1, min(int(tiefe or 2), 5))

        def gehen(ordner: Path, stufe: int, vorsatz: str) -> None:
            if len(zeilen) > 400:
                return
            try:
                eintraege = sorted(ordner.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
            except OSError:
                return
            for eintrag in eintraege:
                if eintrag.name in UEBERSPRINGEN or (eintrag.name.startswith(".") and eintrag.name not in (".github", ".env.example", ".gitignore")):
                    continue
                if eintrag.is_dir():
                    zeilen.append(f"{vorsatz}{eintrag.name}/")
                    if stufe < tiefe:
                        gehen(eintrag, stufe + 1, vorsatz + "  ")
                else:
                    try:
                        groesse = eintrag.stat().st_size
                    except OSError:
                        groesse = 0
                    zeilen.append(f"{vorsatz}{eintrag.name}  ({_groesse(groesse)})")

        gehen(wurzel, 1, "")
        return Ergebnis("\n".join(zeilen[:400]) or "(leer)", True, f"{len(zeilen)} Einträge")

    def dateien_finden(self, muster: str) -> Ergebnis:
        treffer: list[str] = []
        muster = muster.replace("\\", "/")
        for wurzel, ordner, dateien in os.walk(self.arbeitsordner):
            ordner[:] = [o for o in ordner if o not in UEBERSPRINGEN and not o.startswith(".")]
            for name in dateien:
                voll = Path(wurzel) / name
                relativ = self.anzeigen(voll)
                if fnmatch.fnmatch(relativ, muster) or fnmatch.fnmatch(name, muster) or ("**/" in muster and fnmatch.fnmatch(relativ, muster.replace("**/", ""))):
                    treffer.append(relativ)
                    if len(treffer) >= 300:
                        break
        treffer.sort()
        return Ergebnis("\n".join(treffer) or "Keine Treffer.", True, f"{len(treffer)} Dateien")

    def text_suchen(self, muster: str, pfad: str = ".", dateien: str = "", gross_klein: bool = False) -> Ergebnis:
        try:
            ausdruck = re.compile(muster, 0 if gross_klein else re.IGNORECASE)
        except re.error as fehler:
            return Ergebnis(f"Ungültiger Ausdruck: {fehler}", False)
        wurzel = self.pfad(pfad or ".")
        kandidaten = [wurzel] if wurzel.is_file() else []
        if wurzel.is_dir():
            for basis, ordner, namen in os.walk(wurzel):
                ordner[:] = [o for o in ordner if o not in UEBERSPRINGEN and not o.startswith(".")]
                for name in namen:
                    if dateien and not fnmatch.fnmatch(name, dateien):
                        continue
                    kandidaten.append(Path(basis) / name)
        treffer: list[str] = []
        for datei in kandidaten:
            try:
                if datei.stat().st_size > 3_000_000:
                    continue
                roh = datei.read_bytes()
            except OSError:
                continue
            if b"\x00" in roh[:4000]:
                continue
            for nummer, zeile in enumerate(roh.decode("utf-8", errors="replace").splitlines(), 1):
                if ausdruck.search(zeile):
                    treffer.append(f"{self.anzeigen(datei)}:{nummer}: {zeile.strip()[:220]}")
                    if len(treffer) >= 250:
                        break
            if len(treffer) >= 250:
                break
        return Ergebnis("\n".join(treffer) or "Keine Treffer.", True, f"{len(treffer)} Treffer")

    def befehl(self, befehl: str, zeitlimit: int | None = None, hintergrund: bool = False) -> Ergebnis:
        if sys.platform == "win32":
            aufruf = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", "[Console]::OutputEncoding=[Text.Encoding]::UTF8; $OutputEncoding=[Text.Encoding]::UTF8; " + befehl]
        else:
            aufruf = ["bash", "-lc", befehl]
        umgebung = {**os.environ, "PYTHONIOENCODING": "utf-8", "FORCE_COLOR": "0", "NO_COLOR": "1"}
        if hintergrund:
            protokoll = Path(os.environ.get("TEMP", "/tmp")) / f"jon-harness-{int(time.time())}.log"
            with protokoll.open("w", encoding="utf-8") as ausgabe:
                prozess = subprocess.Popen(aufruf, cwd=self.arbeitsordner, stdout=ausgabe, stderr=subprocess.STDOUT, env=umgebung, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.hintergrund.append(prozess)
            time.sleep(2.5)
            anfang = protokoll.read_text(encoding="utf-8", errors="replace")[-3000:]
            zustand = "läuft" if prozess.poll() is None else f"beendet mit {prozess.returncode}"
            return Ergebnis(f"Im Hintergrund gestartet (PID {prozess.pid}, {zustand}). Protokoll: {protokoll}\n{anfang}", prozess.poll() in (None, 0), zustand)
        grenze = max(5, min(int(zeitlimit or 120), 1800))
        try:
            ablauf = subprocess.run(aufruf, cwd=self.arbeitsordner, capture_output=True, timeout=grenze, env=umgebung, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired as fehler:
            teil = (fehler.stdout or b"").decode("utf-8", errors="replace")[-4000:]
            return Ergebnis(f"Abgebrochen nach {grenze} s.\n{teil}", False, "Zeitlimit")
        except FileNotFoundError as fehler:
            return Ergebnis(f"Shell nicht gefunden: {fehler}", False)
        ausgabe = (ablauf.stdout or b"").decode("utf-8", errors="replace")
        fehler = (ablauf.stderr or b"").decode("utf-8", errors="replace")
        text = ausgabe + (("\n[stderr]\n" + fehler) if fehler.strip() else "")
        if len(text) > AUSGABE_MAX:
            text = text[: AUSGABE_MAX // 3] + f"\n… {len(text) - AUSGABE_MAX} Zeichen ausgelassen …\n" + text[-AUSGABE_MAX // 2:]
        return Ergebnis(f"Exitcode {ablauf.returncode}\n{text.strip()}", ablauf.returncode == 0, f"Exitcode {ablauf.returncode}")

    def web_suche(self, anfrage: str) -> Ergebnis:
        kopf = {"Accept-Language": "de-DE,de;q=0.9,en;q=0.7", "Accept": "text/html,application/xhtml+xml"}
        fehler_liste: list[str] = []
        for suche in (_yahoo, _ddg_lite, _ddg_html):
            try:
                treffer = suche(anfrage, kopf)
            except Exception as fehler:
                fehler_liste.append(f"{suche.__name__.strip('_')}: {fehler}")
                continue
            if treffer:
                zeilen = [f"{i}. {titel}\n   {adresse}\n   {text}" for i, (titel, adresse, text) in enumerate(treffer[:8], 1)]
                return Ergebnis("\n".join(zeilen), True, f"{len(zeilen)} Treffer")
        return Ergebnis("Keine Suchmaschine hat geantwortet (" + "; ".join(fehler_liste)[:300] + "). Versuche andere Suchwörter oder lies eine bekannte Seite direkt mit web_lesen.", False, "keine Treffer")

    def web_lesen(self, url: str) -> Ergebnis:
        if not re.match(r"^https?://", url or ""):
            url = "https://" + (url or "")
        try:
            antwort = netz.anfrage("GET", url, kopf={"Accept": "text/html,application/json,text/plain,*/*", "Accept-Language": "de-DE,de;q=0.9,en;q=0.7"}, zeit=25)
        except Exception as fehler:
            return Ergebnis(f"Die Seite ging nicht: {fehler}", False)
        art = antwort.kopf.get("content-type", "")
        text = antwort.text()
        if "html" in art or text.lstrip().startswith("<"):
            titel = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
            text = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", text)
            text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</h[1-6]>|</li>|</tr>", "\n", text)
            text = _sauber(text, zeilen=True)
            if titel:
                text = _sauber(titel.group(1)) + "\n\n" + text
        return Ergebnis(text[:24000] or "(leer)", True, f"{len(text)} Zeichen")

    def aufgaben(self, liste: list) -> Ergebnis:
        sauber = []
        for eintrag in liste or []:
            if isinstance(eintrag, dict) and eintrag.get("text"):
                status = str(eintrag.get("status") or "offen")
                sauber.append({"text": str(eintrag["text"])[:160], "status": status if status in ("offen", "aktiv", "fertig") else "offen"})
        self.aufgabenliste = sauber[:30]
        fertig = sum(1 for e in self.aufgabenliste if e["status"] == "fertig")
        return Ergebnis(f"Aufgabenliste aktualisiert ({fertig}/{len(self.aufgabenliste)} erledigt).", True, f"{fertig}/{len(self.aufgabenliste)}")

    def aufraeumen(self) -> None:
        for prozess in self.hintergrund:
            if prozess.poll() is None:
                try:
                    prozess.terminate()
                except OSError:
                    pass


def _echte_adresse(adresse: str) -> str:
    adresse = html.unescape(adresse)
    if adresse.startswith("//"):
        adresse = "https:" + adresse
    if "/RU=" in adresse:
        adresse = urllib.parse.unquote(adresse.split("/RU=", 1)[1].split("/RK=", 1)[0])
    if "uddg=" in adresse:
        gefunden = urllib.parse.parse_qs(urllib.parse.urlparse(adresse).query).get("uddg")
        if gefunden:
            adresse = gefunden[0]
    return adresse


def _brauchbar(adresse: str) -> bool:
    host = urllib.parse.urlparse(adresse).netloc.lower()
    return adresse.startswith("http") and not any(w in host for w in ("yahoo.com", "duckduckgo.com", "bing.com")) and "/y.js" not in adresse


def _yahoo(anfrage: str, kopf: dict) -> list[tuple[str, str, str]]:
    seite = netz.anfrage("GET", "https://search.yahoo.com/search?" + urllib.parse.urlencode({"p": anfrage}), kopf=kopf, zeit=12).text()
    treffer = []
    for block in re.split(r'<div class="dd [^"]*algo[ "]', seite)[1:]:
        link = re.search(r'href="(https?://r\.search\.yahoo\.com/[^"]+|https?://(?!r\.search)[^"]+)"[^>]*>.*?<h3[^>]*>(.*?)</h3>', block[:6000], re.S)
        if not link:
            continue
        adresse = _echte_adresse(link.group(1))
        if not _brauchbar(adresse):
            continue
        ausschnitt = re.search(r'<div class="compText[^"]*"[^>]*>\s*<p[^>]*>(.*?)</p>', block[:8000], re.S)
        treffer.append((_sauber(link.group(2)), adresse, _sauber(ausschnitt.group(1)) if ausschnitt else ""))
    return treffer


def _ddg_lite(anfrage: str, kopf: dict) -> list[tuple[str, str, str]]:
    seite = netz.anfrage("POST", "https://lite.duckduckgo.com/lite/", urllib.parse.urlencode({"q": anfrage, "kl": "de-de"}), kopf={**kopf, "Content-Type": "application/x-www-form-urlencoded"}, zeit=12).text()
    treffer = []
    offen = None
    for block in re.split(r"<tr[^>]*>", seite):
        link = re.search(r"""<a[^>]+href=["']([^"']+)["'][^>]*class=["']result-link["'][^>]*>(.*?)</a>""", block, re.S)
        if link:
            adresse = _echte_adresse(link.group(1))
            if _brauchbar(adresse):
                offen = [_sauber(link.group(2)), adresse, ""]
                treffer.append(offen)
            continue
        text = re.search(r"""<td[^>]*class=["']result-snippet["'][^>]*>(.*?)</td>""", block, re.S)
        if text and offen is not None:
            offen[2] = _sauber(text.group(1))[:400]
            offen = None
    return [tuple(t) for t in treffer]


def _ddg_html(anfrage: str, kopf: dict) -> list[tuple[str, str, str]]:
    seite = netz.anfrage("GET", "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": anfrage, "kl": "de-de"}), kopf=kopf, zeit=12).text()
    treffer = []
    for block in re.split(r'class="result results_links', seite)[1:]:
        link = re.search(r"""<a[^>]+class=["']result__a["'][^>]+href=["']([^"']+)["'][^>]*>(.*?)</a>""", block, re.S)
        if not link:
            continue
        adresse = _echte_adresse(link.group(1))
        if not _brauchbar(adresse):
            continue
        text = re.search(r"""class=["']result__snippet["'][^>]*>(.*?)</a>""", block, re.S)
        treffer.append((_sauber(link.group(2)), adresse, _sauber(text.group(1)) if text else ""))
    return treffer


def befehl_sicher(befehl: str) -> bool:
    if any(zeichen in befehl for zeichen in (";", "&&", "||", "|", ">", "`", "$(")):
        return False
    return bool(SICHERE_BEFEHLE.match(befehl))


def befehl_gefaehrlich(befehl: str) -> bool:
    return bool(GEFAEHRLICH.search(befehl))


def _toleranter_treffer(text: str, alt: str) -> str | None:
    def normal(zeile: str) -> str:
        return zeile.rstrip().replace("\t", "    ")

    zeilen = text.splitlines(keepends=True)
    gesucht = [normal(z) for z in alt.splitlines()]
    while gesucht and not gesucht[-1].strip():
        gesucht.pop()
    if not gesucht:
        return None
    for start in range(len(zeilen) - len(gesucht) + 1):
        if all(normal(zeilen[start + i].rstrip("\r\n")) == gesucht[i] for i in range(len(gesucht))):
            return "".join(zeilen[start : start + len(gesucht)]).rstrip("\r\n")
    stripped = [g.strip() for g in gesucht]
    for start in range(len(zeilen) - len(gesucht) + 1):
        if all(zeilen[start + i].strip() == stripped[i] for i in range(len(gesucht))):
            return "".join(zeilen[start : start + len(gesucht)]).rstrip("\r\n")
    return None


def _sauber(text: str, zeilen: bool = False) -> str:
    ohne = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    if zeilen:
        teile = [re.sub(r"[ \t\r\f\v]+", " ", z).strip() for z in ohne.splitlines()]
        return "\n".join(z for z in teile if z)
    return re.sub(r"\s+", " ", ohne).strip()


def _groesse(zahl: int) -> str:
    for einheit in ("B", "KB", "MB", "GB"):
        if zahl < 1024:
            return f"{zahl:.0f} {einheit}" if einheit == "B" else f"{zahl:.1f} {einheit}"
        zahl /= 1024
    return f"{zahl:.1f} TB"


def ausfuehren(kasten: Werkzeugkasten, name: str, args: dict) -> Ergebnis:
    try:
        if name == "datei_lesen":
            return kasten.datei_lesen(str(args.get("pfad") or ""), args.get("von"), args.get("bis"))
        if name == "datei_schreiben":
            return kasten.datei_schreiben(str(args.get("pfad") or ""), str(args.get("inhalt") or ""))
        if name == "datei_anhaengen":
            return kasten.datei_anhaengen(str(args.get("pfad") or ""), str(args.get("inhalt") or ""))
        if name == "datei_bearbeiten":
            return kasten.datei_bearbeiten(str(args.get("pfad") or ""), str(args.get("alt") or ""), str(args.get("neu") or ""), bool(args.get("alle")))
        if name == "ordner_zeigen":
            return kasten.ordner_zeigen(str(args.get("pfad") or "."), int(args.get("tiefe") or 2))
        if name == "dateien_finden":
            return kasten.dateien_finden(str(args.get("muster") or "*"))
        if name == "text_suchen":
            return kasten.text_suchen(str(args.get("muster") or ""), str(args.get("pfad") or "."), str(args.get("dateien") or ""), bool(args.get("gross_klein")))
        if name == "befehl":
            return kasten.befehl(str(args.get("befehl") or ""), args.get("zeitlimit"), bool(args.get("hintergrund")))
        if name == "web_suche":
            return kasten.web_suche(str(args.get("anfrage") or ""))
        if name == "web_lesen":
            return kasten.web_lesen(str(args.get("url") or ""))
        if name == "aufgaben":
            return kasten.aufgaben(args.get("liste") or [])
    except Exception as fehler:
        return Ergebnis(f"{name} ist fehlgeschlagen: {type(fehler).__name__}: {fehler}", False)
    return Ergebnis(f"Das Werkzeug {name} gibt es nicht.", False)


FLUCHT = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f"}
ABGESCHNITTEN = ("Deine Antwort war zu lang und wurde abgeschnitten. Gespeichert ist der Inhalt bis zur letzten vollständigen Zeile. "
                 "Schreibe den Rest mit datei_anhaengen in Teilen von höchstens etwa 200 Zeilen. Der nächste Teil beginnt mit genau der Zeile, "
                 "die nach dem folgenden Dateiende kommt, und führt die Datei von oben nach unten weiter. Wiederhole nichts davon. So endet die Datei jetzt:\n")


def _zeichenkette(roh: str, start: int = 0) -> tuple[str, bool]:
    teile: list[str] = []
    stelle = start
    fertig = False
    while stelle < len(roh):
        zeichen = roh[stelle]
        if zeichen == '"':
            fertig = True
            break
        if zeichen == "\\":
            if stelle + 1 >= len(roh):
                break
            weiter = roh[stelle + 1]
            if weiter == "u":
                kode = roh[stelle + 2:stelle + 6]
                if len(kode) < 4:
                    break
                try:
                    teile.append(chr(int(kode, 16)))
                    stelle += 6
                    continue
                except ValueError:
                    teile.append("\\u")
                    stelle += 2
                    continue
            teile.append(FLUCHT.get(weiter, "\\" + weiter))
            stelle += 2
            continue
        teile.append(zeichen)
        stelle += 1
    return "".join(teile).encode("utf-16", "surrogatepass").decode("utf-16", "replace"), fertig


def naht_bereinigen(alt: str, neu: str, fenster: int = 40) -> str:
    vorher = [z.strip() for z in alt.splitlines()]
    zeilen = neu.splitlines(True)
    nachher = [z.strip() for z in zeilen]
    for anzahl in range(min(fenster, len(vorher), len(nachher)), 0, -1):
        if vorher[-anzahl:] == nachher[:anzahl] and sum(len(z) for z in nachher[:anzahl]) >= 30:
            return "".join(zeilen[anzahl:])
    return neu


def teil_args(roh: str) -> dict:
    inhalt = re.search(r'"(?:inhalt|content)"\s*:\s*"', roh)
    pfad = re.search(r'"(?:pfad|path)"\s*:\s*"((?:[^"\\]|\\.)*)"', roh)
    if not inhalt or not pfad:
        return {}
    text, vollstaendig = _zeichenkette(roh, inhalt.end())
    if not vollstaendig:
        if "\n" not in text:
            return {}
        text = text[: text.rfind("\n") + 1]
    return {"pfad": _zeichenkette(pfad.group(1) + '"')[0], "inhalt": text, "_repariert": True, "_abgeschnitten": not vollstaendig}


def args_lesen(roh: str) -> dict:
    roh = (roh or "").strip() or "{}"
    try:
        wert = json.loads(roh)
        return wert if isinstance(wert, dict) else {}
    except ValueError:
        try:
            return json.loads(roh.replace("\n", "\\n"))
        except ValueError:
            return teil_args(roh)
