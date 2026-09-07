from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32), default="chat")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    wichtigkeit: Mapped[float] = mapped_column(Float, default=0.5)
    nutzungen: Mapped[int] = mapped_column(Integer, default=0)
    zuletzt_genutzt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class P2PMessage(Base):
    __tablename__ = "p2p_messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    peer_id: Mapped[str] = mapped_column(String(32), index=True)
    group_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    direction: Mapped[str] = mapped_column(String(8), default="in")
    sender_name: Mapped[str] = mapped_column(String(64), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    media_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    media_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    media_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    media_mime: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    reply_to: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reply_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    reactions: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    seen: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class P2POutbox(Base):
    __tablename__ = "p2p_outbox"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    peer_id: Mapped[str] = mapped_column(String(32), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="inbox")
    message_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[str] = mapped_column(Text)
    tries: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255), default="Neue Unterhaltung")
    provider: Mapped[str] = mapped_column(String(64), default="nvidia")
    model: Mapped[str] = mapped_column(String(128), default="openai/gpt-oss-120b")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.position",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    karten: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class Entitaet(Base):
    __tablename__ = "entitaeten"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    art: Mapped[str] = mapped_column(String(24), default="sache", index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    beschreibung: Mapped[str] = mapped_column(Text, default="")
    merkmale: Mapped[str] = mapped_column(Text, default="{}")
    wichtigkeit: Mapped[float] = mapped_column(Float, default=0.5)
    erwaehnungen: Mapped[int] = mapped_column(Integer, default=1)
    erstellt: Mapped[datetime] = mapped_column(DateTime, default=_now)
    gesehen: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Beziehung(Base):
    __tablename__ = "beziehungen"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    von: Mapped[str] = mapped_column(String(32), index=True)
    nach: Mapped[str] = mapped_column(String(32), index=True)
    art: Mapped[str] = mapped_column(String(40), default="gehoert_zu")
    notiz: Mapped[str] = mapped_column(Text, default="")
    erstellt: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Ziel(Base):
    __tablename__ = "ziele"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    titel: Mapped[str] = mapped_column(String(200))
    beschreibung: Mapped[str] = mapped_column(Text, default="")
    zustand: Mapped[str] = mapped_column(String(16), default="offen", index=True)
    naechster_schritt: Mapped[str] = mapped_column(Text, default="")
    frist: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    haengt_an: Mapped[str] = mapped_column(String(32), default="")
    wichtigkeit: Mapped[float] = mapped_column(Float, default=0.5)
    fortschritt: Mapped[float] = mapped_column(Float, default=0.0)
    quelle: Mapped[str] = mapped_column(String(24), default="nutzer")
    erstellt: Mapped[datetime] = mapped_column(DateTime, default=_now)
    aktualisiert: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Notiz(Base):
    __tablename__ = "notizblock"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    bereich: Mapped[str] = mapped_column(String(48), default="allgemein", index=True)
    inhalt: Mapped[str] = mapped_column(Text, default="")
    erstellt: Mapped[datetime] = mapped_column(DateTime, default=_now)
    aktualisiert: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Erfahrung(Base):
    __tablename__ = "erfahrungen"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    bereich: Mapped[str] = mapped_column(String(80), index=True)
    art: Mapped[str] = mapped_column(String(16), default="klappt")
    text: Mapped[str] = mapped_column(Text, default="")
    treffer: Mapped[int] = mapped_column(Integer, default=1)
    gewicht: Mapped[float] = mapped_column(Float, default=0.5)
    erstellt: Mapped[datetime] = mapped_column(DateTime, default=_now)
    aktualisiert: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Auftrag(Base):
    __tablename__ = "auftraege"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    art: Mapped[str] = mapped_column(String(32), default="browser", index=True)
    titel: Mapped[str] = mapped_column(String(200), default="")
    eingabe: Mapped[str] = mapped_column(Text, default="{}")
    zustand: Mapped[str] = mapped_column(String(16), default="offen", index=True)
    fortschritt: Mapped[float] = mapped_column(Float, default=0.0)
    schritt: Mapped[int] = mapped_column(Integer, default=0)
    schritte: Mapped[int] = mapped_column(Integer, default=0)
    ergebnis: Mapped[str | None] = mapped_column(Text, nullable=True)
    fehler: Mapped[str | None] = mapped_column(Text, nullable=True)
    versuche: Mapped[int] = mapped_column(Integer, default=0)
    gespraech: Mapped[str] = mapped_column(String(32), default="")
    erstellt: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    aktualisiert: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Ereignis(Base):
    __tablename__ = "ereignisse"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zeit: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    art: Mapped[str] = mapped_column(String(24), default="system", index=True)
    titel: Mapped[str] = mapped_column(String(200), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    quelle: Mapped[str] = mapped_column(String(24), default="app", index=True)
    bedeutung: Mapped[float] = mapped_column(Float, default=0.4)
    gelungen: Mapped[int] = mapped_column(Integer, default=1)
    gespraech: Mapped[str] = mapped_column(String(32), default="")


class ActionLog(Base):
    __tablename__ = "action_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(24), default="app", index=True)
    tool: Mapped[str] = mapped_column(String(64))
    args: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="")
    ok: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
