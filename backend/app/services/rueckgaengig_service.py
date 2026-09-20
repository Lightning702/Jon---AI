from __future__ import annotations

import json
import shutil
import threading
import uuid
from datetime import datetime
from pathlib import Path

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.core.store import atomic_write_text

JOURNAL = DATA_DIR / "rueckgaengig.json"
SICHERUNGEN = DATA_DIR / "rueckgaengig"
MAX_EINTRAEGE = 60
MAX_DATEI_MB = 40

UMKEHRBAR = {
    "datei_erstellen",
    "write_file",
    "edit_file",
    "append_file",
    "move_path",
    "copy_path",
    "make_dir",
    "delete_path",
    "unzip",
}


def _jetzt() -> str:
    return datetime.now().isoformat(timespec="seconds")


class RueckgaengigService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._eintraege = self._laden()

    def _laden(self) -> list[dict]:
        if JOURNAL.exists():
            try:
                roh = json.loads(JOURNAL.read_text(encoding="utf-8"))
                if isinstance(roh, list):
                    return roh
            except Exception as _fehler:
                leise(_fehler, "services/rueckgaengig_service")
        return []

    def _sichern(self) -> None:
        try:
            self._eintraege = self._eintraege[-MAX_EINTRAEGE:]
            atomic_write_text(
                JOURNAL,
                json.dumps(self._eintraege, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as _fehler:
            leise(_fehler, "services/rueckgaengig_service")

    def _kopie(self, pfad: Path) -> str:
        try:
            if not pfad.exists() or not pfad.is_file():
                return ""
            if pfad.stat().st_size > MAX_DATEI_MB * 1024 * 1024:
                return ""
            SICHERUNGEN.mkdir(parents=True, exist_ok=True)
            ziel = SICHERUNGEN / f"{uuid.uuid4().hex[:12]}-{pfad.name}"
            shutil.copy2(pfad, ziel)
            return str(ziel)
        except Exception as _fehler:
            leise(_fehler, "services/rueckgaengig_service")
            return ""

    def vormerken(self, werkzeug: str, args: dict) -> None:
        if werkzeug not in UMKEHRBAR:
            return
        eintrag: dict = {
            "id": uuid.uuid4().hex[:12],
            "werkzeug": werkzeug,
            "zeit": _jetzt(),
            "args": {k: str(v)[:400] for k, v in (args or {}).items() if v is not None},
        }
        try:
            if werkzeug == "datei_erstellen":
                ziel = str(args.get("pfad") or args.get("ordner") or "")
                eintrag["ziel"] = ziel
                eintrag["existierte"] = bool(ziel) and Path(ziel).expanduser().exists()
            elif werkzeug in ("write_file", "edit_file", "append_file"):
                pfad = Path(str(args.get("path", ""))).expanduser()
                eintrag["ziel"] = str(pfad)
                eintrag["vorher"] = self._kopie(pfad)
                eintrag["existierte"] = pfad.exists()
            elif werkzeug == "move_path":
                eintrag["quelle"] = str(args.get("source", ""))
                eintrag["ziel"] = str(args.get("destination", ""))
            elif werkzeug in ("copy_path", "make_dir", "unzip", "datei_erstellen"):
                eintrag["ziel"] = str(
                    args.get("destination") or args.get("path") or ""
                )
                eintrag["existierte"] = Path(
                    str(eintrag["ziel"] or ".")
                ).expanduser().exists()
            elif werkzeug == "delete_path":
                eintrag["ziel"] = str(args.get("path", ""))
        except Exception as _fehler:
            leise(_fehler, "services/rueckgaengig_service")
        with self._lock:
            self._eintraege.append(eintrag)
            self._sichern()

    def liste(self, limit: int = 15) -> list[dict]:
        with self._lock:
            return [
                {
                    "id": e["id"],
                    "werkzeug": e["werkzeug"],
                    "zeit": e["zeit"],
                    "ziel": e.get("ziel", ""),
                    "umkehrbar": bool(e.get("vorher"))
                    or e["werkzeug"]
                    in (
                        "move_path",
                        "make_dir",
                        "copy_path",
                        "delete_path",
                        "datei_erstellen",
                    ),
                }
                for e in reversed(self._eintraege[-limit:])
            ]

    def _umkehren(self, eintrag: dict) -> str:
        werkzeug = eintrag.get("werkzeug", "")
        ziel = Path(str(eintrag.get("ziel", ""))).expanduser()
        if werkzeug in ("write_file", "edit_file", "append_file"):
            sicherung = eintrag.get("vorher", "")
            if sicherung and Path(sicherung).exists():
                shutil.copy2(sicherung, ziel)
                return f"{ziel.name} wieder auf den Stand von {eintrag['zeit']} gesetzt."
            if not eintrag.get("existierte") and ziel.exists():
                ziel.unlink()
                return f"{ziel.name} wieder entfernt (war vorher nicht da)."
            return "Keine Sicherung vorhanden - nichts geaendert."
        if werkzeug == "move_path":
            quelle = Path(str(eintrag.get("quelle", ""))).expanduser()
            if ziel.exists():
                shutil.move(str(ziel), str(quelle))
                return f"{quelle.name} zurueckverschoben."
            return "Das Ziel gibt es nicht mehr."
        if werkzeug in ("copy_path", "make_dir", "unzip", "datei_erstellen"):
            if not eintrag.get("existierte") and ziel.exists():
                if ziel.is_dir():
                    shutil.rmtree(ziel, ignore_errors=True)
                else:
                    ziel.unlink()
                return f"{ziel.name} wieder entfernt."
            return "Das war schon vorher da - nichts entfernt."
        if werkzeug == "delete_path":
            from app.services.trash_service import get_trash_service

            papierkorb = get_trash_service()
            eintraege = papierkorb.entries()
            if not eintraege:
                return "Im Papierkorb liegt nichts zum Wiederherstellen."
            ergebnis = papierkorb.restore(str(eintraege[0].get("id", "")))
            if isinstance(ergebnis, dict) and ergebnis.get("error"):
                return str(ergebnis["error"])
            return "Aus dem Papierkorb wiederhergestellt."
        return "Diese Aktion laesst sich nicht umkehren."

    def rueckgaengig(self, kennung: str = "") -> dict:
        with self._lock:
            if not self._eintraege:
                return {"ok": False, "meldung": "Es gibt nichts rueckgaengig zu machen."}
            if kennung:
                treffer = [e for e in self._eintraege if e["id"] == kennung]
                if not treffer:
                    return {"ok": False, "meldung": f"Eintrag {kennung} nicht gefunden."}
                eintrag = treffer[0]
            else:
                eintrag = self._eintraege[-1]
        try:
            meldung = self._umkehren(eintrag)
        except Exception as exc:
            from app.services.fehlertext import verstaendlich

            return {"ok": False, "meldung": verstaendlich(exc, "Rueckgaengig")}
        with self._lock:
            self._eintraege = [e for e in self._eintraege if e["id"] != eintrag["id"]]
            self._sichern()
        return {"ok": True, "meldung": meldung, "werkzeug": eintrag["werkzeug"]}


_service: RueckgaengigService | None = None


def get_rueckgaengig_service() -> RueckgaengigService:
    global _service
    if _service is None:
        _service = RueckgaengigService()
    return _service
