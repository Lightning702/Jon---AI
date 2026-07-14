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
    "zusammenfassend kann gesagt werden",
    "abschließend lässt sich festhalten",
    "abschließend lässt sich sagen",
    "es ist wichtig zu beachten",
    "es ist wichtig zu erwähnen",
    "es ist erwähnenswert",
    "es ist festzuhalten",
    "in der heutigen zeit",
    "in der heutigen schnelllebigen welt",
    "im digitalen zeitalter",
    "in der modernen welt",
    "spielt eine entscheidende rolle",
    "spielt eine wichtige rolle",
    "spielt eine zentrale rolle",
    "ein zweischneidiges schwert",
    "es sei darauf hingewiesen",
    "darüber hinaus",
    "des weiteren",
    "nicht zuletzt",
    "nichtsdestotrotz",
    "insgesamt lässt sich sagen",
    "insgesamt zeigt sich",
    "tauchen wir ein",
    "werfen wir einen blick",
    "im bereich der",
    "eine vielzahl von",
    "eine breite palette",
    "von entscheidender bedeutung",
    "von großer bedeutung",
    "es bleibt abzuwarten",
    "im folgenden werden",
    "im folgenden wird",
    "dieser artikel beleuchtet",
    "in diesem artikel",
    "sowohl für anfänger als auch",
    "revolutioniert die art und weise",
    "nahtlos integrier",
    "ganzheitlichen ansatz",
    "dynamisch und flexibel",
    "letztendlich ist festzuhalten",
    "zusammenspiel verschiedener faktoren",
    "es lohnt sich, einen genaueren blick",
    "gilt es zu berücksichtigen",
    "fazit:",
    "einleitung:",
    "delve",
    "moreover",
    "furthermore",
    "in conclusion",
    "it is important to note",
    "it's worth noting",
    "plays a crucial role",
    "in today's fast-paced world",
    "seamlessly",
    "game-changer",
    "unlock the potential",
]

STARTER_STOPWORDS = {"der", "die", "das", "ein", "eine", "ich", "es", "und", "aber"}

SYSTEM = """Du bist ein erfahrener Lektor. Du schreibst KI-generiert klingende Texte so um,
dass sie klingen, als hätte sie ein Mensch geschrieben.

Regeln:
- Inhalt, Fakten, Zahlen und Aussagen bleiben exakt erhalten. Nichts dazuerfinden, nichts weglassen.
- Sprache des Originals beibehalten. Länge ungefähr beibehalten (plus/minus 15 Prozent).
- Satzlängen stark variieren: sehr kurze Sätze (3-6 Wörter) zwischen lange mischen.
  Ab und zu ein bewusstes Satzfragment. Nie drei ähnlich lange Sätze hintereinander.
- Satzanfänge variieren: nicht mehrere Sätze hintereinander mit demselben Wort oder
  demselben Muster (Subjekt-Verb) beginnen. Mal mit Nebensatz, mal mit Adverb, mal mit
  dem Objekt anfangen.
- Absätze unterschiedlich lang. Keine gleichförmige Struktur, keine perfekte Symmetrie,
  keine Aufzählung mit genau drei Beispielen.
- Floskeln und typische KI-Wendungen streichen ("Zusammenfassend", "Darüber hinaus",
  "Es ist wichtig zu beachten", "spielt eine entscheidende Rolle", "In der heutigen Zeit",
  "Des Weiteren", "Im Folgenden", "eine Vielzahl von"). Übergänge lieber inhaltlich lösen
  oder einfach hart schneiden — Menschen springen auch mal.
- Keine Aufzählungslisten, wenn im Original keine stehen. Keine Zwischenüberschriften
  erfinden. Kein fettgedrucktes Resümee.
- Konkrete Wörter statt abstrakter Substantivierungen. Aktiv statt Passiv. Verben statt
  "erfolgen"/"stattfinden"/"gewährleisten".
- Gedankengänge dürfen leicht unregelmäßig sein: ein Nebengedanke in Klammern, eine kleine
  Wertung, ein konkretes Beispiel, eine rhetorische Frage — sparsam, so wie Menschen schreiben.
- Wiederhole kein auffälliges Wort kurz hintereinander; nimm ein Synonym oder bau den Satz um.
- Keine Emojis, keine Markdown-Formatierung, keine Gedankenstrich-Ketten, wenn das Original
  sie nicht hat.
- Gib NUR den umgeschriebenen Text aus. Keine Einleitung, kein Kommentar, keine Anführungszeichen drumherum."""

REFINE = """Der folgende Text klingt immer noch zu maschinell. Schreibe ihn noch einmal um.
Behalte Inhalt, Fakten und Sprache exakt bei. Konzentriere dich auf:
{issues}
Gib NUR den umgeschriebenen Text aus."""


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def _clean(text: str) -> str:
    text = text.replace("—", " - ").replace("–", "-")
    text = text.replace("„", '"').replace("“", '"').replace("”", '"')
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _starter_repetition(sentences: list[str]) -> float:
    starters = []
    for s in sentences:
        words = s.split()
        if not words:
            continue
        first = words[0].lower().strip("\"'(»„")
        if first and first not in STARTER_STOPWORDS:
            starters.append(first)
    if len(starters) < 4:
        return 0.0
    counts: dict[str, int] = {}
    for s in starters:
        counts[s] = counts.get(s, 0) + 1
    top = max(counts.values())
    return max(0.0, (top / len(starters) - 0.2) / 0.5)


def _structure_signal(text: str) -> float:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return 0.0
    bullets = sum(1 for l in lines if re.match(r"^([-*•]|\d+\.)\s", l))
    headers = sum(1 for l in lines if l.startswith("#") or (l.endswith(":") and len(l) < 60))
    bold = text.count("**") // 2
    hits = bullets * 0.6 + headers * 0.8 + bold * 0.5
    return min(hits / 5.0, 1.0)


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
    starter = min(_starter_repetition(sentences), 1.0)
    structure = _structure_signal(clean)
    raw = (
        0.4 * uniform
        + 0.28 * phrase_hit
        + 0.12 * long_avg
        + 0.12 * starter
        + 0.08 * structure
    )
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
            temperature=0.95,
        )
    except Exception as exc:
        return {"error": f"Umschreiben fehlgeschlagen: {exc}"}
    output = _clean(result)
    if not output:
        return {"error": "Das Modell hat nichts zurückgegeben. Versuch es nochmal."}
    after = score(output)
    passes = 1
    if after["score"] >= 35 or after["score"] >= max(before["score"] - 5, 20):
        issues = []
        if after["phrases"]:
            issues.append(
                "Diese Floskeln stehen noch im Text und müssen raus: "
                + ", ".join(f'"{p}"' for p in after["phrases"][:5])
            )
        if after["burstiness"] < 5:
            issues.append(
                "Die Sätze sind zu gleich lang — mische sehr kurze Sätze "
                "(3-6 Wörter) zwischen deutlich längere."
            )
        issues.append("Satzanfänge stärker variieren, keine parallelen Satzmuster.")
        refine_prompt = (
            REFINE.format(issues="\n".join(f"- {i}" for i in issues))
            + f"\nTon: {tone}\n\nText:\n---\n{output}\n---"
        )
        try:
            second = _clean(
                await complete(
                    SYSTEM,
                    refine_prompt,
                    provider=provider,
                    model=model,
                    max_tokens=8192,
                    temperature=0.95,
                )
            )
            if second and len(second.split()) >= len(output.split()) * 0.6:
                second_score = score(second)
                if second_score["score"] <= after["score"]:
                    output = second
                    after = second_score
                    passes = 2
        except Exception:
            pass
    return {
        "text": output,
        "before": before,
        "after": after,
        "words": len(output.split()),
        "passes": passes,
    }
