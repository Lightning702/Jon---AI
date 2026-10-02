from __future__ import annotations

import json

from app.services.tools import ToolBox


def test_persona_werkzeuge_laufen_ohne_namensfehler():
    box = ToolBox()
    for name, args in (
        ("remember_about_user", {"note": "Mag Pizza mit Oliven"}),
        ("journal", {"entry": "Heute viel gelernt."}),
        ("set_mood", {"mood": "froh"}),
        ("read_journal", {}),
    ):
        ergebnis = json.loads(box._execute(name, args))
        assert "persona" not in json.dumps(ergebnis, ensure_ascii=False), (name, ergebnis)
        assert not (isinstance(ergebnis, dict) and "is not defined" in str(ergebnis.get("error", ""))), (name, ergebnis)
