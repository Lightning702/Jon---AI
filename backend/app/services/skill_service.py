from __future__ import annotations

import re
from pathlib import Path

from app.core.config import ROOT_DIR

SKILLS_DIR = ROOT_DIR / "skills"

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,48}$")


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

    def _path(self, name: str) -> Path:
        if not _NAME_RE.match(name):
            raise ValueError("Ungültiger Skill-Name")
        return SKILLS_DIR / f"{name}.md"

    def list(self) -> list[dict]:
        skills: list[dict] = []
        for path in sorted(SKILLS_DIR.glob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            skills.append(
                {
                    "name": path.stem,
                    "title": _first_heading(text),
                    "chars": len(text),
                }
            )
        return skills

    def read(self, name: str) -> dict:
        path = self._path(name)
        if not path.exists():
            raise FileNotFoundError(name)
        text = path.read_text(encoding="utf-8", errors="replace")
        return {"name": name, "title": _first_heading(text), "content": text}

    def write(self, name: str, content: str) -> dict:
        path = self._path(name)
        path.write_text(content, encoding="utf-8")
        return {"name": name, "title": _first_heading(content), "chars": len(content)}

    def delete(self, name: str) -> bool:
        path = self._path(name)
        if not path.exists():
            return False
        path.unlink()
        return True

    def catalog(self) -> str:
        skills = self.list()
        if not skills:
            return ""
        lines = "\n".join(f"- {s['name']}: {s['title']}" for s in skills)
        return (
            "Verfügbare Skills (Anleitungen). Rufe read_skill mit dem Namen auf, bevor "
            "du eine passende Aufgabe startest, und folge der Anleitung genau:\n" + lines
        )
