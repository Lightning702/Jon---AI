from __future__ import annotations

from pathlib import Path

CODING_PROMPT = (
    "Du bist Jon, ein autonomer KI-Coding-Agent, der direkt im Workspace des Nutzers "
    "arbeitet, vergleichbar mit modernen KI-Coding-Agenten in einem Editor. Nutze deine "
    "Tools, um den Code wirklich zu aendern, statt ihn nur zu beschreiben. "
    "Arbeitsweise: 1) Verstehe Aufgabe und relevanten Projektkontext (search_files, "
    "read_file, list_dir). 2) Plane kurz. 3) Aendere Code. Fuer bestehende Dateien IMMER "
    "edit_file (praeziser Ersatz einer exakten Textstelle), niemals ganze Dateien unnoetig "
    "ueberschreiben; write_file nur fuer neue Dateien. 4) Starte bei Bedarf Builds oder Tests "
    "(run_powershell/run_cmd), lies die Ausgabe, behebe Fehler und wiederhole, bis die "
    "Aufgabe erledigt ist. 5) Nutze Git ueber run_powershell, wenn der Nutzer es will. "
    "Verwende absolute Pfade innerhalb des Workspace. Unterstuetze viele Sprachen und "
    "Frameworks (HTML/CSS/JS/TS, React/Vue/Angular/Svelte, Python, Java, Kotlin, C#, C++, "
    "Rust, Go, PHP, SQL, Flutter, Electron, Tauri u.a.). Antworte knapp auf Deutsch und zeig "
    "lieber Ergebnisse als lange Erklaerungen."
)

IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist",
    "dist-electron", "build", ".vite", ".next", "target", ".idea",
}
PROJECT_MARKERS = {
    "package.json": "Node/JS",
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java/Kotlin (Gradle)",
    "composer.json": "PHP",
    "pubspec.yaml": "Flutter/Dart",
    "index.html": "Web",
}


def workspace_summary(root: Path, max_entries: int = 40) -> str:
    root = Path(root)
    if not root.is_dir():
        return f"Workspace: {root} (nicht gefunden)"
    markers = [
        f"{name} → {kind}"
        for name, kind in PROJECT_MARKERS.items()
        if (root / name).exists()
    ]
    lines: list[str] = []
    count = 0
    for item in sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        if item.name.startswith(".") or item.name in IGNORE_DIRS:
            continue
        lines.append(f"{'[dir]' if item.is_dir() else '[file]'} {item.name}")
        count += 1
        if count >= max_entries:
            lines.append("…")
            break
    context = f"Aktueller Workspace: {root}\n"
    if markers:
        context += "Projekttyp: " + ", ".join(markers) + "\n"
    context += "Oberste Ebene:\n" + "\n".join(lines)
    return context
