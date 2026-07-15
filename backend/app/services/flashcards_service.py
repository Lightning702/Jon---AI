from __future__ import annotations

import json
import re
import threading
import time
import uuid

from app.core.config import DATA_DIR
from app.services.llm import complete
from app.services.settings_service import get_settings_service

DECKS_FILE = DATA_DIR / "flashcards.json"
INTERVALS = [0, 60, 600, 3600, 21600, 86400, 259200, 604800, 1209600]

GEN_SYSTEM = (
    "Du erstellst Lern-Karteikarten aus dem gegebenen Thema oder Text. Jede Karte hat "
    "eine klare Frage und eine kurze, präzise Antwort. Decke die wichtigsten Punkte ab. "
    "Antworte AUSSCHLIESSLICH mit JSON: "
    '{"titel": "kurzer Deckname", "karten": [{"frage": "...", "antwort": "..."}]} '
    "Erzeuge zwischen 5 und 15 Karten, je nach Stofffülle. Sprache wie im Eingabetext."
)

JUDGE_SYSTEM = (
    "Du bewertest, ob die Antwort des Lernenden inhaltlich zur Musterlösung passt. "
    "Kleinere Formulierungsunterschiede sind egal, es zählt der Inhalt. Antworte "
    'AUSSCHLIESSLICH mit JSON: {"richtig": true/false, "feedback": "ein kurzer Satz"}'
)


class FlashcardsService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._decks = self._load()

    def _load(self) -> dict:
        try:
            data = json.loads(DECKS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def _save(self) -> None:
        try:
            DECKS_FILE.write_text(
                json.dumps(self._decks, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    async def generate(self, topic: str) -> dict:
        text = topic.strip()
        if len(text) < 3:
            return {"error": "Gib ein Thema oder einen Text an."}
        provider, model = get_settings_service().selection()
        try:
            raw = await complete(
                GEN_SYSTEM,
                text[:6000],
                provider=provider or None,
                model=model or None,
                max_tokens=1600,
                temperature=0.5,
            )
            match = re.search(r"\{.*\}", raw, re.S)
            data = json.loads(match.group(0)) if match else {}
        except Exception as exc:
            return {"error": f"Karten erstellen fehlgeschlagen: {exc}"}
        raw_cards = data.get("karten") or []
        cards = []
        for c in raw_cards[:15]:
            if isinstance(c, dict) and c.get("frage") and c.get("antwort"):
                cards.append(
                    {
                        "id": uuid.uuid4().hex,
                        "frage": str(c["frage"])[:400],
                        "antwort": str(c["antwort"])[:600],
                        "stufe": 0,
                        "faellig": 0.0,
                    }
                )
        if not cards:
            return {"error": "Es konnten keine Karten erstellt werden. Versuch es nochmal."}
        deck_id = uuid.uuid4().hex
        deck = {
            "id": deck_id,
            "titel": str(data.get("titel") or text[:40])[:60],
            "created": time.time(),
            "karten": cards,
        }
        with self._lock:
            self._decks[deck_id] = deck
            self._save()
        return {"id": deck_id, "titel": deck["titel"], "anzahl": len(cards)}

    def decks(self) -> list[dict]:
        with self._lock:
            now = time.time()
            out = []
            for d in self._decks.values():
                due = sum(1 for c in d["karten"] if c["faellig"] <= now)
                out.append(
                    {
                        "id": d["id"],
                        "titel": d["titel"],
                        "anzahl": len(d["karten"]),
                        "faellig": due,
                    }
                )
            out.sort(key=lambda x: x["titel"].lower())
            return out

    def delete(self, deck_id: str) -> bool:
        with self._lock:
            if deck_id in self._decks:
                self._decks.pop(deck_id)
                self._save()
                return True
        return False

    def next_card(self, deck_id: str) -> dict:
        with self._lock:
            deck = self._decks.get(deck_id)
            if not deck:
                return {"error": "Dieses Deck gibt es nicht."}
            now = time.time()
            due = [c for c in deck["karten"] if c["faellig"] <= now]
            pool = due or deck["karten"]
            if not pool:
                return {"done": True}
            card = min(pool, key=lambda c: c["faellig"])
            return {
                "id": card["id"],
                "frage": card["frage"],
                "stufe": card["stufe"],
                "offen": sum(1 for c in deck["karten"] if c["faellig"] <= now),
            }

    async def answer(self, deck_id: str, card_id: str, given: str) -> dict:
        with self._lock:
            deck = self._decks.get(deck_id)
            if not deck:
                return {"error": "Dieses Deck gibt es nicht."}
            card = next((c for c in deck["karten"] if c["id"] == card_id), None)
            if not card:
                return {"error": "Diese Karte gibt es nicht."}
            solution = card["antwort"]
        correct, feedback = False, ""
        text = given.strip()
        if text:
            provider, model = get_settings_service().selection()
            try:
                raw = await complete(
                    JUDGE_SYSTEM,
                    f"Frage: {card['frage']}\nMusterlösung: {solution}\nAntwort des Lernenden: {text}",
                    provider=provider or None,
                    model=model or None,
                    max_tokens=150,
                    temperature=0.2,
                )
                match = re.search(r"\{.*\}", raw, re.S)
                if match:
                    data = json.loads(match.group(0))
                    correct = bool(data.get("richtig"))
                    feedback = str(data.get("feedback") or "")[:200]
            except Exception:
                correct = text.lower() in solution.lower() or solution.lower() in text.lower()
        with self._lock:
            deck = self._decks.get(deck_id)
            card = next((c for c in deck["karten"] if c["id"] == card_id), None)
            if card:
                if correct:
                    card["stufe"] = min(card["stufe"] + 1, len(INTERVALS) - 1)
                else:
                    card["stufe"] = max(card["stufe"] - 1, 0)
                card["faellig"] = time.time() + INTERVALS[card["stufe"]]
                self._save()
        return {"richtig": correct, "loesung": solution, "feedback": feedback}


_service: FlashcardsService | None = None


def get_flashcards_service() -> FlashcardsService:
    global _service
    if _service is None:
        _service = FlashcardsService()
    return _service
