from __future__ import annotations

import html as html_lib
import json
import re
import shutil
import tempfile
import threading
import time
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.core.config import DATA_DIR

SPOTIFY_ID = re.compile(r"open\.spotify\.com/(?:intl-[a-z]+/)?track/([A-Za-z0-9]+)")
TRACK_ASIN = re.compile(r"trackAsin=([A-Z0-9]+)", re.I)
ARTIST_ASIN = re.compile(r"/artists/([A-Z0-9]+)", re.I)

BASE_DIR = Path(tempfile.gettempdir()) / "jon-downloads"
COOKIE_DIR = DATA_DIR / "downloader"
COOKIE_FILE = COOKIE_DIR / "cookies.txt"
COOKIE_CONFIG = COOKIE_DIR / "cookies.json"
NETSCAPE_HEADER = "# Netscape HTTP Cookie File"
JOB_TTL = 3600.0
LIST_TTL = 1800.0
QUALITIES = ("best", "1080", "720", "480")
BROWSERS = ("firefox", "brave", "edge", "chrome", "chromium", "opera", "vivaldi", "safari")
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}
CRAWLER_HEADERS = {
    "User-Agent": "facebookexternalhit/1.1",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}
LOOKUP_WORKERS = 8
TRACK_WORKERS = 3
MAX_TRACKS = 300
GENERIC_TITLES = ("", "amazon music", "geteilt auf amazon music", "shared on amazon music")

LOGIN_HINT = "Verbinde dazu unten deinen YouTube-Login."
LOGIN_FAILED_HINT = (
    "Dein hinterlegter YouTube-Login hat nicht gereicht — bitte die Cookies erneuern "
    "(sie laufen ab) und prüfen, ob es das Konto ist, mit dem du gekauft hast."
)

AUTH_MARKERS = (
    "requires payment",
    "purchase",
    "purchased",
    "rental",
    "paid content",
    "members-only",
    "members only",
    "sign in",
    "log in to",
    "login required",
    "cookies",
    "not a bot",
    "error 403",
    "403: forbidden",
    "private video",
    "age-restricted",
    "inappropriate",
)

COOKIE_LOAD_FAILURES = (
    "could not find",
    "cookie database",
    "cookies database",
    "unsupported browser",
    "no such file",
    "permission denied",
    "failed to decrypt",
    "could not copy",
    "unable to read",
    "cookieloaderror",
    "does not support",
    "not supported",
)

ERROR_HINTS = (
    ("is not a valid url", "Das sieht nicht wie ein gültiger Link aus."),
    ("unsupported url", "Diese Seite wird leider nicht unterstützt."),
    (
        "requires payment",
        "Dieses Video ist kostenpflichtig (Kauf oder Leihe). Wenn du es gekauft hast, "
        f"brauche ich deinen YouTube-Login, um an deine Kaufversion zu kommen. {LOGIN_HINT}",
    ),
    (
        "purchase",
        "Dieses Video muss gekauft oder geliehen werden. Wenn du es schon gekauft hast, "
        f"brauche ich deinen YouTube-Login. {LOGIN_HINT}",
    ),
    (
        "rental",
        "Dieses Video ist eine Leihe. Wenn du es geliehen oder gekauft hast, "
        f"brauche ich deinen YouTube-Login. {LOGIN_HINT}",
    ),
    ("private video", "Dieses Video ist privat — darauf gibt es keinen Zugriff."),
    ("private account", "Dieses Profil ist privat — darauf gibt es keinen Zugriff."),
    (
        "sign in to confirm your age",
        f"Dieses Video ist altersbeschränkt und braucht einen Login. {LOGIN_HINT}",
    ),
    ("age-restricted", f"Dieses Video ist altersbeschränkt und braucht einen Login. {LOGIN_HINT}"),
    ("inappropriate", f"Dieses Video ist altersbeschränkt und braucht einen Login. {LOGIN_HINT}"),
    ("available in your country", "Dieses Video ist in deinem Land gesperrt (Geo-Sperre)."),
    ("geo restriction", "Dieses Video ist in deinem Land gesperrt (Geo-Sperre)."),
    ("geo-restricted", "Dieses Video ist in deinem Land gesperrt (Geo-Sperre)."),
    ("blocked it in your country", "Dieses Video ist in deinem Land gesperrt (Geo-Sperre)."),
    ("video unavailable", "Dieses Video existiert nicht mehr oder wurde entfernt."),
    ("account has been terminated", "Der Kanal hinter diesem Video wurde gelöscht."),
    (
        "members-only",
        f"Dieses Video ist nur für zahlende Mitglieder des Kanals. {LOGIN_HINT}",
    ),
    ("premieres in", "Diese Premiere hat noch nicht stattgefunden."),
    ("live event will begin", "Dieser Livestream hat noch nicht begonnen."),
    ("requested format is not available", "Diese Qualität gibt es hier nicht — probier eine andere."),
    (
        "confirm you're not a bot",
        f"YouTube hält den Zugriff für einen Bot und will einen Login sehen. {LOGIN_HINT}",
    ),
    ("sign in", f"Diese Plattform verlangt für dieses Video einen Login. {LOGIN_HINT}"),
    ("login required", f"Diese Plattform verlangt für dieses Video einen Login. {LOGIN_HINT}"),
    ("use --cookies", f"Diese Plattform verlangt für dieses Video einen Login. {LOGIN_HINT}"),
    ("ffmpeg", "ffmpeg fehlt oder schlug fehl — bitte ffmpeg installieren."),
    ("unable to download webpage", "Die Seite ist gerade nicht erreichbar — Link prüfen oder später nochmal."),
    ("timed out", "Zeitüberschreitung — die Plattform antwortet gerade nicht."),
)


def friendly_error(
    raw: str, tried_login: bool = False, prefix: str = "Download fehlgeschlagen"
) -> str:
    text = raw.replace("ERROR:", "").strip()
    low = text.lower()
    for needle, message in ERROR_HINTS:
        if needle in low:
            if tried_login and LOGIN_HINT in message:
                return message.replace(LOGIN_HINT, LOGIN_FAILED_HINT)
            return message
    return f"{prefix}: {text[:200]}"


def sanitize_filename(title: str) -> str:
    clean = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "", title)
    clean = re.sub(r"\s+", " ", clean).strip().strip(". ")
    return clean[:120] or "download"


def valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def normalize_cookie_text(text: str) -> str:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith("#") and not line.lstrip().startswith("#HttpOnly_"):
            continue
        if "\t" not in line:
            parts = line.split()
            if len(parts) >= 7:
                line = "\t".join(parts[:6] + [" ".join(parts[6:])])
            else:
                continue
        lines.append(line)
    if not lines:
        return ""
    return NETSCAPE_HEADER + "\n" + "\n".join(lines) + "\n"


def count_cookies(text: str) -> int:
    return sum(
        1
        for line in text.splitlines()
        if line.strip() and not line.startswith("# ") and line.count("\t") >= 6
    )


def cookie_config() -> dict:
    try:
        data = json.loads(COOKIE_CONFIG.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def write_cookie_config(data: dict) -> None:
    try:
        COOKIE_DIR.mkdir(parents=True, exist_ok=True)
        COOKIE_CONFIG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def cookies_ready() -> bool:
    try:
        return COOKIE_FILE.is_file() and COOKIE_FILE.stat().st_size > 40
    except Exception:
        return False


def browser_targets() -> list[str]:
    choice = str(cookie_config().get("browser") or "auto").lower()
    if choice == "off":
        return []
    if choice in BROWSERS:
        return [choice]
    return list(BROWSERS)


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


def needs_auth(message: str) -> bool:
    low = message.lower()
    return any(marker in low for marker in AUTH_MARKERS)


def auth_variants() -> list[dict]:
    variants: list[dict] = [
        {"extractor_args": {"youtube": {"player_client": ["android", "web"]}}}
    ]
    logged_in = {"extractor_args": {"youtube": {"player_client": ["default", "web", "mweb"]}}}
    if cookies_ready():
        variants.append({"cookiefile": str(COOKIE_FILE), **logged_in})
    for browser in browser_targets():
        variants.append({"cookiesfrombrowser": (browser, None, None, None), **logged_in})
    return variants


def is_login_variant(variant: dict) -> bool:
    return "cookiefile" in variant or "cookiesfrombrowser" in variant


def cookie_load_failed(message: str) -> bool:
    low = message.lower()
    return any(marker in low for marker in COOKIE_LOAD_FAILURES)


def extract_info(options: dict, target: str, download: bool = False) -> dict:
    import yt_dlp

    with yt_dlp.YoutubeDL(options) as ydl:
        return first_entry(ydl.extract_info(target, download=download))


def extract_with_fallback(
    options: dict, target: str, download: bool = False, on_retry=None
) -> tuple[dict, str, bool]:
    try:
        return extract_info(options, target, download), "", False
    except Exception as exc:
        first = str(exc)
    if not needs_auth(first):
        return {}, first, False
    tried_login = False
    for variant in auth_variants():
        merged = dict(options)
        merged.update(variant)
        if on_retry:
            on_retry()
        try:
            return extract_info(merged, target, download), "", tried_login
        except Exception as exc:
            if is_login_variant(variant) and not cookie_load_failed(str(exc)):
                tried_login = True
            continue
    return {}, first, tried_login


def first_entry(info: dict | None) -> dict:
    if not info:
        return {}
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


def _meta_all(page: str, prop: str) -> list[str]:
    pattern = (
        rf'<meta[^>]+(?:property|name)=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']*)["\']'
    )
    return [html_lib.unescape(value).strip() for value in re.findall(pattern, page, re.I)]


def music_source(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "spotify" in host:
        return "spotify"
    if "music.amazon" in host:
        return "amazon"
    return ""


def amazon_collection(url: str) -> str:
    parsed = urlparse(url)
    if TRACK_ASIN.search(parsed.query or ""):
        return ""
    path = parsed.path.lower()
    if "/user-playlists/" in path or "/playlists/" in path:
        return "playlist"
    if "/albums/" in path:
        return "album"
    return ""


def amazon_track_asins(page: str) -> list[str]:
    asins: list[str] = []
    for value in _meta_all(page, "music:song"):
        found = TRACK_ASIN.search(value)
        if found and found.group(1) not in asins:
            asins.append(found.group(1))
    return asins


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


def _amazon_page(url: str) -> str:
    for headers in (CRAWLER_HEADERS, BROWSER_HEADERS):
        try:
            page = httpx.get(url, headers=headers, follow_redirects=True, timeout=15).text
        except Exception:
            continue
        if "og:title" in page:
            return page
    return ""


def _amazon_artist(host: str, asin: str, cache: dict[str, str], lock: threading.Lock) -> str:
    with lock:
        if asin in cache:
            return cache[asin]
    name = _strip_noise(_meta(_amazon_page(f"https://{host}/artists/{asin}"), "og:title"))
    if name.lower() in GENERIC_TITLES:
        name = ""
    with lock:
        cache[asin] = name
    return name


def _amazon_song(page: str, host: str, cache: dict[str, str], lock: threading.Lock) -> dict:
    title = _strip_noise(_meta(page, "og:title"))
    if title.lower() in GENERIC_TITLES:
        return {}
    artist = ""
    found = ARTIST_ASIN.search(_meta(page, "music:musician"))
    if found:
        artist = _amazon_artist(host, found.group(1), cache, lock)
    duration = 0
    if re.fullmatch(r"\d+", _meta(page, "music:duration")):
        duration = int(_meta(page, "music:duration"))
    return {
        "query": f"{artist} {title}".strip(),
        "label": f"{artist} – {title}" if artist else title,
        "duration": duration,
    }


def _amazon_track(host: str, asin: str, cache: dict[str, str], lock: threading.Lock) -> dict:
    return _amazon_song(_amazon_page(f"https://{host}/tracks/{asin}"), host, cache, lock)


def resolve_amazon_collection(url: str, kind: str) -> dict:
    page = _amazon_page(url)
    if not page:
        return {"error": "Ich konnte die Amazon-Music-Seite nicht laden — Link prüfen oder später nochmal."}
    asins = amazon_track_asins(page)
    if not asins:
        return {
            "error": "In diesem Link stecken keine Songs. Playlists müssen öffentlich geteilt "
            "sein — in Amazon Music auf „Playlist öffentlich machen“ und dann den Teilen-Link "
            "kopieren."
        }
    cut = len(asins) > MAX_TRACKS
    host = urlparse(url).netloc
    cache: dict[str, str] = {}
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=LOOKUP_WORKERS) as pool:
        found = list(pool.map(lambda asin: _amazon_track(host, asin, cache, lock), asins[:MAX_TRACKS]))
    tracks = [song for song in found if song]
    if not tracks:
        return {"error": "Ich konnte zu diesem Link keine Songtitel lesen — versuch es später nochmal."}
    name = _strip_noise(_meta(page, "og:title"))
    if name.lower() in GENERIC_TITLES:
        name = "Playlist" if kind == "playlist" else "Album"
    owner = _meta(page, "og:description")
    if owner.lower().startswith(("millionen", "millions")):
        owner = ""
    return {
        "name": name,
        "owner": owner,
        "cover": _meta(page, "og:image"),
        "tracks": tracks,
        "cut": cut,
    }


def _resolve_amazon(url: str) -> dict:
    host = urlparse(url).netloc
    cache: dict[str, str] = {}
    lock = threading.Lock()
    found = TRACK_ASIN.search(urlparse(url).query or "")
    if found:
        song = _amazon_track(host, found.group(1), cache, lock)
        if song:
            return song
    page = _amazon_page(url)
    if page:
        song = _amazon_song(page, host, cache, lock)
        if song:
            return song
    return _resolve_amazon_text(url)


def _resolve_amazon_text(url: str) -> dict:
    for headers in (BROWSER_HEADERS, CRAWLER_HEADERS):
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
        self._lists: dict[str, dict] = {}
        self._lock = threading.Lock()
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        COOKIE_DIR.mkdir(parents=True, exist_ok=True)

    def _cleanup_old(self) -> None:
        now = time.time()
        for job_id in list(self._jobs):
            job = self._jobs[job_id]
            if now - job["created"] > JOB_TTL:
                self._jobs.pop(job_id, None)
                shutil.rmtree(job["dir"], ignore_errors=True)

    def cookie_status(self) -> dict:
        config = cookie_config()
        count = 0
        updated = 0.0
        if cookies_ready():
            try:
                count = count_cookies(COOKIE_FILE.read_text(encoding="utf-8", errors="ignore"))
                updated = COOKIE_FILE.stat().st_mtime
            except Exception:
                count = 0
        return {
            "file": cookies_ready(),
            "count": count,
            "updated": updated,
            "browser": str(config.get("browser") or "auto").lower(),
            "browsers": list(BROWSERS),
        }

    def save_cookies(self, text: str, browser: str = "") -> dict:
        choice = (browser or "").strip().lower()
        if choice:
            if choice not in BROWSERS and choice not in ("auto", "off"):
                return {"error": "Unbekannte Browser-Auswahl."}
            config = cookie_config()
            config["browser"] = choice
            write_cookie_config(config)
        raw = (text or "").strip()
        if raw:
            normalized = normalize_cookie_text(raw)
            if not normalized:
                return {
                    "error": "Das ist kein gültiges cookies.txt (Netscape-Format). "
                    "Exportiere es mit einer Erweiterung wie „Get cookies.txt LOCALLY“ "
                    "auf youtube.com, während du eingeloggt bist."
                }
            try:
                COOKIE_DIR.mkdir(parents=True, exist_ok=True)
                COOKIE_FILE.write_text(normalized, encoding="utf-8")
            except Exception as exc:
                return {"error": f"Cookies konnten nicht gespeichert werden: {exc}"}
        return self.cookie_status()

    def clear_cookies(self) -> dict:
        try:
            COOKIE_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        return self.cookie_status()

    def analyze(self, url: str) -> dict:
        url = url.strip()
        if not valid_url(url):
            return {"error": "Das sieht nicht wie ein gültiger Link aus."}
        source = music_source(url)
        options = base_options()
        options["skip_download"] = True
        collection = amazon_collection(url) if source == "amazon" else ""
        if collection:
            data = resolve_amazon_collection(url, collection)
            if "error" in data:
                return data
            with self._lock:
                self._lists[url] = {"data": data, "created": time.time()}
            return {
                "title": data["name"],
                "matched": "",
                "thumbnail": data["cover"],
                "duration": sum(song["duration"] for song in data["tracks"]),
                "uploader": data["owner"],
                "extractor": "Amazon Music",
                "max_height": 0,
                "audio_only": True,
                "music": True,
                "playlist": True,
                "count": len(data["tracks"]),
                "tracks": [song["label"] for song in data["tracks"]],
                "cut": data["cut"],
                "url": url,
            }
        if source:
            resolved = resolve_music(url, source)
            if "error" in resolved:
                return resolved
            info, error, tried_login = extract_with_fallback(
                options, f"ytsearch1:{resolved['query']}"
            )
            if error:
                return {"error": friendly_error(error, tried_login, "Suche fehlgeschlagen")}
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
                "playlist": False,
                "count": 0,
                "tracks": [],
                "cut": False,
                "url": info.get("webpage_url") or "",
            }
        info, error, tried_login = extract_with_fallback(options, url)
        if error:
            return {"error": friendly_error(error, tried_login, "Analyse fehlgeschlagen")}
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
            "playlist": False,
            "count": 0,
            "tracks": [],
            "cut": False,
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
            "total": 0,
            "done": 0,
            "label": "",
            "failed": [],
        }
        with self._lock:
            self._cleanup_old()
            self._jobs[job_id] = job
        if music_source(url) == "amazon" and amazon_collection(url):
            threading.Thread(
                target=self._run_collection, args=(job_id, url, title), daemon=True
            ).start()
            return {"job": job_id}
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

        def restart() -> None:
            job["percent"] = 0.0
            job["speed"] = 0
            job["eta"] = None
            job["status"] = "starting"
            for leftover in job_dir.glob("*"):
                if leftover.is_file() and leftover.suffix.lower() in (".part", ".ytdl"):
                    leftover.unlink(missing_ok=True)

        try:
            info, error, tried_login = extract_with_fallback(options, url, True, restart)
            if error:
                job["status"] = "error"
                job["error"] = friendly_error(error, tried_login)
                return
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
        except Exception as exc:
            job["status"] = "error"
            job["error"] = friendly_error(str(exc))

    def _collection(self, url: str) -> dict:
        with self._lock:
            entry = self._lists.get(url)
        if entry and time.time() - entry["created"] < LIST_TTL:
            return dict(entry["data"])
        data = resolve_amazon_collection(url, amazon_collection(url))
        if "error" not in data:
            with self._lock:
                self._lists[url] = {"data": data, "created": time.time()}
        return data

    def _run_collection(self, job_id: str, url: str, title: str) -> None:
        job = self._jobs[job_id]
        job_dir = Path(job["dir"])
        job["status"] = "reading"
        data = self._collection(url)
        if "error" in data:
            job["status"] = "error"
            job["error"] = data["error"]
            return
        tracks = data["tracks"]
        job["total"] = len(tracks)
        job["status"] = "downloading"
        shares: dict[int, float] = {}
        speeds: dict[int, float] = {}
        guard = threading.Lock()

        def refresh() -> None:
            job["percent"] = min(99.0, sum(shares.values()) / len(tracks) * 100.0)
            job["speed"] = int(sum(speeds.values()))

        def hook_for(index: int):
            def inner(d: dict) -> None:
                status = d.get("status")
                with guard:
                    if status == "downloading":
                        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                        done = d.get("downloaded_bytes") or 0
                        shares[index] = min(0.9, done / total) if total else 0.0
                        speeds[index] = d.get("speed") or 0
                    elif status == "finished":
                        shares[index] = 0.95
                        speeds[index] = 0
                    refresh()
            return inner

        def fetch(item: tuple[int, dict]) -> Path | None:
            index, song = item
            options = base_options()
            options.update(
                {
                    "outtmpl": str(job_dir / f"{index:03d}.%(ext)s"),
                    "format": "bestaudio/best",
                    "progress_hooks": [hook_for(index)],
                    "concurrent_fragment_downloads": 2,
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "320",
                        }
                    ],
                }
            )
            with guard:
                job["label"] = song["label"]
            try:
                _, error, _ = extract_with_fallback(
                    options, f"ytsearch1:{song['query']}", True
                )
            except Exception as exc:
                error = str(exc)
            made = job_dir / f"{index:03d}.mp3"
            target: Path | None = None
            if not error and made.is_file():
                stem = sanitize_filename(f"{index:03d} - {song['label']}")
                target = job_dir / f"{stem}.mp3"
                try:
                    made.replace(target)
                except OSError:
                    target = made
            with guard:
                if target is None:
                    job["failed"].append(song["label"])
                else:
                    job["done"] += 1
                shares[index] = 1.0
                speeds[index] = 0
                refresh()
            return target

        try:
            with ThreadPoolExecutor(max_workers=TRACK_WORKERS) as pool:
                files = [path for path in pool.map(fetch, enumerate(tracks, 1)) if path]
            if not files:
                job["status"] = "error"
                job["error"] = (
                    "Zu keinem Song dieser Playlist habe ich eine Aufnahme gefunden."
                )
                return
            job["status"] = "packing"
            job["label"] = ""
            job["speed"] = 0
            bundle = job_dir / "bundle.zip"
            with zipfile.ZipFile(bundle, "w", zipfile.ZIP_STORED) as archive:
                for path in sorted(files):
                    archive.write(path, path.name)
                    path.unlink(missing_ok=True)
            job["file"] = str(bundle)
            job["name"] = f"{sanitize_filename(title or data['name'])}.zip"
            job["percent"] = 100.0
            job["status"] = "done"
        except Exception as exc:
            job["status"] = "error"
            job["error"] = friendly_error(str(exc))

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
            "total": job["total"],
            "done": job["done"],
            "label": job["label"],
            "failed": list(job["failed"]),
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
