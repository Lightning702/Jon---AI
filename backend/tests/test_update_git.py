from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

import pytest

from app.services.update_process import git_aktualisieren

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="Git fehlt")

ICH = ["-c", "user.name=Test", "-c", "user.email=test@example.com", "-c", "init.defaultBranch=main", "-c", "core.autocrlf=false"]


def sh(cwd: Path, *argumente: str) -> str:
    return subprocess.run(["git", *ICH, *argumente], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture()
def repos(tmp_path, monkeypatch):
    leer = tmp_path / "gitconfig"
    leer.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(leer))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    server = tmp_path / "server.git"
    subprocess.run(["git", *ICH, "init", "--bare", "-b", "main", str(server)], check=True, capture_output=True)
    entwickler = tmp_path / "entwickler"
    subprocess.run(["git", *ICH, "clone", str(server), str(entwickler)], check=True, capture_output=True)
    (entwickler / "frontend").mkdir()
    for name, inhalt in {"a.txt": "a1\n", "b.txt": "b1\n", "frontend/x.ts": "x1\n"}.items():
        (entwickler / name).write_text(inhalt, encoding="utf-8")
    sh(entwickler, "add", "-A")
    sh(entwickler, "commit", "-m", "Start")
    sh(entwickler, "push", "origin", "HEAD:main")
    pc = tmp_path / "Jon"
    subprocess.run(["git", *ICH, "clone", str(server), str(pc)], check=True, capture_output=True)

    def veroeffentlichen(dateien: dict[str, str]) -> None:
        for name, inhalt in dateien.items():
            ziel = entwickler / name
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(inhalt, encoding="utf-8")
        sh(entwickler, "add", "-A")
        sh(entwickler, "commit", "-m", "Neu")
        sh(entwickler, "push", "origin", "HEAD:main")

    return pc, veroeffentlichen


def laufen(pc: Path) -> tuple[dict, str]:
    ergebnis: dict = {}

    async def sammeln():
        return "".join([zeile async for zeile in git_aktualisieren(pc, ergebnis)])

    return ergebnis, asyncio.run(sammeln())


def test_lokale_aenderungen_und_eigene_dateien_bleiben_erhalten(repos):
    pc, veroeffentlichen = repos
    veroeffentlichen({"b.txt": "b2\n", "frontend/x.ts": "x2\n"})
    (pc / "a.txt").write_text("meine Arbeit\n", encoding="utf-8")
    (pc / "notizen.txt").write_text("privat\n", encoding="utf-8")
    ergebnis, text = laufen(pc)
    assert ergebnis["ok"], text
    assert (pc / "a.txt").read_text(encoding="utf-8") == "meine Arbeit\n"
    assert (pc / "notizen.txt").read_text(encoding="utf-8") == "privat\n"
    assert (pc / "b.txt").read_text(encoding="utf-8") == "b2\n"
    assert "frontend/x.ts" in ergebnis["dateien"]
    assert ergebnis["sicherung"] in sh(pc, "branch", "--list", "sicherung-vor-update-*")
    assert not sh(pc, "stash", "list")


def test_bearbeitete_datei_der_neuen_version_bricht_ohne_aenderung_ab(repos):
    pc, veroeffentlichen = repos
    veroeffentlichen({"b.txt": "b2\n"})
    (pc / "b.txt").write_text("meine Version\n", encoding="utf-8")
    vorher = sh(pc, "rev-parse", "HEAD")
    ergebnis, text = laufen(pc)
    assert not ergebnis["ok"]
    assert ergebnis["konflikte"] == ["b.txt"]
    assert (pc / "b.txt").read_text(encoding="utf-8") == "meine Version\n"
    assert sh(pc, "rev-parse", "HEAD") == vorher
    assert "nichts verändert" in text


def test_unversionierte_datei_wird_nicht_ueberschrieben(repos):
    pc, veroeffentlichen = repos
    veroeffentlichen({"neu.txt": "vom Server\n"})
    (pc / "neu.txt").write_text("von mir\n", encoding="utf-8")
    ergebnis, _ = laufen(pc)
    assert not ergebnis["ok"]
    assert ergebnis["konflikte"] == ["neu.txt"]
    assert (pc / "neu.txt").read_text(encoding="utf-8") == "von mir\n"


def test_aktueller_stand_und_eigene_commits(repos):
    pc, veroeffentlichen = repos
    ergebnis, _ = laufen(pc)
    assert ergebnis["ok"] and ergebnis.get("aktuell")
    (pc / "a.txt").write_text("eigener Commit\n", encoding="utf-8")
    sh(pc, "commit", "-am", "Eigenes")
    veroeffentlichen({"b.txt": "b3\n"})
    ergebnis, text = laufen(pc)
    assert ergebnis["ok"], text
    assert (pc / "a.txt").read_text(encoding="utf-8") == "eigener Commit\n"
    assert (pc / "b.txt").read_text(encoding="utf-8") == "b3\n"
    assert "Eigenes" in sh(pc, "log", "--format=%s")
