import asyncio
from pathlib import Path

import pytest

from app.services import bildschirm_video as bv
from app.services import telegram_service as ts
from app.services.settings_service import get_settings_service


@pytest.fixture(autouse=True)
def _video_einstellungen_zuruecksetzen():
    yield
    get_settings_service().update(
        {"telegram_aktionsvideo": True, "telegram_video_bildschirm": "maus"}
    )


def test_nur_sichtbare_werkzeuge_starten_ein_video():
    assert bv.sichtbar("mouse_click")
    assert bv.sichtbar("keyboard_type")
    assert bv.sichtbar("start_program")
    assert bv.sichtbar("browser_goto")
    assert not bv.sichtbar("browser_status")
    assert not bv.sichtbar("web_search")
    assert not bv.sichtbar("")


MONITORE = [
    {"links": 0, "oben": 0, "rechts": 1366, "unten": 768},
    {"links": 1366, "oben": 0, "rechts": 3286, "unten": 1080},
]


def test_bildschirm_nach_nummer_oder_maus():
    assert bv.waehle_bereich("2", MONITORE, None) == {
        "x": 1366,
        "y": 0,
        "breite": 1920,
        "hoehe": 1080,
    }
    assert bv.waehle_bereich("maus", MONITORE, (2000, 500))["x"] == 1366
    assert bv.waehle_bereich("maus", MONITORE, (100, 100))["x"] == 0
    assert bv.waehle_bereich("9", MONITORE, None)["x"] == 0
    assert bv.waehle_bereich("maus", [], (1, 1)) is None


def test_ffmpeg_befehl_nimmt_den_bereich_mit_mauszeiger_auf(tmp_path):
    ziel = tmp_path / "v.mp4"
    feld = {"x": 1366, "y": 0, "breite": 1920, "hoehe": 1080}
    befehl = bv.ffmpeg_befehl("ffmpeg", feld, ziel, system="nt")
    text = " ".join(befehl)
    assert "-f gdigrab" in text
    assert "-draw_mouse 1" in text
    assert "-offset_x 1366" in text
    assert "-video_size 1920x1080" in text
    assert "libx264" in text
    assert befehl[-1] == str(ziel)
    linux = " ".join(
        bv.ffmpeg_befehl("ffmpeg", feld, ziel, encoder="mpeg4", system="posix", anzeige=":0")
    )
    assert "-f x11grab" in linux
    assert ":0+1366,0" in linux
    assert "mpeg4" in linux


class _FakeAufnahme:
    gestartet: list = []
    fehler = ""

    def __init__(self, welcher="maus", *args, **kwargs):
        self.welcher = welcher
        self.ziel = None

    def starten(self):
        if _FakeAufnahme.fehler:
            raise bv.VideoFehler(_FakeAufnahme.fehler)
        _FakeAufnahme.gestartet.append(self.welcher)

    def stoppen(self):
        pfad = Path(bv.ORDNER) / "fake.mp4"
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_bytes(b"x" * 2048)
        return pfad

    def verwerfen(self):
        return None


@pytest.fixture
def fake_aufnahme(monkeypatch):
    _FakeAufnahme.gestartet = []
    _FakeAufnahme.fehler = ""
    monkeypatch.setattr(bv, "Aufnahme", _FakeAufnahme)
    monkeypatch.setattr(bv, "ANLAUF", 0.0)
    return _FakeAufnahme


def test_aktionsvideo_startet_einmal_beim_ersten_sichtbaren_werkzeug(fake_aufnahme):
    async def lauf():
        begleiter = bv.Aktionsvideo("2")
        await begleiter.werkzeug("web_search")
        assert fake_aufnahme.gestartet == []
        await begleiter.werkzeug("mouse_click")
        await begleiter.werkzeug("keyboard_type")
        assert fake_aufnahme.gestartet == ["2"]
        return await begleiter.beenden(0)

    pfad = asyncio.run(lauf())
    assert pfad is not None and pfad.name == "fake.mp4"


def test_aktionsvideo_merkt_sich_den_fehler(fake_aufnahme):
    fake_aufnahme.fehler = "kein Bildschirm"

    async def lauf():
        begleiter = bv.Aktionsvideo()
        await begleiter.werkzeug("mouse_click")
        return begleiter, await begleiter.beenden(0)

    begleiter, pfad = asyncio.run(lauf())
    assert pfad is None
    assert begleiter.fehler == "kein Bildschirm"


def _telegram_mit_fakes(monkeypatch, gesendet, videos):
    async def fake_send(self, chat_id, text):
        gesendet.append(text)

    async def fake_video(self, chat_id, pfad, beschriftung=""):
        videos.append(beschriftung)
        return True

    async def fake_typing(self, chat_id):
        await asyncio.sleep(3600)

    monkeypatch.setattr(ts.TelegramService, "send", fake_send)
    monkeypatch.setattr(ts.TelegramService, "video_senden", fake_video)
    monkeypatch.setattr(ts.TelegramService, "_typing", fake_typing)
    return ts.TelegramService()


def test_nach_einer_aktion_kommt_das_video(monkeypatch, fake_aufnahme):
    gesendet: list = []
    videos: list = []
    dienst = _telegram_mit_fakes(monkeypatch, gesendet, videos)

    async def fake_answer(self, chat_id, text, begleiter=None):
        await begleiter.werkzeug("start_program")
        return "YouTube ist offen.", []

    monkeypatch.setattr(ts.TelegramService, "_answer", fake_answer)
    monkeypatch.setattr(ts.TelegramService, "_direct_control", lambda self, text: None)
    asyncio.run(dienst._handle("1", "oeffne youtube"))
    assert "YouTube ist offen." in gesendet
    assert videos and videos[0].startswith("🎬")


def test_ohne_aktion_kein_video_und_abschaltbar(monkeypatch, fake_aufnahme):
    gesendet: list = []
    videos: list = []
    dienst = _telegram_mit_fakes(monkeypatch, gesendet, videos)

    async def nur_text(self, chat_id, text, begleiter=None):
        await begleiter.werkzeug("web_search")
        return "Es ist sonnig.", []

    monkeypatch.setattr(ts.TelegramService, "_answer", nur_text)
    monkeypatch.setattr(ts.TelegramService, "_direct_control", lambda self, text: None)
    asyncio.run(dienst._handle("1", "wie ist das wetter"))
    assert videos == []

    get_settings_service().update({"telegram_aktionsvideo": False})
    assert dienst._aktionsvideo() is None


def test_direktbefehl_schickt_ebenfalls_ein_video(monkeypatch, fake_aufnahme):
    gesendet: list = []
    videos: list = []
    dienst = _telegram_mit_fakes(monkeypatch, gesendet, videos)
    monkeypatch.setattr(
        ts.TelegramService, "_direct_control", lambda self, text: "🖱️ Linksklick"
    )
    asyncio.run(dienst._handle("1", "klick"))
    assert "🖱️ Linksklick" in gesendet
    assert fake_aufnahme.gestartet
    assert videos


def test_live_video_schickt_stuecke_bis_zum_ende(monkeypatch, tmp_path):
    gesendet: list = []
    videos: list = []
    dienst = _telegram_mit_fakes(monkeypatch, gesendet, videos)
    datei = tmp_path / "stueck.mp4"
    datei.write_bytes(b"x" * 2048)

    async def fake_clip(welcher="maus", sekunden=10.0):
        await asyncio.sleep(0.02)
        return datei

    monkeypatch.setattr(bv, "clip", fake_clip)
    monkeypatch.setattr(ts, "LIVE_DAUER", 0.1)
    asyncio.run(dienst._live_video_schleife("1", "2"))
    assert len(videos) >= 2
    assert videos[0].startswith("🔴 Live 1")
    assert "Bildschirm 2" in gesendet[0]


def test_livestop_beendet_das_live_video(monkeypatch, tmp_path):
    gesendet: list = []
    videos: list = []
    dienst = _telegram_mit_fakes(monkeypatch, gesendet, videos)
    datei = tmp_path / "stueck.mp4"
    datei.write_bytes(b"x" * 2048)

    async def fake_clip(welcher="maus", sekunden=10.0):
        await asyncio.sleep(0.05)
        return datei

    monkeypatch.setattr(bv, "clip", fake_clip)

    async def lauf():
        await dienst.live_video_starten("1", "maus")
        await asyncio.sleep(0.12)
        aufgabe = dienst._live_videos["1"]
        await dienst.live_stoppen("1")
        await asyncio.sleep(0.05)
        return aufgabe

    aufgabe = asyncio.run(lauf())
    assert aufgabe.done()
    assert any("beendet" in text for text in gesendet)


def test_video_befehl_schaltet_und_nimmt_auf(monkeypatch):
    gesendet: list = []
    videos: list = []
    dienst = _telegram_mit_fakes(monkeypatch, gesendet, videos)
    aufnahmen: list = []

    async def fake_schicken(self, chat_id, sekunden):
        aufnahmen.append(sekunden)

    monkeypatch.setattr(ts.TelegramService, "video_schicken", fake_schicken)
    asyncio.run(dienst._video_befehl("1", "/video aus"))
    assert get_settings_service().get()["telegram_aktionsvideo"] is False
    asyncio.run(dienst._video_befehl("1", "/video an"))
    assert get_settings_service().get()["telegram_aktionsvideo"] is True
    asyncio.run(dienst._video_befehl("1", "/video 5"))
    asyncio.run(dienst._video_befehl("1", "/video 500"))
    asyncio.run(dienst._video_befehl("1", "/video"))
    assert aufnahmen == [5, ts.VIDEO_MAX, ts.VIDEO_KURZ]
