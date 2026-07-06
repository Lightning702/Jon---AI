from __future__ import annotations

import os
import shutil
import subprocess
import webbrowser
from dataclasses import dataclass
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
