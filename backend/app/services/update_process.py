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
            download_installer, url, latest, info.get("installer_size", 0), progress
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
        yield "Bitte lade die neueste Version manuell von der Website herunter: https://getjon.netlify.app\n"
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

    yield "Schritt 3: Git Update...\n"
    try:
        if os.name == 'nt':
            proc = await asyncio.create_subprocess_shell(
                "git stash",
                cwd=str(root_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                "git", "stash",
                cwd=str(root_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
        stdout, _ = await proc.communicate()
        yield f"Git stash: {stdout.decode('utf-8', errors='replace').strip()}\n"

        if os.name == 'nt':
            proc2 = await asyncio.create_subprocess_shell(
                "git pull",
                cwd=str(root_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
        else:
            proc2 = await asyncio.create_subprocess_exec(
                "git", "pull",
                cwd=str(root_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
        stdout2, _ = await proc2.communicate()
        pull_output = stdout2.decode('utf-8', errors='replace').strip()
        yield f"Git pull: {pull_output}\n"

        if proc2.returncode != 0:
            yield "Git pull fehlgeschlagen, mache Rollback...\n"
            if os.name == 'nt':
                proc3 = await asyncio.create_subprocess_shell(
                    "git stash pop",
                    cwd=str(root_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT
                )
            else:
                proc3 = await asyncio.create_subprocess_exec(
                    "git", "stash", "pop",
                    cwd=str(root_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT
                )
            await proc3.communicate()
            yield "Rollback abgeschlossen. Abbruch.\n"
            return
            
    except Exception as e:
        yield f"Git-Fehler: {e}\nAbbruch.\n"
        return

    req_changed = "requirements.txt" in pull_output
    frontend_changed = "frontend/" in pull_output

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
