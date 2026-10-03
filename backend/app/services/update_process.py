from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from app.core.config import DATA_DIR


async def _update_installed_app():
    from app.services.update_service import check_update, download_installer

    yield "Schritt 1: Suche nach einer neueren Version...\n"
    info = await asyncio.to_thread(check_update, True)
    current, latest = info["current"], info["latest"]
    announced = info.get("announced")
    if not info["update"]:
        yield f"Jon ist aktuell (Version {current}). Nichts zu tun.\n"
        if announced:
            yield f"Version {announced} ist angekuendigt, aber noch nicht zum Installieren fertig.\n"
        yield "DONE\n"
        return
    yield f"Version {latest} gefunden (installiert: {current}).\n"
    if announced:
        yield f"Hinweis: {announced} ist bereits angekuendigt, fertig ist bisher {latest}.\n"

    url = info.get("installer_url") or ""
    if not url:
        yield "Zu dieser Version gibt es noch kein fertiges Installationsprogramm.\n"
        yield f"Du kannst sie hier laden: {info.get('url')}\n"
        return

    yield "Schritt 2: Lade das Installationsprogramm...\n"
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    last = [0]

    def progress(done: int, total: int) -> None:
        percent = int(done * 100 / total) if total else 0
        if percent >= last[0] + 10 or (total and done >= total):
            last[0] = percent
            mb = done / 1_048_576
            whole = total / 1_048_576 if total else 0
            text = f"  {percent}% ({mb:.1f} von {whole:.1f} MB)\n" if total else f"  {mb:.1f} MB\n"
            loop.call_soon_threadsafe(queue.put_nowait, text)

    task = asyncio.create_task(
        asyncio.to_thread(
            download_installer,
            url,
            latest,
            info.get("installer_size", 0),
            progress,
            info.get("checksum_url", ""),
        )
    )
    while not task.done() or not queue.empty():
        try:
            yield await asyncio.wait_for(queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            continue
    try:
        target = task.result()
    except Exception as error:
        yield f"Download fehlgeschlagen: {error}\n"
        yield f"Du kannst die Version auch hier laden: {info.get('url')}\n"
        return

    yield f"Gespeichert: {target}\n"
    yield "Schritt 3: Deine Daten bleiben erhalten - das Installationsprogramm "
    yield "aktualisiert nur die Programmdateien.\n"
    yield "Schritt 4: Jon schliesst sich jetzt und startet die Installation.\n"
    yield f"INSTALLER {target}\n"
    yield "DONE\n"


GIT_UMGEBUNG = {"GIT_TERMINAL_PROMPT": "0", "GIT_MERGE_AUTOEDIT": "no", "GIT_EDITOR": "true", "LC_ALL": "C"}


async def git(root: Path, *argumente: str) -> tuple[int, str]:
    programm = shutil.which("git")
    if not programm:
        return 127, "Git wurde nicht gefunden."
    prozess = await asyncio.create_subprocess_exec(
        programm, *argumente,
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ, **GIT_UMGEBUNG},
    )
    ausgabe, _ = await prozess.communicate()
    return prozess.returncode or 0, ausgabe.decode("utf-8", errors="replace").strip()


def _zeilen(text: str) -> list[str]:
    return [zeile.strip() for zeile in text.splitlines() if zeile.strip()]


async def git_aktualisieren(root: Path, ergebnis: dict, ziel: str = "main"):
    ergebnis.update(ok=False, dateien=[], konflikte=[])
    code, remotes = await git(root, "remote")
    if code != 0 or not _zeilen(remotes):
        yield "Kein Git-Server eingetragen. Lade die neue Version von https://getjon.info.\n"
        return
    remote = "origin" if "origin" in _zeilen(remotes) else _zeilen(remotes)[0]
    if (root / ".git" / "MERGE_HEAD").exists() or (root / ".git" / "rebase-merge").exists() or (root / ".git" / "rebase-apply").exists():
        yield "Im Jon-Ordner läuft gerade ein unvollständiges Zusammenführen. Bitte zuerst abschließen.\n"
        return
    code, ausgabe = await git(root, "fetch", remote, ziel)
    if code != 0:
        yield f"Neue Version konnte nicht geladen werden: {ausgabe[-500:]}\n"
        return
    code, neu = await git(root, "rev-parse", "FETCH_HEAD")
    if code != 0:
        yield "Die geladene Version ist nicht lesbar.\n"
        return
    code, vorher = await git(root, "rev-parse", "HEAD")
    if code != 0:
        yield "Der Jon-Ordner hat noch keinen Git-Stand.\n"
        return
    code, basis = await git(root, "merge-base", "HEAD", neu)
    if code == 0 and basis == neu:
        yield "Jon ist bereits auf dem neuesten Stand.\n"
        ergebnis.update(ok=True, aktuell=True)
        return
    code, kommend = await git(root, "diff", "--name-only", basis if code == 0 else "HEAD", neu)
    kommende = set(_zeilen(kommend))
    _, lokal = await git(root, "diff", "--name-only", "HEAD")
    _, unversioniert = await git(root, "ls-files", "--others", "--exclude-standard")
    konflikte = sorted(kommende & (set(_zeilen(lokal)) | set(_zeilen(unversioniert))))
    if konflikte:
        ergebnis["konflikte"] = konflikte
        yield "Die neue Version ändert Dateien, die du selbst bearbeitet hast:\n"
        for name in konflikte[:20]:
            yield f"  {name}\n"
        yield "Ich habe nichts verändert, damit deine Arbeit sicher bleibt. Sichere oder committe diese Dateien und starte das Update dann erneut.\n"
        return
    sicherung = "sicherung-vor-update-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    await git(root, "branch", sicherung, "HEAD")
    yield f"Sicherungsstand angelegt: {sicherung}\n"
    if _zeilen(lokal):
        yield f"Deine {len(_zeilen(lokal))} lokal geänderten Dateien bleiben unverändert erhalten.\n"
    identitaet: list[str] = []
    if not (await git(root, "config", "user.email"))[1]:
        identitaet = ["-c", "user.name=Jon Update", "-c", "user.email=update@jon.local"]
    code, ausgabe = await git(root, *identitaet, "merge", "--no-edit", neu)
    if code != 0:
        await git(root, "merge", "--abort")
        yield f"Zusammenführen nicht möglich, alles zurückgesetzt auf deinen Stand: {ausgabe[-500:]}\n"
        return
    _, nachher = await git(root, "rev-parse", "HEAD")
    _, dateien = await git(root, "diff", "--name-only", vorher, nachher)
    ergebnis.update(ok=True, dateien=_zeilen(dateien), sicherung=sicherung)
    yield f"Aktualisiert: {len(_zeilen(dateien))} Dateien neu, nichts gelöscht, was dir gehört.\n"


async def perform_update():
    from app.services.update_service import install_mode

    mode = install_mode()
    if mode == "exe":
        async for line in _update_installed_app():
            yield line
        return

    yield "Schritt 1: Prüfe Umgebung...\n"
    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    git_dir = root_dir / ".git"

    if not git_dir.exists():
        yield "Hinweis: Keine Git-Umgebung gefunden.\n"
        yield "Bitte lade die neueste Version manuell von der Website herunter: https://getjon.info\n"
        return

    yield "Schritt 2: Erstelle Backup...\n"
    backup_dir = DATA_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"pre-update-{timestamp}.zip"

    try:
        shutil.make_archive(str(backup_path).replace(".zip", ""), "zip", str(DATA_DIR))
        yield f"Backup erstellt: {backup_path.name}\n"

        backups = sorted(backup_dir.glob("pre-update-*.zip"))
        while len(backups) > 5:
            oldest = backups.pop(0)
            oldest.unlink(missing_ok=True)
            yield f"Altes Backup entfernt: {oldest.name}\n"
    except Exception as e:
        yield f"Fehler beim Backup: {e}\nAbbruch.\n"
        return

    yield "Schritt 3: Hole die neue Version, ohne etwas zu löschen...\n"
    ergebnis: dict = {}
    async for zeile in git_aktualisieren(root_dir, ergebnis):
        yield zeile
    if not ergebnis.get("ok"):
        yield "Abbruch. Dein Jon-Ordner ist unverändert.\n"
        return
    if ergebnis.get("aktuell"):
        yield "DONE\n"
        return
    geaendert = ergebnis.get("dateien", [])
    req_changed = any(name.startswith("backend/requirements") for name in geaendert)
    frontend_changed = any(name.startswith("frontend/") for name in geaendert)

    if req_changed:
        yield "Schritt 4: Installiere Backend-Abhängigkeiten...\n"
        try:
            if os.name == 'nt':
                proc_pip = await asyncio.create_subprocess_shell(
                    f"{sys.executable} -m pip install -r backend/requirements.txt",
                    cwd=str(root_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT
                )
            else:
                proc_pip = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt",
                    cwd=str(root_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT
                )
            stdout_pip, _ = await proc_pip.communicate()
            yield "Backend-Abhängigkeiten aktualisiert.\n"
        except Exception as e:
            yield f"Fehler bei pip install: {e}\n"

    if frontend_changed:
        yield "Schritt 5: Installiere und baue Frontend...\n"
        frontend_dir = root_dir / "frontend"
        try:
            if os.name == 'nt':
                proc_npm_i = await asyncio.create_subprocess_shell(
                    "npm install",
                    cwd=str(frontend_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT
                )
            else:
                proc_npm_i = await asyncio.create_subprocess_exec(
                    "npm", "install",
                    cwd=str(frontend_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT
                )
            await proc_npm_i.communicate()

            if os.name == 'nt':
                proc_npm_b = await asyncio.create_subprocess_shell(
                    "npm run build",
                    cwd=str(frontend_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT
                )
            else:
                proc_npm_b = await asyncio.create_subprocess_exec(
                    "npm", "run", "build",
                    cwd=str(frontend_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT
                )
            await proc_npm_b.communicate()
            yield "Frontend neu gebaut.\n"
        except Exception as e:
            yield f"Fehler beim Frontend-Build: {e}\n"

    yield "Schritt 6: Neustart...\n"
    yield "DONE\n"
    await asyncio.sleep(1)

    is_pi = Path("/etc/systemd/system/jon.service").exists()
    if is_pi:
        if os.name != 'nt':
            await asyncio.create_subprocess_exec("sudo", "systemctl", "restart", "jon")
    else:
        os.execv(sys.executable, [sys.executable] + sys.argv)
