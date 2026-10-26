from __future__ import annotations

import json
import re
import time
import uuid
from contextlib import nullcontext
from pathlib import Path

from . import kommentare, netz, oberflaeche as ui, prompt
from .anbieter import Verbindung, protokoll
from .oberflaeche import BLAU, FETT, GOLD, GRAU, GRUEN, MATT, ROT, TUERKIS, WEISS, f, sag
from .werkzeuge import ABGESCHNITTEN, JON_WERKZEUG, SCHEMA, Ergebnis, Werkzeugkasten, args_lesen, ausfuehren, befehl_gefaehrlich, befehl_sicher

MAX_SCHRITTE = 400
KONTEXT_ZEICHEN = 340_000
LESE_WERKZEUGE = {"datei_lesen", "ordner_zeigen", "dateien_finden", "text_suchen", "web_suche", "web_lesen", "aufgaben", "nutzer_fragen"}
TEXT_BLOCK = re.compile(r"```werkzeug\s*(\{.*?\})\s*```", re.S)


class Abbruch(Exception):
    pass


class Sitzung:
    def __init__(self, arbeitsordner: Path) -> None:
        self.kennung = uuid.uuid4().hex[:12]
        self.arbeitsordner = arbeitsordner
        self.nachrichten: list[dict] = []
        self.zusammenfassung = ""
        self.tokens_ein = 0
        self.tokens_aus = 0
        self.beginn = time.time()

    def als_dict(self) -> dict:
        return {"kennung": self.kennung, "ordner": str(self.arbeitsordner), "nachrichten": self.nachrichten, "zusammenfassung": self.zusammenfassung, "zeit": int(time.time())}


class Agent:
    def __init__(self, verbindung: Verbindung, kasten: Werkzeugkasten, sitzung: Sitzung, anbieter: str, modell: str, modus: str = "vorsichtig") -> None:
        self.verbindung = verbindung
        self.kasten = kasten
        self.sitzung = sitzung
        self.anbieter = anbieter
        self.modell = modell
        self.modus = modus
        self.erlaubt_immer: set[str] = set()
        self.denken: bool | None = True
        self.unzensiert = False
        self.letzte_antwort = ""
        self.pause = nullcontext

    def zwischenfrage(self, frage: str) -> str:
        verlauf = []
        for nachricht in self.sitzung.nachrichten[-16:]:
            rolle = nachricht.get("role")
            inhalt = str(nachricht.get("content") or "")
            if rolle == "tool":
                inhalt = "Werkzeugergebnis: " + inhalt[:400]
            elif nachricht.get("tool_calls"):
                inhalt += " [ruft auf: " + ", ".join(str(a.get("function", {}).get("name")) for a in nachricht["tool_calls"]) + "]"
            if inhalt.strip():
                verlauf.append(f"{rolle}: {inhalt[:1500]}")
        teile = [f"Arbeitsordner: {self.kasten.arbeitsordner}"]
        if self.kasten.aufgabenliste:
            teile.append("Aufgaben: " + "; ".join(f"{e['text']} ({e['status']})" for e in self.kasten.aufgabenliste))
        if self.sitzung.zusammenfassung:
            teile.append("Bisher zusammengefasst: " + self.sitzung.zusammenfassung[:2000])
        teile.append("VERLAUF:\n" + "\n".join(verlauf)[-12000:])
        teile.append("ZWISCHENFRAGE: " + frage)
        nachrichten = [{"role": "system", "content": prompt.ZWISCHENFRAGE}, {"role": "user", "content": "\n\n".join(teile)}]
        antwort, _ = self.verbindung.strom(self.anbieter, self.modell, nachrichten, None, False, 700, 0.4)
        stuecke = []
        for ereignis in netz.strom_ereignisse(antwort):
            for wahl in ereignis.get("choices") or []:
                stuecke.append((wahl.get("delta") or {}).get("content") or "")
        return "".join(stuecke)

    def werkzeuge(self) -> list[dict]:
        liste = list(SCHEMA)
        if self.verbindung.jon.verbunden:
            liste.append(JON_WERKZEUG)
        return liste

    def _text_modus(self) -> bool:
        return f"{self.anbieter}|{self.modell}" in self.verbindung.ohne_werkzeuge

    def _system(self) -> dict:
        info = self.verbindung.jon.info if self.verbindung.jon.verbunden else None
        inhalt = prompt.bauen(self.sitzung.arbeitsordner, info, self.werkzeuge() if self._text_modus() else None)
        if self.sitzung.zusammenfassung:
            inhalt += "\n\nBISHERIGER VERLAUF (verdichtet):\n" + self.sitzung.zusammenfassung
        if self.unzensiert and prompt.lokal(self.anbieter, self.modell):
            inhalt += "\n\n" + prompt.UNZENSIERT
        if self.kasten.aufgabenliste:
            inhalt += "\n\nAKTUELLE AUFGABENLISTE:\n" + "\n".join(f"- [{e['status']}] {e['text']}" for e in self.kasten.aufgabenliste)
        return {"role": "system", "content": inhalt}

    def groesse(self) -> int:
        return sum(len(json.dumps(n, ensure_ascii=False)) for n in self.sitzung.nachrichten)

    def runde(self, text: str, still: bool = False) -> str:
        self.sitzung.nachrichten.append({"role": "user", "content": text})
        return self._schleife(still)

    def weiter(self, still: bool = False) -> str:
        return self._schleife(still)

    def _schleife(self, still: bool = False) -> str:
        antwort_gesamt = ""
        for schritt in range(MAX_SCHRITTE):
            if self.groesse() > KONTEXT_ZEICHEN:
                self.verdichten()
            inhalt, aufrufe, grund = self._modell_aufruf(still)
            antwort_gesamt = inhalt or antwort_gesamt
            if not aufrufe:
                self.letzte_antwort = inhalt
                return inhalt
            for aufruf in aufrufe:
                ergebnis = self._werkzeug(aufruf["name"], aufruf["args"])
                if aufruf["name"] in ("datei_schreiben", "datei_anhaengen") and ergebnis.ok and self._ohne_kommentare():
                    self._kommentare_entfernen(str(aufruf["args"].get("pfad") or ""), ergebnis)
                if aufruf["args"].get("_abgeschnitten") and ergebnis.ok:
                    ergebnis.text += "\n" + ABGESCHNITTEN + "\n".join(str(aufruf["args"].get("inhalt", "")).splitlines()[-30:])
                if self._text_modus() or aufruf.get("text"):
                    self.sitzung.nachrichten.append({"role": "user", "content": f"Ergebnis von {aufruf['name']}:\n{ergebnis.text[:20000]}"})
                else:
                    self.sitzung.nachrichten.append({"role": "tool", "tool_call_id": aufruf["id"], "content": ergebnis.text[:20000]})
        sag(f("  Ich habe die Höchstzahl an Schritten erreicht. Sag „weiter“, dann mache ich weiter.", GOLD))
        return antwort_gesamt

    def _modell_aufruf(self, still: bool) -> tuple[str, list[dict], str]:
        nachrichten = [self._system(), *self.sitzung.nachrichten]
        werkzeuge = None if self._text_modus() else self.werkzeuge()
        kreisel = ui.Kreisel("Jon denkt")
        if not still:
            kreisel.start()
        beginn = time.time()
        try:
            antwort, mit_werkzeugen = self.verbindung.strom(self.anbieter, self.modell, nachrichten, werkzeuge, self.denken)
        except KeyboardInterrupt:
            kreisel.stopp()
            raise Abbruch()
        except netz.NetzFehler as fehler:
            kreisel.stopp()
            raise
        inhalt: list[str] = []
        aufrufe: dict[int, dict] = {}
        darstellung = ui.Markdown()
        begonnen = False
        denken_zeichen = 0
        gedanken_zeile = ""
        gedanken_kopf = False
        grund = ""

        def gedanken_ausgeben(text: str, ende: bool = False) -> None:
            nonlocal gedanken_zeile, gedanken_kopf
            if still or self._text_modus():
                return
            gedanken_zeile += text
            if not gedanken_kopf and gedanken_zeile.strip():
                kreisel.stopp()
                sag(f("  ∴ Jon denkt nach", GRAU, MATT))
                gedanken_kopf = True
            while "\n" in gedanken_zeile or len(gedanken_zeile) > 110 or (ende and gedanken_zeile):
                if "\n" in gedanken_zeile and gedanken_zeile.index("\n") <= 110:
                    zeile, gedanken_zeile = gedanken_zeile.split("\n", 1)
                elif len(gedanken_zeile) > 110:
                    schnitt = gedanken_zeile.rfind(" ", 0, 110)
                    schnitt = schnitt if schnitt > 40 else 110
                    zeile, gedanken_zeile = gedanken_zeile[:schnitt], gedanken_zeile[schnitt:].lstrip()
                else:
                    zeile, gedanken_zeile = gedanken_zeile, ""
                if zeile.strip():
                    sag(f("    " + zeile.rstrip(), GRAU, MATT))
        try:
            for ereignis in netz.strom_ereignisse(antwort):
                nutzung = ereignis.get("usage")
                if isinstance(nutzung, dict):
                    self.sitzung.tokens_ein += int(nutzung.get("prompt_tokens") or 0)
                    self.sitzung.tokens_aus += int(nutzung.get("completion_tokens") or 0)
                for wahl in ereignis.get("choices") or []:
                    delta = wahl.get("delta") or {}
                    grund = wahl.get("finish_reason") or grund
                    gedanke = delta.get("reasoning_content") or delta.get("reasoning")
                    if gedanke:
                        denken_zeichen += len(gedanke)
                        kreisel.zusatz = f"denkt nach ({denken_zeichen} Zeichen)"
                        gedanken_ausgeben(gedanke)
                    stueck = delta.get("content")
                    if stueck:
                        inhalt.append(stueck)
                        if not still and not self._text_modus():
                            if not begonnen and "".join(inhalt).strip():
                                kreisel.stopp()
                                if gedanken_kopf:
                                    gedanken_ausgeben("", True)
                                    sag()
                                begonnen = True
                                darstellung.vorsatz = f("● ", GOLD)
                                stueck = "".join(inhalt).lstrip()
                            if begonnen:
                                darstellung.zufuehren(stueck)
                    for teil in delta.get("tool_calls") or []:
                        index = int(teil.get("index") or 0)
                        platz = aufrufe.setdefault(index, {"id": "", "name": "", "args": ""})
                        if teil.get("id"):
                            platz["id"] = teil["id"]
                        funktion = teil.get("function") or {}
                        if funktion.get("name"):
                            platz["name"] += funktion["name"]
                        if funktion.get("arguments"):
                            platz["args"] += funktion["arguments"]
        except KeyboardInterrupt:
            kreisel.stopp()
            antwort.schliessen()
            text = "".join(inhalt)
            if text:
                self.sitzung.nachrichten.append({"role": "assistant", "content": text + "\n[vom Nutzer abgebrochen]"})
            raise Abbruch()
        finally:
            kreisel.stopp()
        darstellung.ende()
        text = "".join(inhalt)
        if self._text_modus():
            return self._text_auswerten(text, still)
        liste = []
        for index, platz in sorted(aufrufe.items()):
            if not platz["name"]:
                continue
            gelesen = args_lesen(platz["args"])
            roh = json.dumps({k: v for k, v in gelesen.items() if not k.startswith("_")}, ensure_ascii=False) if gelesen.get("_repariert") else platz["args"] or "{}"
            liste.append({"id": platz["id"] or f"aufruf_{index}_{uuid.uuid4().hex[:6]}", "name": platz["name"], "args": gelesen, "roh": roh})
        nachricht: dict = {"role": "assistant", "content": text or None}
        if liste:
            nachricht["tool_calls"] = [{"id": a["id"], "type": "function", "function": {"name": a["name"], "arguments": a["roh"]}} for a in liste]
        if text or liste:
            self.sitzung.nachrichten.append(nachricht)
        protokoll({"art": "modell", "anbieter": self.anbieter, "modell": self.modell, "dauer": round(time.time() - beginn, 2), "werkzeuge": [a["name"] for a in liste]})
        if not text and not liste:
            sag(f("  Das Modell hat nichts geantwortet. Versuch es noch einmal oder wechsle mit /modell.", GRAU))
        return text, liste, grund

    def _ohne_kommentare(self) -> bool:
        return kommentare.gewuenscht(*[str(n.get("content") or "") for n in self.sitzung.nachrichten if n.get("role") == "user"])

    def _kommentare_entfernen(self, pfad: str, ergebnis: Ergebnis) -> None:
        try:
            ziel = self.kasten.pfad(pfad)
            text = ziel.read_text(encoding="utf-8")
            sauber = kommentare.entfernen(str(ziel), text)
            if sauber != text:
                ziel.write_text(sauber, encoding="utf-8", newline="")
                self.kasten.gelesen[str(ziel)] = ziel.stat().st_mtime
                ergebnis.text += "\nKommentare wurden entfernt, wie gewünscht."
        except (OSError, ValueError):
            pass

    def _text_auswerten(self, text: str, still: bool) -> tuple[str, list[dict], str]:
        treffer = TEXT_BLOCK.search(text)
        sichtbar = TEXT_BLOCK.sub("", text).strip()
        if sichtbar and not still:
            darstellung = ui.Markdown(vorsatz=f("● ", GOLD))
            darstellung.zufuehren(sichtbar + "\n")
            darstellung.ende()
        self.sitzung.nachrichten.append({"role": "assistant", "content": text})
        if not treffer:
            return sichtbar, [], "stop"
        try:
            daten = json.loads(treffer.group(1))
        except ValueError:
            return sichtbar, [], "stop"
        return sichtbar, [{"id": "", "name": str(daten.get("name") or ""), "args": daten.get("args") or {}, "text": True}], "tool_calls"

    def _freigabe(self, name: str, args: dict) -> bool:
        if name in LESE_WERKZEUGE or self.modus == "alles":
            return True
        if name == "jon":
            if "jon" in self.erlaubt_immer or self.modus == "auto":
                return True
        elif name in ("datei_schreiben", "datei_bearbeiten", "datei_anhaengen"):
            ziel = self.kasten.pfad(str(args.get("pfad") or ""))
            if self.modus == "auto" and self.kasten.im_arbeitsordner(ziel):
                return True
            if "dateien" in self.erlaubt_immer and self.kasten.im_arbeitsordner(ziel):
                return True
        elif name == "befehl":
            befehl = str(args.get("befehl") or "")
            kopf = befehl.strip().split()[0].lower() if befehl.strip() else ""
            if befehl_gefaehrlich(befehl):
                sag(f("  ⚠ Dieser Befehl kann Daten zerstören oder das System verändern.", ROT, FETT))
            elif befehl_sicher(befehl) or self.modus == "auto" or kopf in self.erlaubt_immer:
                return True
        frage = f("  Erlauben? ", WEISS, FETT) + f("[j] ja  [i] immer  [n] nein  [a] alles in dieser Sitzung ", GRAU)
        while True:
            try:
                with self.pause():
                    antwort = input(frage).strip().lower()
            except EOFError:
                return False
            if antwort in ("", "j", "y", "ja"):
                return True
            if antwort in ("i", "immer"):
                if name in ("datei_schreiben", "datei_bearbeiten", "datei_anhaengen"):
                    self.erlaubt_immer.add("dateien")
                elif name == "befehl":
                    kopf = str(args.get("befehl") or "").strip().split()
                    if kopf:
                        self.erlaubt_immer.add(kopf[0].lower())
                else:
                    self.erlaubt_immer.add(name)
                return True
            if antwort in ("a", "alles"):
                self.modus = "alles"
                sag(f("  Alles erlaubt bis zum Ende dieser Sitzung (/modus vorsichtig schaltet zurück).", GOLD))
                return True
            if antwort in ("n", "nein", "no"):
                return False

    def _werkzeug(self, name: str, args: dict) -> Ergebnis:
        self._ankuendigen(name, args)
        if name == "nutzer_fragen":
            return self._fragen(args)
        if not self._freigabe(name, args):
            sag(f("  ⎿ abgelehnt", ROT))
            return Ergebnis("Der Nutzer hat diese Aktion abgelehnt. Frag nach, was er stattdessen möchte, oder nimm einen anderen Weg.", False)
        beginn = time.time()
        if name == "jon":
            if not self.verbindung.jon.verbunden:
                return Ergebnis("Jon ist nicht verbunden.", False)
            kreisel = ui.Kreisel("Jon arbeitet")
            kreisel.start()
            try:
                text = self.verbindung.jon.auftrag(str(args.get("auftrag") or ""), str(self.sitzung.arbeitsordner), lambda s: setattr(kreisel, "zusatz", s[:60]))
                ergebnis = Ergebnis(text, True, "erledigt")
            except Exception as fehler:
                ergebnis = Ergebnis(f"Jon konnte den Auftrag nicht ausführen: {fehler}", False)
            finally:
                kreisel.stopp()
        else:
            kreisel = ui.Kreisel("läuft") if name in ("befehl", "web_suche", "web_lesen") else None
            if kreisel:
                kreisel.start()
            try:
                ergebnis = ausfuehren(self.kasten, name, args)
            except KeyboardInterrupt:
                ergebnis = Ergebnis("Vom Nutzer abgebrochen.", False)
            finally:
                if kreisel:
                    kreisel.stopp()
        self._ergebnis_zeigen(name, ergebnis, time.time() - beginn)
        protokoll({"art": "werkzeug", "name": name, "ok": ergebnis.ok, "dauer": round(time.time() - beginn, 2)})
        return ergebnis

    def _ankuendigen(self, name: str, args: dict) -> None:
        pfad = str(args.get("pfad") or "")
        texte = {
            "datei_lesen": ("Liest", pfad),
            "datei_schreiben": ("Schreibt", pfad),
            "datei_anhaengen": ("Schreibt weiter an", pfad),
            "datei_bearbeiten": ("Bearbeitet", pfad),
            "ordner_zeigen": ("Schaut in", pfad or "."),
            "dateien_finden": ("Sucht Dateien", str(args.get("muster") or "")),
            "text_suchen": ("Durchsucht", str(args.get("muster") or "")),
            "befehl": ("Führt aus", str(args.get("befehl") or "")),
            "web_suche": ("Sucht im Web", str(args.get("anfrage") or "")),
            "web_lesen": ("Liest Webseite", str(args.get("url") or "")),
            "aufgaben": ("Plant", ""),
            "jon": ("Auftrag an Jon", str(args.get("auftrag") or "")),
            "nutzer_fragen": ("Frage", ""),
        }
        verb, ziel = texte.get(name, (name, json.dumps(args, ensure_ascii=False)[:80]))
        if name == "aufgaben":
            return
        zeile = f("● ", BLAU) + f(verb, FETT, WEISS) + (f(" " + ziel[:140], TUERKIS) if ziel else "")
        sag(zeile)
        if name == "datei_schreiben":
            alt, neu = self.kasten.vorschau_schreiben(pfad, str(args.get("inhalt") or ""))
            if alt:
                ui.diff_zeigen(alt, neu, pfad)
            else:
                zeilen = neu.splitlines()
                for zeile_text in zeilen[:14]:
                    sag("    " + f(zeile_text[:150], GRUEN))
                if len(zeilen) > 14:
                    sag("    " + f(f"… {len(zeilen) - 14} weitere Zeilen", GRAU))
        elif name == "datei_bearbeiten":
            vorher, nachher, fehler = self.kasten.vorschau_bearbeiten(pfad, str(args.get("alt") or ""), str(args.get("neu") or ""), bool(args.get("alle")))
            if not fehler:
                ui.diff_zeigen(vorher, nachher, pfad)

    def _ergebnis_zeigen(self, name: str, ergebnis: Ergebnis, dauer: float) -> None:
        if name == "aufgaben":
            self.aufgaben_zeigen()
            return
        farbe = GRUEN if ergebnis.ok else ROT
        kurz = ergebnis.kurz or ("ok" if ergebnis.ok else "Fehler")
        zeit = f" · {dauer:.1f} s" if dauer >= 1 else ""
        sag("  " + f("⎿ ", GRAU) + f(kurz, farbe) + f(zeit, GRAU))
        if name == "befehl":
            zeilen = [z for z in ergebnis.text.splitlines()[1:] if z.strip()]
            for zeile in zeilen[:8]:
                sag("    " + f(zeile[:160], GRAU))
            if len(zeilen) > 8:
                sag("    " + f(f"… {len(zeilen) - 8} weitere Zeilen", GRAU, MATT))
        elif not ergebnis.ok:
            sag("    " + f(ergebnis.text.splitlines()[0][:200] if ergebnis.text else "", ROT))
        elif name == "jon":
            darstellung = ui.Markdown("    ")
            darstellung.zufuehren(ergebnis.text[:3000] + "\n")
            darstellung.ende()

    def aufgaben_zeigen(self) -> None:
        if not self.kasten.aufgabenliste:
            return
        sag(f("● ", BLAU) + f("Aufgaben", FETT, WEISS))
        for eintrag in self.kasten.aufgabenliste:
            if eintrag["status"] == "fertig":
                sag("    " + f("✔ ", GRUEN) + f(eintrag["text"], GRAU, MATT))
            elif eintrag["status"] == "aktiv":
                sag("    " + f("▶ ", GOLD) + f(eintrag["text"], WEISS, FETT))
            else:
                sag("    " + f("○ ", GRAU) + f(eintrag["text"], WEISS))

    def _fragen(self, args: dict) -> Ergebnis:
        frage = str(args.get("frage") or "")
        optionen = [str(o) for o in (args.get("optionen") or []) if str(o).strip()][:8]
        sag(f("  ? ", GOLD, FETT) + f(frage, WEISS, FETT))
        with self.pause():
            if optionen:
                wahl = ui.waehlen("Deine Antwort", [(o, "") for o in optionen] + [("Etwas anderes eingeben", "")])
                if wahl is not None and wahl < len(optionen):
                    return Ergebnis(f"Der Nutzer antwortet: {optionen[wahl]}", True, optionen[wahl])
            try:
                antwort = input(f("  › ", GOLD)).strip()
            except EOFError:
                antwort = ""
        return Ergebnis(f"Der Nutzer antwortet: {antwort or '(keine Antwort, entscheide selbst sinnvoll)'}", True, antwort[:60] or "keine Antwort")

    def verdichten(self, still: bool = False) -> None:
        if len(self.sitzung.nachrichten) < 6:
            return
        behalten = 8
        alt = self.sitzung.nachrichten[:-behalten]
        rest = self.sitzung.nachrichten[-behalten:]
        while rest and rest[0].get("role") == "tool":
            alt.append(rest.pop(0))
        verlauf = []
        for nachricht in alt:
            rolle = nachricht.get("role")
            inhalt = nachricht.get("content") or ""
            if nachricht.get("tool_calls"):
                inhalt += " " + "; ".join(f"{a['function']['name']}({a['function']['arguments'][:300]})" for a in nachricht["tool_calls"])
            verlauf.append(f"{rolle}: {str(inhalt)[:3000]}")
        if not still:
            sag(f("  ↻ Verdichte den bisherigen Verlauf …", GRAU))
        auftrag = [
            {"role": "system", "content": "Fasse den folgenden Arbeitsverlauf eines Coding-Agenten so zusammen, dass er nahtlos weiterarbeiten kann: Ziel des Nutzers, getroffene Entscheidungen, geänderte Dateien, wichtige Befunde, offene Punkte. Stichpunkte, höchstens 600 Wörter."},
            {"role": "user", "content": (self.sitzung.zusammenfassung + "\n\n" if self.sitzung.zusammenfassung else "") + "\n".join(verlauf)[-120000:]},
        ]
        try:
            antwort, _ = self.verbindung.strom(self.anbieter, self.modell, auftrag, None, False, 2000, 0.2)
            teile = []
            for ereignis in netz.strom_ereignisse(antwort):
                for wahl in ereignis.get("choices") or []:
                    teile.append((wahl.get("delta") or {}).get("content") or "")
            zusammenfassung = "".join(teile).strip()
        except Exception:
            zusammenfassung = "\n".join(verlauf)[-6000:]
        if zusammenfassung:
            self.sitzung.zusammenfassung = zusammenfassung
            while rest and rest[0].get("role") != "user":
                rest.pop(0)
            self.sitzung.nachrichten = rest
