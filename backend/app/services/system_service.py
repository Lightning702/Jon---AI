from __future__ import annotations

import base64
import json
import os
import platform
import shutil
import subprocess
import urllib.request
import webbrowser
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


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

    def local_llm_status(self, base_url: str) -> dict:
        root = base_url.rstrip("/")
        if root.endswith("/v1"):
            root = root[:-3]
        for suffix, key in (("/api/tags", "models"), ("/v1/models", "data")):
            try:
                request = urllib.request.Request(root + suffix)
                with urllib.request.urlopen(request, timeout=1.5) as response:
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
