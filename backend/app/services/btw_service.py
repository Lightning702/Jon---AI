from __future__ import annotations

import re

from app.core.fehler import leise

NACHAUFTRAG = re.compile(
    r"^\s*(?:danach|anschlie(?:ss|ß)end|nachher|hinterher|im anschluss|wenn du fertig bist|sobald du fertig bist|als n(?:ae|ä)chstes|zum schluss|dann noch|und dann|after that|afterwards|then)\b[\s,:-]*",
    re.IGNORECASE,
)
NACHAUFTRAG_INNEN = re.compile(
    r"\b(?:mach|mache|erledige|erstelle|bau|baue|schreib|schreibe|schick|schicke|f(?:ue|ü)g|f(?:ue|ü)ge|(?:ae|ä)nder|(?:ae|ä)ndere)\b.*\b(?:danach|anschlie(?:ss|ß)end|nachher|hinterher|wenn du fertig bist|sobald du fertig bist)\b",
    re.IGNORECASE,
)

SYSTEM = (
    "Du bist Jon von FelWorks. Der Nutzer stellt dir nebenbei eine kurze Zwischenfrage, waehrend du "
    "an einer anderen Aufgabe arbeitest. Beantworte sie sofort, kurz und konkret (hoechstens 4 Saetze), "
    "auf Deutsch, ausser der Nutzer schreibt in einer anderen Sprache. Nutze den mitgeschickten "
    "Arbeitsstand, wenn die Frage sich darauf bezieht. Du fuehrst hier nichts aus und aenderst nichts – "
    "behaupte also nie, etwas erledigt zu haben. Soll etwas getan werden, sag, dass er es mit "
    "'danach: …' als Nachauftrag eintragen kann."
)


def ohne_befehl(text: str) -> str:
    return re.sub(r"^\s*/btw\b[\s:,-]*", "", str(text or ""), flags=re.IGNORECASE).strip()


def ist_nachauftrag(text: str) -> bool:
    roh = ohne_befehl(text)
    return bool(NACHAUFTRAG.match(roh) or NACHAUFTRAG_INNEN.search(roh))


def auftrag_text(text: str) -> str:
    roh = ohne_befehl(text)
    return NACHAUFTRAG.sub("", roh, count=1).strip() or roh


def _harness_stand(task_id: str) -> str:
    try:
        from app.services.harness import get_harness_service

        task = get_harness_service().get(task_id)
    except Exception as fehler:
        leise(fehler, "btw/harness")
        return ""
    zeilen = [f"Auftrag: {str(task.get('goal', ''))[:1500]}", f"Status: {task.get('status')}"]
    for nummer, schritt in enumerate(task.get("steps") or [], 1):
        zeilen.append(f"Plan {nummer}: {schritt}")
    notizen = [d.get("text") for d in (task.get("decisions") or []) if isinstance(d, dict) and d.get("text")]
    if notizen:
        zeilen.append("Zuletzt: " + " | ".join(str(n) for n in notizen[-5:]))
    dateien = [c.get("path") for c in (task.get("changes") or []) if isinstance(c, dict) and c.get("path")]
    if dateien:
        zeilen.append("Geaenderte Dateien: " + ", ".join(dict.fromkeys(str(d) for d in dateien[-12:])))
    if task.get("summary"):
        zeilen.append("Ergebnis bisher: " + str(task["summary"])[:800])
    if task.get("nachauftraege"):
        zeilen.append("Vorgemerkte Nachauftraege: " + " | ".join(task["nachauftraege"]))
    return "\n".join(zeilen)


def _verlauf_text(verlauf: list | None) -> str:
    zeilen = []
    for eintrag in (verlauf or [])[-12:]:
        if not isinstance(eintrag, dict):
            continue
        rolle = "Nutzer" if eintrag.get("role") == "user" else "Jon"
        inhalt = str(eintrag.get("content") or "").strip()
        if inhalt:
            zeilen.append(f"{rolle}: {inhalt[:1200]}")
    return "\n".join(zeilen)


def _modell() -> tuple[str | None, str | None]:
    from app.services.settings_service import get_settings_service

    einstellungen = get_settings_service()
    anbieter, modell = einstellungen.pet_selection()
    if not anbieter:
        anbieter, modell = einstellungen.selection()
    return anbieter or None, modell or None


async def antworten(frage: str, verlauf: list | None = None, task_id: str = "", nebenbei: str = "") -> dict:
    from app.services.llm import complete

    text = ohne_befehl(frage)
    if not text:
        return {"art": "leer", "antwort": "Was möchtest du nebenbei wissen? Schreib zum Beispiel: /btw Wie weit bist du?"}
    if ist_nachauftrag(text):
        auftrag = auftrag_text(text)
        if task_id:
            try:
                from app.services.harness import get_harness_service

                liste = get_harness_service().nachauftrag(task_id, auftrag)
                return {"art": "nachauftrag", "auftrag": auftrag, "antwort": f"Notiert. Sobald ich mit dem aktuellen Auftrag fertig bin, mache ich: {auftrag}", "nachauftraege": liste}
            except (KeyError, ValueError) as fehler:
                return {"art": "fehler", "antwort": str(fehler)}
        return {"art": "nachauftrag", "auftrag": auftrag, "antwort": f"Notiert. Wenn ich mit der aktuellen Antwort fertig bin, mache ich: {auftrag}"}
    teile = []
    if task_id:
        stand = _harness_stand(task_id)
        if stand:
            teile.append("ARBEITSSTAND DES LAUFENDEN AUFTRAGS:\n" + stand)
    if nebenbei:
        teile.append("WORAN JON GERADE ARBEITET:\n" + str(nebenbei)[:3000])
    verlauf_text = _verlauf_text(verlauf)
    if verlauf_text:
        teile.append("BISHERIGES GESPRAECH:\n" + verlauf_text)
    teile.append("ZWISCHENFRAGE: " + text)
    anbieter, modell = _modell()
    try:
        antwort = await complete(SYSTEM, "\n\n".join(teile), provider=anbieter, model=modell, max_tokens=700, temperature=0.4, slot="emil", denken=False)
    except Exception as fehler:
        leise(fehler, "btw")
        return {"art": "fehler", "antwort": f"Gerade komme ich nicht ans Modell ({str(fehler)[:160]}). Frag gleich noch einmal."}
    return {"art": "frage", "antwort": antwort.strip() or "Dazu fällt mir gerade nichts ein."}
