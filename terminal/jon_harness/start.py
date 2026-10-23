from __future__ import annotations

import argparse
import getpass
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from . import NAME, VERSION, netz, oberflaeche as ui, prompt
from .agent import Abbruch, Agent, Sitzung
from .anbieter import KATALOG, Jon, Verbindung, letzte_wahl_speichern
from .nebenbei import Nebenbei, frage_aus
from .oberflaeche import BLAU, FETT, GOLD, GRAU, GRUEN, MATT, ROT, TUERKIS, WEISS, f, sag
from .speicher import Einstellungen, ordner, schreiben
from .werkzeuge import Werkzeugkasten

GITHUB = "https://api.github.com/repos/Lightning702/Jon---AI/releases/latest"
INSTALLER = "https://getjon.info/install.ps1"

BEFEHLE = [
    ("/api", "Anbieter wählen und API-Schlüssel einmal eingeben"),
    ("/modell", "Modell wechseln"),
    ("/jon", "Verbindung zu Jon prüfen"),
    ("/modus", "vorsichtig · auto · alles (Freigaben)"),
    ("/ziel <Ziel>", "arbeitet selbstständig, bis das Ziel erreicht ist"),
    ("/verbessern", "prüft, bewertet und verbessert das Projekt in Runden"),
    ("/init", "legt JON.md als Projektgedächtnis an"),
    ("/design <Auftrag>", "Oberfläche auf Agentur-Niveau gestalten"),
    ("/spiel <Idee>", "komplettes, spielbares Spiel programmieren"),
    ("/praesentation <Thema>", "PowerPoint oder HTML-Folien erstellen"),
    ("/btw <Frage>", "nebenbei fragen – geht auch, während Jon arbeitet"),
    ("/denken", "sichtbares Nachdenken an/aus (Standard: an)"),
    ("/aufgaben", "aktuelle Aufgabenliste"),
    ("/rueckgaengig", "letzte Dateiänderung zurücknehmen"),
    ("/kompakt", "Verlauf verdichten"),
    ("/neu", "neues Gespräch"),
    ("/fortsetzen", "letztes Gespräch in diesem Ordner fortsetzen"),
    ("/kosten", "Tokens und Dauer dieser Sitzung"),
    ("/update", "auf die neueste Version aktualisieren"),
    ("/hilfe", "diese Übersicht"),
    ("/exit", "beenden"),
]


class Terminal:
    def __init__(self, argumente: argparse.Namespace) -> None:
        self.argumente = argumente
        self.einstellungen = Einstellungen()
        self.jon = Jon()
        self.verbindung = Verbindung(self.einstellungen, self.jon)
        self.ordner = Path(argumente.ordner or os.getcwd()).resolve()
        self.kasten = Werkzeugkasten(self.ordner)
        self.sitzung = Sitzung(self.ordner)
        anbieter, modell = self._startwahl()
        modus = "alles" if argumente.alles else ("auto" if argumente.auto else self.einstellungen.get("modus", "vorsichtig"))
        self.agent = Agent(self.verbindung, self.kasten, self.sitzung, anbieter, modell, modus)
        self.nebenbei = Nebenbei(lambda frage: self.agent.zwischenfrage(frage))
        self.agent.pause = self.nebenbei.pause
        self._strg_c = 0.0

    def _startwahl(self) -> tuple[str, str]:
        if not self.argumente.ohne_jon:
            self.jon.verbinden()
        gewuenscht = self.argumente.anbieter or self.einstellungen.get("anbieter") or ""
        if gewuenscht and gewuenscht in KATALOG and self.verbindung.bereit(gewuenscht) and not (gewuenscht == "jon" and not self.jon.verbunden):
            anbieter = gewuenscht
        elif self.jon.verbunden:
            anbieter = "jon"
        else:
            anbieter = "felworks"
        modell = self.argumente.modell or self.einstellungen.modell(anbieter) or (KATALOG[anbieter].modelle[0] if KATALOG[anbieter].modelle else "")
        if anbieter in ("ollama", "lmstudio") and not modell:
            liste = self.verbindung.modelle(anbieter)
            modell = liste[0] if liste else ""
        return anbieter, modell

    def anzeige_anbieter(self) -> str:
        eintrag = KATALOG[self.agent.anbieter]
        modell = self.agent.modell
        if self.agent.anbieter == "jon":
            modell = f"{self.jon.info.get('anbieter', '')} · {self.jon.info.get('modell', '')}"
        return f(eintrag.name, WEISS, FETT) + f(" · " + modell, GRAU)

    def kopf(self) -> None:
        if self.jon.verbunden:
            jon_text = f("● verbunden", GRUEN) + f(f"  Jon {self.jon.info.get('version', '')} läuft auf diesem PC", GRAU)
        elif self.jon.installiert():
            jon_text = f("○ nicht verbunden", GOLD) + f(f"  {self.jon.grund} – starte Jon, dann /jon", GRAU)
        else:
            jon_text = f("○ eigenständig", GRAU) + f("  (ohne Jon-App – alles Wichtige geht trotzdem)", GRAU, MATT)
        modus = {"vorsichtig": "fragt vor Änderungen", "auto": "ändert Dateien selbst", "alles": "führt alles ohne Rückfrage aus"}[self.agent.modus]
        ui.kopf(VERSION, [
            ("Modell", self.anzeige_anbieter()),
            ("Jon", jon_text),
            ("Ordner", f(str(self.ordner), TUERKIS)),
            ("Modus", f(self.agent.modus, WEISS) + f(f"  {modus}", GRAU)),
        ])
        if self.agent.anbieter == "felworks":
            sag(f("  FelWorks ist kostenlos und braucht keinen Schlüssel. Eigene Schlüssel: /api", GRAU))
        tipp = "Sag einfach, was ich tun soll – z. B. „Bau mir eine moderne Portfolio-Website“ oder „Programmier mir Snake in 3D“."
        sag(f("  " + tipp, GRAU))
        sag(f("  /hilfe zeigt alle Befehle · Strg+C bricht ab", GRAU, MATT))
        sag()
        self._neue_version()

    def _neue_version(self) -> None:
        letzte = float(self.einstellungen.get("versionspruefung") or 0)
        if time.time() - letzte < 6 * 3600 and not self.einstellungen.get("neue_version"):
            return
        try:
            if time.time() - letzte >= 6 * 3600:
                daten = netz.anfrage("GET", GITHUB, kopf={"Accept": "application/vnd.github+json"}, zeit=4).json()
                self.einstellungen.setzen(versionspruefung=time.time(), neue_version=str(daten.get("tag_name") or "").lstrip("v"))
        except Exception:
            self.einstellungen.setzen(versionspruefung=time.time())
            return
        neu = str(self.einstellungen.get("neue_version") or "")
        if neu and _version(neu) > _version(VERSION):
            sag(f(f"  Neue Version {neu} verfügbar – ", GOLD) + f("/update", WEISS, FETT) + f(" installiert sie.", GOLD))
            sag()

    def eingabe(self) -> str | None:
        zeichen = f("› ", GOLD, FETT)
        try:
            zeile = input(zeichen)
        except EOFError:
            return None
        except KeyboardInterrupt:
            jetzt = time.time()
            if jetzt - self._strg_c < 2:
                return None
            self._strg_c = jetzt
            sag()
            sag(f("  Nochmal Strg+C oder /exit zum Beenden.", GRAU))
            return ""
        if zeile.strip() == '"""':
            teile = []
            while True:
                try:
                    weitere = input(f("… ", GRAU))
                except (EOFError, KeyboardInterrupt):
                    break
                if weitere.strip() == '"""':
                    break
                teile.append(weitere)
            return "\n".join(teile)
        while zeile.endswith("\\"):
            try:
                zeile = zeile[:-1] + "\n" + input(f("… ", GRAU))
            except (EOFError, KeyboardInterrupt):
                break
        return zeile

    def laufen(self, erster: str = "") -> None:
        self.kopf()
        if erster:
            self.ausfuehren(erster)
        while True:
            vorgemerkt = self.nebenbei.naechste()
            if vorgemerkt is not None:
                sag(f("› ", GOLD, FETT) + f(vorgemerkt, WEISS) + f("  (vorgemerkt)", GRAU))
            zeile = vorgemerkt if vorgemerkt is not None else self.eingabe()
            if zeile is None:
                break
            text = zeile.strip()
            if not text:
                continue
            if text.startswith("/"):
                weiter = self.befehl(text)
                if weiter is False:
                    break
                if isinstance(weiter, str) and weiter:
                    self.ausfuehren(weiter)
                continue
            if text.lower() in ("exit", "quit", "ende", "beenden"):
                break
            self.ausfuehren(text)
        self.ende()

    def ende(self) -> None:
        self.kasten.aufraeumen()
        self.speichern()
        dauer = int(time.time() - self.sitzung.beginn)
        sag(f(f"  Bis bald! · {dauer // 60} min {dauer % 60} s · {self.sitzung.tokens_ein + self.sitzung.tokens_aus} Tokens", GRAU))

    def ausfuehren(self, text: str) -> str:
        sag()
        try:
            with self.nebenbei.lauschen():
                antwort = self.agent.runde(text)
        except Abbruch:
            sag(f("  ⎿ abgebrochen – sag einfach, wie es weitergehen soll.", GOLD))
            antwort = ""
        except netz.NetzFehler as fehler:
            self._fehler(fehler)
            antwort = ""
        except KeyboardInterrupt:
            sag(f("  ⎿ abgebrochen", GOLD))
            antwort = ""
        sag()
        self.speichern()
        return antwort

    def _fehler(self, fehler: netz.NetzFehler) -> None:
        text = str(fehler)
        if self.agent.anbieter == "felworks" and fehler.status in (401, 403):
            text = "Der freie FelWorks-Zugang hat diese Anfrage nicht angenommen."
        sag(f("  ✕ " + text, ROT))
        if self.agent.anbieter == "felworks":
            if self.verbindung.felworks.fehler:
                sag(f("  " + self.verbindung.felworks.fehler, GRAU))
            sag(f("  Tipp: Mit /api nimmst du einen eigenen Anbieter (z. B. NVIDIA, kostenlos auf build.nvidia.com).", GRAU))
        elif fehler.status in (401, 403):
            sag(f("  Gib mit /api einen neuen Schlüssel ein.", GRAU))
        elif fehler.status in (404,):
            sag(f("  Das Modell gibt es dort nicht. Wähle eins mit /modell.", GRAU))
        else:
            sag(f("  Mit /modell oder /api kannst du ausweichen.", GRAU))

    def speichern(self) -> None:
        if not self.sitzung.nachrichten:
            return
        pfad = ordner() / "sitzungen" / f"{self.sitzung.kennung}.json"
        try:
            schreiben(pfad, json.dumps(self.sitzung.als_dict(), ensure_ascii=False))
        except OSError:
            pass

    def befehl(self, zeile: str):
        teile = zeile.split(maxsplit=1)
        wort = teile[0].lower()
        rest = teile[1].strip() if len(teile) > 1 else ""
        if wort in ("/exit", "/quit", "/ende", "/q"):
            return False
        if wort in ("/hilfe", "/help", "/?"):
            ui.kasten("Befehle", [f(n.ljust(24), GOLD) + f(b, GRAU) for n, b in BEFEHLE], BLAU)
            sag(f("  Mehrere Zeilen: mit \\ am Zeilenende fortsetzen oder zwischen zwei \"\"\" schreiben.", GRAU))
            sag()
            return True
        if wort in ("/api", "/anbieter", "/provider", "/key", "/schluessel"):
            self.api(rest)
            return True
        if wort in ("/modell", "/model", "/models"):
            self.modell(rest)
            return True
        if wort == "/jon":
            self.jon_pruefen()
            return True
        if wort == "/modus":
            self.modus(rest)
            return True
        if wort in ("/neu", "/clear", "/reset"):
            self.speichern()
            self.sitzung = Sitzung(self.ordner)
            self.agent.sitzung = self.sitzung
            self.kasten.aufgabenliste = []
            sag(f("  Neues Gespräch.", GRAU))
            return True
        if wort in ("/kompakt", "/compact"):
            self.agent.verdichten()
            sag(f("  Verlauf verdichtet.", GRAU))
            return True
        if wort in ("/rueckgaengig", "/rückgängig", "/undo"):
            sag(f("  " + self.kasten.rueckgaengig(), GRAU))
            return True
        if wort in ("/aufgaben", "/todo"):
            if self.kasten.aufgabenliste:
                self.agent.aufgaben_zeigen()
            else:
                sag(f("  Gerade gibt es keine Aufgabenliste.", GRAU))
            return True
        if wort in ("/kosten", "/cost", "/status"):
            dauer = int(time.time() - self.sitzung.beginn)
            sag(f(f"  Tokens: {self.sitzung.tokens_ein} rein · {self.sitzung.tokens_aus} raus · Dauer {dauer // 60} min · Verlauf {self.agent.groesse() // 1000} KB", GRAU))
            sag("  " + self.anzeige_anbieter())
            return True
        if wort in ("/btw", "/nebenbei"):
            frage = frage_aus(zeile)
            if not frage:
                sag(f("  So geht's: /btw Was macht die Funktion main? – auch während Jon arbeitet einfach lostippen.", GRAU))
                return True
            try:
                with ui.Kreisel("Jon antwortet nebenbei"):
                    antwort = self.agent.zwischenfrage(frage)
            except netz.NetzFehler as fehler:
                self._fehler(fehler)
                return True
            except KeyboardInterrupt:
                return True
            ui.kasten("Nebenbei", [f(z, WEISS) for z in (antwort.strip() or "Dazu fällt mir gerade nichts ein.").replace("**", "").splitlines()], GOLD)
            return True
        if wort in ("/denken", "/think"):
            self.agent.denken = not self.agent.denken
            sag(f("  Gründliches Nachdenken " + ("an – langsamer, aber gründlicher." if self.agent.denken else "aus – Jon antwortet sofort."), GRAU))
            return True
        if wort in ("/fortsetzen", "/resume", "/weiter"):
            self.fortsetzen()
            return True
        if wort in ("/update", "/aktualisieren"):
            self.update()
            return True
        if wort in ("/version",):
            sag(f(f"  {NAME} {VERSION}", GRAU))
            return True
        if wort == "/init":
            return prompt.INIT_AUFTRAG
        if wort in ("/verbessern", "/improve"):
            return prompt.VERBESSERN_AUFTRAG + (f"\n\nSchwerpunkt: {rest}" if rest else "")
        if wort in ("/ziel", "/goal"):
            if not rest:
                sag(f("  So geht's: /ziel Baue eine Todo-App mit Login und teste alles", GRAU))
                return True
            self.ziel(rest)
            return True
        if wort == "/design":
            return "Gestalte auf dem Niveau einer Top-Design-Agentur (siehe DESIGN-Regeln): " + (rest or "Überarbeite die Oberfläche dieses Projekts komplett, modern und hochwertig.") + " Prüfe das Ergebnis, indem du es baust oder startest."
        if wort in ("/spiel", "/game"):
            idee = rest or "ein eigenes, originelles Arcade-Spiel"
            return f"Programmiere ein komplettes, sofort spielbares Spiel: {idee}. Halte dich an die SPIELE-Regeln (Startbildschirm, Punkte, Highscore, Sound, Partikel, flüssige 60 FPS, Maus/Tastatur/Touch). Lege es in einem eigenen Ordner an und sag mir am Ende, wie ich es starte."
        if wort in ("/praesentation", "/präsentation", "/pptx", "/folien"):
            thema = rest or "ein Thema deiner Wahl"
            if self.jon.verbunden:
                return f"Erstelle mit dem Werkzeug jon eine hochwertige PowerPoint-Präsentation über: {thema}. Mindestens 8 Folien mit Titelfolie, Agenda, Bildern, mindestens einem Diagramm, Übergängen und Fazit. Speichere sie im Ordner {self.ordner} und nenne mir den Pfad."
            return f"Erstelle eine hochwertige PowerPoint-Präsentation (.pptx) über: {thema}. Nutze python-pptx (prüfe mit befehl, ob es installiert ist, sonst pip install python-pptx). Mindestens 8 Folien: Titelfolie, Agenda, Inhaltsfolien mit klarer Kernaussage, ein Diagramm, Fazit; einheitliches modernes Design mit Farbflächen und grossen Überschriften. Speichere sie im Arbeitsordner."
        sag(f(f"  Den Befehl {wort} kenne ich nicht. /hilfe zeigt alle.", GRAU))
        return True

    def api(self, rest: str = "") -> None:
        kennungen = [k for k in KATALOG if k != "jon" or self.jon.verbunden]
        if rest.split()[:1] == ["entfernen"] and len(rest.split()) == 2:
            name = rest.split()[1].lower()
            self.einstellungen.schluessel_setzen(name, "")
            sag(f(f"  Schlüssel für {name} entfernt.", GRAU))
            return
        if rest and rest.lower() in KATALOG:
            wahl = rest.lower()
        else:
            eintraege = []
            for kennung in kennungen:
                eintrag = KATALOG[kennung]
                if kennung == "felworks":
                    stand = f("kostenlos", GRUEN)
                elif kennung == "jon":
                    stand = f("verbunden", GRUEN)
                elif eintrag.braucht_schluessel:
                    stand = f("✓ Schlüssel gespeichert", GRUEN) if self.einstellungen.schluessel(kennung) else f("Schlüssel nötig", GRAU)
                else:
                    stand = f("lokal", GRAU)
                eintraege.append((eintrag.name, f(eintrag.hinweis + " · ", GRAU) + stand if eintrag.hinweis else stand))
            start = kennungen.index(self.agent.anbieter) if self.agent.anbieter in kennungen else 0
            index = ui.waehlen("Welchen Anbieter möchtest du nutzen?", eintraege, start)
            if index is None:
                return
            wahl = kennungen[index]
        eintrag = KATALOG[wahl]
        if eintrag.braucht_schluessel:
            vorhanden = self.einstellungen.schluessel(wahl)
            neu_eingeben = not vorhanden or ui.frage_ja(f"Für {eintrag.name} ist schon ein Schlüssel gespeichert. Neuen eingeben?", False)
            if neu_eingeben:
                if eintrag.seite:
                    sag(f("  Schlüssel bekommst du hier: ", GRAU) + f(eintrag.seite, BLAU))
                while True:
                    try:
                        schluessel = getpass.getpass(f("  API-Schlüssel (wird verschlüsselt gespeichert, Eingabe unsichtbar): ", WEISS)).strip()
                    except (EOFError, KeyboardInterrupt):
                        sag()
                        return
                    if not schluessel:
                        return
                    with ui.Kreisel("prüfe den Schlüssel"):
                        problem = self.verbindung.pruefen(wahl, schluessel)
                    if not problem:
                        self.einstellungen.schluessel_setzen(wahl, schluessel)
                        sag(f("  ✓ Schlüssel gespeichert.", GRUEN))
                        break
                    sag(f("  ✕ " + problem, ROT))
                    if not ui.frage_ja("Nochmal versuchen?", True):
                        return
        if wahl in ("ollama", "lmstudio"):
            with ui.Kreisel("suche lokale Modelle"):
                liste = self.verbindung.modelle(wahl, True)
            if not liste:
                sag(f(f"  {eintrag.name} antwortet nicht. Läuft es? Download: {eintrag.seite}", ROT))
                return
        self.agent.anbieter = wahl
        self.agent.modell = self.einstellungen.modell(wahl) or (eintrag.modelle[0] if eintrag.modelle else "")
        self.modell("", nur_wenn_noetig=bool(self.agent.modell))
        letzte_wahl_speichern(self.einstellungen, wahl, self.agent.modell)
        sag(f("  Jetzt aktiv: ", GRAU) + self.anzeige_anbieter())

    def modell(self, rest: str = "", nur_wenn_noetig: bool = False) -> None:
        anbieter = self.agent.anbieter
        if anbieter == "jon":
            self.agent.modell = "jon"
            if not nur_wenn_noetig:
                sag(f("  Über Jon nutzt das Terminal Jons eingestelltes Modell. Ändern kannst du es in der Jon-App oder hier mit /api.", GRAU))
            return
        with ui.Kreisel("lade Modelle"):
            liste = self.verbindung.modelle(anbieter)
        if rest:
            treffer = next((m for m in liste if m.lower() == rest.lower()), "") or next((m for m in liste if rest.lower() in m.lower()), "") or rest
            self.agent.modell = treffer
            letzte_wahl_speichern(self.einstellungen, anbieter, treffer)
            sag(f("  Modell: ", GRAU) + f(treffer, WEISS, FETT))
            return
        if nur_wenn_noetig and self.agent.modell in liste:
            return
        if not liste:
            sag(f("  Keine Modelle gefunden.", ROT))
            return
        sichtbar = liste[:40]
        start = sichtbar.index(self.agent.modell) if self.agent.modell in sichtbar else 0
        index = ui.waehlen(f"Modell bei {KATALOG[anbieter].name}", [(m, "empfohlen" if m in KATALOG[anbieter].modelle[:1] else "") for m in sichtbar], start)
        if index is None:
            return
        self.agent.modell = sichtbar[index]
        letzte_wahl_speichern(self.einstellungen, anbieter, self.agent.modell)
        sag(f("  Modell: ", GRAU) + f(self.agent.modell, WEISS, FETT))

    def jon_pruefen(self) -> None:
        with ui.Kreisel("suche Jon"):
            ok = self.jon.verbinden(4)
        if ok:
            sag(f(f"  ● Mit Jon {self.jon.info.get('version', '')} verbunden.", GRUEN) + f(" Ich kann ihm jetzt Aufträge geben (Bildschirm, Office, Telegram …).", GRAU))
            if self.agent.anbieter == "felworks" and ui.frage_ja("Jons Modelle und Schlüssel im Terminal nutzen?", True):
                self.agent.anbieter = "jon"
                self.agent.modell = "jon"
                letzte_wahl_speichern(self.einstellungen, "jon", "jon")
        else:
            sag(f(f"  ○ {self.jon.grund}.", GOLD))
            if not self.jon.installiert():
                sag(f("  Jon gibt es kostenlos auf https://getjon.info – das Terminal funktioniert aber auch ohne.", GRAU))

    def modus(self, rest: str) -> None:
        moegliche = {"vorsichtig": "fragt vor jeder Änderung und jedem Befehl", "auto": "ändert Dateien im Projekt und führt normale Befehle selbst aus", "alles": "führt alles ohne Rückfrage aus"}
        if rest.lower() in moegliche:
            wahl = rest.lower()
        else:
            namen = list(moegliche)
            index = ui.waehlen("Wie selbstständig soll ich arbeiten?", [(n, moegliche[n]) for n in namen], namen.index(self.agent.modus))
            if index is None:
                return
            wahl = namen[index]
        self.agent.modus = wahl
        self.einstellungen.setzen(modus=wahl if wahl != "alles" else "auto")
        sag(f(f"  Modus: {wahl} – {moegliche[wahl]}.", GRAU))

    def ziel(self, ziel: str) -> None:
        sag(f("  ◆ Ziel: ", GOLD, FETT) + f(ziel, WEISS))
        auftrag = f"ZIEL: {ziel}\n\nArbeite selbstständig und vollständig daran. Plane mit aufgaben, setze um, teste wirklich und behebe alle Fehler. Frag nur, wenn es gar nicht anders geht."
        for runde in range(1, 13):
            antwort = self.ausfuehren(auftrag)
            if not antwort and not self.sitzung.nachrichten:
                return
            try:
                urteil = self.agent.runde(prompt.ZIEL_PRUEFEN.format(ziel=ziel), still=True)
            except (Abbruch, KeyboardInterrupt):
                sag(f("  ⎿ Ziel-Modus abgebrochen.", GOLD))
                return
            except netz.NetzFehler as fehler:
                self._fehler(fehler)
                return
            zeile = (urteil or "").strip().splitlines()[0] if (urteil or "").strip() else ""
            if zeile.upper().startswith("ZIEL ERREICHT"):
                sag(f("  ✔ " + zeile, GRUEN, FETT))
                return
            sag(f(f"  ↻ Runde {runde}: " + (zeile or "noch nicht fertig"), GOLD))
            auftrag = f"Mach weiter am ZIEL „{ziel}“. Noch offen: {zeile.removeprefix('WEITER:').strip() or 'prüfe selbst, was fehlt'}"
        sag(f("  Nach 12 Runden halte ich an. Sag „weiter“, wenn ich fortfahren soll.", GOLD))

    def fortsetzen(self) -> None:
        kandidaten = []
        for pfad in (ordner() / "sitzungen").glob("*.json"):
            try:
                daten = json.loads(pfad.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if daten.get("ordner") == str(self.ordner) and daten.get("kennung") != self.sitzung.kennung:
                kandidaten.append(daten)
        if not kandidaten:
            sag(f("  Hier gibt es noch kein früheres Gespräch.", GRAU))
            return
        kandidaten.sort(key=lambda d: d.get("zeit", 0), reverse=True)
        eintraege = []
        for daten in kandidaten[:10]:
            erste = next((n.get("content") for n in daten.get("nachrichten", []) if n.get("role") == "user"), "") or ""
            eintraege.append((str(erste)[:70].replace("\n", " "), time.strftime("%d.%m. %H:%M", time.localtime(daten.get("zeit", 0)))))
        index = ui.waehlen("Welches Gespräch fortsetzen?", eintraege)
        if index is None:
            return
        daten = kandidaten[index]
        self.sitzung.kennung = daten["kennung"]
        self.sitzung.nachrichten = daten.get("nachrichten", [])
        self.sitzung.zusammenfassung = daten.get("zusammenfassung", "")
        sag(f(f"  Fortgesetzt ({len(self.sitzung.nachrichten)} Nachrichten).", GRAU))

    def update(self) -> None:
        if sys.platform != "win32":
            sag(f("  Aktualisieren: curl -fsSL https://getjon.info/install.sh | bash", GRAU))
            return
        sag(f("  Lade die neueste Version …", GRAU))
        subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", f"Start-Sleep -Seconds 1; irm {INSTALLER} | iex"], creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
        sag(f("  Das Update läuft in einem neuen Fenster. Starte danach einfach wieder mit „jonh“.", GRAU))
        self.ende()
        raise SystemExit(0)


def _version(text: str) -> tuple:
    teile = []
    for teil in str(text).split("."):
        try:
            teile.append(int("".join(z for z in teil if z.isdigit()) or 0))
        except ValueError:
            teile.append(0)
    return tuple(teile)


def argumente(liste: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="jonh", description="Jon Harness – Jon von FelWorks im Terminal")
    parser.add_argument("frage", nargs="*", help="Erster Auftrag")
    parser.add_argument("-p", "--print", dest="einmal", action="store_true", help="Nur antworten und beenden")
    parser.add_argument("-c", "--weiter", action="store_true", help="Letztes Gespräch fortsetzen")
    parser.add_argument("--anbieter")
    parser.add_argument("--modell")
    parser.add_argument("--ordner")
    parser.add_argument("--auto", action="store_true", help="Dateien und Befehle ohne Rückfrage")
    parser.add_argument("--alles", action="store_true", help="Alles ohne Rückfrage")
    parser.add_argument("--ohne-jon", dest="ohne_jon", action="store_true", help="Nicht mit Jon verbinden")
    parser.add_argument("--version", action="store_true")
    return parser.parse_args(liste)


def main(liste: list[str] | None = None) -> None:
    ui.vorbereiten()
    werte = argumente(liste)
    if werte.version:
        print(f"{NAME} {VERSION}")
        return
    if werte.frage[:1] == ["update"]:
        Terminal(werte).update()
        return
    terminal = Terminal(werte)
    text = " ".join(werte.frage).strip()
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    if werte.weiter:
        terminal.fortsetzen()
    if werte.einmal:
        if not text:
            print("Bitte einen Auftrag angeben, z. B. jonh -p \"Erkläre dieses Projekt\"")
            return
        terminal.ausfuehren(text)
        terminal.speichern()
        return
    try:
        terminal.laufen(text)
    except KeyboardInterrupt:
        terminal.ende()
