from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import threading
import uuid
from datetime import datetime
from pathlib import Path

from app.core.config import DATA_DIR
from app.core.store import atomic_write_text
from app.services.coding import IGNORE_DIRS, PROJECT_MARKERS, TEXT_SUFFIXES
from app.core.fehler import leise

PROJECTS_FILE = DATA_DIR / "projects.json"

LANGUAGE_BY_SUFFIX = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript React",
    ".js": "JavaScript",
    ".jsx": "JavaScript React",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".java": "Java",
    ".kt": "Kotlin",
    ".cs": "C#",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".hpp": "C++",
    ".rs": "Rust",
    ".go": "Go",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".dart": "Dart",
    ".lua": "Lua",
    ".sql": "SQL",
    ".sh": "Shell",
    ".ps1": "PowerShell",
    ".md": "Markdown",
}

FRAMEWORK_HINTS = {
    "react": "React",
    "next": "Next.js",
    "vue": "Vue",
    "svelte": "Svelte",
    "@angular/core": "Angular",
    "vite": "Vite",
    "tailwindcss": "Tailwind",
    "electron": "Electron",
    "express": "Express",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "uvicorn": "Uvicorn",
    "sqlalchemy": "SQLAlchemy",
    "pydantic": "Pydantic",
    "pytest": "pytest",
    "jest": "Jest",
    "vitest": "Vitest",
    "playwright": "Playwright",
    "torch": "PyTorch",
    "pandas": "pandas",
    "numpy": "NumPy",
}

KEY_FILES = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "composer.json",
    "pubspec.yaml",
    "tsconfig.json",
    "vite.config.ts",
    "vite.config.js",
    "next.config.js",
    "tailwind.config.js",
    "docker-compose.yml",
    "Dockerfile",
    "Makefile",
    "README.md",
    "index.html",
    "main.py",
    "app.py",
    "manage.py",
    "src/main.ts",
    "src/main.tsx",
    "src/index.ts",
    "src/App.tsx",
    "src/App.vue",
)

MAX_WALK_FILES = 6000
MAX_SNAPSHOT_FILES = 4000


class ProjectError(RuntimeError):
    pass


def _skip(name: str) -> bool:
    return name in IGNORE_DIRS or (name.startswith(".") and name != ".env")


def _root_of(value: str) -> Path:
    root = Path(str(value or "")).expanduser()
    if not root.is_absolute():
        raise ProjectError("Bitte einen vollstaendigen Ordnerpfad angeben.")
    if not root.is_dir():
        raise ProjectError(f"Ordner nicht gefunden: {root}")
    return root.resolve()


def _run_git(root: Path, args: list[str], timeout: float = 20.0) -> tuple[int, str, str]:
    try:
        done = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except FileNotFoundError:
        return 127, "", "Git ist auf diesem Rechner nicht installiert."
    except subprocess.TimeoutExpired:
        return 124, "", "Git hat zu lange gebraucht."
    return done.returncode, done.stdout or "", done.stderr or ""


def _walk(root: Path) -> tuple[list[Path], list[Path]]:
    files: list[Path] = []
    folders: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not _skip(d))
        current = Path(dirpath)
        if current != root:
            folders.append(current)
        for name in sorted(filenames):
            if name.startswith(".") and name not in {".env", ".gitignore"}:
                continue
            files.append(current / name)
            if len(files) >= MAX_WALK_FILES:
                return files, folders
    return files, folders


def _json_file(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _dependencies(root: Path) -> tuple[list[str], dict[str, str]]:
    deps: list[str] = []
    scripts: dict[str, str] = {}
    package = root / "package.json"
    if package.is_file():
        data = _json_file(package)
        for key in ("dependencies", "devDependencies"):
            block = data.get(key)
            if isinstance(block, dict):
                deps.extend(str(name) for name in block)
        raw_scripts = data.get("scripts")
        if isinstance(raw_scripts, dict):
            scripts.update({str(k): str(v) for k, v in raw_scripts.items()})
    requirements = root / "requirements.txt"
    if requirements.is_file():
        try:
            for line in requirements.read_text(encoding="utf-8").splitlines():
                name = re.split(r"[<>=!\[;#]", line.strip(), maxsplit=1)[0].strip()
                if name and not name.startswith("-"):
                    deps.append(name)
        except Exception as _fehler:
            leise(_fehler, "services/project_service")
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8")
            block = re.search(r"dependencies\s*=\s*\[(.*?)\]", text, re.S)
            if block:
                for item in re.findall(r"[\"']([^\"']+)[\"']", block.group(1)):
                    name = re.split(r"[<>=!\[;]", item, maxsplit=1)[0].strip()
                    if name:
                        deps.append(name)
        except Exception as _fehler:
            leise(_fehler, "services/project_service")
    cargo = root / "Cargo.toml"
    if cargo.is_file():
        try:
            text = cargo.read_text(encoding="utf-8")
            block = re.search(r"\[dependencies\](.*?)(\n\[|\Z)", text, re.S)
            if block:
                deps.extend(re.findall(r"^\s*([\w-]+)\s*=", block.group(1), re.M))
        except Exception as _fehler:
            leise(_fehler, "services/project_service")
    seen: set[str] = set()
    unique: list[str] = []
    for name in deps:
        low = name.lower()
        if low in seen:
            continue
        seen.add(low)
        unique.append(name)
    return unique, scripts


def _git_info(root: Path) -> dict:
    code, out, _ = _run_git(root, ["rev-parse", "--is-inside-work-tree"])
    if code != 0 or out.strip() != "true":
        return {"repo": False}
    branch = _run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"])[1].strip()
    status = _run_git(root, ["status", "--porcelain"])[1]
    changed = [line for line in status.splitlines() if line.strip()]
    last = _run_git(root, ["log", "-1", "--pretty=%h %s (%cr)"])[1].strip()
    remote = _run_git(root, ["remote", "get-url", "origin"])[1].strip()
    return {
        "repo": True,
        "branch": branch,
        "geaendert": len(changed),
        "dateien": [line[3:].strip() for line in changed[:40]],
        "letzter_commit": last,
        "remote": remote,
    }


def analyze(root_value: str, deep: bool = True) -> dict:
    root = _root_of(root_value)
    files, folders = _walk(root)
    languages: dict[str, int] = {}
    text_files = 0
    total_bytes = 0
    for item in files:
        suffix = item.suffix.lower()
        label = LANGUAGE_BY_SUFFIX.get(suffix)
        if label:
            languages[label] = languages.get(label, 0) + 1
        if suffix in TEXT_SUFFIXES:
            text_files += 1
        try:
            total_bytes += item.stat().st_size
        except OSError:
            continue
    markers = [
        f"{name} ({kind})"
        for name, kind in PROJECT_MARKERS.items()
        if (root / name).exists()
    ]
    deps, scripts = _dependencies(root)
    frameworks = sorted(
        {
            label
            for key, label in FRAMEWORK_HINTS.items()
            for dep in deps
            if key == dep.lower() or dep.lower().startswith(key)
        }
    )
    key_files = [name for name in KEY_FILES if (root / name).is_file()]
    top = sorted(
        (item.name for item in root.iterdir() if not _skip(item.name)),
        key=str.lower,
    )
    return {
        "root": str(root),
        "name": root.name,
        "dateien": len(files),
        "ordner": len(folders),
        "textdateien": text_files,
        "groesse_bytes": total_bytes,
        "sprachen": sorted(
            ({"name": k, "dateien": v} for k, v in languages.items()),
            key=lambda entry: -entry["dateien"],
        )[:10],
        "projekttyp": markers,
        "frameworks": frameworks,
        "abhaengigkeiten": deps[:60],
        "skripte": scripts,
        "schluesseldateien": key_files,
        "oberste_ebene": top[:40],
        "git": _git_info(root) if deep else {"repo": False},
        "stand": datetime.now().isoformat(timespec="seconds"),
    }


def context_block(root_value: str) -> str:
    try:
        data = analyze(root_value, deep=True)
    except ProjectError:
        return ""
    lines = [f"Projektanalyse fuer {data['root']}:"]
    lines.append(
        f"- Umfang: {data['dateien']} Dateien in {data['ordner']} Unterordnern"
    )
    if data["projekttyp"]:
        lines.append("- Projekttyp: " + ", ".join(data["projekttyp"]))
    if data["sprachen"]:
        lines.append(
            "- Sprachen: "
            + ", ".join(f"{s['name']} ({s['dateien']})" for s in data["sprachen"][:6])
        )
    if data["frameworks"]:
        lines.append("- Frameworks: " + ", ".join(data["frameworks"]))
    if data["abhaengigkeiten"]:
        lines.append(
            "- Abhaengigkeiten: " + ", ".join(data["abhaengigkeiten"][:25])
        )
    if data["skripte"]:
        lines.append(
            "- Skripte: "
            + ", ".join(f"{k} = {v}" for k, v in list(data["skripte"].items())[:10])
        )
    if data["schluesseldateien"]:
        lines.append("- Schluesseldateien: " + ", ".join(data["schluesseldateien"]))
    git = data["git"]
    if git.get("repo"):
        lines.append(
            f"- Git: Branch {git.get('branch') or '?'}, "
            f"{git.get('geaendert', 0)} geaenderte Dateien, "
            f"letzter Commit: {git.get('letzter_commit') or 'keiner'}"
        )
    lines.append(
        "Behandle diesen Ordner als ein zusammenhaengendes Projekt: pruefe vor einer "
        "Aenderung, welche Dateien zusammenhaengen, aendere alle noetigen Stellen und "
        "nutze die vorhandenen Skripte fuer Build und Tests."
    )
    project = get_project_service().find_by_root(str(data["root"]))
    if project:
        lines.append(get_project_service().memory_block(project["id"]))
    return "\n".join(part for part in lines if part)


def snapshot(root_value: str) -> dict:
    root = _root_of(root_value)
    files, _ = _walk(root)
    state: dict[str, list[float]] = {}
    for item in files[:MAX_SNAPSHOT_FILES]:
        try:
            info = item.stat()
        except OSError:
            continue
        state[str(item.relative_to(root))] = [info.st_mtime, info.st_size]
    return {"root": str(root), "dateien": state, "stand": datetime.now().isoformat()}


def changes(root_value: str, before: dict) -> dict:
    current = snapshot(root_value)
    old = before.get("dateien") or {}
    new = current["dateien"]
    created = [name for name in new if name not in old]
    deleted = [name for name in old if name not in new]
    changed = [
        name
        for name, value in new.items()
        if name in old and (old[name][0] != value[0] or old[name][1] != value[1])
    ]
    return {
        "root": current["root"],
        "erstellt": sorted(created)[:200],
        "geloescht": sorted(deleted)[:200],
        "geaendert": sorted(changed)[:200],
        "anzahl": {
            "erstellt": len(created),
            "geloescht": len(deleted),
            "geaendert": len(changed),
        },
        "snapshot": current,
    }


def git_status(root_value: str) -> dict:
    root = _root_of(root_value)
    info = _git_info(root)
    if not info.get("repo"):
        return {"repo": False, "hinweis": "Dieser Ordner ist kein Git-Repository."}
    return info


def git_diff(root_value: str, staged: bool = False, max_chars: int = 24000) -> dict:
    root = _root_of(root_value)
    if not _git_info(root).get("repo"):
        return {"repo": False, "hinweis": "Dieser Ordner ist kein Git-Repository."}
    args = ["diff", "--no-color"]
    if staged:
        args.append("--cached")
    stat = _run_git(root, [*args, "--stat"])[1]
    code, diff, error = _run_git(root, args)
    if code not in (0, 1) and not diff:
        return {"repo": True, "fehler": error.strip() or "Diff nicht moeglich."}
    gekuerzt = len(diff) > max_chars
    return {
        "repo": True,
        "stat": stat.strip(),
        "diff": diff[:max_chars],
        "gekuerzt": gekuerzt,
    }


class ProjectService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> list[dict]:
        try:
            data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception as _fehler:
            leise(_fehler, "services/project_service")
        return []

    def _save(self) -> None:
        try:
            atomic_write_text(
                PROJECTS_FILE,
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as _fehler:
            leise(_fehler, "services/project_service")

    def list(self) -> list[dict]:
        with self._lock:
            items = [dict(entry) for entry in self._data]
        return sorted(items, key=lambda entry: entry.get("zuletzt", ""), reverse=True)

    def get(self, project_id: str) -> dict | None:
        with self._lock:
            entry = next((e for e in self._data if e["id"] == project_id), None)
            return dict(entry) if entry else None

    def find_by_root(self, root: str) -> dict | None:
        try:
            wanted = str(Path(root).expanduser().resolve()).lower()
        except OSError:
            return None
        with self._lock:
            for entry in self._data:
                if str(entry.get("root", "")).lower() == wanted:
                    return dict(entry)
        return None

    def add(self, root: str, name: str = "", note: str = "") -> dict:
        target = _root_of(root)
        existing = self.find_by_root(str(target))
        if existing:
            return self.touch(existing["id"])
        try:
            info = analyze(str(target))
            tech = ", ".join(info["frameworks"] or [s["name"] for s in info["sprachen"][:3]])
        except Exception:
            tech = ""
        entry = {
            "id": uuid.uuid4().hex[:10],
            "name": name.strip() or target.name,
            "root": str(target),
            "technik": tech,
            "notizen": [note.strip()] if note.strip() else [],
            "regeln": [],
            "geraet": platform.node(),
            "erstellt": datetime.now().isoformat(timespec="seconds"),
            "zuletzt": datetime.now().isoformat(timespec="seconds"),
        }
        with self._lock:
            self._data.insert(0, entry)
            self._save()
        return dict(entry)

    def update(self, project_id: str, fields: dict) -> dict:
        with self._lock:
            entry = next((e for e in self._data if e["id"] == project_id), None)
            if entry is None:
                raise ProjectError("Projekt nicht gefunden.")
            if fields.get("name"):
                entry["name"] = str(fields["name"]).strip()[:120]
            if fields.get("technik") is not None:
                entry["technik"] = str(fields["technik"]).strip()[:200]
            if isinstance(fields.get("regeln"), list):
                entry["regeln"] = [str(r).strip()[:300] for r in fields["regeln"] if str(r).strip()][:20]
            if isinstance(fields.get("notizen"), list):
                entry["notizen"] = [str(n).strip()[:400] for n in fields["notizen"] if str(n).strip()][:40]
            entry["zuletzt"] = datetime.now().isoformat(timespec="seconds")
            self._save()
            return dict(entry)

    def remember(self, project_id: str, note: str) -> dict:
        text = note.strip()
        if not text:
            raise ProjectError("Leere Notiz.")
        with self._lock:
            entry = next((e for e in self._data if e["id"] == project_id), None)
            if entry is None:
                raise ProjectError("Projekt nicht gefunden.")
            notes = entry.setdefault("notizen", [])
            if text not in notes:
                notes.insert(0, text[:400])
                del notes[40:]
            entry["zuletzt"] = datetime.now().isoformat(timespec="seconds")
            self._save()
            return dict(entry)

    def touch(self, project_id: str) -> dict:
        with self._lock:
            entry = next((e for e in self._data if e["id"] == project_id), None)
            if entry is None:
                raise ProjectError("Projekt nicht gefunden.")
            entry["zuletzt"] = datetime.now().isoformat(timespec="seconds")
            self._save()
            return dict(entry)

    def delete(self, project_id: str) -> bool:
        with self._lock:
            before = len(self._data)
            self._data = [e for e in self._data if e["id"] != project_id]
            if len(self._data) != before:
                self._save()
                return True
        return False

    def memory_block(self, project_id: str) -> str:
        entry = self.get(project_id)
        if entry is None:
            return ""
        lines = [f"Projektgedaechtnis fuer {entry['name']}:"]
        if entry.get("technik"):
            lines.append(f"- Technik: {entry['technik']}")
        for rule in entry.get("regeln") or []:
            lines.append(f"- Projektregel: {rule}")
        for note in (entry.get("notizen") or [])[:12]:
            lines.append(f"- Merkposten: {note}")
        return "\n".join(lines) if len(lines) > 1 else ""

    def search(self, query: str, limit: int = 6) -> list[dict]:
        text = query.strip().lower()
        if not text:
            return []
        hits = []
        for entry in self.list():
            blob = " ".join(
                [
                    entry.get("name", ""),
                    entry.get("root", ""),
                    entry.get("technik", ""),
                    " ".join(entry.get("notizen") or []),
                    " ".join(entry.get("regeln") or []),
                ]
            ).lower()
            if text in blob or any(word in blob for word in text.split() if len(word) > 2):
                hits.append(entry)
            if len(hits) >= limit:
                break
        return hits


_service: ProjectService | None = None


def get_project_service() -> ProjectService:
    global _service
    if _service is None:
        _service = ProjectService()
    return _service
