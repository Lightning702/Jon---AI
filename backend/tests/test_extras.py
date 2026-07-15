import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_pomodoro_zyklen(monkeypatch):
    import time as _time

    from app.services.pomodoro_service import PomodoroService

    svc = PomodoroService()
    state = svc.start(25, 5, 3, "Lernen")
    assert state["active"] and state["phase"] == "work" and state["rounds"] == 3
    svc._session["ends"] = _time.time() - 1
    svc.tick()
    assert svc.state()["phase"] == "break"
    svc._session["ends"] = _time.time() - 1
    svc.tick()
    assert svc.state()["phase"] == "work" and svc.state()["round"] == 2
    events = svc.poll_events()
    assert any(e["kind"] == "pomodoro" for e in events)


def test_cleanup_kategorien():
    from app.services.cleanup_service import _category

    assert _category(".jpg") == "Bilder"
    assert _category(".mp3") == "Musik"
    assert _category(".pdf") == "Dokumente"
    assert _category(".xyz") == "Sonstiges"


def test_notes_crud(tmp_path, monkeypatch):
    import app.services.notes_service as ns

    monkeypatch.setattr(ns, "NOTES_FILE", tmp_path / "notes.json")
    svc = ns.NotesService()
    note = svc.add("Milch kaufen", "blau")
    assert note["color"] == "blau"
    svc.update(note["id"], pinned=True, done=True)
    items = svc.list()
    assert items[0]["pinned"] and items[0]["done"]
    assert svc.delete(note["id"])
    assert svc.list() == []


def test_vault_verschluesselung(tmp_path, monkeypatch):
    import app.services.vault_service as vs

    monkeypatch.setattr(vs, "VAULT_FILE", tmp_path / "vault.dat")
    svc = vs.VaultService()
    assert not svc.exists()
    assert svc.create("geheim12")["ok"]
    entry = svc.add("GitHub", "felix", "s3cret!")
    assert entry["title"] == "GitHub"
    assert svc.reveal(entry["id"])["secret"] == "s3cret!"
    raw = (tmp_path / "vault.dat").read_bytes()
    assert b"s3cret!" not in raw
    svc.lock()
    assert svc.reveal(entry["id"]).get("error")
    assert svc.unlock("falsch").get("error")
    assert svc.unlock("geheim12")["ok"]
    assert len(svc.list()["entries"]) == 1


def test_vault_generator():
    from app.services.vault_service import VaultService

    pw = VaultService().generate(24, True)
    assert len(pw) == 24
    assert VaultService().generate(4, False) and len(VaultService().generate(4, False)) == 6
