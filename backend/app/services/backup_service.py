from __future__ import annotations

import io
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from app.core.config import DATA_DIR, ROOT_DIR

SKILLS_DIR = ROOT_DIR / "skills"
SECRET_KEYS = {
    "mail_imap_password",
    "telegram_bot_token",
    "ha_token",
    "spotify_client_secret",
}
SKIP = {"backend.log", "chat_key.bin"}


def export_backup(include_keys: bool = False) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(DATA_DIR.rglob("*")):
            if not path.is_file() or path.name in SKIP:
                continue
            rel = path.relative_to(DATA_DIR)
            if rel.name == "user_settings.json" and not include_keys:
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    for key in SECRET_KEYS:
                        if key in data:
                            data[key] = ""
                    if "accounts.json" not in str(rel):
                        zf.writestr(
                            f"data/{rel.as_posix()}",
                            json.dumps(data, ensure_ascii=False, indent=2),
                        )
                        continue
                except Exception:
                    pass
            if rel.name == "accounts.json" and not include_keys:
                continue
            zf.write(path, f"data/{rel.as_posix()}")
        if SKILLS_DIR.is_dir():
            for path in sorted(SKILLS_DIR.glob("*.md")):
                zf.write(path, f"skills/{path.name}")
        zf.writestr(
            "jon-backup.json",
            json.dumps(
                {"created_at": datetime.now().isoformat(timespec="seconds")},
                ensure_ascii=False,
            ),
        )
    return buffer.getvalue()


def import_backup(raw: bytes) -> dict:
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except Exception:
        return {"error": "Keine gültige Backup-Datei"}
    names = archive.namelist()
    if "jon-backup.json" not in names:
        return {"error": "Das ist kein Jon-Backup"}
    restored = 0
    for name in names:
        if name.endswith("/") or name == "jon-backup.json":
            continue
        if name.startswith("data/"):
            target = DATA_DIR / Path(name[5:])
        elif name.startswith("skills/"):
            target = SKILLS_DIR / Path(name[7:]).name
        else:
            continue
        if ".." in Path(name).parts:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(name) as source, target.open("wb") as handle:
            shutil.copyfileobj(source, handle)
        restored += 1
    return {"restored": restored, "hinweis": "Bitte Jon neu starten."}
