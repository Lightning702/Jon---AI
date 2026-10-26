from __future__ import annotations

import asyncio
import re

STANDARD = "Neue Unterhaltung"
LAENGE = 60

GRUSS = re.compile(
    r"^\s*(hallo|hi|hey|servus|moin|guten\s+(morgen|tag|abend)|griass?\s*di|gruess?\s*gott|yo)\b[\s,!.:-]*(jon\b)?[\s,!.:-]*",
    re.I,
)
FUELLER = re.compile(
    r"\b(kannst\s+du|könntest\s+du|koenntest\s+du|würdest\s+du|wuerdest\s+du|magst\s+du|bitte|danke(\s+schön|\s+schoen)?|jon)\b[\s,]*",
    re.I,
)
SCHLUSS = re.compile(r"\b(code\s+mir\s+alles\s+ohne\s+kommentar(en)?|und\s+fahre?\s+fort|fahre?\s+fort)\b.*$", re.I)
VORSPANN = re.compile(r"^(code|schreib|mach|erstell|bau|zeig|erklär|erklaer|sag|hilf)\s+(mir|uns)\s+", re.I)
PRONOMEN = re.compile(r"^(mir|uns|dir)\s+", re.I)
AUFTAKT = re.compile(r"^(und|also|ok|okay|ach\s+ja|noch\s+was|ausserdem|außerdem)\b[\s,]*", re.I)
ENDWORT = re.compile(r"\s+(in|im|den|der|die|das|dem|und|mit|zu|zum|zur|für|fuer|von|auf|an|am|ein|eine|einen|kann|soll|dass|das)$", re.I)

SYSTEM = (
    "Du vergibst Titel fuer Chatverlaeufe, wie ein Ordnername. Antworte nur mit dem Titel: 2 bis 6 Woerter "
    "auf Deutsch, sachlich, das Thema treffend, ohne Anfuehrungszeichen, ohne Satzzeichen am Ende, ohne "
    "Begruessung, ohne Wort wie Titel, Chat oder Unterhaltung. Beispiele: Primzahltest in Python, Reise nach "
    "Rom planen, Fehler im Telegram-Bot, Rezept fuer Kaesespaetzle."
)


def _erster_satz(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    teile = re.split(r"(?<=[.!?])\s+|\n", text)
    for teil in teile:
        if len(teil.strip(" .!?")) >= 3:
            return teil.strip()
    return text


def vorlaeufig(text: str) -> str:
    roh = (text or "").strip()
    if not roh:
        return STANDARD
    satz = _erster_satz(roh)
    satz = GRUSS.sub("", satz)
    satz = SCHLUSS.sub("", satz)
    satz = AUFTAKT.sub("", satz.strip())
    satz = FUELLER.sub("", satz)
    satz = VORSPANN.sub("", satz.strip())
    satz = PRONOMEN.sub("", satz.strip())
    satz = re.sub(r"\s+", " ", satz).strip(" ,.!?:;-–")
    if len(satz) < 3:
        satz = re.sub(r"\s+", " ", roh).strip()[:LAENGE]
    woerter = satz.split(" ")
    if len(woerter) > 8:
        satz = " ".join(woerter[:8])
    if len(satz) > LAENGE:
        satz = satz[:LAENGE].rsplit(" ", 1)[0]
    satz = satz.strip(" ,.!?:;-–")
    while ENDWORT.search(satz) and len(satz.split()) > 2:
        satz = ENDWORT.sub("", satz)
    return (satz[:1].upper() + satz[1:]) if satz else STANDARD


def bereinigen(text: str) -> str:
    zeile = next((z for z in (text or "").splitlines() if z.strip()), "")
    zeile = re.sub(r"<think>.*?</think>", "", zeile, flags=re.S)
    zeile = re.sub(r"^\s*(titel|title)\s*[:\-–]\s*", "", zeile, flags=re.I)
    zeile = zeile.strip().strip("\"'„“”‚‘»«*#` .!?:;")
    zeile = re.sub(r"\s+", " ", zeile)
    if not zeile or len(zeile) > 80 or len(zeile.split()) > 10:
        return ""
    return zeile[:LAENGE]


def automatisch(titel: str, erste_frage: str) -> bool:
    titel = (titel or "").strip()
    if not titel or titel == STANDARD:
        return True
    roh = (erste_frage or "").strip()
    return titel in (roh[:LAENGE], roh[:LAENGE].strip(), vorlaeufig(roh))


async def erzeugen(frage: str, antwort: str = "", provider: str | None = None, model: str | None = None) -> str:
    from app.core.config import get_settings
    from app.services.chat_service import grundmodell
    from app.services.llm import complete
    from app.services.settings_service import get_settings_service

    gewaehlt, gewaehlt_modell = get_settings_service().selection()
    anbieter = provider or gewaehlt or get_settings().default_provider
    modell = grundmodell(anbieter, "emil") or model or gewaehlt_modell or None
    inhalt = f"Nutzer: {frage.strip()[:1500]}"
    if antwort.strip():
        inhalt += f"\n\nAssistent: {antwort.strip()[:1500]}"
    try:
        roh = await asyncio.wait_for(
            complete(SYSTEM, inhalt, provider=anbieter, model=modell, max_tokens=60, temperature=0.3, slot="emil", first_token_timeout=15, denken=False),
            25,
        )
    except Exception:
        return ""
    return bereinigen(roh)


async def benennen(conversation_id: str) -> dict:
    from app.db.database import session_scope
    from app.db.models import Conversation

    with session_scope() as session:
        conv = session.get(Conversation, conversation_id)
        if conv is None:
            return {"id": conversation_id, "title": "", "geaendert": False}
        nachrichten = sorted(conv.messages, key=lambda m: m.position)
        frage = next((m.content for m in nachrichten if m.role == "user"), "")
        antwort = next((m.content for m in nachrichten if m.role == "assistant"), "")
        titel = conv.title
        anbieter, modell = conv.provider, conv.model
    if not automatisch(titel, frage) or not frage.strip():
        return {"id": conversation_id, "title": titel, "geaendert": False}
    neu = await erzeugen(frage, antwort, anbieter, modell) or vorlaeufig(frage)
    if neu == titel:
        return {"id": conversation_id, "title": titel, "geaendert": False}
    with session_scope() as session:
        conv = session.get(Conversation, conversation_id)
        if conv is None or not automatisch(conv.title, frage):
            return {"id": conversation_id, "title": conv.title if conv else "", "geaendert": False}
        conv.title = neu
    return {"id": conversation_id, "title": neu, "geaendert": True}
