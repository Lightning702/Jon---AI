from datetime import date
import asyncio
import json
from types import SimpleNamespace

import pytest

from app.services.daily_memory import DailyMemory, resolve_day
from app.services.mini_jon_agent import MiniJonAgent
from app.services import mini_jon_screen as screen


def test_sunday_lunch_survives_restart_and_does_not_move_to_next_week(tmp_path):
    path = tmp_path / "memory.json"
    saved = DailyMemory(path).respond("Am Sonntag gibt es Schnitzel zu Mittag", date(2026, 10, 2))
    assert "04.10.2026" in saved
    memory = DailyMemory(path)
    assert "Schnitzel" in memory.respond("Was gibt es heute zu Mittag?", date(2026, 10, 4))
    assert "Schnitzel" in memory.respond("Was gibt es am Sonntag zu Mittag?", date(2026, 10, 4))
    assert "noch nichts" in memory.respond("Was gibt es am Sonntag zu Mittag?", date(2026, 10, 5))
    assert memory.list()[0]["date"] == "2026-10-04"


def test_meal_update_is_specific_and_forget_persists(tmp_path):
    memory = DailyMemory(tmp_path / "memory.json")
    now = date(2026, 10, 2)
    for text in ("Am Sonntag gibt es Schnitzel zu Mittag", "Am Sonntag gibt es Suppe zu Abend", "Am Sonntag gibt es Nudeln zu Mittag"):
        assert memory.respond(text, now)
    assert len(memory.list()) == 2
    assert "Nudeln" in memory.respond("Was essen wir Sonntag zum Mittagessen?", now)
    assert memory.delete("2026-10-04:Mittagessen")
    assert len(DailyMemory(memory.path).list()) == 1
    assert not memory.delete("absent")


@pytest.mark.parametrize("text", [
    "Am Sonntag gibt es Schnitzel zu Mittag?", "Wenn am Sonntag gibt es Schnitzel zu Mittag",
    "Am Sonntag gibt es vielleicht Schnitzel zu Mittag", 'Übersetze: "Am Sonntag gibt es Schnitzel zu Mittag"',
    "Am Sonntag gibt es kein Schnitzel zu Mittag", "Was gibt es Sonntag zu Mittag?",
])
def test_questions_examples_and_uncertainty_are_not_saved(tmp_path, text):
    memory = DailyMemory(tmp_path / "memory.json")
    memory.respond(text, date(2026, 10, 2))
    assert memory.list() == []


def test_dates_handle_year_rollover_and_same_day():
    assert resolve_day("morgen", date(2026, 12, 31)) == date(2027, 1, 1)
    assert resolve_day("sonntag", date(2026, 10, 4)) == date(2026, 10, 4)
    assert resolve_day("nächsten Sonntag", date(2026, 10, 4)) == date(2026, 10, 11)


@pytest.fixture
def vision(monkeypatch, tmp_path):
    from app.services import mini_jon_agent

    agent = MiniJonAgent(tmp_path / "agent.json")
    agent.configure({"screen_enabled": True})
    context = {"supported": True, "title": "Latein", "pid": 1, "process": "editor", "bounds": {"x": 0, "y": 0, "width": 800, "height": 600}}
    calls = []
    async def describe(*args, **kwargs):
        calls.append(args)
        return json.dumps({"observation": "Ein lateinischer Satz", "visible_text": "Marcus dicit puellam legere.", "confidence": .9, "activity": "learning", "next_action": {"type": "explain", "text": "puellam ist der Subjektsakkusativ."}})
    provider = SimpleNamespace(describe_image=describe)
    async def explain(*args):
        return "Marcus sagt, dass das Mädchen liest. puellam ist das Subjekt des AcI."
    monkeypatch.setattr(screen, "explain_observation", explain)
    monkeypatch.setattr(screen, "destination", lambda: {"provider": "local", "model": "vision", "identity": "local@host", "local": True, "available": True})
    monkeypatch.setattr(screen, "get_registry", lambda: SimpleNamespace(get=lambda _: provider))
    monkeypatch.setattr(mini_jon_agent, "foreground", lambda: dict(context))
    monkeypatch.setattr(screen, "capture", lambda _: b"image bytes")
    return agent, context, calls, provider


def test_vision_reads_current_window_and_deduplicates(vision):
    agent, context, calls, provider = vision
    async def run():
        result = await screen.analyze(agent, "Was heißt der Satz?", automatic=True)
        assert result["visible_text"] == "Marcus dicit puellam legere."
        assert result["next_action"]["type"] == "explain"
        assert await screen.analyze(agent, automatic=True) == {"skipped": True}
        assert len(calls) == 1
        assert not list(agent.path.parent.glob("*.jpg"))
    asyncio.run(run())


@pytest.mark.parametrize("protection", ["privacy", "blacklist", "cloud", "disabled"])
def test_protection_blocks_capture_and_provider(monkeypatch, vision, protection):
    agent, context, calls, _ = vision
    def capture(_):
        pytest.fail("No pixels may be captured")
    monkeypatch.setattr(screen, "capture", capture)
    if protection == "privacy": agent.configure({"privacy": True})
    if protection == "disabled": agent.configure({"screen_enabled": False})
    if protection == "blacklist": context["title"] = "Bitwarden"
    if protection == "cloud": monkeypatch.setattr(screen, "destination", lambda: {"provider": "cloud", "identity": "cloud@host", "local": False, "available": True})
    with pytest.raises(ValueError): asyncio.run(screen.analyze(agent))
    assert not calls


def test_window_change_during_capture_is_not_uploaded(monkeypatch, vision):
    agent, context, calls, _ = vision
    def capture(_):
        context["title"] = "another window"
        return b"pixels"
    monkeypatch.setattr(screen, "capture", capture)
    with pytest.raises(ValueError, match="geändert"): asyncio.run(screen.analyze(agent))
    assert not calls


def test_privacy_change_discards_inflight_vision(vision):
    agent, _, _, provider = vision
    async def describe(*args, **kwargs):
        agent.configure({"privacy": True})
        return '{"observation":"secret"}'
    provider.describe_image = describe
    assert asyncio.run(screen.analyze(agent)) == {"skipped": True}
    assert agent.state["screen"] is None


def test_low_confidence_cannot_start_actions(vision):
    agent, _, _, provider = vision
    async def describe(*args, **kwargs):
        return '{"observation":"unsicher", "confidence":0.2, "next_action":{"type":"command","text":"delete files"}}'
    provider.describe_image = describe
    result = asyncio.run(screen.analyze(agent))
    assert result["next_action"]["type"] == "ask"
    assert "delete" not in result["next_action"]["text"]


def test_manual_vision_uses_separate_subject_review(vision):
    result = asyncio.run(screen.analyze(vision[0], "Übersetze den Satz."))
    assert result["reviewed"]
    assert "Subjekt des AcI" in result["next_action"]["text"]


def test_invalid_json_escape_is_data_not_a_command():
    data = screen.parse_observation('{"observation":"Text", "visible_text":"Marcus\\Uebersetze"}')
    assert data["visible_text"] == "Marcus\\Uebersetze"
    with pytest.raises(ValueError): screen.parse_observation("Nicht lesbares JSON")


def test_specialist_without_search_reasons_and_never_opens_browser(monkeypatch):
    from app.services import llm
    from app.services.agenten_service import AgentenService
    from app.services.tools import ToolBox
    calls = []
    async def complete(system, user, **kwargs):
        calls.append((system, user))
        return "puellam ist Akkusativ Singular und Subjekt des AcI."
    async def execute(*args, **kwargs): pytest.fail("Unrequested external tool")
    monkeypatch.setattr(llm, "complete", complete)
    monkeypatch.setattr(ToolBox, "execute", execute)
    for tool in ("keins", "browser_task", "unknown"):
        result = asyncio.run(AgentenService()._teil_ausfuehren({"titel": "Latein", "auftrag": "Prüfe puellam.", "werkzeug": tool}))
        assert not result.fehler
        assert "Akkusativ" in result.ergebnis
    assert len(calls) == 3


def test_chat_memory_works_without_network_and_keeps_model(monkeypatch, tmp_path):
    from app.services import daily_memory
    from app.services.chat_service import ChatService
    from app.schemas import ChatIn
    monkeypatch.setattr(daily_memory, "_service", DailyMemory(tmp_path / "memory.json"))
    monkeypatch.setattr(daily_memory, "today", lambda: date(2026, 10, 2))
    service = ChatService()
    monkeypatch.setattr(service, "resolve", lambda _: ("test-provider", "test-model"))
    async def route(*args): pytest.fail("No model connection needed")
    monkeypatch.setattr(service, "route", route)
    async def run(text):
        return [event async for event in service.stream(ChatIn(messages=[{"role": "user", "content": text}], persist=False))]
    events = asyncio.run(run("Am Sonntag gibt es Schnitzel zu Mittag"))
    assert events[0]["provider"] == "test-provider"
    assert events[0]["from_memory"]
    monkeypatch.setattr(daily_memory, "today", lambda: date(2026, 10, 4))
    assert "Schnitzel" in asyncio.run(run("Was gibt es heute zu Mittag?"))[1]["delta"]
