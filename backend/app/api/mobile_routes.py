from __future__ import annotations

import asyncio
import base64
import io
import json
import mimetypes
import platform
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.config import DATA_DIR
from app.core.store import atomic_write_text
from app.services.dateiindex_service import get_dateiindex_service
from app.services.dateiraum_service import get_dateiraum_service

router = APIRouter(prefix="/api/mobile")
_lock = threading.Lock()
_state = DATA_DIR / "mobile-state.json"


def _file(path: str) -> Path:
    raum = get_dateiraum_service()
    roh = Path(path).expanduser()
    kandidaten = [roh] if roh.is_absolute() else [raum.sicherstellen() / roh, roh]
    grund = "Datei nicht gefunden."
    for kandidat in kandidaten:
        target = kandidat.resolve()
        allowed, reason = raum.frei(target)
        if not allowed:
            grund = reason
            continue
        if target.is_file():
            return target
    raise HTTPException(403 if grund != "Datei nicht gefunden." else 404, grund)


@router.get("/state")
def state() -> dict:
    with _lock:
        return json.loads(_state.read_text(encoding="utf-8")) if _state.exists() else {}


@router.patch("/state")
def update_state(payload: dict) -> dict:
    allowed = {"chats", "favorites", "folders", "fileFolders", "profile", "feedback"}
    if set(payload) - allowed or len(json.dumps(payload)) > 500_000:
        raise HTTPException(400, "Ungültige Einstellungen.")
    with _lock:
        value = json.loads(_state.read_text(encoding="utf-8")) if _state.exists() else {}
        for key, patch in payload.items():
            if isinstance(patch, dict):
                value[key] = {**value.get(key, {}), **patch}
            else:
                value[key] = patch
        atomic_write_text(_state, json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return value


@router.get("/status")
def status() -> dict:
    import shutil
    import time

    root = get_dateiraum_service().sicherstellen()
    disk = shutil.disk_usage(root)
    return {"hostname": platform.node(), "system": platform.system(), "machine": platform.machine(), "time": time.time(), "free": disk.free, "total": disk.total, "root": str(root)}


class Upload(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    data: str = Field(max_length=5_600_000)


@router.post("/upload")
def upload(payload: Upload) -> dict:
    try:
        raw = base64.b64decode(payload.data, validate=True)
    except ValueError:
        raise HTTPException(400, "Datei nicht lesbar.")
    if len(raw) > 4_000_000:
        raise HTTPException(413, "Anhänge dürfen maximal 4 MB groß sein.")
    target = get_dateiraum_service().zielpfad(Path(payload.name.replace("\\", "/")).name)
    if target.get("error"):
        raise HTTPException(400, target["error"])
    path = Path(target["pfad"])
    with path.open("xb") as output:
        output.write(raw)
    return get_dateiindex_service().merken(path, quelle="handy")


@router.get("/file")
def file_chunk(path: str, offset: int = 0) -> dict:
    target = _file(path)
    size = target.stat().st_size
    if size > 32_000_000 or offset < 0 or offset > size:
        raise HTTPException(413, "Download maximal 32 MB; ungültiger Dateibereich.")
    with target.open("rb") as file:
        file.seek(offset)
        raw = file.read(384_000)
    return {"name": target.name, "mime": mimetypes.guess_type(target.name)[0] or "application/octet-stream", "data": base64.b64encode(raw).decode("ascii"), "offset": offset + len(raw), "size": size}


@router.get("/preview")
def preview(path: str) -> Response:
    from PIL import Image, ImageOps

    target = _file(path)
    if target.stat().st_size > 32_000_000:
        raise HTTPException(413, "Bild zu groß.")
    try:
        with Image.open(target) as original:
            if original.width * original.height > 40_000_000:
                raise ValueError("Bild zu groß")
            picture = ImageOps.exif_transpose(original)
            picture.thumbnail((900, 900))
            buffer = io.BytesIO()
            picture.convert("RGB").save(buffer, format="JPEG", quality=82)
            return Response(buffer.getvalue(), media_type="image/jpeg")
    except Exception:
        raise HTTPException(415, "Keine Bildvorschau verfügbar.")


@router.post("/projects")
async def create_project(payload: dict) -> dict:
    from app.services.project_service import get_project_service
    from app.services.dateiraum_service import saeubern

    name = str(payload.get("name", "")).strip()
    if not name or len(name) > 100:
        raise HTTPException(400, "Projektname fehlt oder ist zu lang.")
    root = get_dateiraum_service().sicherstellen() / "Projects" / saeubern(name)
    root.mkdir(parents=True, exist_ok=True)
    return await asyncio.to_thread(get_project_service().add, str(root), name, str(payload.get("note", ""))[:5000])


@router.get("/view")
def view(path: str) -> dict:
    from app.services.dateiansicht_service import ansehen

    target = _file(path)
    if target.stat().st_size > 60_000_000:
        raise HTTPException(413, "Datei ist für die Vorschau zu groß.")
    return ansehen(target)


@router.get("/view/seite")
def view_page(path: str, seite: int = 1) -> Response:
    from app.services.dateiansicht_service import pdfseite

    target = _file(path)
    if target.suffix.lower() != ".pdf" or seite < 1:
        raise HTTPException(400, "Nur PDF-Seiten.")
    try:
        return Response(pdfseite(target, seite), media_type="image/jpeg")
    except Exception as exc:
        raise HTTPException(415, str(exc)[:200])


@router.get("/view/bild")
def view_picture(path: str, folie: int, form: int) -> Response:
    from app.services.dateiansicht_service import folienbild

    target = _file(path)
    if target.suffix.lower() != ".pptx" or folie < 1 or form < 0:
        raise HTTPException(400, "Nur Bilder aus Präsentationen.")
    try:
        daten, mime = folienbild(target, folie, form)
    except Exception:
        raise HTTPException(404, "Bild nicht gefunden.")
    return Response(daten, media_type=mime)


WEB_TYPEN = {
    ".html": "text/html", ".htm": "text/html", ".css": "text/css", ".js": "text/javascript", ".mjs": "text/javascript",
    ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".ico": "image/x-icon", ".woff": "font/woff", ".woff2": "font/woff2",
    ".ttf": "font/ttf", ".otf": "font/otf", ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
    ".mp4": "video/mp4", ".webm": "video/webm", ".txt": "text/plain", ".md": "text/markdown", ".wasm": "application/wasm",
    ".csv": "text/csv", ".xml": "application/xml",
}
UEBERSPRINGEN = {".git", "node_modules", "__pycache__", ".venv", "venv", ".idea", ".vscode"}
AUSFUEHRBAR = {".py", ".sh", ".js", ".mjs", ".cjs"}


@router.get("/roh")
def raw_file(path: str) -> Response:
    target = _file(path)
    if target.stat().st_size > 3_900_000:
        raise HTTPException(413, "Datei ist für die Vorschau zu groß.")
    mime = WEB_TYPEN.get(target.suffix.lower()) or mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return Response(target.read_bytes(), media_type=mime, headers={"Cache-Control": "no-store"})


@router.post("/zip")
def zip_folder(payload: dict) -> dict:
    import time
    import zipfile

    from app.services.dateiraum_service import saeubern

    raum = get_dateiraum_service()
    roh = Path(str(payload.get("path", ""))).expanduser()
    if not roh.is_absolute():
        roh = raum.sicherstellen() / roh
    quelle = roh.resolve()
    erlaubt, grund = raum.frei(quelle)
    if not erlaubt:
        raise HTTPException(403, grund)
    if not quelle.exists():
        raise HTTPException(404, "Nicht gefunden.")
    ordner = quelle if quelle.is_dir() else quelle.parent
    if ordner == raum.sicherstellen().resolve() or ordner == Path.home().resolve():
        raise HTTPException(400, "Den ganzen Jon- oder Benutzerordner packt Jon nicht ein.")
    ziel = raum.ordner("Downloads") / f"{saeubern(ordner.name, 'Jon')}-{time.strftime('%Y%m%d-%H%M%S')}.zip"
    gesamt = 0
    anzahl = 0
    zu_gross = False
    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as archiv:
        for datei in sorted(ordner.rglob("*")):
            if not datei.is_file() or any(teil in UEBERSPRINGEN for teil in datei.relative_to(ordner).parts):
                continue
            gesamt += datei.stat().st_size
            if gesamt > 60_000_000 or anzahl >= 2000:
                zu_gross = True
                break
            archiv.write(datei, Path(ordner.name) / datei.relative_to(ordner))
            anzahl += 1
    if zu_gross or ziel.stat().st_size > 32_000_000:
        ziel.unlink(missing_ok=True)
        raise HTTPException(413, "Der Ordner ist zu groß für einen Download aufs Handy.")
    return {"pfad": str(ziel), "name": ziel.name, "groesse": ziel.stat().st_size, "dateien": anzahl}


@router.post("/ausfuehren")
async def run_file(payload: dict) -> dict:
    import shutil
    import sys
    import time

    target = _file(str(payload.get("path", "")))
    endung = target.suffix.lower()
    if endung not in AUSFUEHRBAR:
        raise HTTPException(400, "Ausführen geht mit .py, .sh und .js. Websites öffnest du mit „Website ansehen“.")
    if endung == ".py":
        from app.services.testumgebung import _programm

        python = _programm("python")
        if not python:
            raise HTTPException(400, "Python ist auf diesem Gerät nicht installiert.")
        befehl = [python, "-X", "utf8", target.name]
    elif endung == ".sh":
        bash = shutil.which("bash")
        if not bash:
            raise HTTPException(400, "Auf diesem Gerät gibt es keine Bash.")
        befehl = [bash, target.name]
    else:
        node = shutil.which("node")
        if not node:
            raise HTTPException(400, "Node.js ist auf dem Pi nicht installiert. Installiere es mit: sudo apt install nodejs")
        befehl = [node, target.name]
    argumente = [str(a)[:200] for a in (payload.get("args") or [])][:10]
    start = time.monotonic()
    prozess = await asyncio.create_subprocess_exec(
        *befehl, *argumente, cwd=str(target.parent),
        stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        aus, fehler = await asyncio.wait_for(prozess.communicate(), timeout=60)
        code = prozess.returncode
    except asyncio.TimeoutError:
        prozess.kill()
        aus, fehler = await prozess.communicate()
        code = -1
        fehler = (fehler or b"") + "\nNach 60 Sekunden abgebrochen.".encode()
    return {
        "stdout": (aus or b"").decode("utf-8", "replace")[-20000:],
        "stderr": (fehler or b"").decode("utf-8", "replace")[-8000:],
        "exit_code": code,
        "dauer": round(time.monotonic() - start, 2),
        "befehl": " ".join([Path(befehl[0]).name, *befehl[1:]]),
    }


BEFEHLE = [
    ("/hilfe", "", "Alle Befehle"),
    ("/video", "[Sekunden]", "Kurzes Video vom Bildschirm"),
    ("/live", "[1|2|alle]", "Bildschirm live ansehen"),
    ("/livestop", "", "Live-Ansicht beenden"),
    ("/geraete", "", "Alle verbundenen Jon-Geräte"),
    ("/modell", "[Name]", "Modell anzeigen oder wechseln"),
    ("/anbieter", "[Name]", "KI-Anbieter wechseln"),
    ("/stimme", "", "Jon liest Antworten vor"),
    ("/endstimme", "", "Nur noch Text"),
    ("/lernen", "<Thema>", "Tiefenrecherche starten"),
    ("/lernstatus", "", "Stand der Recherche"),
    ("/lernstop", "", "Recherche abbrechen"),
    ("/lernweiter", "", "Recherche fortsetzen"),
    ("/goal", "<Ziel>", "Jon arbeitet selbstständig, bis das Ziel erreicht ist"),
    ("/stopp", "", "Laufende Antwort abbrechen"),
    ("/reset", "", "Neuer Chat"),
    ("/bildschirme", "", "Bildschirme des PCs anzeigen"),
    ("/telegram", "<Text>", "Nachricht an dein Telegram schicken"),
    ("/ja", "", "Zeitanfrage erlauben"),
    ("/nein", "", "Zeitanfrage ablehnen"),
    ("/projekte", "", "Harness-Projekte anzeigen"),
    ("/projekt", "<Name>", "Harness-Arbeitsordner wählen"),
    ("/harness", "<Auftrag>", "Harness-Auftrag starten"),
    ("/hneu", "<Auftrag>", "Neue Harness-Sitzung"),
    ("/aufgaben", "", "Harness-Aufträge anzeigen"),
    ("/hstatus", "<ID>", "Stand eines Auftrags"),
    ("/diff", "<ID>", "Änderungen eines Auftrags"),
    ("/hstop", "<ID>", "Auftrag stoppen"),
    ("/erlauben", "", "Shellbefehl freigeben"),
    ("/ablehnen", "", "Shellbefehl ablehnen"),
]


def _video_wunsch(teile: list[str]) -> tuple[int, str]:
    sekunden = 15
    welcher = "maus"
    for wort in [t.strip().lower().rstrip(",.") for t in teile]:
        zahl = wort.rstrip("sek").rstrip("s") if wort.endswith(("s", "sek")) else wort
        if wort in ("alle", "maus"):
            welcher = wort
        elif wort.endswith(("s", "sek")) and zahl.isdigit():
            sekunden = max(3, min(60, int(zahl)))
        elif wort.isdigit() and int(wort) <= 4:
            welcher = wort
        elif wort.isdigit():
            sekunden = max(3, min(60, int(wort)))
    return sekunden, welcher


def _bildschirme_text() -> str:
    from app.services.live_service import monitore

    liste = [m for m in monitore() if m["id"] != "alle"]
    zeilen = [f"**{len(liste)} Bildschirm{'e' if len(liste) != 1 else ''}**", ""]
    for m in liste:
        groesse = f" ({m['breite']}x{m['hoehe']})" if m.get("breite") else ""
        zeilen.append(f"- **{m['id']}** · {m['name']}{groesse}")
    zeilen += ["", "/video 2 = Bildschirm 2 · /video alle · /video 2 30s = 30 Sekunden von Bildschirm 2"]
    return "\n".join(zeilen)


async def _bildschirmvideo(sekunden: int, welcher: str) -> dict:
    import shutil
    import time

    from app.services.bildschirm_video import VideoFehler, clip

    try:
        quelle = await clip(welcher, float(sekunden))
    except VideoFehler as exc:
        raise HTTPException(400, f"Video geht hier nicht: {exc}")
    ziel = get_dateiraum_service().ordner("Videos") / f"Bildschirm-{time.strftime('%Y%m%d-%H%M%S')}.mp4"
    await asyncio.to_thread(shutil.move, str(quelle), str(ziel))
    return {"pfad": str(ziel), "name": ziel.name, "groesse": ziel.stat().st_size, "sekunden": sekunden}


def _geraete_text() -> str:
    from app.services.verbund_service import get_verbund_service

    geraete = get_verbund_service().geraete()
    if not geraete:
        return "Hier hängt noch kein weiteres Jon-Gerät dran. Am PC unter Einstellungen → Geräte im Verbund koppelst du zum Beispiel deinen Pi."
    zeilen = ["**Deine Jon-Geräte**", ""]
    for g in geraete:
        zeilen.append(f"- **{g.get('name', '?')}** · {g.get('version') or '?'} · {g.get('weg') or 'noch nicht erreicht'}")
    return "\n".join(zeilen)


def _befehl_zeile(name: str, args: str, info: str) -> str:
    zusatz = f" {args}" if args else ""
    return f"- **{name}{zusatz}** – {info}"


@router.post("/befehl")
async def command(payload: dict) -> dict:
    from app.services.telegram_extras import is_learn_command, research_command

    text = " ".join(str(payload.get("text", "")).split())
    if not text.startswith("/"):
        raise HTTPException(400, "Befehle beginnen mit /.")
    befehl = text.split()[0].split("@")[0].lower()
    teile = text.split()[1:]
    quelle = str(payload.get("quelle") or "handy").strip()[:40] or "handy"
    if befehl in ("/hilfe", "/help", "/start", "/befehle"):
        zeilen = ["**Befehle**", ""] + [_befehl_zeile(name, args, info) for name, args, info in BEFEHLE]
        return {"text": "\n".join(zeilen), "befehle": [{"name": n, "args": a, "text": i} for n, a, i in BEFEHLE]}
    if befehl in ("/geraete", "/geräte"):
        return {"text": await asyncio.to_thread(_geraete_text)}
    if befehl == "/video":
        sekunden, welcher = _video_wunsch(teile)
        video = await _bildschirmvideo(sekunden, welcher)
        wo = {"maus": "vom Bildschirm mit der Maus", "alle": "von allen Bildschirmen"}.get(welcher, f"von Bildschirm {welcher}")
        return {"text": f"🎬 {sekunden} Sekunden {wo}.", "video": video}
    if befehl in ("/live", "/livebild"):
        from app.services.live_service import LiveFehler, get_live_service

        wunsch = " ".join(teile).strip()
        klein = wunsch.lower()
        if wunsch and klein not in ("alle", "maus") and not klein.isdigit():
            from app.services.verbund_service import VerbundFehler, get_verbund_service

            verbund = get_verbund_service()
            try:
                eintrag = verbund.finden(wunsch)
                daten = await verbund.bildschirm(eintrag["id"], "alle")
            except VerbundFehler as fehler:
                return {"text": str(fehler)}
            import time

            ziel = get_dateiraum_service().ordner("Images") / f"Bildschirm-{time.strftime('%Y%m%d-%H%M%S')}.jpg"
            await asyncio.to_thread(ziel.write_bytes, daten)
            return {"text": f"Der Bildschirm von {eintrag.get('name', wunsch)}:", "bild": f"/api/verbund/{eintrag['id']}/bild?welcher=alle", "bild_pfad": str(ziel)}
        try:
            await asyncio.to_thread(get_live_service().starten, klein or "alle", 2.0)
        except LiveFehler as fehler:
            return {"text": str(fehler)}
        return {"text": "Die Live-Übertragung läuft. Auf dem Handy oder in Telegram siehst du sie mit /live, /livestop beendet sie."}
    if befehl == "/livestop":
        from app.services.live_service import get_live_service

        get_live_service().stoppen()
        return {"text": "Die Übertragung ist beendet."}
    if befehl in ("/bildschirme", "/monitore"):
        return {"text": await asyncio.to_thread(_bildschirme_text)}
    if befehl in ("/ja", "/nein"):
        from app.services.telegram_service import get_telegram_service

        return {"text": await get_telegram_service()._zeitanfrage_antwort(text, befehl == "/ja")}
    if befehl == "/telegram":
        from app.services.telegram_plan import senden

        rest = text.split(maxsplit=1)[1].strip() if len(teile) else ""
        if not rest:
            return {"text": "Was soll ich dir schicken? Beispiel: /telegram Denk an den Einkauf"}
        ergebnis = await senden(rest)
        return {"text": "Auf Telegram geschickt." if ergebnis.get("ok") else ergebnis.get("error", "Das hat nicht geklappt.")}
    if befehl in ("/goal", "/ziel"):
        from app.services.ziel_modus import STOPP, get_ziel_modus

        modus = get_ziel_modus()
        rest = " ".join(teile)
        laufend = modus.laufend(quelle)
        if rest.casefold() in STOPP:
            if laufend is None:
                return {"text": "Gerade arbeite ich an keinem Ziel."}
            await modus.stoppen(laufend["id"])
            return {"text": f"Angehalten: {laufend['ziel']}. Was schon fertig ist, bleibt erhalten."}
        if not rest:
            if laufend is None:
                return {"text": "So geht's: /goal und dein Ziel. Ich arbeite dann selbstständig in Runden, bis es erreicht ist. /goal stopp hält an."}
            return {"text": f"Ich arbeite an: {laufend['ziel']}\nRunde {laufend['runde']}." + (f"\nLetzte Prüfung: {laufend['urteil']}" if laufend.get("urteil") else "")}
        try:
            neu = modus.starten(rest, quelle)
        except ValueError as fehler:
            return {"text": str(fehler)}
        return {"text": f"Ziel gestartet: {neu['ziel']}\nIch arbeite jetzt selbstständig daran und prüfe mich nach jeder Runde. /goal zeigt den Stand, /goal stopp hält an.", "ziel": neu["id"]}
    if befehl in ("/stopp", "/stop"):
        from app.services.harness import get_harness_service
        from app.services.harness.service import TERMINAL

        from app.services.ziel_modus import get_ziel_modus

        harness = get_harness_service()
        gestoppt = 0
        ziel = get_ziel_modus().laufend(quelle)
        if ziel is not None:
            await get_ziel_modus().stoppen(ziel["id"])
            gestoppt += 1
        for aufgabe in harness.list(quelle):
            if aufgabe["status"] not in TERMINAL:
                await harness.cancel(aufgabe["id"])
                gestoppt += 1
        return {"text": f"{gestoppt} Harness-Auftrag gestoppt." if gestoppt == 1 else f"{gestoppt} Harness-Aufträge gestoppt." if gestoppt else "Gerade läuft nichts, alles ruhig."}
    from app.services.harness.messages import handle as harness_befehl

    harness_antwort = await harness_befehl(text, quelle)
    if harness_antwort is not None:
        return {"text": harness_antwort["text"], "harness": harness_antwort.get("task_id")}
    if is_learn_command(text):
        ergebnis = await research_command(text)
        if ergebnis is None:
            return {"text": "Das habe ich nicht verstanden. Beispiel: /lernen Quantencomputer"}
        antwort, aufgabe = ergebnis
        return {"text": antwort, "aufgabe": aufgabe}
    return {"text": f"Den Befehl {befehl} kenne ich nicht. /hilfe zeigt alle Befehle."}
