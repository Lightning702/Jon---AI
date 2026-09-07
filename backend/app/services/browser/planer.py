from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from app.services.browser.sicherheit import (
    AENDERUNGS_WOERTER,
    EINGABE,
    EXTERNE_AENDERUNG,
    HOCH,
    KAUF,
    KAUF_WOERTER,
    LESEN,
    LOESCH_WOERTER,
    LOESCHEN,
    MITTEL,
    NAVIGIEREN,
    NIEDRIG,
    RANG,
    SENDE_WOERTER,
)

PLAN_AUSLOESER = (
    "bestell",
    "kauf",
    "buch",
    "reservier",
    "abo",
    "abonnement",
    "vertrag",
    "bezahl",
    "zahlung",
    "ueberweis",
    "überweis",
    "warenkorb",
    "checkout",
    "kasse",
    "formular",
    "ausfuell",
    "ausfüll",
    "anmeld",
    "registrier",
    "account",
    "konto",
    "loesch",
    "lösch",
    "senden",
    "schreib eine nachricht",
    "kommentar",
    "bewerb",
)

MEHRSCHRITT_AUSLOESER = (
    "vergleich",
    "und dann",
    "danach",
    "anschliessend",
    "anschließend",
    "beste",
    "billigste",
    "guenstigste",
    "günstigste",
    "mehrere",
    "alle ",
    "sammle",
    "recherchier",
    "finde heraus",
    "such und",
    "pruef",
    "prüf",
)

ARTEN = (LESEN, NAVIGIEREN, EINGABE, EXTERNE_AENDERUNG, KAUF, LOESCHEN)


@dataclass
class PlanSchritt:
    id: int
    beschreibung: str
    art: str = NAVIGIEREN
    risiko: str = NIEDRIG

    @property
    def bestaetigung_noetig(self) -> bool:
        return self.risiko == HOCH

    def als_dict(self) -> dict:
        return {
            "id": self.id,
            "beschreibung": self.beschreibung,
            "art": self.art,
            "risiko": self.risiko,
            "bestaetigung_noetig": self.bestaetigung_noetig,
        }


@dataclass
class BrowserPlan:
    ziel: str
    schritte: list[PlanSchritt] = field(default_factory=list)
    aktueller_schritt: int = 0
    status: str = "geplant"
    grund: str = ""

    @property
    def risiko(self) -> str:
        hoechste = NIEDRIG
        for schritt in self.schritte:
            if RANG[schritt.risiko] > RANG[hoechste]:
                hoechste = schritt.risiko
        return hoechste

    @property
    def kritische_schritte(self) -> list[int]:
        return [s.id for s in self.schritte if s.risiko == HOCH]

    @property
    def bestaetigung_noetig(self) -> bool:
        return bool(self.kritische_schritte)

    def als_dict(self) -> dict:
        return {
            "ziel": self.ziel,
            "schritte": [s.als_dict() for s in self.schritte],
            "aktueller_schritt": self.aktueller_schritt,
            "risiko": self.risiko,
            "bestaetigung_noetig": self.bestaetigung_noetig,
            "kritische_schritte": self.kritische_schritte,
            "geschaetzte_tool_calls": max(2, len(self.schritte) * 2),
            "status": self.status,
            "grund": self.grund,
        }

    def als_text(self) -> str:
        zeilen = [f"Ziel: {self.ziel}"]
        for schritt in self.schritte:
            marke = " [BESTAETIGUNG NOETIG]" if schritt.bestaetigung_noetig else ""
            zeilen.append(
                f"{schritt.id}. {schritt.beschreibung} "
                f"({schritt.art}, Risiko {schritt.risiko}){marke}"
            )
        return "\n".join(zeilen)


def braucht_plan(auftrag: str, modus: str = "auto") -> tuple[bool, str]:
    wahl = (modus or "auto").strip().lower()
    if wahl == "immer":
        return True, "Planmodus ist auf 'immer' gestellt."
    if wahl in ("aus", "off", "nie"):
        return False, "Planmodus ist ausgeschaltet."
    text = (auftrag or "").lower()
    for wort in PLAN_AUSLOESER:
        if wort in text:
            return True, f"Der Auftrag enthaelt '{wort}' und kann etwas veraendern."
    treffer = [w for w in MEHRSCHRITT_AUSLOESER if w in text]
    if len(treffer) >= 1 and len(text.split()) > 8:
        return True, "Mehrstufige Aufgabe ueber mehrere Seiten."
    if len(text.split()) > 28:
        return True, "Langer, zusammengesetzter Auftrag."
    return False, "Einfache Aufgabe - direkt ausfuehrbar."


def schritt_risiko(beschreibung: str) -> tuple[str, str]:
    text = (beschreibung or "").lower()
    for wort in KAUF_WOERTER:
        if wort in text:
            return HOCH, KAUF
    for wort in LOESCH_WOERTER:
        if wort in text:
            return HOCH, LOESCHEN
    for wort in SENDE_WOERTER:
        if wort in text:
            return HOCH, EXTERNE_AENDERUNG
    for wort in ("bestellung", "bestellen", "kaufen", "buchen", "bezahlen", "abschicken"):
        if wort in text:
            return HOCH, KAUF
    for wort in AENDERUNGS_WOERTER:
        if wort in text:
            return MITTEL, EINGABE
    for wort in ("eingeben", "eintragen", "ausfuellen", "ausfüllen", "auswaehlen", "auswählen", "filter"):
        if wort in text:
            return MITTEL, EINGABE
    for wort in ("lesen", "pruefen", "prüfen", "vergleichen", "ansehen", "auslesen"):
        if wort in text:
            return NIEDRIG, LESEN
    return NIEDRIG, NAVIGIEREN


def _json_block(text: str) -> dict | None:
    roh = (text or "").strip()
    if roh.startswith("```"):
        roh = re.sub(r"^```[a-zA-Z]*\s*", "", roh)
        roh = re.sub(r"```\s*$", "", roh).strip()
    start = roh.find("{")
    ende = roh.rfind("}")
    if start < 0 or ende <= start:
        return None
    try:
        daten = json.loads(roh[start : ende + 1])
    except Exception:
        return None
    return daten if isinstance(daten, dict) else None


def _kritischen_schritt_ergaenzen(plan: BrowserPlan, auftrag: str) -> BrowserPlan:
    risiko, art = schritt_risiko(auftrag)
    if risiko != HOCH or plan.kritische_schritte:
        return plan
    nummer = len(plan.schritte) + 1
    plan.schritte.insert(
        max(0, nummer - 2),
        PlanSchritt(
            0,
            "Kritischen Schritt vorbereiten und vom Nutzer bestaetigen lassen: "
            + auftrag.strip()[:120],
            art,
            HOCH,
        ),
    )
    for stelle, schritt in enumerate(plan.schritte, start=1):
        schritt.id = stelle
    return plan


def _ersatzplan(auftrag: str, grund: str) -> BrowserPlan:
    schritte = [
        "Passende Website oeffnen",
        "Seite lesen und Aufbau verstehen",
        "Cookie- oder Consent-Hinweis datensparsam wegklicken",
        "Suchfunktion nutzen und Treffer pruefen",
        "Relevante Angaben (Preis, Verfuegbarkeit, Bedingungen) pruefen",
        "Ergebnis dem Nutzer berichten",
    ]
    plan = BrowserPlan(ziel=auftrag.strip()[:200], grund=grund)
    for nummer, text in enumerate(schritte, start=1):
        risiko, art = schritt_risiko(text)
        plan.schritte.append(PlanSchritt(nummer, text, art, risiko))
    return _kritischen_schritt_ergaenzen(plan, auftrag)


PLAN_SYSTEM = (
    "Du planst Browser-Aufgaben fuer den Assistenten Jon. Du fuehrst nichts aus, "
    "du planst nur. Antworte ausschliesslich mit JSON in genau dieser Form:\n"
    '{"ziel": "...", "schritte": [{"beschreibung": "...", "art": "lesen|navigieren|'
    'eingabe|externe_aenderung|kauf|loeschen"}]}\n'
    "Regeln: 3 bis 9 Schritte, jeder Schritt ist eine konkrete Handlung im Browser. "
    "Keine Website-spezifischen CSS-Selektoren. Denk an Cookie-Dialoge, Suche, "
    "Ergebnispruefung und den Bericht an den Nutzer. Ein Plan ist KEINE Erlaubnis: "
    "kostenpflichtige, sendende oder loeschende Schritte markierst du ehrlich mit "
    "der passenden art."
)


async def plan_bauen(auftrag: str, grund: str = "") -> BrowserPlan:
    from app.services.llm import complete

    try:
        antwort = await complete(
            PLAN_SYSTEM,
            f"Auftrag des Nutzers: {auftrag}",
            max_tokens=900,
            temperature=0.2,
        )
    except Exception:
        return _ersatzplan(auftrag, grund)
    daten = _json_block(antwort)
    if not daten or not isinstance(daten.get("schritte"), list):
        return _ersatzplan(auftrag, grund)
    plan = BrowserPlan(ziel=str(daten.get("ziel") or auftrag)[:200], grund=grund)
    for nummer, eintrag in enumerate(daten["schritte"][:9], start=1):
        if isinstance(eintrag, dict):
            beschreibung = str(eintrag.get("beschreibung", "")).strip()
            gemeldet = str(eintrag.get("art", "")).strip().lower()
        else:
            beschreibung = str(eintrag).strip()
            gemeldet = ""
        if not beschreibung:
            continue
        risiko, art = schritt_risiko(beschreibung)
        if gemeldet in ARTEN:
            gemeldetes_risiko = (
                HOCH
                if gemeldet in (KAUF, LOESCHEN, EXTERNE_AENDERUNG)
                else MITTEL
                if gemeldet == EINGABE
                else NIEDRIG
            )
            if RANG[gemeldetes_risiko] > RANG[risiko]:
                risiko, art = gemeldetes_risiko, gemeldet
        plan.schritte.append(PlanSchritt(nummer, beschreibung[:200], art, risiko))
    if not plan.schritte:
        return _ersatzplan(auftrag, grund)
    return _kritischen_schritt_ergaenzen(plan, auftrag)
