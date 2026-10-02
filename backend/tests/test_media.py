import asyncio
import io
import json
import wave
from types import SimpleNamespace

import pytest

from app.services import media_service as media


def wav_bytes():
    result = io.BytesIO()
    with wave.open(result, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(16000)
        writer.writeframes(b"\0\0" * 16000)
    return result.getvalue()


async def stream(data):
    yield data


@pytest.mark.parametrize("url", ["https://youtu.be/abcdefghijk?t=3", "https://www.youtube.com/watch?v=abcdefghijk", "https://youtube.com/shorts/abcdefghijk"])
def test_public_video_urls(url):
    assert media.youtube_id(url) == "abcdefghijk"


@pytest.mark.parametrize("url", ["file:///video", "https://youtube.com.evil.test/watch?v=abcdefghijk", "https://user:pass@youtube.com/watch?v=abcdefghijk", "https://youtube.com/playlist?list=abc"])
def test_invalid_video_urls(url):
    with pytest.raises(ValueError):
        media.youtube_id(url)


def test_captions_preserve_last_segment():
    data = {"events": [{"segs": [{"utf8": "Anfang"}]}, {"segs": [{"utf8": "Anfang"}]}, {"segs": [{"utf8": "Ganz am Ende."}]}]}
    assert media.caption_text(json.dumps(data), "json3") == "Anfang\nGanz am Ende."
    assert media.caption_text("WEBVTT\n\n00:00.000 --> 00:01.000\n<c>Ein &amp; zwei</c>\n\n00:01.000 --> 00:02.000\nEnde", "vtt") == "Ein & zwei\nEnde"


def test_transcription_keeps_entire_file_and_download(tmp_path, monkeypatch):
    from app.services import voice_service
    full = "Hallo " * 7000 + "Letzter Satz."
    model = SimpleNamespace(transcribe=lambda *a, **k: (iter([SimpleNamespace(start=0, end=1, text=full)]), SimpleNamespace(duration=1)))
    monkeypatch.setattr(voice_service, "_get_whisper", lambda: model)
    service = media.MediaService(tmp_path)
    async def run():
        upload = await service.upload("aufnahme.wav", stream(wav_bytes()))
        job = service.start("transcribe", upload_id=upload["id"])
        await service.running[job["id"]]
        result = service.get(job["id"])
        assert result["status"] == "done", result
        assert result["preview_truncated"]
        assert service.file(job["id"], "transkript.txt").read_text(encoding="utf-8") == full
        assert media.MediaService(tmp_path).get(job["id"])["characters"] == len(full)
        with pytest.raises(KeyError):
            service.file(job["id"], "../../private")
    asyncio.run(run())


def test_speech_includes_all_long_text(tmp_path, monkeypatch):
    from app.services import voice_service
    spoken = []
    async def synthesize(text, *a, **k):
        spoken.append(text)
        return text.encode()
    monkeypatch.setattr(voice_service, "synthesize_speech", synthesize)
    text = "Ein vollständiger Satz. " * 400 + "ABSCHLUSS"
    service = media.MediaService(tmp_path)
    async def run():
        job = service.start("speech", text=text)
        await service.running[job["id"]]
        result = service.get(job["id"])
        assert result["status"] == "done", result
        assert len(spoken) > 1
        assert "".join("".join(spoken).split()) == "".join(text.split())
        assert service.file(job["id"], "audio.mp3").read_bytes().endswith(b"ABSCHLUSS")
    asyncio.run(run())


def test_summary_failure_retains_full_transcript(tmp_path, monkeypatch):
    monkeypatch.setattr(media, "fetch_youtube", lambda url: {"text": "Vollständig", "title": "Video", "url": url})
    service = media.MediaService(tmp_path)
    async def fail(*a):
        raise ValueError("Modell offline")
    monkeypatch.setattr(service, "summarize", fail)
    async def run():
        job = service.start("youtube", url="https://youtu.be/abcdefghijk", summarize=True)
        await service.running[job["id"]]
        assert service.get(job["id"])["status"] == "failed"
        assert service.file(job["id"], "transkript.txt").read_text(encoding="utf-8") == "Vollständig"
    asyncio.run(run())


def test_parallel_jobs_and_cancel(tmp_path, monkeypatch):
    from app.services import voice_service
    entered = asyncio.Event()
    release = asyncio.Event()
    async def synthesize(*a, **k):
        entered.set()
        await release.wait()
        return b"audio"
    monkeypatch.setattr(voice_service, "synthesize_speech", synthesize)
    service = media.MediaService(tmp_path)
    async def run():
        first = service.start("speech", text="Erster Auftrag")
        second = service.start("speech", text="Zweiter Auftrag")
        with pytest.raises(ValueError, match="bereits"):
            service.start("speech", text="Dritter Auftrag")
        await entered.wait()
        await service.cancel(first["id"])
        tasks = list(service.running.values())
        release.set()
        await asyncio.gather(*tasks)
        assert service.get(first["id"])["status"] == "cancelled"
        assert service.get(first["id"])["files"] == []
        assert service.get(second["id"])["status"] == "done"
    asyncio.run(run())


def test_invalid_and_empty_uploads(tmp_path, monkeypatch):
    service = media.MediaService(tmp_path)
    async def run():
        with pytest.raises(ValueError):
            await service.upload("evil.exe", stream(b"a"))
        with pytest.raises(ValueError, match="leer"):
            await service.upload("leer.mp3", stream(b""))
        monkeypatch.setattr(media, "MAX_UPLOAD", 3)
        with pytest.raises(ValueError, match="größer"):
            await service.upload("gross.mp3", stream(b"1234"))
        upload = await service.upload("fake.mp3", stream(b"abc"))
        job = service.start("transcribe", upload_id=upload["id"])
        await service.running[job["id"]]
        assert service.get(job["id"])["status"] == "failed"
    asyncio.run(run())


def test_api_requires_token_and_downloads_complete_text(tmp_path, monkeypatch):
    import os
    import httpx
    from fastapi import FastAPI
    from app.api.media_routes import router
    from app.core.auth import TokenMiddleware

    service = media.MediaService(tmp_path)
    monkeypatch.setattr(media, "_service", service)
    monkeypatch.setattr(media, "fetch_youtube", lambda url: {"text": "Vollständiger letzter Satz", "title": "Video", "url": url})
    app = FastAPI()
    app.add_middleware(TokenMiddleware)
    app.include_router(router)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
            assert (await client.get("/api/media/jobs")).status_code == 401
            client.headers["X-Jon-Token"] = os.environ["JON_TOKEN"]
            assert (await client.post("/api/media/uploads?name=leer.mp3", content=b"")).status_code == 400
            response = await client.post("/api/media/jobs", json={"kind": "youtube", "url": "https://youtu.be/abcdefghijk"})
            assert response.status_code == 200
            key = response.json()["id"]
            if key in service.running:
                await service.running[key]
            download = await client.get(f"/api/media/jobs/{key}/files/transkript.txt")
            assert download.status_code == 200
            assert download.text == "Vollständiger letzter Satz"
            assert (await client.get(f"/api/media/jobs/{key}/files/source.mp3")).status_code == 404
    asyncio.run(run())
