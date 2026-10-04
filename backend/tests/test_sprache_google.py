import io
import wave

from app.services import voice_service


def _wav(kanaele: int = 1) -> bytes:
    puffer = io.BytesIO()
    with wave.open(puffer, "wb") as wav:
        wav.setnchannels(kanaele)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x01\x00" * 1600 * kanaele)
    return puffer.getvalue()


class _Antwort:
    def __init__(self, text: str) -> None:
        self._text = text

    def read(self) -> bytes:
        return self._text.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None


def test_rohdaten_ohne_flac(monkeypatch):
    gesehen = {}

    def oeffnen(anfrage, timeout=0):
        gesehen["typ"] = anfrage.headers.get("Content-type")
        gesehen["laenge"] = len(anfrage.data)
        return _Antwort('{"result":[]}\n{"result":[{"alternative":[{"transcript":"erinnere mich um 8 Uhr"}]}]}\n')

    monkeypatch.setattr(voice_service.urllib.request, "urlopen", oeffnen)
    monkeypatch.setattr(voice_service, "_get_whisper", lambda: None)
    assert voice_service.VoiceService().transcribe_wav(_wav()) == "Erinnere mich um 8 Uhr"
    assert gesehen["typ"].startswith("audio/l16; rate=16000")
    assert gesehen["laenge"] == 3200


def test_stereo_wird_nicht_als_rohdaten_gesendet(monkeypatch):
    monkeypatch.setattr(voice_service.urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("kein Aufruf erwartet")))
    assert voice_service._google_rohdaten(_wav(2), "de-DE") == ""


def test_whisper_bekommt_jons_namen_als_hinweis(monkeypatch):
    aufrufe = []

    class Segment:
        text = " Hallo Jon "

    class Modell:
        def transcribe(self, pfad, **werte):
            aufrufe.append(werte)
            return [Segment()], None

    monkeypatch.setattr(voice_service, "_get_whisper", lambda: Modell())
    assert voice_service.VoiceService().transcribe_wav(_wav()) == "Hallo Jon"
    assert aufrufe[0]["language"] == "de" and "Jon" in aufrufe[0]["initial_prompt"]
