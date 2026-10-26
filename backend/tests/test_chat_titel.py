from __future__ import annotations

import asyncio

from app.db.database import session_scope
from app.db.models import Conversation, Message
from app.services import chat_titel


def test_vorlaeufiger_titel_ohne_hoeflichkeiten():
    assert chat_titel.vorlaeufig("Hallo Jon, kannst du mir bitte eine Python-Funktion für Primzahlen coden? danke") == "Eine Python-Funktion für Primzahlen coden"
    assert chat_titel.vorlaeufig("code mir ein snake spiel in html danke code mir alles ohne Kommentaren") == "Ein snake spiel in html"
    assert chat_titel.vorlaeufig("Wie wird das Wetter morgen in Wien?") == "Wie wird das Wetter morgen in Wien"
    assert chat_titel.vorlaeufig("") == chat_titel.STANDARD
    assert len(chat_titel.vorlaeufig("wort " * 40)) <= chat_titel.LAENGE


def test_modellantwort_wird_bereinigt():
    assert chat_titel.bereinigen('Titel: "Primzahltest in Python".') == "Primzahltest in Python"
    assert chat_titel.bereinigen("**Reise nach Rom**\nWeitere Zeile") == "Reise nach Rom"
    assert chat_titel.bereinigen("Das ist ein viel zu langer Satz statt eines kurzen Titels mit sehr vielen Woertern darin") == ""


def _gespraech(titel: str, frage: str, antwort: str) -> str:
    with session_scope() as session:
        conv = Conversation(title=titel, provider="nvidia", model="x")
        session.add(conv)
        session.flush()
        session.add(Message(conversation_id=conv.id, role="user", content=frage, position=0))
        session.add(Message(conversation_id=conv.id, role="assistant", content=antwort, position=1))
        return conv.id


def _titel(kennung: str) -> str:
    with session_scope() as session:
        return session.get(Conversation, kennung).title


def test_benennen_ersetzt_nur_automatische_titel(monkeypatch):
    frage = "Hallo Jon, kannst du mir bitte eine Python-Funktion für Primzahlen coden?"
    aufrufe: list[str] = []

    async def erzeugen(f, a, p=None, m=None):
        aufrufe.append(f + "|" + a)
        return "Primzahltest in Python"

    monkeypatch.setattr(chat_titel, "erzeugen", erzeugen)
    automatisch = _gespraech(chat_titel.vorlaeufig(frage), frage, "def ist_primzahl(n): ...")
    ergebnis = asyncio.run(chat_titel.benennen(automatisch))
    assert ergebnis == {"id": automatisch, "title": "Primzahltest in Python", "geaendert": True}
    assert _titel(automatisch) == "Primzahltest in Python"
    assert "def ist_primzahl" in aufrufe[0]
    eigener = _gespraech("Mein Projekt", frage, "Antwort")
    assert asyncio.run(chat_titel.benennen(eigener))["geaendert"] is False
    assert _titel(eigener) == "Mein Projekt"
    alt = _gespraech(frage[:60], frage, "Antwort")
    assert asyncio.run(chat_titel.benennen(alt))["geaendert"] is True


def test_ohne_modell_bleibt_der_bereinigte_titel(monkeypatch):
    async def erzeugen(*_):
        return ""

    monkeypatch.setattr(chat_titel, "erzeugen", erzeugen)
    frage = "hey jon wie spät ist es in Tokio?"
    kennung = _gespraech("Neue Unterhaltung", frage, "Dort ist es 14 Uhr.")
    ergebnis = asyncio.run(chat_titel.benennen(kennung))
    assert ergebnis["title"] == "Wie spät ist es in Tokio"
