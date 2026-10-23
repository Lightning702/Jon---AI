from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.skill_service import eingebaute_einspielen


def test_eingebaute_skills_werden_eingespielt_und_aktualisiert(tmp_path):
    quelle = tmp_path / "quelle"
    ziel = tmp_path / "ziel"
    quelle.mkdir()
    (quelle / "web-design.md").write_text("# Web\nv1", encoding="utf-8")
    (quelle / "game-design.md").write_text("# Spiele\nv1", encoding="utf-8")
    assert sorted(eingebaute_einspielen(quelle, ziel)) == ["game-design.md", "web-design.md"]
    assert (ziel / "web-design.md").read_text(encoding="utf-8") == "# Web\nv1"
    (ziel / "game-design.md").write_text("# Spiele\nmeine Regeln", encoding="utf-8")
    (quelle / "web-design.md").write_text("# Web\nv2", encoding="utf-8")
    (quelle / "game-design.md").write_text("# Spiele\nv2", encoding="utf-8")
    assert eingebaute_einspielen(quelle, ziel) == ["web-design.md"]
    assert (ziel / "web-design.md").read_text(encoding="utf-8") == "# Web\nv2"
    assert (ziel / "game-design.md").read_text(encoding="utf-8") == "# Spiele\nmeine Regeln"
    assert eingebaute_einspielen(quelle, ziel) == []


def test_ohne_paket_passiert_nichts(tmp_path):
    assert eingebaute_einspielen(tmp_path / "fehlt", tmp_path / "ziel") == []
    assert not (tmp_path / "ziel").exists()
