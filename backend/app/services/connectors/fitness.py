from __future__ import annotations

from typing import Any

from app.services.connectors.basis import Connector, Werkzeug
from app.services.fitness_service import ARTEN, FitnessFehler, get_fitness_service

FITNESS_WOERTER = (
    "schritt",
    "gym",
    "fitness",
    "training",
    "trainier",
    "workout",
    "sport",
    "muskel",
    "bankdr",
    "kniebeug",
    "kreuzheb",
    "klimmz",
    "liegestütz",
    "liegestuetz",
    "gelaufen",
    "joggen",
    "gejoggt",
    "radfahr",
    "geradelt",
    "geschwommen",
    "körpergewicht",
    "koerpergewicht",
    "abgenommen",
    "zugenommen",
    "wiege",
    "sätze",
    "saetze",
    "wiederholung",
    "cardio",
    "hantel",
    "rekord",
    "bestleistung",
)


class FitnessConnector(Connector):
    id = "fitness"
    name = "Fitness"
    woerter = FITNESS_WOERTER

    def werkzeuge(self) -> list[Werkzeug]:
        satz = {
            "type": "object",
            "properties": {"wdh": {"type": "integer"}, "gewicht": {"type": "number", "description": "kg, 0 ohne Gewicht"}},
        }
        uebung = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "saetze": {"type": "array", "items": satz}},
        }
        return [
            Werkzeug(
                name="fitness_training_eintragen",
                beschreibung=(
                    "Trägt ein Training ins Fitness-Tagebuch des Nutzers ein. Nimm das immer, wenn "
                    "er erzählt, was er trainiert hat (Gym, Laufen, Rad, Schwimmen, Yoga). Kraftübungen "
                    "entweder als uebungen mit saetze (wdh, gewicht in kg) oder einfach als text wie "
                    "'Bankdrücken 3x10 60kg, Kniebeugen 4x8 80kg, 20 Liegestütze'. Ausdauer mit "
                    "dauer_min und distanz_km. datum: heute, gestern oder TT.MM.JJJJ."
                ),
                eigenschaften={
                    "art": {"type": "string", "enum": list(ARTEN)},
                    "titel": {"type": "string", "description": "Kurzer Name, z.B. Push Day oder Morgenlauf."},
                    "text": {"type": "string", "description": "Übungen als Freitext."},
                    "uebungen": {"type": "array", "items": uebung},
                    "dauer_min": {"type": "integer"},
                    "distanz_km": {"type": "number"},
                    "datum": {"type": "string"},
                    "notiz": {"type": "string"},
                },
                pflicht=["art"],
                stufe="standard",
                kurz="Trägt ein Training ein.",
            ),
            Werkzeug(
                name="fitness_uebersicht",
                beschreibung=(
                    "Zeigt Schritte (heute, Verlauf, Ziel), Trainings dieser Woche, Serie, letzte "
                    "Trainings, Rekorde pro Übung und Körpergewicht. Nimm das für Fragen wie 'Wie viele "
                    "Schritte habe ich heute?' oder 'Was habe ich diese Woche trainiert?'."
                ),
                eigenschaften={"tage": {"type": "integer", "description": "Wie viele Tage Schrittverlauf, Standard 7."}},
                pflicht=[],
                stufe="standard",
                kurz="Zeigt deine Fitness-Übersicht.",
            ),
            Werkzeug(
                name="fitness_ziel_setzen",
                beschreibung="Setzt das tägliche Schrittziel und/oder wie oft pro Woche trainiert werden soll.",
                eigenschaften={"schritte": {"type": "integer"}, "trainings_pro_woche": {"type": "integer"}},
                pflicht=[],
                stufe="standard",
                kurz="Setzt deine Fitnessziele.",
            ),
            Werkzeug(
                name="fitness_gewicht_eintragen",
                beschreibung="Trägt das Körpergewicht des Nutzers in kg ein (datum: heute, gestern oder TT.MM.JJJJ).",
                eigenschaften={"kg": {"type": "number"}, "datum": {"type": "string"}},
                pflicht=["kg"],
                stufe="standard",
                kurz="Trägt dein Gewicht ein.",
            ),
            Werkzeug(
                name="fitness_training_loeschen",
                beschreibung="Löscht ein falsch eingetragenes Training. Die id steht in fitness_uebersicht.",
                eigenschaften={"id": {"type": "string"}},
                pflicht=["id"],
                stufe="standard",
                kurz="Löscht ein Training.",
            ),
        ]

    async def ausfuehren(self, name: str, args: dict[str, Any]) -> dict:
        dienst = get_fitness_service()
        try:
            if name == "fitness_training_eintragen":
                return dienst.training_eintragen(args)
            if name == "fitness_uebersicht":
                try:
                    tage = int(args.get("tage") or 7)
                except (TypeError, ValueError):
                    tage = 7
                return dienst.uebersicht(tage)
            if name == "fitness_ziel_setzen":
                return dienst.ziel_setzen(args.get("schritte"), args.get("trainings_pro_woche"))
            if name == "fitness_gewicht_eintragen":
                return dienst.gewicht_eintragen(args.get("kg"), args.get("datum"))
            if name == "fitness_training_loeschen":
                return {"geloescht": dienst.training_loeschen(str(args.get("id", "")))}
        except FitnessFehler as exc:
            return {"error": str(exc)}
        return {"error": f"Das Fitness-Werkzeug {name} gibt es nicht."}
