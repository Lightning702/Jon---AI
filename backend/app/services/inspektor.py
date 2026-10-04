from __future__ import annotations

import itertools
import threading
import time
from collections import Counter, deque
from datetime import date


class Inspektor:
    def __init__(self, groesse: int = 120, uhr=time.time) -> None:
        self.eintraege: deque[dict] = deque(maxlen=groesse)
        self.lock = threading.Lock()
        self.uhr = uhr
        self.nummer = itertools.count(1)
        self._tag = date.today().isoformat()
        self._zaehler = self._leer()

    @staticmethod
    def _leer() -> dict:
        return {"anfragen": 0, "fehler": 0, "tokens": 0, "modelle": Counter(), "werkzeuge": Counter(), "anbieter": Counter()}

    def _tageswechsel(self) -> None:
        heute = date.today().isoformat()
        if heute != self._tag:
            self._tag = heute
            self._zaehler = self._leer()

    def umhuellen(self, anbieter: str, stream):
        inspektor = self

        async def gemessen(request, tool_executor=None):
            eintrag = inspektor.beginnen(anbieter, request)
            try:
                async for teil in stream(request, tool_executor):
                    inspektor.teil(eintrag, teil)
                    yield teil
            except BaseException as fehler:
                inspektor.fehler(eintrag, fehler)
                raise
            finally:
                inspektor.beenden(eintrag)

        return gemessen

    def beginnen(self, anbieter: str, request) -> dict:
        nachrichten = list(getattr(request, "messages", []) or [])
        letzte = next((m.content for m in reversed(nachrichten) if getattr(m, "role", "") == "user"), "")
        eintrag = {
            "id": next(self.nummer),
            "zeit": self.uhr(),
            "start": time.perf_counter(),
            "anbieter": anbieter,
            "modell": str(getattr(request, "model", "")),
            "slot": str(getattr(request, "slot", "")),
            "nachrichten": len(nachrichten),
            "zeichen": sum(len(str(getattr(m, "content", ""))) for m in nachrichten),
            "werkzeuge_angeboten": len(getattr(request, "tools", []) or []),
            "frage": str(letzte)[:240],
            "antwort": "",
            "denken": 0,
            "erstes_token": None,
            "dauer": None,
            "prompt_tokens": 0,
            "antwort_tokens": 0,
            "werkzeuge": [],
            "fehler": "",
            "laeuft": True,
        }
        with self.lock:
            self.eintraege.append(eintrag)
        return eintrag

    def teil(self, eintrag: dict, teil) -> None:
        art = getattr(teil, "kind", "")
        if eintrag["erstes_token"] is None and art in {"content", "reasoning", "tool"}:
            eintrag["erstes_token"] = round(time.perf_counter() - eintrag["start"], 3)
        if art == "content" and len(eintrag["antwort"]) < 600:
            eintrag["antwort"] = (eintrag["antwort"] + (teil.delta or ""))[:600]
        elif art == "reasoning":
            eintrag["denken"] += len(teil.delta or "")
        elif art == "usage":
            eintrag["prompt_tokens"] = int(getattr(teil, "prompt_tokens", 0) or 0)
            eintrag["antwort_tokens"] = int(getattr(teil, "completion_tokens", 0) or 0)
        elif art == "tool":
            eintrag["werkzeuge"].append({"name": teil.name or "", "ok": None})
        elif art == "tool_result":
            for werkzeug in reversed(eintrag["werkzeuge"]):
                if werkzeug["name"] == teil.name and werkzeug["ok"] is None:
                    werkzeug["ok"] = bool(teil.ok)
                    break

    def fehler(self, eintrag: dict, fehler: BaseException) -> None:
        eintrag["fehler"] = (type(fehler).__name__ + ": " + str(fehler))[:400]

    def beenden(self, eintrag: dict) -> None:
        eintrag["dauer"] = round(time.perf_counter() - eintrag["start"], 3)
        eintrag["laeuft"] = False
        with self.lock:
            self._tageswechsel()
            z = self._zaehler
            z["anfragen"] += 1
            z["tokens"] += eintrag["prompt_tokens"] + eintrag["antwort_tokens"]
            z["fehler"] += 1 if eintrag["fehler"] else 0
            z["modelle"][eintrag["modell"]] += 1
            z["anbieter"][eintrag["anbieter"]] += 1
            for werkzeug in eintrag["werkzeuge"]:
                z["werkzeuge"][werkzeug["name"]] += 1

    def liste(self) -> list[dict]:
        with self.lock:
            return [{k: v for k, v in e.items() if k != "start"} for e in reversed(self.eintraege)]

    def leeren(self) -> None:
        with self.lock:
            self.eintraege.clear()

    def nutzung(self) -> dict:
        with self.lock:
            self._tageswechsel()
            z = self._zaehler
            return {"tag": self._tag, "anfragen": z["anfragen"], "fehler": z["fehler"], "tokens": z["tokens"], "modelle": dict(z["modelle"].most_common(15)), "werkzeuge": dict(z["werkzeuge"].most_common(25)), "anbieter": dict(z["anbieter"].most_common(10))}


_inspektor: Inspektor | None = None


def get_inspektor() -> Inspektor:
    global _inspektor
    if _inspektor is None:
        _inspektor = Inspektor()
    return _inspektor
