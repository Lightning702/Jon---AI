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

from app.core.config import DATA_DIR

ALARM_PREFIX = "JonWecker_"
ALARM_DIR = DATA_DIR / "alarms"

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
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def edit_file(self, path: str, old: str, new: str, count: int = 1) -> dict:
        target = Path(path).expanduser()
        text = target.read_text(encoding="utf-8")
        occurrences = text.count(old)
        if occurrences == 0:
            raise ValueError("Textstelle nicht gefunden")
        replaced = text.replace(old, new) if count < 0 else text.replace(old, new, count)
        target.write_text(replaced, encoding="utf-8")
        return {"path": str(target), "replacements": occurrences if count < 0 else min(count, occurrences)}

    def move_path(self, source: str, destination: str) -> str:
        src = Path(source).expanduser()
        dst = Path(destination).expanduser()
        if not src.exists():
            raise FileNotFoundError(str(src))
        dst.parent.mkdir(parents=True, exist_ok=True)
        return shutil.move(str(src), str(dst))

    def delete_path(self, path: str) -> None:
        target = Path(path).expanduser()
        if not target.exists():
            raise FileNotFoundError(str(target))
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
