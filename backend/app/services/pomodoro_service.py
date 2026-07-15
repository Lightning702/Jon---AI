from __future__ import annotations

import random
import threading
import time

STRETCHES = (
    "Streck dich mal kurz — Arme hoch und tief durchatmen.",
    "Kurz aufstehen, Schultern kreisen, Blick aus dem Fenster in die Ferne.",
    "Trink einen Schluck Wasser und lockere den Nacken.",
    "Augen kurz schließen, 10 Sekunden weg vom Bildschirm.",
    "Ein paar Schritte gehen, dann geht's frisch weiter.",
)


class PomodoroService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._session = None
        self._events: list[dict] = []

    def _push(self, kind: str, say: str) -> None:
        self._events.append({"kind": kind, "say": say})
        del self._events[:-4]

    def start(self, work: int = 25, brk: int = 5, rounds: int = 4, goal: str = "") -> dict:
        work = max(5, min(int(work or 25), 90))
        brk = max(2, min(int(brk or 5), 30))
        rounds = max(1, min(int(rounds or 4), 12))
        with self._lock:
            now = time.time()
            self._session = {
                "goal": goal.strip() or "deine Aufgabe",
                "work": work,
                "break": brk,
                "rounds": rounds,
                "round": 1,
                "phase": "work",
                "ends": now + work * 60,
            }
            self._push(
                "pomodoro",
                f"Pomodoro startet: {work} Minuten fokussiert an „{self._session['goal']}“. "
                f"Runde 1 von {rounds}. Los! 🍅",
            )
            return self.state()

    def stop(self) -> dict:
        with self._lock:
            was = self._session is not None
            self._session = None
            if was:
                self._push("pomodoro", "Pomodoro beendet. Gut gemacht! ✅")
            return {"active": False}

    def tick(self) -> None:
        with self._lock:
            s = self._session
            if s is None or time.time() < s["ends"]:
                return
            now = time.time()
            if s["phase"] == "work":
                if s["round"] >= s["rounds"]:
                    self._push(
                        "pomodoro",
                        f"Alle {s['rounds']} Runden geschafft — stark! "
                        "Mach jetzt eine richtige Pause. 🎉",
                    )
                    self._session = None
                    return
                s["phase"] = "break"
                s["ends"] = now + s["break"] * 60
                self._push(
                    "pomodoro",
                    f"Runde {s['round']} geschafft! {s['break']} Minuten Pause. "
                    + random.choice(STRETCHES),
                )
            else:
                s["round"] += 1
                s["phase"] = "work"
                s["ends"] = now + s["work"] * 60
                self._push(
                    "pomodoro",
                    f"Pause vorbei — Runde {s['round']} von {s['rounds']}. "
                    f"{s['work']} Minuten fokussiert weiter! 💪",
                )

    def poll_events(self) -> list[dict]:
        with self._lock:
            events = self._events
            self._events = []
            return events

    def state(self) -> dict:
        with self._lock:
            s = self._session
            if s is None:
                return {"active": False}
            return {
                "active": True,
                "goal": s["goal"],
                "phase": s["phase"],
                "round": s["round"],
                "rounds": s["rounds"],
                "remaining_seconds": max(0, int(s["ends"] - time.time())),
            }


_service: PomodoroService | None = None


def get_pomodoro_service() -> PomodoroService:
    global _service
    if _service is None:
        _service = PomodoroService()
    return _service
