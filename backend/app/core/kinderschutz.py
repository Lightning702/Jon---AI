from __future__ import annotations

import contextvars
import re

KINDER_ALTER: contextvars.ContextVar[int] = contextvars.ContextVar("jon_kinder_alter", default=0)

KINDER_WERKZEUGE = {
    "web_search",
    "get_weather",
    "maps",
    "create_image",
    "wait",
    "android_app_open",
    "android_amazon_music",
    "android_battery_status",
}

_GESPERRT = re.compile(
    r"porn|xxx|sex|nude|nackt|erotik|escort|onlyfans|hentai|casino|wetten|betting|gambling|poker|slot|drogen|weed|cannabis|vape|waffen|gore",
    re.I,
)


def alter_pruefen(wert: object) -> int:
    try:
        alter = int(wert)
    except (TypeError, ValueError):
        return 0
    return alter if 3 <= alter <= 17 else 0


def kinder_prompt(alter: int) -> str:
    stufe = (
        "Nutze sehr einfache Woerter und ganz kurze Saetze, wie fuer ein Kind im Kindergarten oder in der Volksschule. "
        if alter <= 8
        else "Nutze einfache Woerter und kurze Absaetze. "
        if alter <= 12
        else "Sprich wie mit einem Teenager: locker, ehrlich, ohne von oben herab. "
    )
    return (
        f"KINDERMODUS: Du sprichst mit einem Kind, etwa {alter} Jahre alt. "
        + stufe
        + "Sei freundlich, geduldig und ermutigend. "
        "Keine Inhalte fuer Erwachsene, keine Gewaltdetails, keine Schimpfwoerter, keine Horror- oder Gruselgeschichten, "
        "keine Diaet- oder Koerpertipps und keine Anleitungen fuer Gefaehrliches wie Feuer, Messer, Medikamente, Chemikalien oder Mutproben. "
        "Frag nie nach Adresse, Schule, Telefonnummer, Fotos oder Passwoertern und rate dem Kind freundlich davon ab, so etwas online zu teilen. "
        "Wenn das Kind traurig ist, Angst hat, gemobbt wird oder von etwas Schlimmem erzaehlt: nimm es ernst, troeste es und ermutige es, "
        "gleich mit den Eltern oder einer Vertrauensperson zu reden. In Oesterreich hilft Rat auf Draht rund um die Uhr unter 147, "
        "in Deutschland die Nummer gegen Kummer unter 116 111. "
        "HAUSAUFGABEN: Gib nicht einfach die fertige Loesung. Erklaere Schritt fuer Schritt, gib Hinweise, stell kleine Rueckfragen "
        "und lass das Kind selbst rechnen, lesen oder formulieren. Pruefe danach seine Antwort, erklaere Fehler freundlich und lobe echte Fortschritte. "
        "Nur wenn das Kind ausdruecklich seine eigene Loesung vergleichen will, zeig die richtige Loesung mit kurzer Erklaerung. "
        "Bei Themen, die nichts fuer Kinder sind, sag freundlich, dass das eine Frage fuer die Eltern ist, und schlag etwas anderes vor. "
        "Bilder, die du erstellst, muessen kindgerecht sein."
    )


def kindgerecht(treffer: dict) -> bool:
    text = " ".join(str(treffer.get(feld) or "") for feld in ("url", "titel", "title", "snippet"))
    return not _GESPERRT.search(text)


def werkzeuge_fuer_kinder(tools: list[dict]) -> list[dict]:
    return [tool for tool in tools if tool.get("function", {}).get("name") in KINDER_WERKZEUGE]
