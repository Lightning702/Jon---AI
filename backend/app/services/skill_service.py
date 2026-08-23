from __future__ import annotations

import re
import shutil
from pathlib import Path

from app.core.config import ROOT_DIR

SKILLS_DIR = ROOT_DIR / "skills"

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,48}$")
_FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,60}$")
FOLDER_ENTRY = "skill.md"


def _first_heading(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        if stripped:
            return stripped[:80]
    return ""


class SkillService:
    def __init__(self) -> None:
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    def _check(self, name: str) -> str:
        if not _NAME_RE.match(name):
            raise ValueError("Ungültiger Skill-Name")
        return name

    def _folder(self, name: str) -> Path:
        return SKILLS_DIR / self._check(name)

    def _path(self, name: str) -> Path:
        folder = self._folder(name)
        entry = folder / FOLDER_ENTRY
        if entry.exists():
            return entry
        flat = SKILLS_DIR / f"{name}.md"
        if flat.exists() or not folder.is_dir():
            return flat
        return entry

    def is_folder(self, name: str) -> bool:
        return (self._folder(name) / FOLDER_ENTRY).exists()

    def list(self) -> list[dict]:
        skills: list[dict] = []
        for path in sorted(SKILLS_DIR.glob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            skills.append(
                {
                    "name": path.stem,
                    "title": _first_heading(text),
                    "chars": len(text),
                    "kind": "datei",
                    "files": 1,
                }
            )
        for folder in sorted(SKILLS_DIR.iterdir()):
            if not folder.is_dir():
                continue
            entry = folder / FOLDER_ENTRY
            if not entry.exists():
                continue
            if not _NAME_RE.match(folder.name):
                continue
            text = entry.read_text(encoding="utf-8", errors="replace")
            skills.append(
                {
                    "name": folder.name,
                    "title": _first_heading(text),
                    "chars": len(text),
                    "kind": "wissen",
                    "files": len(list(folder.glob("*.md"))),
                }
            )
        skills.sort(key=lambda item: item["name"])
        return skills

    def read(self, name: str) -> dict:
        path = self._path(name)
        if not path.exists():
            raise FileNotFoundError(name)
        text = path.read_text(encoding="utf-8", errors="replace")
        result = {"name": name, "title": _first_heading(text), "content": text}
        if self.is_folder(name):
            result["kind"] = "wissen"
            result["files"] = self.files(name)
        else:
            result["kind"] = "datei"
            result["files"] = []
        return result

    def files(self, name: str) -> list[dict]:
        folder = self._folder(name)
        if not folder.is_dir():
            return []
        entries: list[dict] = []
        for path in sorted(folder.glob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            entries.append(
                {
                    "name": path.name,
                    "title": _first_heading(text),
                    "chars": len(text),
                }
            )
        return entries

    def read_file(self, name: str, file_name: str) -> dict:
        folder = self._folder(name)
        stem = Path(str(file_name)).stem
        if not _FILE_RE.match(stem):
            raise ValueError("Ungültiger Dateiname")
        path = folder / f"{stem}.md"
        if not path.exists():
            raise FileNotFoundError(file_name)
        text = path.read_text(encoding="utf-8", errors="replace")
        return {
            "name": name,
            "file": path.name,
            "title": _first_heading(text),
            "content": text,
        }

    def write(self, name: str, content: str) -> dict:
        folder = self._folder(name)
        if folder.is_dir():
            path = folder / FOLDER_ENTRY
        else:
            path = SKILLS_DIR / f"{name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"name": name, "title": _first_heading(content), "chars": len(content)}

    def delete(self, name: str) -> bool:
        folder = self._folder(name)
        flat = SKILLS_DIR / f"{name}.md"
        removed = False
        if flat.exists():
            flat.unlink()
            removed = True
        if folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)
            removed = True
        return removed

    def catalog(self) -> str:
        skills = self.list()
        if not skills:
            return ""
        lines = []
        for skill in skills:
            extra = (
                f" (Wissensordner mit {skill['files']} Dateien)"
                if skill.get("kind") == "wissen"
                else ""
            )
            lines.append(f"- {skill['name']}: {skill['title']}{extra}")
        return (
            "Verfügbare Skills (Anleitungen). Rufe read_skill mit dem Namen auf, bevor "
            "du eine passende Aufgabe startest, und folge der Anleitung genau. Bei "
            "Wissensordnern liefert read_skill zusätzlich die Liste der Wissensdateien, "
            "die du mit read_skill_file oder ask_knowledge öffnen kannst:\n"
            + "\n".join(lines)
        )
