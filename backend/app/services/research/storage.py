from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from app.services.skill_service import SKILLS_DIR

from .models import ResearchTask, slugify

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,60}$")


def topic_dir(slug: str) -> Path:
    path = SKILLS_DIR / slugify(slug)
    path.mkdir(parents=True, exist_ok=True)
    return path


def file_name(name: str) -> str:
    stem = Path(str(name)).stem
    if _SAFE_NAME.match(stem):
        return f"{stem}.md"
    return f"{slugify(stem, 'notiz')}.md"


def write_file(slug: str, name: str, content: str) -> str:
    safe = file_name(name)
    path = topic_dir(slug) / safe
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return safe


def read_file(slug: str, name: str) -> str:
    path = topic_dir(slug) / file_name(name)
    if not path.exists():
        raise FileNotFoundError(name)
    return path.read_text(encoding="utf-8", errors="replace")


def list_files(slug: str) -> list[dict[str, object]]:
    path = SKILLS_DIR / slugify(slug)
    if not path.exists():
        return []
    return [
        {
            "name": item.name,
            "chars": item.stat().st_size,
            "geaendert": datetime.fromtimestamp(item.stat().st_mtime).isoformat(
                timespec="seconds"
            ),
        }
        for item in sorted(path.glob("*.md"))
    ]


def write_sources(task: ResearchTask) -> str:
    lines = [
        f"# Quellen — {task.title or task.topic}",
        "",
        f"Recherche vom {datetime.fromtimestamp(task.created_at).strftime('%d.%m.%Y')} · "
        f"{len(task.sources)} geprüfte Quellen",
        "",
    ]
    by_topic: dict[str, list] = {}
    for source in task.sources:
        by_topic.setdefault(source.subtopic or "Allgemein", []).append(source)
    for name, entries in by_topic.items():
        lines.append(f"## {name}")
        lines.append("")
        for source in entries:
            mark = {
                "genutzt": "✅",
                "verworfen": "➖",
                "fehler": "⚠️",
            }.get(source.status, "•")
            title = source.title or source.domain or source.url
            lines.append(f"- {mark} [{title}]({source.url}) — {source.domain}")
            if source.reason:
                lines.append(f"  - {source.reason}")
        lines.append("")
    lines.append("## Legende")
    lines.append("")
    lines.append("- ✅ genutzt · ➖ nicht brauchbar · ⚠️ nicht erreichbar")
    return write_file(task.slug, "sources", "\n".join(lines))


def write_index(task: ResearchTask, overview: str) -> str:
    header = (
        f"> Automatisch von Jon Deep Learning erstellt am "
        f"{datetime.fromtimestamp(task.created_at).strftime('%d.%m.%Y um %H:%M')} · "
        f"{len(task.sources)} Quellen · {len(task.files)} Dateien\n\n"
    )
    return write_file(task.slug, "README", header + overview)
