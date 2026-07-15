import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.game_service import fallback_actions, sanitize_actions


def test_fallback_versteht_bauwuensche():
    actions = fallback_actions("Bau mir ein Haus aus Glas")
    assert actions[0]["type"] == "build"
    assert actions[0]["structure"] == "haus"
    assert actions[0]["material"] == "glas"
    assert fallback_actions("Grab mal ein Loch")[0]["type"] == "dig"
    assert fallback_actions("Spreng den Berg weg!")[0]["type"] == "tnt"
    assert fallback_actions("komm her")[0]["type"] == "come"
    assert fallback_actions("folg mir")[0] == {"type": "follow", "on": True}
    assert fallback_actions("stopp!")[0]["type"] == "stop"
    assert fallback_actions("wie geht es dir?") == []


def test_sanitize_verwirft_unsinn_und_klemmt_werte():
    actions = sanitize_actions(
        [
            {"type": "build", "structure": "haus", "size": 999, "dx": 5000},
            {"type": "build", "structure": "raumschiff"},
            {"type": "tnt", "count": 99},
            {"type": "hack_pc"},
            "quatsch",
            {"type": "follow", "on": False},
        ]
    )
    assert actions[0]["size"] == 24
    assert actions[0]["dx"] == 40
    assert all(a["type"] != "hack_pc" for a in actions)
    assert len([a for a in actions if a["type"] == "build"]) == 1
    assert next(a for a in actions if a["type"] == "tnt")["count"] == 5
    assert next(a for a in actions if a["type"] == "follow")["on"] is False


def test_telegram_hat_neue_befehle():
    from app.services.telegram_service import TelegramService

    service = TelegramService()
    assert hasattr(service, "_cancel_running")
    assert hasattr(service, "_launch")
    assert isinstance(service._voice_off, set)
