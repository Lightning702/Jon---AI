from __future__ import annotations

import re
import statistics

from app.services.llm import complete

STYLES = {
    "neutral": "sachlich, aber locker geschrieben — wie ein aufmerksamer Mensch schreibt",
    "locker": "umgangssprachlich und persönlich, mit Ich-Perspektive und kurzen Einwürfen",
    "schule": "wie ein guter Schüler- oder Studententext: klar, argumentativ, ohne Floskeln",
    "beruflich": "professionell, aber natürlich — keine Marketing- oder Behördensprache",
}

AI_PHRASES = [
    "zusammenfassend lässt sich sagen",
    "abschließend lässt sich festhalten",
    "es ist wichtig zu beachten",
    "es ist wichtig zu erwähnen",
    "in der heutigen zeit",
    "in der heutigen schnelllebigen welt",
    "spielt eine entscheidende rolle",
    "spielt eine wichtige rolle",
    "ein zweischneidiges schwert",
    "es sei darauf hingewiesen",
    "darüber hinaus",
    "des weiteren",
    "nicht zuletzt",
    "insgesamt lässt sich sagen",
    "tauchen wir ein",
    "im bereich der",
    "eine vielzahl von",
    "von entscheidender bedeutung",
    "es bleibt abzuwarten",
    "fazit:",
    "einleitung:",
    "delve",
    "moreover",
    "furthermore",
    "in conclusion",
    "it is important to note",
    "plays a crucial role",
    "in today's fast-paced world",
]

SYSTEM = """Du bist ein erfahrener Lektor. Du schreibst KI-generiert klingende Texte so um,
dass sie klingen, als hätte sie ein Mensch geschrieben.

Regeln:
- Inhalt, Fakten, Zahlen und Aussagen bleiben exakt erhalten. Nichts dazuerfinden, nichts weglassen.
- Sprache des Originals beibehalten.
- Satzlängen stark variieren: kurze Sätze zwischen lange mischen. Auch mal ein Satzfragment.
- Absätze unterschiedlich lang. Keine gleichförmige Struktur.
- Floskeln und typische KI-Wendungen streichen ("Zusammenfassend", "Darüber hinaus",
  "Es ist wichtig zu beachten", "spielt eine entscheidende Rolle", "In der heutigen Zeit").
- Keine Aufzählungslisten, wenn im Original keine stehen. Keine Zwischenüberschriften erfinden.
- Konkrete Wörter statt abstrakter Substantivierungen. Aktiv statt Passiv.
- Gedankengänge dürfen leicht unregelmäßig sein: ein Nebengedanke, eine kleine Wertung,
  ein Beispiel — so wie Menschen schreiben.
- Keine Emojis, keine Markdown-Formatierung, wenn das Original keine hat.
- Gib NUR den umgeschriebenen Text aus. Keine Einleitung, kein Kommentar, keine Anführungszeichen drumherum."""


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def _clean(text: str) -> str:
    text = text.replace("—", " - ").replace("–", "-")
    text = text.replace("„", '"').replace("“", '"').replace("”", '"')
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def score(text: str) -> dict:
    clean = text.strip()
    if len(clean) < 40:
        return {"score": 0, "label": "zu kurz", "burstiness": 0.0, "phrases": []}
    sentences = _sentences(clean)
    lengths = [len(s.split()) for s in sentences] or [0]
    burstiness = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0
    lower = clean.lower()
    found = [p for p in AI_PHRASES if p in lower]
    uniform = max(0.0, 1.0 - min(burstiness, 8.0) / 8.0)
    phrase_hit = min(len(found) / 3.0, 1.0)
    long_avg = 1.0 if statistics.fmean(lengths) > 22 else 0.0
    raw = 0.5 * uniform + 0.35 * phrase_hit + 0.15 * long_avg
    value = int(round(raw * 100))
    if value >= 66:
        label = "klingt stark nach KI"
    elif value >= 33:
        label = "teilweise maschinell"
    else:
        label = "klingt menschlich"
    return {
        "score": value,
        "label": label,
        "burstiness": round(burstiness, 1),
        "phrases": found[:8],
    }


async def humanize(
    text: str,
    style: str = "neutral",
    strength: int = 2,
    provider: str | None = None,
    model: str | None = None,
) -> dict:
    source = text.strip()
    if len(source) < 20:
        return {"error": "Der Text ist zu kurz (mindestens 20 Zeichen)."}
    if len(source) > 20000:
        return {"error": "Der Text ist zu lang (maximal 20.000 Zeichen)."}
    tone = STYLES.get(style, STYLES["neutral"])
    level = max(1, min(int(strength), 3))
    intensity = {
        1: "Schreibe behutsam um. Formulierungen glätten, Floskeln raus, Struktur bleibt.",
        2: "Schreibe deutlich um. Sätze neu bauen, Rhythmus abwechslungsreich machen.",
        3: "Schreibe frei neu. Nur der Inhalt bleibt, die Formulierung ist komplett deine.",
    }[level]
    before = score(source)
    prompt = (
        f"Ton: {tone}\n{intensity}\n\n"
        f"Text:\n---\n{source}\n---\n\nSchreibe den Text jetzt um."
    )
    try:
        result = await complete(
            SYSTEM,
            prompt,
            provider=provider,
            model=model,
            max_tokens=8192,
            temperature=1.0,
        )
    except Exception as exc:
        return {"error": f"Umschreiben fehlgeschlagen: {exc}"}
    output = _clean(result)
    if not output:
        return {"error": "Das Modell hat nichts zurückgegeben. Versuch es nochmal."}
    return {
        "text": output,
        "before": before,
        "after": score(output),
        "words": len(output.split()),
    }
