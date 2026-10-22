from __future__ import annotations

from app.db.models import Conversation
from app.db.database import session_scope
from app.schemas import ChatIn
from app.services.chat_service import ChatService


def _verlauf(kennung: str) -> list[tuple[str, str]]:
    with session_scope() as session:
        return [(m.role, m.content) for m in session.get(Conversation, kennung).messages]


def test_folgefragen_bleiben_in_der_richtigen_reihenfolge():
    dienst = ChatService()
    erste = ChatIn(messages=[{"role": "user", "content": "Erklär mir Backups"}])
    kennung = dienst._ensure_conversation(erste, "nvidia", "m")
    dienst._store_answer(kennung, "Backups sind Kopien.", None)
    zweite = ChatIn(conversation_id=kennung, messages=[
        {"role": "user", "content": "Erklär mir Backups"},
        {"role": "assistant", "content": "Backups sind Kopien."},
        {"role": "user", "content": "Fass das zusammen"},
    ])
    dienst._ensure_conversation(zweite, "nvidia", "m")
    dienst._store_answer(kennung, "Kurz: Kopien.", None)
    dritte = ChatIn(conversation_id=kennung, messages=[
        {"role": "user", "content": "Erklär mir Backups"},
        {"role": "assistant", "content": "Backups sind Kopien."},
        {"role": "user", "content": "Fass das zusammen"},
        {"role": "assistant", "content": "Kurz: Kopien."},
        {"role": "user", "content": "Erklär mir Backups"},
    ])
    dienst._ensure_conversation(dritte, "nvidia", "m")
    dienst._store_answer(kennung, "Gern noch einmal.", None)
    assert _verlauf(kennung) == [
        ("user", "Erklär mir Backups"),
        ("assistant", "Backups sind Kopien."),
        ("user", "Fass das zusammen"),
        ("assistant", "Kurz: Kopien."),
        ("user", "Erklär mir Backups"),
        ("assistant", "Gern noch einmal."),
    ]


def test_wiederholtes_senden_legt_keine_doppelte_frage_an():
    dienst = ChatService()
    nachricht = ChatIn(messages=[{"role": "user", "content": "Hallo"}])
    kennung = dienst._ensure_conversation(nachricht, "nvidia", "m")
    nochmal = ChatIn(conversation_id=kennung, messages=[{"role": "user", "content": "Hallo"}])
    dienst._ensure_conversation(nochmal, "nvidia", "m")
    assert _verlauf(kennung) == [("user", "Hallo")]
