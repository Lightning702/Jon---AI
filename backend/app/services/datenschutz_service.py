from __future__ import annotations

import re
from dataclasses import dataclass

OEFFENTLICH = "oeffentlich"
PERSOENLICH = "persoenlich"
GEHEIM = "geheim"

RANG = {OEFFENTLICH: 0, PERSOENLICH: 1, GEHEIM: 2}

GEHEIM_MUSTER = (
    (re.compile(r"(?i)\b(sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,})"), "API-Schluessel"),
    (
        re.compile(
            r"(?i)\b(passwor[dt]|kennwort|passphrase)\b\s*(?:[:=]|ist|lautet)\s*\S+"
        ),
        "Passwort",
    ),
    (re.compile(r"\bey[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}"), "Token"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "Kartennummer"),
    (re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,28}\b"), "IBAN"),
    (re.compile(r"(?i)\b(cvv|cvc|pin)\s*[:=]?\s*\d{3,6}\b"), "Sicherheitscode"),
    (re.compile(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----"), "Privater Schluessel"),
)

PERSOENLICH_MUSTER = (
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}"), "E-Mail-Adresse"),
    (re.compile(r"(?<!\d)(?:\+\d{1,3}[ /-]?)?(?:\(?\d{2,5}\)?[ /-]?){2,4}\d{2,}(?!\d)"), "Telefonnummer"),
    (re.compile(r"(?i)\b\d{4,5}\s+[A-ZÄÖÜ][a-zäöüß]{2,}\b"), "Anschrift"),
    (re.compile(r"(?i)\b(geburtstag|geburtsdatum)\b"), "Geburtsdatum"),
    (re.compile(r"(?i)\b(krank|diagnose|medikament|arztbrief|befund)\b"), "Gesundheitsdaten"),
    (re.compile(r"(?i)\b(gehalt|lohn|kontostand|schulden)\b"), "Finanzdaten"),
)

AUSGEHENDE_TOOLS = {
    "send_mail",
    "send_friend_message",
    "telegram_send",
    "http_get",
    "download_file",
    "web_search",
    "browser_fill",
    "browser_task",
    "create_image",
    "learn_document",
}

LOKALE_PROVIDER = ("ollama", "lmstudio")


@dataclass
class Befund:
    stufe: str
    funde: list[str]

    @property
    def heikel(self) -> bool:
        return RANG[self.stufe] >= RANG[PERSOENLICH]

    def als_dict(self) -> dict:
        return {"stufe": self.stufe, "funde": self.funde, "heikel": self.heikel}


def einstufen(text: str) -> Befund:
    inhalt = str(text or "")
    funde: list[str] = []
    stufe = OEFFENTLICH
    for muster, name in GEHEIM_MUSTER:
        if muster.search(inhalt):
            stufe = GEHEIM
            if name not in funde:
                funde.append(name)
    if stufe != GEHEIM:
        for muster, name in PERSOENLICH_MUSTER:
            if muster.search(inhalt):
                stufe = PERSOENLICH
                if name not in funde:
                    funde.append(name)
    return Befund(stufe, funde)


def maskieren(text: str) -> str:
    inhalt = str(text or "")
    for muster, name in GEHEIM_MUSTER:
        inhalt = muster.sub(f"[{name} entfernt]", inhalt)
    return inhalt


def _regel() -> str:
    try:
        from app.services.settings_service import get_settings_service

        return str(
            get_settings_service().get().get("datenschutz_regel", "warnen")
        ).strip().lower()
    except Exception:
        return "warnen"


def darf_raus(werkzeug: str, args: dict, provider: str = "") -> tuple[bool, str, dict]:
    if werkzeug not in AUSGEHENDE_TOOLS:
        return True, "", {}
    if provider and provider.lower() in LOKALE_PROVIDER:
        return True, "", {}
    text = " ".join(str(w) for w in (args or {}).values() if isinstance(w, (str, int)))
    befund = einstufen(text)
    if befund.stufe == OEFFENTLICH:
        return True, "", befund.als_dict()
    regel = _regel()
    if befund.stufe == GEHEIM and regel != "erlauben":
        return (
            False,
            "Da stehen Zugangsdaten oder Zahlungsangaben drin ("
            + ", ".join(befund.funde)
            + "). Jon schickt so etwas nicht nach aussen. Nimm die Daten raus oder "
            "erledige den Schritt selbst.",
            befund.als_dict(),
        )
    if regel == "streng" and befund.heikel:
        return (
            False,
            "Diese Angabe ist persoenlich ("
            + ", ".join(befund.funde)
            + ") und die Einstellung steht auf streng. Jon schickt sie nicht raus.",
            befund.als_dict(),
        )
    if befund.heikel:
        return (
            True,
            "Achtung: Hier gehen persoenliche Angaben nach aussen ("
            + ", ".join(befund.funde)
            + "). Sag dem Nutzer kurz Bescheid.",
            befund.als_dict(),
        )
    return True, "", befund.als_dict()
