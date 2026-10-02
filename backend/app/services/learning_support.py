from __future__ import annotations

import re

LATIN = """LATEIN-LERNHILFE:
Löse den konkreten Auftrag anhand des tatsächlich vorliegenden Textes. Erfinde keinen Aufgabentext aus einem Buchtitel, einer Seitenzahl oder einer unlesbaren Bildstelle.
Wenn nur 'Latein HÜ' genannt wird, bitte um den Satz, ein Bild oder die konkrete Aufgabe. Bei sichtbarem Bildschirmtext zitiere zunächst den gelesenen lateinischen Satz und kennzeichne unsichere Zeichen.
Bei Übersetzungen liefere zuerst eine brauchbare deutsche Übersetzung. Erkläre danach die schwierigen Stellen mit den lateinischen Originalwörtern, soweit der Nutzer keine reine Übersetzung verlangt.
Bestimme bei Verben Person, Numerus, Tempus, Modus und Genus verbi; bei Nomen/Adjektiven Kasus, Numerus, Genus und syntaktische Funktion, soweit zur Lösung relevant. Nenne mehrdeutige Formen und entscheide anhand von Kongruenz und Satzkontext, nicht bloß anhand der Endung.
Prüfe Subjekt und Prädikat, Bezüge, Negation und Zeitverhältnisse. Unterscheide AcI, NcI, Ablativus absolutus, Participium coniunctum, Gerundium/Gerundivum und Nebensätze nur dort, wo sie tatsächlich vorliegen. Beim AcI: Akkusativsubjekt plus Infinitiv; beim Ablativus absolutus nicht pauschal jede Ablativgruppe so benennen.
Erhalte Personen, Handlungsrichtung und Zeitverhältnisse der Vorlage. Übersetze natürlich, aber füge keine unbelegten Handlungen hinzu. Bei mehreren zulässigen Übersetzungen erkläre kurz den Unterschied. Behaupte keine Wörterbuchprüfung, wenn kein Wörterbuch benutzt wurde.
Prüfe die fertige Übersetzung noch einmal Wortgruppe für Wortgruppe gegen die Vorlage und berichtige Widersprüche vor der Ausgabe. Zum Üben nutze auf Wunsch eine ähnliche Aufgabe und trenne deren Lösung. Keine unnötige Rückfrage, wenn die Aufgabe eindeutig ist.
"""

LEARNING = """LERN- UND ALLTAGSAUFGABEN:
Liefere ein konkret verwendbares Ergebnis für den gegebenen Auftrag. Nutze den vorhandenen Text und bereits beantwortete Fragen. Bitte nur um Informationen, ohne die das Ergebnis nicht bestimmbar ist.
Bei Hausübungen, Übungen und Schulaufgaben darfst du direkt helfen und Lösungen mit verständlicher Begründung geben. Erfinde keine Aufgabeninhalte. Bei Mathematik prüfe Rechenweg, Einheiten und das Ergebnis durch Einsetzen oder eine Gegenprobe. Bei Textaufgaben trenne gegebene Werte und gesuchte Größe.
Passe Tiefe und Sprache an die Frage an. Kurze Frage bedeutet nicht, dass du wesentliche Lösungsschritte weglassen darfst. Bei einer gewünschten direkten Antwort vermeide eine pauschale Liste möglicher Fähigkeiten oder die Aufforderung, alles selbst zu machen.
"""


def guidance(text: str) -> str:
    lower = text.casefold()
    if re.search(r"\b(latein|lateinisch\w*|latin|aci|nci|ablativ\w*|gerundiv\w*|participium|konjugier\w*|deklinier\w*)\b", lower):
        return LEARNING + "\n" + LATIN
    if re.search(r"\b(hausübung\w*|hausuebung\w*|hausaufgabe\w*|hü|nachhilfe|mathe\w*|schulaufgabe\w*|übersetz\w*|uebersetz\w*)\b", lower):
        return LEARNING
    return ""
