from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Werkzeug:
    name: str
    beschreibung: str
    eigenschaften: dict[str, Any] = field(default_factory=dict)
    pflicht: list[str] = field(default_factory=list)
    stufe: str = "standard"
    recht: str = ""
    kurz: str = ""
    frei: bool = True

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.beschreibung,
                "parameters": {
                    "type": "object",
                    "properties": dict(self.eigenschaften),
                    "required": list(self.pflicht),
                },
            },
        }


class Connector:
    id = ""
    name = ""

    def bereit(self) -> bool:
        return True

    def geraete(self) -> list[dict]:
        return []

    def werkzeuge(self) -> list[Werkzeug]:
        return []

    def kann(self, name: str) -> bool:
        return any(werkzeug.name == name for werkzeug in self.werkzeuge())

    def uebersicht(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "bereit": self.bereit(),
            "geraete": self.geraete(),
            "werkzeuge": [
                {
                    "name": werkzeug.name,
                    "stufe": werkzeug.stufe,
                    "recht": werkzeug.recht,
                    "beschreibung": werkzeug.beschreibung,
                }
                for werkzeug in self.werkzeuge()
            ],
        }

    async def ausfuehren(self, name: str, args: dict[str, Any]) -> dict:
        raise NotImplementedError
