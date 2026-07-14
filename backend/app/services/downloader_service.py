from __future__ import annotations

import html as html_lib
import json
import re
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx

SPOTIFY_ID = re.compile(r"open\.spotify\.com/(?:intl-[a-z]+/)?track/([A-Za-z0-9]+)")

BASE_DIR = Path(tempfile.gettempdir()) / "jon-downloads"
JOB_TTL = 3600.0
QUALITIES = ("best", "1080", "720", "480")
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}

ERROR_HINTS = (
    ("is not a valid url", "Das sieht nicht wie ein gültiger Link aus."),
    ("unsupported url", "Diese Seite wird leider nicht unterstützt."),
    ("private video", "Dieses Video ist privat — darauf gibt es keinen Zugriff."),
    ("private account", "Dieses Profil ist privat — darauf gibt es keinen Zugriff."),
    ("sign in to confirm your age", "Dieses Video ist altersbeschränkt und braucht einen Login."),
    ("age-restricted", "Dieses Video ist altersbeschränkt und braucht einen Login."),
    ("inappropriate", "Dieses Video ist altersbeschränkt und braucht einen Login."),
    ("available in your country", "Dieses Video ist in deinem Land gesperrt (Geo-Sperre)."),
    ("geo restriction", "Dieses Video ist in deinem Land gesperrt (Geo-Sperre)."),
    ("geo-restricted", "Dieses Video ist in deinem Land gesperrt (Geo-Sperre)."),
    ("blocked it in your country", "Dieses Video ist in deinem Land gesperrt (Geo-Sperre)."),
    ("video unavailable", "Dieses Video existiert nicht mehr oder wurde entfernt."),
    ("account has been terminated", "Der Kanal hinter diesem Video wurde gelöscht."),
    ("members-only", "Dieses Video ist nur für zahlende Mitglieder."),
    ("premieres in", "Diese Premiere hat noch nicht stattgefunden."),
    ("live event will begin", "Dieser Livestream hat noch nicht begonnen."),
    ("requested format is not available", "Diese Qualität gibt es hier nicht — probier eine andere."),
    ("sign in", "Diese Plattform verlangt für dieses Video einen Login."),
    ("login required", "Diese Plattform verlangt für dieses Video einen Login."),
    ("use --cookies", "Diese Plattform verlangt für dieses Video einen Login."),
    ("ffmpeg", "ffmpeg fehlt oder schlug fehl — bitte ffmpeg installieren."),
    ("unable to download webpage", "Die Seite ist gerade nicht erreichbar — Link prüfen oder später nochmal."),
    ("timed out", "Zeitüberschreitung — die Plattform antwortet gerade nicht."),
)


def friendly_error(raw: str) -> str:
    text = raw.replace("ERROR:", "").strip()
    low = text.lower()
    for needle, message in ERROR_HINTS:
        if needle in low:
            return message
    return f"Download fehlgeschlagen: {text[:200]}"


def sanitize_filename(title: str) -> str:
    clean = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "", title)
    clean = re.sub(r"\s+", " ", clean).strip().strip(". ")
    return clean[:120] or "download"


def valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


class _SilentLogger:
    def debug(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        pass

    def error(self, msg: str) -> None:
        pass


def base_options() -> dict:
    return {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
        "playlist_items": "1",
        "socket_timeout": 20,
        "retries": 3,
        "logger": _SilentLogger(),
    }


def first_entry(info: dict) -> dict:
    if info.get("_type") == "playlist":
        entries = [e for e in info.get("entries") or [] if e]
        return entries[0] if entries else {}
    return info


def format_for(kind: str, quality: str) -> str:
    if kind == "mp3":
        return "bestaudio/best"
    if quality == "best":
        return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
    return (
        f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/"
        f"bestvideo[height<={quality}]+bestaudio/"
        f"best[height<={quality}]/best"
    )


def _meta(page: str, prop: str) -> str:
    for pattern in (
        rf'<meta[^>]+(?:property|name)=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']*)["\']',
        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']{re.escape(prop)}["\']',
    ):
        match = re.search(pattern, page, re.I)
        if match:
            return html_lib.unescape(match.group(1)).strip()
    return ""


def music_source(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "spotify" in host:
        return "spotify"
    if "music.amazon" in host:
        return "amazon"
    return ""


def _strip_noise(title: str) -> str:
    title = re.sub(r"\[(explicit|clean)\]", "", title, flags=re.I)
    title = re.sub(r"\s*[|\-–]\s*(amazon music|amazon\.\w+|spotify).*$", "", title, flags=re.I)
    return title.strip(" -–|")


def _json_unescape(value: str) -> str:
    try:
        return str(json.loads(f'"{value}"'))
    except Exception:
        return value


def _resolve_spotify(url: str) -> dict:
    final_url = url
    if "spotify.link" in urlparse(url).netloc.lower():
        try:
            final_url = str(
                httpx.get(
                    url, headers=BROWSER_HEADERS, follow_redirects=True, timeout=15
                ).url
            )
        except Exception:
            return {"error": "Ich konnte den Spotify-Kurzlink nicht auflösen."}
    match = SPOTIFY_ID.search(final_url)
    if not match:
        return {"error": "Bitte verlinke einen einzelnen Song — Playlists und Alben gehen noch nicht."}
    track_id = match.group(1)
    title = ""
    artist = ""
    try:
        data = httpx.get(
            "https://open.spotify.com/oembed",
            params={"url": f"https://open.spotify.com/track/{track_id}"},
            timeout=15,
        ).json()
        title = str(data.get("title") or "").strip()
    except Exception:
        pass
    try:
        page = httpx.get(
            f"https://open.spotify.com/embed/track/{track_id}",
            headers=BROWSER_HEADERS,
            timeout=15,
        ).text
        found = re.search(r'"artists":\[\{"name":"((?:[^"\\]|\\.)*)"', page)
        if found:
            artist = _json_unescape(found.group(1))
        if not title:
            found = re.search(r'"name":"((?:[^"\\]|\\.)*)"', page)
            if found:
                title = _json_unescape(found.group(1))
    except Exception:
        pass
    if not title:
        return {"error": "Ich konnte die Song-Infos von Spotify nicht lesen — versuch es später nochmal."}
    query = f"{artist} {title}".strip()
    label = f"{artist} – {title}" if artist else title
    return {"query": query, "label": label}


def _resolve_amazon(url: str) -> dict:
    crawler = {"User-Agent": "facebookexternalhit/1.1"}
    for headers in (BROWSER_HEADERS, crawler):
        try:
            response = httpx.get(url, headers=headers, follow_redirects=True, timeout=15)
            page = response.text
        except Exception:
            continue
        title = _strip_noise(_meta(page, "og:title") or _meta(page, "twitter:title"))
        if not title:
            found = re.search(r"<title>([^<]+)</title>", page, re.I)
            candidate = _strip_noise(html_lib.unescape(found.group(1)).strip()) if found else ""
            if candidate.lower() not in ("", "amazon music", "amazon.de", "amazon.com"):
                title = candidate
        if not title:
            continue
        description = _meta(page, "og:description") or _meta(page, "twitter:description")
        artist = ""
        match = re.search(r"\bvon\s+(.+?)\s+(?:bei|auf|\||$)", f"{title} {description}")
        if not match:
            match = re.search(r"\bby\s+(.+?)\s+(?:on|\||$)", f"{title} {description}")
        if match:
            artist = _strip_noise(match.group(1))
            title = re.sub(r"\s+(?:von|by)\s+.+$", "", title).strip() or title
        query = f"{artist} {title}".strip()
        label = f"{artist} – {title}" if artist else title
        return {"query": query, "label": label}
    return {"error": "Ich konnte die Song-Infos von Amazon Music nicht lesen — lade den Song alternativ direkt über einen YouTube-Link."}


def resolve_music(url: str, source: str) -> dict:
    if source == "spotify":
        return _resolve_spotify(url)
    return _resolve_amazon(url)


class DownloaderService:
    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()
        BASE_DIR.mkdir(parents=True, exist_ok=True)

    def _cleanup_old(self) -> None:
        now = time.time()
        for job_id in list(self._jobs):
            job = self._jobs[job_id]
            if now - job["created"] > JOB_TTL:
                self._jobs.pop(job_id, None)
                shutil.rmtree(job["dir"], ignore_errors=True)

    def analyze(self, url: str) -> dict:
        import yt_dlp

        url = url.strip()
        if not valid_url(url):
            return {"error": "Das sieht nicht wie ein gültiger Link aus."}
        source = music_source(url)
        if source:
            resolved = resolve_music(url, source)
            if "error" in resolved:
                return resolved
            options = base_options()
            options["skip_download"] = True
            try:
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = first_entry(
                        ydl.extract_info(f"ytsearch1:{resolved['query']}", download=False)
                    )
            except yt_dlp.utils.DownloadError as exc:
                return {"error": friendly_error(str(exc))}
            except Exception as exc:
                return {"error": f"Suche fehlgeschlagen: {exc}"}
            if not info:
                return {"error": "Ich habe zu diesem Song keine passende Aufnahme gefunden."}
            return {
                "title": resolved["label"],
                "matched": info.get("title") or "",
                "thumbnail": info.get("thumbnail") or "",
                "duration": info.get("duration") or 0,
                "uploader": info.get("uploader") or info.get("channel") or "",
                "extractor": "Spotify" if source == "spotify" else "Amazon Music",
                "max_height": 0,
                "audio_only": True,
                "music": True,
                "url": info.get("webpage_url") or "",
            }
        options = base_options()
        options["skip_download"] = True
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = first_entry(ydl.extract_info(url, download=False))
        except yt_dlp.utils.DownloadError as exc:
            return {"error": friendly_error(str(exc))}
        except Exception as exc:
            return {"error": f"Analyse fehlgeschlagen: {exc}"}
        if not info:
            return {"error": "Hier wurde kein Video gefunden."}
        heights = sorted(
            {
                int(f["height"])
                for f in info.get("formats") or []
                if f.get("height") and f.get("vcodec") not in (None, "none")
            },
            reverse=True,
        )
        return {
            "title": info.get("title") or "Ohne Titel",
            "matched": "",
            "thumbnail": info.get("thumbnail") or "",
            "duration": info.get("duration") or 0,
            "uploader": info.get("uploader") or info.get("channel") or "",
            "extractor": info.get("extractor_key") or "",
            "max_height": heights[0] if heights else 0,
            "audio_only": not heights,
            "music": False,
            "url": info.get("webpage_url") or url,
        }

    def start(self, url: str, kind: str, quality: str, title: str = "") -> dict:
        url = url.strip()
        if not valid_url(url):
            return {"error": "Das sieht nicht wie ein gültiger Link aus."}
        if kind not in ("mp4", "mp3") or quality not in QUALITIES:
            return {"error": "Ungültige Format- oder Qualitätswahl."}
        if not shutil.which("ffmpeg"):
            return {
                "error": "ffmpeg wurde nicht gefunden — installieren mit: "
                "winget install --id Gyan.FFmpeg (danach Jon neu starten)."
            }
        job_id = uuid.uuid4().hex
        job_dir = BASE_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        job = {
            "status": "starting",
            "percent": 0.0,
            "speed": 0,
            "eta": None,
            "file": None,
            "name": None,
            "error": None,
            "created": time.time(),
            "dir": str(job_dir),
        }
        with self._lock:
            self._cleanup_old()
            self._jobs[job_id] = job
        threading.Thread(
            target=self._run, args=(job_id, url, kind, quality, title), daemon=True
        ).start()
        return {"job": job_id}

    def _hook(self, job: dict):
        def inner(d: dict) -> None:
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                done = d.get("downloaded_bytes") or 0
                percent = done * 100.0 / total if total else 0.0
                job["status"] = "downloading"
                job["percent"] = max(job["percent"], min(99.0, percent))
                job["speed"] = d.get("speed") or 0
                job["eta"] = d.get("eta")
            elif status == "finished":
                job["status"] = "processing"
                job["percent"] = max(job["percent"], 99.0)
                job["speed"] = 0
                job["eta"] = None
        return inner

    def _run(self, job_id: str, url: str, kind: str, quality: str, title: str) -> None:
        import yt_dlp

        job = self._jobs[job_id]
        job_dir = Path(job["dir"])
        options = base_options()
        options.update(
            {
                "outtmpl": str(job_dir / "media.%(ext)s"),
                "format": format_for(kind, quality),
                "progress_hooks": [self._hook(job)],
                "concurrent_fragment_downloads": 4,
            }
        )
        if kind == "mp3":
            options["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320",
                }
            ]
        else:
            options["merge_output_format"] = "mp4"
            options["postprocessors"] = [
                {"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}
            ]
        def grab(opts: dict) -> dict:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return first_entry(ydl.extract_info(url, download=True))

        try:
            try:
                info = grab(options)
            except yt_dlp.utils.DownloadError as exc:
                if "403" not in str(exc):
                    raise
                retry = dict(options)
                retry["extractor_args"] = {"youtube": {"player_client": ["android"]}}
                job["percent"] = 0.0
                job["status"] = "starting"
                info = grab(retry)
            ext = "mp3" if kind == "mp3" else "mp4"
            files = [
                p
                for p in job_dir.iterdir()
                if p.is_file() and p.suffix.lower() == f".{ext}"
            ]
            if not files:
                files = [
                    p
                    for p in job_dir.iterdir()
                    if p.is_file() and p.suffix.lower() not in (".part", ".ytdl")
                ]
            if not files:
                raise RuntimeError("Die fertige Datei wurde nicht gefunden.")
            target = max(files, key=lambda p: p.stat().st_size)
            name = sanitize_filename(title or str(info.get("title") or "download"))
            job["file"] = str(target)
            job["name"] = f"{name}{target.suffix.lower()}"
            job["percent"] = 100.0
            job["status"] = "done"
        except yt_dlp.utils.DownloadError as exc:
            job["status"] = "error"
            job["error"] = friendly_error(str(exc))
        except Exception as exc:
            job["status"] = "error"
            job["error"] = f"Download fehlgeschlagen: {exc}"

    def state(self, job_id: str) -> dict | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        return {
            "status": job["status"],
            "percent": round(job["percent"], 1),
            "speed": job["speed"],
            "eta": job["eta"],
            "error": job["error"],
            "name": job["name"],
        }

    def file_for(self, job_id: str) -> tuple[Path, str] | None:
        job = self._jobs.get(job_id)
        if not job or job["status"] != "done" or not job["file"]:
            return None
        path = Path(job["file"])
        if not path.exists():
            return None
        return path, str(job["name"])


_service: DownloaderService | None = None


def get_downloader_service() -> DownloaderService:
    global _service
    if _service is None:
        _service = DownloaderService()
    return _service
