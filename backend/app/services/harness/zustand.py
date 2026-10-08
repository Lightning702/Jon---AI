from __future__ import annotations

import time

STATUS = {
    "queued", "planning", "working", "waiting_for_tool", "waiting_approval", "evaluating", "verifying",
    "compacting", "paused", "interrupted", "needs_review", "done", "failed", "cancelled",
}
MAX_LISTE = 40


def anlegen(task: dict, modus: str) -> dict:
    task.setdefault("objective", task.get("goal", "")[:2000])
    task.setdefault("modus", modus)
    task.setdefault("decisions", [])
    task.setdefault("errors", [])
    task.setdefault("relevant_files", [])
    task.setdefault("tool_results", [])
    task.setdefault("kompakt", "")
    task.setdefault("kompaktierungen", 0)
    task.setdefault("kontext", {"zeichen": 0, "budget": 0, "schaetzung_tokens": 0})
    task.setdefault("modellaufrufe", 0)
    task.setdefault("gestartet", time.time())
    return task


def _anhaengen(task: dict, feld: str, wert) -> None:
    liste = task.setdefault(feld, [])
    liste.append(wert)
    del liste[:-MAX_LISTE]


def fehler(task: dict, werkzeug: str, meldung: str) -> None:
    _anhaengen(task, "errors", {"zeit": time.time(), "werkzeug": werkzeug[:40], "meldung": meldung[:400]})


def entscheidung(task: dict, text: str) -> None:
    text = " ".join(str(text or "").split())[:300]
    if text and (not task.get("decisions") or task["decisions"][-1].get("text") != text):
        _anhaengen(task, "decisions", {"zeit": time.time(), "text": text})


def datei(task: dict, pfad: str) -> None:
    pfad = str(pfad or "").strip()
    if not pfad:
        return
    liste = task.setdefault("relevant_files", [])
    if pfad in liste:
        liste.remove(pfad)
    liste.append(pfad)
    del liste[:-MAX_LISTE]


def ergebnis(task: dict, werkzeug: str, ok: bool, kurz: str) -> None:
    _anhaengen(task, "tool_results", {"zeit": time.time(), "werkzeug": werkzeug[:60], "ok": bool(ok), "kurz": str(kurz)[:300]})


def plan_status(task: dict) -> list[dict]:
    schritte = task.get("steps") or []
    aktiv = int(task.get("plan_schritt") or (1 if schritte else 0))
    fertig = task.get("status") == "done"
    ergebnis_liste = []
    for nummer, text in enumerate(schritte, start=1):
        if fertig or nummer < aktiv:
            zustand = "erledigt"
        elif nummer == aktiv and task.get("status") not in {"failed", "cancelled", "needs_review", "interrupted"}:
            zustand = "aktiv"
        else:
            zustand = "offen"
        ergebnis_liste.append({"nummer": nummer, "text": text, "zustand": zustand})
    return ergebnis_liste


def zusammenfassung(task: dict) -> dict:
    return {
        "objective": task.get("objective", ""),
        "plan": plan_status(task),
        "relevant_files": task.get("relevant_files", [])[-15:],
        "decisions": [d["text"] for d in task.get("decisions", [])[-8:]],
        "errors": [f'{e["werkzeug"]}: {e["meldung"]}' for e in task.get("errors", [])[-6:]],
    }
