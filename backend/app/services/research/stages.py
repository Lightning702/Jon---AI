from __future__ import annotations

import json
import re
from typing import Any

from app.services.llm import complete

SYSTEM = (
    "Du bist Jons autonomer Recherche-Agent. Du arbeitest gruendlich, praezise und "
    "ehrlich. Du erfindest nichts, du kennzeichnest Unsicherheiten und du "
    "antwortest immer auf Deutsch. Wenn ein JSON-Format verlangt wird, gibst du "
    "ausschliesslich gueltiges JSON ohne Code-Fences aus."
)

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def parse_json(text: str, fallback: Any = None) -> Any:
    raw = (text or "").strip()
    if not raw:
        return fallback
    match = _JSON_BLOCK.search(raw)
    if match:
        raw = match.group(1).strip()
    try:
        return json.loads(raw)
    except Exception:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = raw.find(opener)
        end = raw.rfind(closer)
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except Exception:
                continue
    return fallback


async def _ask(
    user: str,
    provider: str,
    model: str,
    max_tokens: int = 2600,
    temperature: float = 0.4,
) -> str:
    return await complete(
        SYSTEM,
        user,
        provider=provider or None,
        model=model or None,
        max_tokens=max_tokens,
        temperature=temperature,
    )


async def analyze_topic(
    topic: str,
    minutes: int,
    depth: str,
    max_subtopics: int,
    provider: str,
    model: str,
) -> dict[str, Any]:
    count = {"schnell": 5, "normal": 8, "tief": max_subtopics}.get(depth, 8)
    count = max(3, min(count, max_subtopics))
    prompt = (
        f"Lernauftrag: „{topic}“\n"
        f"Zeitbudget: {minutes} Minuten. Recherchetiefe: {depth}.\n\n"
        "Analysiere das Thema und zerlege es in Unterthemen, die man nacheinander "
        "recherchieren kann. Sortiere sie so, dass die wichtigsten Grundlagen zuerst "
        "kommen. Antworte als JSON:\n"
        "{\n"
        '  "titel": "kurzer Titel des Wissensgebiets",\n'
        '  "zusammenfassung": "2-3 Saetze, worum es geht und was man am Ende koennen soll",\n'
        '  "unterthemen": [\n'
        '    {"titel": "...", "frage": "die konkrete Frage, die dieses Unterthema '
        'beantwortet", "wichtigkeit": 1-5}\n'
        "  ]\n"
        "}\n"
        f"Erzeuge genau {count} Unterthemen. wichtigkeit 5 = unverzichtbar."
    )
    data = parse_json(await _ask(prompt, provider, model), {})
    if not isinstance(data, dict):
        data = {}
    topics = data.get("unterthemen")
    if not isinstance(topics, list) or not topics:
        data["unterthemen"] = [
            {"titel": "Grundlagen", "frage": f"Was sind die Grundlagen von {topic}?", "wichtigkeit": 5},
            {"titel": "Kernkonzepte", "frage": f"Welche Kernkonzepte gehoeren zu {topic}?", "wichtigkeit": 4},
            {"titel": "Anwendung", "frage": f"Wie wird {topic} praktisch angewendet?", "wichtigkeit": 3},
        ]
    data.setdefault("titel", topic)
    data.setdefault("zusammenfassung", "")
    return data


async def plan_queries(
    topic: str, subtopic_title: str, question: str, provider: str, model: str
) -> list[str]:
    prompt = (
        f"Oberthema: {topic}\nUnterthema: {subtopic_title}\nLeitfrage: {question}\n\n"
        "Formuliere 3 unterschiedliche Suchanfragen fuer eine Websuche, die zusammen "
        "verlaessliche Quellen zu diesem Unterthema finden. Eine davon auf Englisch. "
        'Antworte als JSON-Liste: ["...", "...", "..."]'
    )
    data = parse_json(await _ask(prompt, provider, model, 500, 0.5), [])
    queries = [str(item).strip() for item in data if str(item).strip()] if isinstance(data, list) else []
    if not queries:
        queries = [f"{topic} {subtopic_title}", f"{subtopic_title} erklaert", f"{topic} {subtopic_title} basics"]
    return queries[:4]


async def analyze_source(
    topic: str,
    subtopic_title: str,
    question: str,
    source_title: str,
    source_url: str,
    text: str,
    provider: str,
    model: str,
) -> dict[str, Any]:
    prompt = (
        f"Oberthema: {topic}\nUnterthema: {subtopic_title}\nLeitfrage: {question}\n"
        f"Quelle: {source_title} ({source_url})\n\n"
        "Text der Quelle:\n---\n"
        f"{text[:12000]}\n---\n\n"
        "Pruefe, was diese Quelle wirklich zum Unterthema beitraegt. Antworte als JSON:\n"
        "{\n"
        '  "relevanz": 0-10,\n'
        '  "brauchbar": true/false,\n'
        '  "zusammenfassung": "3-6 Saetze, nur was im Text steht",\n'
        '  "kernaussagen": ["konkrete Fakten, jeweils ein Satz"],\n'
        '  "zahlen_und_daten": ["Zahl/Datum mit Bedeutung"],\n'
        '  "begriffe": ["Fachbegriff: kurze Erklaerung"],\n'
        '  "unsicher": ["was die Quelle offen laesst oder nur behauptet"]\n'
        "}\n"
        "brauchbar=false, wenn der Text Werbung, eine Fehlerseite oder thematisch "
        "unpassend ist."
    )
    data = parse_json(await _ask(prompt, provider, model, 1800, 0.3), {})
    if not isinstance(data, dict):
        return {"relevanz": 0, "brauchbar": False, "zusammenfassung": "", "kernaussagen": []}
    data.setdefault("relevanz", 0)
    data.setdefault("brauchbar", bool(data.get("kernaussagen")))
    data.setdefault("kernaussagen", [])
    data.setdefault("zusammenfassung", "")
    return data


async def validate_findings(
    subtopic_title: str, notes: list[dict[str, Any]], provider: str, model: str
) -> dict[str, Any]:
    compact = [
        {
            "quelle": note.get("domain", ""),
            "zusammenfassung": str(note.get("zusammenfassung", ""))[:900],
            "kernaussagen": [str(item)[:220] for item in note.get("kernaussagen", [])][:8],
        }
        for note in notes
    ]
    prompt = (
        f"Unterthema: {subtopic_title}\n\n"
        "Diese Notizen stammen aus verschiedenen Quellen:\n"
        f"{json.dumps(compact, ensure_ascii=False)[:9000]}\n\n"
        "Vergleiche die Quellen miteinander. Antworte als JSON:\n"
        "{\n"
        '  "widersprueche": ["Quelle A sagt X, Quelle B sagt Y"],\n'
        '  "gesichert": ["Aussagen, die mehrere Quellen stuetzen"],\n'
        '  "vertrauen": "hoch|mittel|niedrig",\n'
        '  "offene_fragen": ["was noch fehlt"],\n'
        '  "braucht_mehr_quellen": true/false\n'
        "}"
    )
    data = parse_json(await _ask(prompt, provider, model, 1200, 0.3), {})
    if not isinstance(data, dict):
        data = {}
    data.setdefault("widersprueche", [])
    data.setdefault("gesichert", [])
    data.setdefault("vertrauen", "mittel")
    data.setdefault("offene_fragen", [])
    data.setdefault("braucht_mehr_quellen", False)
    return data


async def write_subtopic(
    topic: str,
    subtopic_title: str,
    question: str,
    notes: list[dict[str, Any]],
    validation: dict[str, Any],
    provider: str,
    model: str,
) -> str:
    material = json.dumps(
        [
            {
                "quelle": note.get("domain", ""),
                "url": note.get("url", ""),
                "titel": note.get("title", ""),
                "zusammenfassung": str(note.get("zusammenfassung", ""))[:1400],
                "kernaussagen": [str(item)[:300] for item in note.get("kernaussagen", [])][:12],
                "zahlen_und_daten": [str(item)[:200] for item in note.get("zahlen_und_daten", [])][:8],
                "begriffe": [str(item)[:200] for item in note.get("begriffe", [])][:10],
            }
            for note in notes
        ],
        ensure_ascii=False,
    )[:14000]
    prompt = (
        f"Oberthema: {topic}\nUnterthema: {subtopic_title}\nLeitfrage: {question}\n\n"
        f"Recherchematerial:\n{material}\n\n"
        f"Quellenvergleich: {json.dumps(validation, ensure_ascii=False)[:2000]}\n\n"
        "Schreibe daraus eine Wissensdatei in Markdown, auf Deutsch. Aufbau:\n"
        f"# {subtopic_title}\n"
        "Ein kurzer Einstieg, dann `## Kernaussagen` mit Stichpunkten, `## Details` "
        "mit ausformuliertem Wissen, `## Begriffe` als Liste `**Begriff** — Erklaerung`, "
        "`## Merksaetze` mit 3-5 Punkten und `## Unsicher / strittig`, falls es "
        "Widersprueche gibt. Nutze nur das Material. Nenne keine Quellen-URLs im "
        "Fliesstext, sondern schreibe Domains in Klammern, wo eine Aussage strittig ist. "
        "Gib nur Markdown aus, keine Einleitung davor."
    )
    return (await _ask(prompt, provider, model, 3200, 0.5)).strip()


async def write_overview(
    topic: str,
    title: str,
    subtopics: list[dict[str, Any]],
    provider: str,
    model: str,
) -> str:
    listing = json.dumps(subtopics, ensure_ascii=False)[:6000]
    prompt = (
        f"Wissensgebiet: {title} (Auftrag: „{topic}“)\n"
        f"Recherchierte Unterthemen mit Dateien:\n{listing}\n\n"
        "Schreibe eine README.md auf Deutsch fuer diesen Wissensordner. Aufbau:\n"
        f"# {title}\n"
        "kurze Einordnung, dann `## Was Jon jetzt kann` (Stichpunkte), "
        "`## Aufbau` mit einer Liste der Dateien im Format "
        "`- [dateiname.md](dateiname.md) — worum es geht`, "
        "`## Roter Faden` mit der empfohlenen Lesereihenfolge und "
        "`## Offene Fragen`. Gib nur Markdown aus."
    )
    return (await _ask(prompt, provider, model, 2200, 0.5)).strip()


async def write_skill(
    topic: str,
    title: str,
    slug: str,
    summary: str,
    subtopics: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    provider: str,
    model: str,
) -> str:
    listing = json.dumps(subtopics, ensure_ascii=False)[:6000]
    domains = sorted({str(item.get("domain", "")) for item in sources if item.get("domain")})
    prompt = (
        f"Wissensgebiet: {title}\nSlug: {slug}\nAuftrag war: „{topic}“\n"
        f"Zusammenfassung: {summary}\n"
        f"Unterthemen und Dateien: {listing}\n"
        f"Genutzte Quellen-Domains: {', '.join(domains[:30])}\n\n"
        "Schreibe daraus eine Skill-Datei fuer Jon in Markdown, auf Deutsch. Ein Skill "
        "ist eine Anleitung, die Jon liest, bevor er eine passende Aufgabe uebernimmt. "
        "Aufbau:\n"
        f"# {title}\n"
        "ein Satz, was dieser Skill kann.\n"
        "## Wann Jon diesen Skill nutzt\n"
        "Stichpunkte mit konkreten Ausloesern (Fragen und Aufgaben des Nutzers).\n"
        "## Was Jon gelernt hat\n"
        "die wichtigsten Konzepte in Stichpunkten.\n"
        "## Wissensdateien\n"
        f"Liste im Format `- skills/{slug}/datei.md — Inhalt`.\n"
        "## Vorgehen\n"
        "nummerierte Schritte, wie Jon eine Aufgabe in diesem Gebiet angeht, inklusive "
        "des Hinweises, die passende Wissensdatei mit read_skill oder ask_knowledge zu "
        "oeffnen.\n"
        "## Grenzen\n"
        "was dieser Skill nicht abdeckt und wo Jon nachrecherchieren muss.\n"
        "Gib nur Markdown aus."
    )
    return (await _ask(prompt, provider, model, 2600, 0.45)).strip()


async def final_summary(
    topic: str, subtopics: list[dict[str, Any]], provider: str, model: str
) -> str:
    listing = json.dumps(subtopics, ensure_ascii=False)[:5000]
    prompt = (
        f"Auftrag: „{topic}“\nErforschte Unterthemen: {listing}\n\n"
        "Fasse in 3-5 Saetzen auf Deutsch zusammen, was du jetzt weisst und wo die "
        "Grenzen liegen. Kein Markdown, nur Fliesstext."
    )
    return (await _ask(prompt, provider, model, 700, 0.5)).strip()
