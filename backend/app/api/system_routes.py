from __future__ import annotations

import asyncio
import base64
import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.system_service import SystemService

router = APIRouter(prefix="/api/system")
_service = SystemService()
_voice = None
_voice_error: str | None = None


def _get_voice():
    global _voice, _voice_error
    if _voice is None and _voice_error is None:
        try:
            from app.services.voice_service import VoiceService

            _voice = VoiceService()
        except Exception as exc:
            _voice_error = str(exc)
    if _voice is None:
        raise HTTPException(
            status_code=501,
            detail=(
                "Spracherkennung nicht verfuegbar: "
                f"{_voice_error}. Installiere: pip install SpeechRecognition audioop-lts"
            ),
        )
    return _voice


class CommandIn(BaseModel):
    command: str


class CommandOut(BaseModel):
    exit_code: int
    stdout: str
    stderr: str


class UrlIn(BaseModel):
    url: str


class ProgramIn(BaseModel):
    path: str
    args: list[str] = []


class NameIn(BaseModel):
    name: str


class PathIn(BaseModel):
    path: str


class MoveIn(BaseModel):
    source: str
    destination: str


class WriteIn(BaseModel):
    path: str
    content: str


@router.post("/powershell", response_model=CommandOut)
async def powershell(payload: CommandIn) -> CommandOut:
    try:
        result = _service.run_powershell(payload.command)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return CommandOut(**result.__dict__)


@router.post("/cmd", response_model=CommandOut)
async def cmd(payload: CommandIn) -> CommandOut:
    try:
        result = _service.run_cmd(payload.command)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return CommandOut(**result.__dict__)


@router.post("/open-url")
async def open_url(payload: UrlIn) -> dict:
    return {"opened": _service.open_url(payload.url)}


@router.post("/start-program")
async def start_program(payload: ProgramIn) -> dict:
    try:
        pid = _service.start_program(payload.path, payload.args)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"pid": pid}


@router.post("/kill-program", response_model=CommandOut)
async def kill_program(payload: NameIn) -> CommandOut:
    result = _service.kill_program(payload.name)
    return CommandOut(**result.__dict__)


@router.post("/explorer")
async def open_explorer(payload: PathIn) -> dict:
    try:
        _service.open_explorer(payload.path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"opened": True}


@router.post("/files/list")
async def list_dir(payload: PathIn) -> list[dict]:
    try:
        return _service.list_dir(payload.path)
    except NotADirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/files/read")
async def read_file(payload: PathIn) -> dict:
    try:
        return {"content": _service.read_file(payload.path)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/files/write")
async def write_file(payload: WriteIn) -> dict:
    _service.write_file(payload.path, payload.content)
    return {"written": True}


@router.post("/files/mkdir")
async def make_dir(payload: PathIn) -> dict:
    try:
        created = _service.make_dir(payload.path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"created": created}


@router.post("/files/read-base64")
async def read_file_base64(payload: PathIn) -> dict:
    target = Path(payload.path).expanduser()
    if not target.is_file():
        raise HTTPException(status_code=404, detail=str(target))
    try:
        data = target.read_bytes()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if len(data) > 25_000_000:
        raise HTTPException(status_code=413, detail="Datei zu gross")
    mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
    return {"data": base64.b64encode(data).decode("ascii"), "mime": mime}


@router.post("/files/move")
async def move_path(payload: MoveIn) -> dict:
    try:
        result = _service.move_path(payload.source, payload.destination)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"moved_to": result}


@router.post("/files/delete")
async def delete_path(payload: PathIn) -> dict:
    try:
        _service.delete_path(payload.path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"deleted": True}


class TtsIn(BaseModel):
    text: str
    voice: str = "de-DE-ConradNeural"
    rate: str = "+8%"
    volume: str = "+45%"
    pitch: str = "+0Hz"


@router.post("/tts")
async def tts(payload: TtsIn):
    from fastapi.responses import Response

    try:
        from app.services.voice_service import synthesize_speech

        audio = await synthesize_speech(
            payload.text,
            payload.voice,
            payload.rate,
            payload.volume,
            payload.pitch,
        )
    except Exception as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    if not audio:
        raise HTTPException(status_code=400, detail="kein Text")
    return Response(content=audio, media_type="audio/mpeg")


@router.get("/health-check")
async def health_check() -> dict:
    return await asyncio.to_thread(_service.health_check)


@router.post("/transcribe")
async def transcribe(request: Request) -> dict:
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="keine Audiodaten")
    voice = _get_voice()
    try:
        text = await asyncio.to_thread(voice.transcribe_wav, data)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"text": text}


@router.post("/vscode")
async def open_vscode(payload: PathIn) -> dict:
    try:
        pid = _service.open_in_vscode(payload.path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"pid": pid}


@router.post("/pick-folder")
async def pick_folder() -> dict:
    try:
        path = await asyncio.to_thread(_service.choose_folder)
    except Exception as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    return {"path": path}


@router.get("/idle")
async def idle() -> dict:
    return {"seconds": _service.idle_seconds()}


class AutostartIn(BaseModel):
    enabled: bool


@router.get("/autostart")
async def autostart_status() -> dict:
    return {"enabled": _service.autostart_status()}


@router.post("/autostart")
async def set_autostart(payload: AutostartIn) -> dict:
    try:
        enabled = await asyncio.to_thread(_service.set_autostart, payload.enabled)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"enabled": enabled}


@router.post("/path-info")
async def path_info(payload: PathIn) -> dict:
    target = Path(payload.path).expanduser()
    return {
        "exists": target.exists(),
        "is_dir": target.is_dir(),
        "parent": str(target.parent),
    }
