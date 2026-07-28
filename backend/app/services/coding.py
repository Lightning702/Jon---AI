from __future__ import annotations

import re
from pathlib import Path

CODING_PROMPT = (
    "Du bist Jon, ein autonomer KI-Coding-Agent, der direkt im geoeffneten Projektordner "
    "des Nutzers arbeitet, vergleichbar mit modernen KI-Coding-Agenten in einem Editor. "
    "Nutze deine Tools, um den Code wirklich zu aendern, statt ihn nur zu beschreiben. "
    "Arbeitsweise: 1) Verstehe Aufgabe und relevanten Projektkontext (search_files, "
    "read_file, list_dir). 2) Plane kurz. 3) Aendere Code. Fuer bestehende Dateien IMMER "
    "edit_file (praeziser Ersatz einer exakten Textstelle), niemals ganze Dateien unnoetig "
    "ueberschreiben; write_file nur fuer neue Dateien. 4) Starte bei Bedarf Builds oder Tests "
    "(run_powershell/run_cmd), lies die Ausgabe, behebe Fehler und wiederhole, bis die "
    "Aufgabe erledigt ist. 5) Nutze Git ueber run_powershell, wenn der Nutzer es will. "
    "\n\nORDNER-REGEL (hart): Dein einziger Arbeitsbereich ist der aktuell geoeffnete "
    "Projektordner. Alles, was du liest, schreibst, loeschst, startest oder installierst, "
    "liegt in diesem Ordner. Die Datei-Tools sind technisch darauf begrenzt und Shell-Befehle "
    "starten immer darin, Zugriffe ausserhalb werden blockiert. Versuche gar nicht erst, "
    "ausserhalb zu lesen, zu schreiben oder dorthin zu wechseln (kein cd, kein Set-Location, "
    "kein .., kein C:\\Users\\..., kein Desktop, kein Systemordner). Wenn etwas ausserhalb "
    "liegt, sag das kurz, statt es zu umgehen. Systemaufgaben ausserhalb des Codens "
    "(Mails, Musik, Smarthome, Termine) gehoeren nicht hierher. "
    "\n\nDATEI-REGEL (hart): Nennt der Nutzer eine Datei ('schreib das in index.html', "
    "'mach das in app.py'), dann aendere genau diese Datei sofort mit edit_file bzw. "
    "write_file. Existiert sie noch nicht, lege sie im Projektordner an. Sagt der Nutzer "
    "'hier', 'da', 'in der Datei' oder gar nichts, ist die aktuell geoeffnete Datei gemeint. "
    "Gib fertigen Code niemals nur im Chat aus und frag nicht um Erlaubnis zum Schreiben - "
    "schreib ihn direkt in die Datei und antworte danach in 1-3 Saetzen, was du geaendert "
    "hast. Behalte den Stil, die Sprache und die Struktur der Datei bei und lass alles "
    "unberuehrt, wonach nicht gefragt wurde. "
    "\n\nCODE-STIL: Schreibe Code ohne Kommentare, ausser der Nutzer verlangt sie "
    "ausdruecklich. Sprechende Namen, kurze Funktionen, keine toten Platzhalter, keine "
    "TODO-Reste. Nutze die im Projekt bereits vorhandenen Bibliotheken, Konventionen und "
    "Design-Tokens, statt neue einzufuehren. "
    "Unterstuetze viele Sprachen und Frameworks (HTML/CSS/JS/TS, React/Vue/Angular/Svelte, "
    "Python, Java, Kotlin, C#, C++, Rust, Go, PHP, SQL, Flutter, Electron, Tauri u.a.). "
    "Antworte knapp auf Deutsch und zeig lieber Ergebnisse als lange Erklaerungen."
)

DESIGN_PROMPT = (
    "OBERFLAECHEN-DESIGN (bei allem, was der Nutzer sieht - HTML, CSS, React, Vue, Svelte, "
    "Flutter, Tailwind): liefere von selbst ein modernes, hochwertiges Ergebnis, nie ein "
    "graues Standard-Formular. Richtwerte:\n"
    "- Liquid Glass / Glassmorphism als Grundoptik: halbtransparente Flaechen "
    "(rgba(255,255,255,.06-.12) auf dunklem, rgba(255,255,255,.55-.7) auf hellem Grund), "
    "backdrop-filter: blur(20px) saturate(180%), 1px Rand aus rgba(255,255,255,.14), "
    "innerer Lichtrand per inset-box-shadow, weiche Tiefenschatten "
    "(0 8px 32px rgba(0,0,0,.35)), Radien 14-28px.\n"
    "- Hintergrund mit Tiefe: dezente Farbverlaeufe oder weich leuchtende Farbflecken "
    "hinter dem Glas, damit die Unschaerfe sichtbar wird; nie flaches Grau hinter Glas.\n"
    "- Design-Tokens als CSS-Variablen (Farben, Radien, Abstaende, Schatten, Uebergaenge) "
    "im :root, Abstandsskala in 4px-Schritten, Layout mit Grid/Flex, mobile first, "
    "clamp() fuer fluide Typografie, kein horizontales Scrollen.\n"
    "- Typografie: moderner System-Stack (ui-sans-serif, -apple-system, 'Segoe UI', Inter, "
    "Roboto, sans-serif), klare Groessenhierarchie, Zeilenhoehe 1.5, ruhige Zeilenlaengen.\n"
    "- Interaktion: sichtbare hover-, active-, focus-visible- und disabled-Zustaende, "
    "Uebergaenge 150-250ms mit cubic-bezier(.22,1,.36,1), sparsame Animationen und "
    "@media (prefers-reduced-motion: reduce) respektieren.\n"
    "- Hell und Dunkel unterstuetzen (prefers-color-scheme), Kontrast mindestens 4.5:1, "
    "semantisches HTML, sinnvolle aria-Attribute, Tastaturbedienung.\n"
    "- Keine externen CDNs, Fonts oder Bibliotheken nachladen, wenn das Projekt sie nicht "
    "schon nutzt; eine einzelne HTML-Datei bleibt in sich geschlossen.\n"
    "- Hat das Projekt bereits ein eigenes Design (Tailwind-Klassen, Theme-Variablen, "
    "Komponenten), fuege dich exakt dort ein, statt einen zweiten Stil daneben zu bauen."
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

TEXT_SUFFIXES = {
    ".html", ".htm", ".css", ".scss", ".sass", ".less", ".js", ".jsx", ".ts",
    ".tsx", ".vue", ".svelte", ".json", ".jsonc", ".md", ".txt", ".py", ".java",
    ".kt", ".cs", ".c", ".h", ".cpp", ".hpp", ".rs", ".go", ".php", ".rb",
    ".sql", ".sh", ".ps1", ".bat", ".yml", ".yaml", ".toml", ".ini", ".cfg",
    ".env", ".xml", ".dart", ".swift", ".lua", ".r", ".pl", ".gradle",
}
FILE_TOKEN_RE = re.compile(r"[\w\-./\\]*[\w\-]+\.[A-Za-z0-9]{1,8}")
MAX_FILE_CHARS = 9000


def _visible(path: Path) -> bool:
    return not path.name.startswith(".") and path.name not in IGNORE_DIRS


def _tree(root: Path, depth: int, budget: list[int], prefix: str = "") -> list[str]:
    lines: list[str] = []
    try:
        items = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except OSError:
        return lines
    for item in items:
        if not _visible(item) or budget[0] <= 0:
            continue
        budget[0] -= 1
        if item.is_dir():
            lines.append(f"{prefix}{item.name}/")
            if depth > 0:
                lines.extend(_tree(item, depth - 1, budget, prefix + "  "))
        else:
            lines.append(f"{prefix}{item.name}")
    return lines


def workspace_summary(root: Path, max_entries: int = 120) -> str:
    root = Path(root)
    if not root.is_dir():
        return f"Workspace: {root} (nicht gefunden)"
    markers = [
        f"{name} → {kind}"
        for name, kind in PROJECT_MARKERS.items()
        if (root / name).exists()
    ]
    budget = [max_entries]
    lines = _tree(root, 2, budget)
    context = (
        f"Geoeffneter Projektordner (dein einziger Arbeitsbereich): {root}\n"
    )
    if markers:
        context += "Projekttyp: " + ", ".join(markers) + "\n"
    context += "Dateien im Projekt:\n" + "\n".join(lines)
    if budget[0] <= 0:
        context += "\n… (gekuerzt, weitere Dateien mit list_dir/search_files)"
    return context


def _read_text(path: Path, limit: int = MAX_FILE_CHARS) -> str | None:
    try:
        if path.stat().st_size > 4_000_000:
            return None
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if len(text) > limit:
        return text[:limit] + "\n… (gekuerzt, Rest mit read_file)"
    return text


def active_file_context(workspace: str | None, active_file: str | None) -> str:
    if not active_file:
        return ""
    path = Path(active_file).expanduser()
    try:
        resolved = path.resolve()
    except OSError:
        return ""
    if workspace:
        root = Path(workspace).expanduser().resolve()
        if resolved != root and root not in resolved.parents:
            return ""
    if not resolved.is_file():
        return ""
    header = (
        f"Aktuell im Editor geoeffnete Datei: {resolved}\n"
        "Unklare Ortsangaben des Nutzers ('hier', 'da', 'in der Datei') beziehen sich "
        "auf genau diese Datei. Aendere sie direkt mit edit_file."
    )
    if resolved.suffix.lower() not in TEXT_SUFFIXES:
        return header
    content = _read_text(resolved)
    if content is None:
        return header
    return f"{header}\nAktueller Inhalt:\n```\n{content}\n```"


def _candidates(root: Path, name: str, budget: list[int]) -> list[Path]:
    hits: list[Path] = []
    target = name.lower()
    stack = [root]
    while stack and budget[0] > 0:
        current = stack.pop(0)
        try:
            items = list(current.iterdir())
        except OSError:
            continue
        for item in items:
            if not _visible(item):
                continue
            budget[0] -= 1
            if budget[0] <= 0:
                break
            if item.is_dir():
                stack.append(item)
            elif item.name.lower() == target:
                hits.append(item)
                if len(hits) >= 4:
                    return hits
    return hits


def mentioned_files_context(
    workspace: str | None, text: str, active_file: str | None = None
) -> str:
    if not workspace or not text:
        return ""
    root = Path(workspace).expanduser()
    if not root.is_dir():
        return ""
    root = root.resolve()
    active = ""
    if active_file:
        try:
            active = str(Path(active_file).expanduser().resolve()).lower()
        except OSError:
            active = ""
    names: list[str] = []
    for raw in FILE_TOKEN_RE.findall(text):
        name = raw.strip().split("/")[-1].split("\\")[-1]
        suffix = Path(name).suffix.lower()
        if suffix not in TEXT_SUFFIXES:
            continue
        if name.lower() not in [n.lower() for n in names]:
            names.append(name)
        if len(names) >= 3:
            break
    if not names:
        return ""
    blocks: list[str] = []
    budget = [4000]
    chars = MAX_FILE_CHARS
    for name in names:
        hits = _candidates(root, name, budget)
        if not hits:
            blocks.append(
                f"{name}: im Projektordner nicht gefunden — lege sie an, wenn der "
                "Nutzer dort Code haben will."
            )
            continue
        if len(hits) > 1:
            listing = ", ".join(str(h) for h in hits)
            blocks.append(
                f"{name}: mehrere Treffer ({listing}) — nimm die passendste und sag kurz, "
                "welche du geaendert hast."
            )
            continue
        target = hits[0]
        if str(target).lower() == active:
            blocks.append(f"{name} → {target} (bereits im Editor geoeffnet)")
            continue
        content = _read_text(target, chars) if chars > 400 else None
        if content is None:
            blocks.append(f"{name} → {target}")
        else:
            chars -= len(content)
            blocks.append(f"{name} → {target}\nAktueller Inhalt:\n```\n{content}\n```")
    return (
        "Vom Nutzer genannte Dateien — aendere genau diese direkt:\n"
        + "\n".join(blocks)
    )
