from __future__ import annotations

import base64
import html
import json
import os
import platform
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
import uuid
import webbrowser
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from app.core.config import DATA_DIR, ROOT_DIR

ALARM_PREFIX = "JonWecker_"
ALARM_DIR = DATA_DIR / "alarms"
AUTOSTART_NAME = "Jon-Autostart.vbs"

WEATHER_CODES = {
    0: "klar",
    1: "überwiegend klar",
    2: "teils bewölkt",
    3: "bedeckt",
    45: "Nebel",
    48: "Reifnebel",
    51: "leichter Nieselregen",
    53: "Nieselregen",
    55: "starker Nieselregen",
    56: "gefrierender Nieselregen",
    57: "starker gefrierender Nieselregen",
    61: "leichter Regen",
    63: "Regen",
    65: "starker Regen",
    66: "gefrierender Regen",
    67: "starker gefrierender Regen",
    71: "leichter Schneefall",
    73: "Schneefall",
    75: "starker Schneefall",
    77: "Schneegriesel",
    80: "leichte Regenschauer",
    81: "Regenschauer",
    82: "heftige Regenschauer",
    85: "Schneeschauer",
    86: "starke Schneeschauer",
    95: "Gewitter",
    96: "Gewitter mit Hagel",
    99: "schweres Gewitter mit Hagel",
}


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str


class SystemService:
    def __init__(self, command_timeout: float = 60.0) -> None:
        self._timeout = command_timeout

    def run_powershell(self, command: str) -> CommandResult:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=self._timeout,
        )
        return CommandResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def run_cmd(self, command: str) -> CommandResult:
        completed = subprocess.run(
            ["cmd", "/c", command],
            capture_output=True,
            text=True,
            timeout=self._timeout,
        )
        return CommandResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def open_url(self, url: str) -> bool:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return webbrowser.open(url)

    def start_program(self, path: str, args: list[str] | None = None) -> int:
        resolved = shutil.which(path) or path
        process = subprocess.Popen(
            [resolved, *(args or [])],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            if os.name == "nt"
            else 0,
        )
        return process.pid

    def kill_program(self, name: str) -> CommandResult:
        target = name if name.lower().endswith(".exe") else f"{name}.exe"
        return self.run_cmd(f'taskkill /IM "{target}" /F')

    def open_explorer(self, path: str) -> None:
        target = Path(path).expanduser()
        if not target.exists():
            raise FileNotFoundError(str(target))
        subprocess.Popen(["explorer", str(target)])

    def list_dir(self, path: str) -> list[dict]:
        target = Path(path).expanduser()
        if not target.is_dir():
            raise NotADirectoryError(str(target))
        entries: list[dict] = []
        for item in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            stat = item.stat()
            entries.append(
                {
                    "name": item.name,
                    "path": str(item),
                    "is_dir": item.is_dir(),
                    "size": stat.st_size,
                }
            )
        return entries

    def read_file(self, path: str, max_bytes: int = 2_000_000) -> str:
        target = Path(path).expanduser()
        data = target.read_bytes()[:max_bytes]
        return data.decode("utf-8", errors="replace")

    def write_file(self, path: str, content: str) -> None:
        target = Path(path).expanduser()
        if target.exists():
            from app.services.trash_service import get_trash_service

            get_trash_service().stash_overwrite(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def edit_file(self, path: str, old: str, new: str, count: int = 1) -> dict:
        target = Path(path).expanduser()
        text = target.read_text(encoding="utf-8")
        occurrences = text.count(old)
        if occurrences == 0:
            raise ValueError("Textstelle nicht gefunden")
        from app.services.trash_service import get_trash_service

        get_trash_service().stash_overwrite(target, "bearbeitet")
        replaced = text.replace(old, new) if count < 0 else text.replace(old, new, count)
        target.write_text(replaced, encoding="utf-8")
        return {"path": str(target), "replacements": occurrences if count < 0 else min(count, occurrences)}

    def move_path(self, source: str, destination: str) -> str:
        from app.services.trash_service import get_trash_service

        src = Path(source).expanduser()
        dst = Path(destination).expanduser()
        if not src.exists():
            raise FileNotFoundError(str(src))
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and dst.is_file():
            get_trash_service().stash_overwrite(dst)
        moved = shutil.move(str(src), str(dst))
        get_trash_service().record_move(src, Path(moved))
        return moved

    def delete_path(self, path: str) -> None:
        target = Path(path).expanduser()
        if not target.exists():
            raise FileNotFoundError(str(target))
        from app.services.trash_service import get_trash_service

        if get_trash_service().stash_delete(target) is None:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

    def open_in_vscode(self, path: str) -> int:
        return self.start_program("code", [path])

    def make_dir(self, path: str) -> str:
        target = Path(path).expanduser()
        target.mkdir(parents=True, exist_ok=True)
        return str(target)

    def append_file(self, path: str, content: str) -> None:
        target = Path(path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(content)

    def copy_path(self, source: str, destination: str) -> str:
        src = Path(source).expanduser()
        dst = Path(destination).expanduser()
        if not src.exists():
            raise FileNotFoundError(str(src))
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            return shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
        return shutil.copy2(str(src), str(dst))

    def search_files(self, root: str, pattern: str, limit: int = 200) -> list[str]:
        base = Path(root).expanduser()
        if not base.is_dir():
            raise NotADirectoryError(str(base))
        matches: list[str] = []
        for item in base.rglob(pattern):
            matches.append(str(item))
            if len(matches) >= limit:
                break
        return matches

    def zip_paths(self, sources: list[str], destination: str) -> str:
        dst = Path(destination).expanduser()
        dst.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as archive:
            for source in sources:
                src = Path(source).expanduser()
                if src.is_dir():
                    for file in src.rglob("*"):
                        if file.is_file():
                            archive.write(file, file.relative_to(src.parent))
                elif src.is_file():
                    archive.write(src, src.name)
        return str(dst)

    def unzip(self, source: str, destination: str) -> str:
        src = Path(source).expanduser()
        dst = Path(destination).expanduser()
        dst.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(src) as archive:
            archive.extractall(dst)
        return str(dst)

    def clipboard_get(self) -> str:
        try:
            import pyperclip

            return pyperclip.paste()
        except Exception:
            result = self.run_powershell("Get-Clipboard")
            return result.stdout

    def clipboard_set(self, text: str) -> bool:
        try:
            import pyperclip

            pyperclip.copy(text)
            return True
        except Exception:
            self.run_powershell(f"Set-Clipboard -Value @'\n{text}\n'@")
            return True

    def screenshot(self, path: str | None = None) -> dict:
        import pyautogui

        image = pyautogui.screenshot()
        if path:
            target = Path(path).expanduser()
            target.parent.mkdir(parents=True, exist_ok=True)
            image.save(str(target))
            return {"path": str(target), "width": image.width, "height": image.height}
        from io import BytesIO

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return {"data_url": f"data:image/png;base64,{encoded}"}

    def screenshot_data_url(self, max_width: int = 1024, quality: int = 65) -> str:
        import pyautogui
        from io import BytesIO

        image = pyautogui.screenshot()
        if image.width > max_width:
            ratio = max_width / image.width
            image = image.resize((max_width, max(1, int(image.height * ratio))))
        if image.mode != "RGB":
            image = image.convert("RGB")
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=quality)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"

    def webcam_snapshot_data_url(
        self, camera: int = 0, max_width: int = 1024, quality: int = 80
    ) -> str:
        try:
            import cv2
        except Exception:
            raise RuntimeError(
                "Webcam braucht OpenCV. Installiere: pip install opencv-python"
            )
        backends = (
            [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
            if os.name == "nt"
            else [cv2.CAP_ANY]
        )
        indices = [camera, 1, 2] if camera == 0 else [camera]
        frame = None
        for index in indices:
            for backend in backends:
                cap = cv2.VideoCapture(index, backend)
                try:
                    if not cap.isOpened():
                        continue
                    for _ in range(6):
                        ok, grabbed = cap.read()
                        if ok and grabbed is not None:
                            frame = grabbed
                finally:
                    cap.release()
                if frame is not None:
                    break
            if frame is not None:
                break
        if frame is None:
            raise RuntimeError(
                "Keine Webcam gefunden oder sie wird gerade von einer anderen "
                "App benutzt"
            )
        height, width = frame.shape[:2]
        if width > max_width:
            ratio = max_width / width
            frame = cv2.resize(frame, (max_width, max(1, int(height * ratio))))
        ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not ok:
            raise RuntimeError("Webcam-Bild konnte nicht kodiert werden")
        encoded = base64.b64encode(buffer.tobytes()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"

    def idle_seconds(self) -> float:
        if os.name != "nt":
            return 0.0
        import ctypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        millis = ctypes.windll.kernel32.GetTickCount() - info.dwTime
        return max(0.0, millis / 1000.0)

    def http_get(self, url: str, max_bytes: int = 200_000) -> dict:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        request = urllib.request.Request(url, headers={"User-Agent": "Jon/1.0"})
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            raw = response.read(max_bytes)
            charset = response.headers.get_content_charset() or "utf-8"
            return {
                "status": response.status,
                "content_type": response.headers.get_content_type(),
                "body": raw.decode(charset, errors="replace"),
            }

    def download_file(self, url: str, destination: str) -> str:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        dst = Path(destination).expanduser()
        dst.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(url, headers={"User-Agent": "Jon/1.0"})
        with urllib.request.urlopen(request, timeout=self._timeout) as response, dst.open(
            "wb"
        ) as handle:
            shutil.copyfileobj(response, handle)
        return str(dst)

    def system_info(self) -> dict:
        info = {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "python": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "time": datetime.now().isoformat(timespec="seconds"),
            "user": os.environ.get("USERNAME") or os.environ.get("USER"),
        }
        try:
            usage = shutil.disk_usage(Path.home().anchor or "C:/")
            info["disk_total_gb"] = round(usage.total / 1e9, 1)
            info["disk_free_gb"] = round(usage.free / 1e9, 1)
        except Exception:
            pass
        return info

    def list_processes(self, limit: int = 60) -> list[dict]:
        result = self.run_powershell(
            "Get-Process | Sort-Object -Property WS -Descending | "
            f"Select-Object -First {limit} Name, Id, "
            "@{N='MB';E={[math]::Round($_.WS/1MB,1)}} | ConvertTo-Json -Compress"
        )
        try:
            data = json.loads(result.stdout or "[]")
            return data if isinstance(data, list) else [data]
        except Exception:
            return []

    def lock_screen(self) -> bool:
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=False)
        return True

    def choose_folder(self) -> str:
        script = (
            "Add-Type -AssemblyName System.Windows.Forms | Out-Null; "
            "$dialog = New-Object System.Windows.Forms.FolderBrowserDialog; "
            "$dialog.Description = 'Projektordner fuer Jon waehlen'; "
            "$dialog.ShowNewFolderButton = $true; "
            "$anchor = New-Object System.Windows.Forms.Form; "
            "$anchor.TopMost = $true; $anchor.ShowInTaskbar = $false; "
            "$anchor.Opacity = 0; $anchor.Show(); $anchor.Activate(); "
            "$result = $dialog.ShowDialog($anchor); $anchor.Close(); "
            "if ($result -eq [System.Windows.Forms.DialogResult]::OK) "
            "{ [Console]::Out.Write($dialog.SelectedPath) }"
        )
        completed = subprocess.run(
            ["powershell", "-STA", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=600,
        )
        return (completed.stdout or "").strip()

    def set_alarm(
        self, label: str, time_str: str = "", in_minutes: float | None = None
    ) -> dict:
        if os.name != "nt":
            raise RuntimeError("Wecker sind nur unter Windows verfuegbar")
        now = datetime.now()
        if in_minutes is not None and float(in_minutes) > 0:
            target = now + timedelta(minutes=float(in_minutes))
        elif time_str.strip():
            try:
                hour, minute = [int(x) for x in time_str.strip().split(":")[:2]]
            except Exception:
                raise ValueError("time muss das Format HH:MM haben")
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
        else:
            raise ValueError("time (HH:MM) oder in_minutes angeben")
        target = target.replace(microsecond=0)
        task_name = f"{ALARM_PREFIX}{uuid.uuid4().hex[:8]}"
        ALARM_DIR.mkdir(parents=True, exist_ok=True)
        script = ALARM_DIR / f"{task_name}.ps1"
        text = (label.strip() or "Wecker").replace("'", "''")
        script.write_text(
            f"$player = New-Object System.Media.SoundPlayer \"$env:WINDIR\\Media\\Alarm01.wav\"\n"
            "try { $player.PlayLooping() } catch { }\n"
            "$shell = New-Object -ComObject WScript.Shell\n"
            f"$null = $shell.Popup('{text}', 0, 'Jon Wecker', 0x1040)\n"
            "try { $player.Stop() } catch { }\n"
            f"Unregister-ScheduledTask -TaskName '{task_name}' -Confirm:$false "
            "-ErrorAction SilentlyContinue\n"
            "Remove-Item -LiteralPath $MyInvocation.MyCommand.Path -Force "
            "-ErrorAction SilentlyContinue\n",
            encoding="utf-8-sig",
        )
        at = target.strftime("%Y-%m-%dT%H:%M:%S")
        command = (
            "$action = New-ScheduledTaskAction -Execute 'powershell.exe' "
            f"-Argument '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"{script}\"'; "
            f"$trigger = New-ScheduledTaskTrigger -Once -At ([datetime]'{at}'); "
            f"Register-ScheduledTask -TaskName '{task_name}' -Description '{text}' "
            "-Action $action -Trigger $trigger -Force | Out-Null"
        )
        result = self.run_powershell(command)
        if result.exit_code != 0:
            script.unlink(missing_ok=True)
            raise RuntimeError(
                result.stderr.strip() or "Wecker konnte nicht angelegt werden"
            )
        return {"task": task_name, "label": label.strip() or "Wecker", "rings_at": at}

    def list_alarms(self) -> list[dict]:
        command = (
            f"Get-ScheduledTask -TaskName '{ALARM_PREFIX}*' -ErrorAction SilentlyContinue "
            "| ForEach-Object { $info = $_ | Get-ScheduledTaskInfo; [pscustomobject]@{ "
            "name = $_.TaskName; label = $_.Description; "
            "rings_at = if ($info.NextRunTime) { $info.NextRunTime.ToString('yyyy-MM-ddTHH:mm:ss') } else { $null } "
            "} } | ConvertTo-Json -Compress"
        )
        result = self.run_powershell(command)
        raw = (result.stdout or "").strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except Exception:
            return []
        return data if isinstance(data, list) else [data]

    def delete_alarm(self, name: str) -> bool:
        name = name.strip()
        if not name.startswith(ALARM_PREFIX):
            raise ValueError(f"Weckername muss mit {ALARM_PREFIX} beginnen")
        result = self.run_powershell(
            f"Unregister-ScheduledTask -TaskName '{name}' -Confirm:$false"
        )
        (ALARM_DIR / f"{name}.ps1").unlink(missing_ok=True)
        return result.exit_code == 0

    def _fetch(self, url: str, timeout: float = 8.0) -> str:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 "
                "Safari/537.36"
            },
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")

    @staticmethod
    def _strip_tags(fragment: str) -> str:
        return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()

    def web_search(self, query: str, max_results: int = 6) -> list[dict]:
        query = query.strip()
        if not query:
            return []
        page = self._fetch(
            "https://html.duckduckgo.com/html/?"
            + urllib.parse.urlencode({"q": query})
        )
        snippets = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</a>', page, re.S
        )
        results: list[dict] = []
        for i, match in enumerate(
            re.finditer(
                r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                page,
                re.S,
            )
        ):
            href = match.group(1)
            url = href
            if "uddg=" in href:
                params = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                url = params.get("uddg", [href])[0]
            snippet = self._strip_tags(snippets[i]) if i < len(snippets) else ""
            results.append(
                {
                    "title": self._strip_tags(match.group(2)),
                    "url": url,
                    "snippet": snippet[:300],
                }
            )
            if len(results) >= max(1, min(int(max_results), 10)):
                break
        return results

    def get_weather(self, city: str, days: int = 3) -> dict:
        city = city.strip()
        if not city:
            raise ValueError("Stadt angeben")
        geo = json.loads(
            self._fetch(
                "https://geocoding-api.open-meteo.com/v1/search?"
                + urllib.parse.urlencode({"name": city, "count": 1, "language": "de"})
            )
        )
        places = geo.get("results") or []
        if not places:
            raise ValueError(f"Ort nicht gefunden: {city}")
        place = places[0]
        days = max(1, min(int(days), 7))
        data = json.loads(
            self._fetch(
                "https://api.open-meteo.com/v1/forecast?"
                + urllib.parse.urlencode(
                    {
                        "latitude": place["latitude"],
                        "longitude": place["longitude"],
                        "current": "temperature_2m,apparent_temperature,"
                        "relative_humidity_2m,precipitation,weather_code,"
                        "wind_speed_10m",
                        "daily": "weather_code,temperature_2m_max,"
                        "temperature_2m_min,precipitation_probability_max",
                        "timezone": "auto",
                        "forecast_days": days,
                    }
                )
            )
        )
        current = data.get("current", {})
        daily = data.get("daily", {})
        forecast = []
        for i, date in enumerate(daily.get("time", [])):
            forecast.append(
                {
                    "date": date,
                    "min": daily.get("temperature_2m_min", [None] * 7)[i],
                    "max": daily.get("temperature_2m_max", [None] * 7)[i],
                    "regen_prozent": daily.get(
                        "precipitation_probability_max", [None] * 7
                    )[i],
                    "wetter": WEATHER_CODES.get(
                        daily.get("weather_code", [None] * 7)[i], "unbekannt"
                    ),
                }
            )
        return {
            "ort": f"{place.get('name')}, {place.get('country', '')}".strip(", "),
            "jetzt": {
                "temperatur": current.get("temperature_2m"),
                "gefuehlt": current.get("apparent_temperature"),
                "luftfeuchte": current.get("relative_humidity_2m"),
                "niederschlag": current.get("precipitation"),
                "wind_kmh": current.get("wind_speed_10m"),
                "wetter": WEATHER_CODES.get(current.get("weather_code"), "unbekannt"),
            },
            "vorhersage": forecast,
        }

    def read_pdf(self, path: str, max_pages: int = 40) -> dict:
        from pypdf import PdfReader

        target = Path(path).expanduser()
        if not target.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {path}")
        reader = PdfReader(str(target))
        total = len(reader.pages)
        limit = max(1, min(int(max_pages), total))
        text = "\n\n".join(
            reader.pages[i].extract_text() or "" for i in range(limit)
        )
        return {
            "seiten_gesamt": total,
            "seiten_gelesen": limit,
            "text": text[:20000],
        }

    def media_control(self, action: str, times: int = 1) -> dict:
        if os.name != "nt":
            raise RuntimeError("Medien-Steuerung ist nur unter Windows verfuegbar")
        import ctypes

        keys = {
            "play_pause": 0xB3,
            "play": 0xB3,
            "pause": 0xB3,
            "next": 0xB0,
            "previous": 0xB1,
            "stop": 0xB2,
            "volume_up": 0xAF,
            "volume_down": 0xAE,
            "mute": 0xAD,
        }
        code = keys.get(action.strip().lower())
        if code is None:
            raise ValueError(f"Unbekannte Aktion. Erlaubt: {', '.join(sorted(set(keys)))}")
        count = max(1, min(int(times), 50))
        for _ in range(count):
            ctypes.windll.user32.keybd_event(code, 0, 0, 0)
            ctypes.windll.user32.keybd_event(code, 0, 2, 0)
        return {"action": action, "times": count}

    def scan_network(self) -> list[dict]:
        import socket as sock
        from concurrent.futures import ThreadPoolExecutor

        result = self.run_cmd("arp -a")
        found: list[dict] = []
        for line in (result.stdout or "").splitlines():
            m = re.match(
                r"\s*(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{2}(?:-[0-9a-fA-F]{2}){5})\s+(\S+)",
                line,
            )
            if not m:
                continue
            ip, mac, kind = m.groups()
            if (
                ip.endswith(".255")
                or ip.startswith(("224.", "239.", "255."))
                or mac.lower() == "ff-ff-ff-ff-ff-ff"
                or mac.lower().startswith("01-00-5e")
            ):
                continue
            found.append({"ip": ip, "mac": mac, "typ": kind, "name": ""})

        def resolve(device: dict) -> None:
            try:
                device["name"] = sock.gethostbyaddr(device["ip"])[0]
            except Exception:
                pass

        with ThreadPoolExecutor(max_workers=12) as pool:
            list(pool.map(resolve, found))
        return found

    def wake_on_lan(self, mac: str) -> dict:
        import socket as sock

        clean = re.sub(r"[^0-9a-fA-F]", "", mac)
        if len(clean) != 12:
            raise ValueError("MAC-Adresse ungueltig (Format AA-BB-CC-DD-EE-FF)")
        packet = b"\xff" * 6 + bytes.fromhex(clean) * 16
        with sock.socket(sock.AF_INET, sock.SOCK_DGRAM) as s:
            s.setsockopt(sock.SOL_SOCKET, sock.SO_BROADCAST, 1)
            s.sendto(packet, ("255.255.255.255", 9))
        return {"sent": True, "mac": mac}

    def list_printers(self) -> list[dict]:
        result = self.run_powershell(
            "Get-Printer | Select-Object Name, PrinterStatus, Default "
            "| ConvertTo-Json -Compress"
        )
        raw = (result.stdout or "").strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except Exception:
            return []
        items = data if isinstance(data, list) else [data]
        return [
            {
                "name": p.get("Name"),
                "status": str(p.get("PrinterStatus", "")),
                "standard": bool(p.get("Default")),
            }
            for p in items
        ]

    def print_file(self, path: str, printer: str = "") -> dict:
        target = Path(path).expanduser()
        if not target.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {path}")
        if printer.strip():
            safe = printer.strip().replace("'", "''")
            command = (
                f"Start-Process -FilePath '{target}' -Verb PrintTo "
                f"-ArgumentList '\"{safe}\"'"
            )
        else:
            command = f"Start-Process -FilePath '{target}' -Verb Print"
        result = self.run_powershell(command)
        if result.exit_code != 0:
            raise RuntimeError(
                result.stderr.strip()
                or "Drucken fehlgeschlagen (unterstuetzt der Dateityp Drucken?)"
            )
        return {"printing": True, "file": str(target), "printer": printer or "Standard"}

    def health_check(self) -> dict:
        report: dict = {}
        try:
            usage = shutil.disk_usage(Path.home().anchor or "C:/")
            report["festplatte"] = {
                "gesamt_gb": round(usage.total / 1e9, 1),
                "frei_gb": round(usage.free / 1e9, 1),
                "belegt_prozent": round(100 * (1 - usage.free / usage.total)),
            }
        except Exception:
            pass
        report["ram_top"] = self.list_processes(10)
        result = self.run_powershell(
            "Get-CimInstance Win32_StartupCommand | "
            "Select-Object Name, Command, Location | ConvertTo-Json -Compress"
        )
        try:
            data = json.loads((result.stdout or "").strip() or "[]")
            items = data if isinstance(data, list) else [data]
            report["autostart"] = [
                {"name": i.get("Name"), "befehl": str(i.get("Command", ""))[:120]}
                for i in items
            ][:25]
        except Exception:
            report["autostart"] = []
        try:
            import ctypes

            report["laufzeit_stunden"] = round(
                ctypes.windll.kernel32.GetTickCount64() / 3_600_000, 1
            )
        except Exception:
            pass
        try:
            temp = Path(os.environ.get("TEMP", ""))
            total = 0
            count = 0
            for item in temp.rglob("*"):
                if count > 20000:
                    break
                if item.is_file():
                    total += item.stat().st_size
                    count += 1
            report["temp_ordner_mb"] = round(total / 1e6)
        except Exception:
            pass
        try:
            mem = self.run_powershell(
                "Get-CimInstance Win32_OperatingSystem | Select-Object "
                "TotalVisibleMemorySize, FreePhysicalMemory | ConvertTo-Json -Compress"
            )
            data = json.loads((mem.stdout or "").strip())
            total_gb = round(data["TotalVisibleMemorySize"] / 1e6, 1)
            free_gb = round(data["FreePhysicalMemory"] / 1e6, 1)
            report["arbeitsspeicher"] = {
                "gesamt_gb": total_gb,
                "frei_gb": free_gb,
                "belegt_prozent": round(100 * (1 - free_gb / total_gb)),
            }
        except Exception:
            pass
        return report

    def _autostart_launcher(self) -> Path:
        base = os.environ.get("APPDATA")
        if not base:
            raise RuntimeError("APPDATA nicht gefunden")
        startup = (
            Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        )
        return startup / AUTOSTART_NAME

    def autostart_status(self) -> bool:
        if os.name != "nt":
            return False
        try:
            return self._autostart_launcher().exists()
        except Exception:
            return False

    def set_autostart(self, enabled: bool) -> bool:
        if os.name != "nt":
            raise RuntimeError("Autostart ist nur unter Windows verfuegbar")
        launcher = self._autostart_launcher()
        if not enabled:
            launcher.unlink(missing_ok=True)
            return False
        bat = ROOT_DIR / "autostart-jon.bat"
        if not bat.exists():
            bat = ROOT_DIR / "start-jon.bat"
        if not bat.exists():
            raise FileNotFoundError(f"Autostart-Skript nicht gefunden: {bat}")
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_text(
            'Set sh = CreateObject("WScript.Shell")\n'
            f'sh.Run Chr(34) & "{bat}" & Chr(34), 7, False\n',
            encoding="utf-8",
        )
        return True

    def local_llm_status(self, base_url: str) -> dict:
        root = base_url.rstrip("/").replace("://localhost", "://127.0.0.1")
        if root.endswith("/v1"):
            root = root[:-3]
        for suffix, key in (("/api/tags", "models"), ("/v1/models", "data")):
            try:
                request = urllib.request.Request(root + suffix)
                with urllib.request.urlopen(request, timeout=1.0) as response:
                    data = json.loads(response.read())
                    items = data.get(key, [])
                    models = [
                        item.get("name") or item.get("id")
                        for item in items
                        if isinstance(item, dict)
                    ]
                    return {"reachable": True, "models": [m for m in models if m]}
            except Exception:
                continue
        return {"reachable": False, "models": []}
