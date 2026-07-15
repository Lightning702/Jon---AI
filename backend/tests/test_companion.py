import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.cowork_service import detect_work_app
from app.services.focus_service import FocusService, active_window_title
from app.services.routine_service import RoutineService, _app_name, _slot


def test_arbeits_app_erkennung():
    assert detect_work_app("main.py - Visual Studio Code") == "VS Code"
    assert detect_work_app("Mein Buch.docx - Word") == "Word"
    assert detect_work_app("Kapitel 3 - LibreOffice Writer") == "LibreOffice"
    assert detect_work_app("YouTube - Google Chrome") == ""
    assert detect_work_app("") == ""


def test_gewaehlte_app_offen_erkennung(monkeypatch):
    import app.services.cowork_service as cw

    monkeypatch.setattr(cw, "open_window_titles", lambda: ["Kapitel 3 - Word", "Chrome"])
    assert cw.app_open("word") == "Word"
    assert cw.app_open("vscode") == ""
    assert cw.app_open("auto") == "Word"
    monkeypatch.setattr(cw, "open_window_titles", lambda: ["Chrome", "Explorer"])
    assert cw.app_open("word") == ""
    assert cw.app_open("auto") == ""
    assert cw.CHECK_INTERVAL == 300


def test_fokus_start_stop(tmp_path, monkeypatch):
    import app.services.focus_service as fs

    monkeypatch.setattr(fs, "STATS_FILE", tmp_path / "focus.json")
    service = FocusService()
    state = service.start(30, "Mathe lernen")
    assert state["active"] is True
    assert state["goal"] == "Mathe lernen"
    assert service.state()["remaining_seconds"] > 0
    result = service.stop()
    assert result["active"] is False
    assert service.state()["active"] is False


def test_fokus_erkennt_ablenkung(tmp_path, monkeypatch):
    import app.services.focus_service as fs

    monkeypatch.setattr(fs, "STATS_FILE", tmp_path / "focus.json")
    monkeypatch.setattr(fs, "active_window_title", lambda: "YouTube - Google Chrome")
    service = FocusService()
    service.start(30, "lernen")
    service._session["last_nudge"] = 0.0
    service.poll_events()
    service.tick()
    events = service.poll_events()
    assert any(e["kind"] == "nudge" for e in events)


def test_routine_app_name_und_slot():
    assert _app_name("main.py - Projekt - Visual Studio Code") == "Visual Studio Code"
    assert _slot(9)[0] == "morgens"
    assert _slot(20)[0] == "abends"
    assert _slot(3) is None


def test_routine_schlaegt_erst_nach_mehreren_tagen_vor(tmp_path, monkeypatch):
    import app.services.routine_service as rs

    monkeypatch.setattr(rs, "LOG_FILE", tmp_path / "log.json")
    monkeypatch.setattr(rs, "STATE_FILE", tmp_path / "state.json")
    service = RoutineService()
    service._log = {
        f"2026-07-0{i}": {"morgens": {"Spotify": 1}} for i in range(1, 7)
    }
    suggestions = service.suggestions()
    assert suggestions
    assert suggestions[0]["app"] == "Spotify"
    assert suggestions[0]["days"] >= 5
    service.dismiss(suggestions[0]["id"])
    assert all(s["app"] != "Spotify" for s in service.suggestions())
