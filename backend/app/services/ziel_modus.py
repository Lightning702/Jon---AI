from __future__ import annotations

import asyncio
import re
import time
import uuid

RUNDEN = 12
FEHLVERSUCHE = 2
WEITERGEBEN = {"gedanke", "notiz", "action", "action_error", "approval_required", "hinweis", "running_tool", "running_command"}
BEFEHL = re.compile(r"^/(?:goal|ziel)(?:@\w+)?(?:\s+(.*))?$", re.IGNORECASE | re.DOTALL)
STOPP = {"stopp", "stop", "abbrechen", "aus", "ende", "halt"}
AUFTRAG = (
    "ZIEL: {ziel}\n\n"
    "Arbeite selbstständig, gründlich und so lange daran, bis dieses Ziel vollständig erreicht und geprüft ist. "
    "Nimm dir die Zeit, die es braucht: plane, recherchiere, setze um, teste wirklich und behebe alle Fehler. "
    "Liefere fertige Ergebnisse (Dateien, Antworten, Belege mit Quellen) statt Zwischenständen. "
    "Frag nur nach, wenn es gar nicht anders geht."
)
WEITER = "Mach weiter am ZIEL „{ziel}“. Bisheriger Stand: {stand}\nNoch offen: {offen}\nSetze genau das um, prüfe es und schließe erst ab, wenn das Ziel erreicht ist."
PRUEFEN = (
    "Prüfe streng und ehrlich, ob dieses Ziel vollständig erreicht ist: „{ziel}“\n\n"
    "Ergebnis der letzten Runde ({status}): {zusammenfassung}\n"
    "Dateien: {dateien}\n"
    "Prüfungen: {pruefungen}\n\n"
    "Antworte NUR mit einer Zeile: entweder „ZIEL ERREICHT: <kurze Begründung>“ oder „WEITER: <was konkret noch fehlt>“."
)


def befehl(text: str) -> str | None:
    treffer = BEFEHL.match(str(text or "").strip())
    if not treffer:
        return None
    return (treffer.group(1) or "").strip()


class ZielModus:
    def __init__(self) -> None:
        self.ziele: dict[str, dict] = {}
        self.ereignisse: dict[str, list[dict]] = {}
        self.signale: dict[str, asyncio.Event] = {}
        self.laeufe: dict[str, asyncio.Task] = {}

    def starten(self, ziel: str, source: str = "app", root: str = "", modus: str = "", provider: str = "", model: str = "") -> dict:
        text = " ".join(str(ziel or "").split())
        if not text:
            raise ValueError("Sag mir das Ziel, z. B. /goal Erstelle eine Präsentation über Datensicherung mit Bildern und Quellen.")
        if len(text) > 4000:
            raise ValueError("Das Ziel ist zu lang. Fasse es in höchstens 4000 Zeichen.")
        laufend = [z for z in self.ziele.values() if z["source"] == source and z["status"] == "laeuft"]
        if laufend:
            raise ValueError(f"An einem Ziel arbeite ich hier schon: „{laufend[0]['ziel'][:120]}“. Mit /goal stopp halte ich es an.")
        kennung = uuid.uuid4().hex[:10]
        eintrag = {
            "id": kennung, "ziel": text, "source": source, "status": "laeuft", "runde": 0, "aufgaben": [],
            "urteil": "", "zusammenfassung": "", "dateien": [], "start": time.time(), "ende": 0.0,
            "root": str(root or ""), "modus": modus or ("code" if root else "allgemein"), "provider": provider, "model": model,
        }
        self.ziele[kennung] = eintrag
        self.ereignisse[kennung] = []
        self.signale[kennung] = asyncio.Event()
        lauf = asyncio.create_task(self._lauf(eintrag))
        self.laeufe[kennung] = lauf
        lauf.add_done_callback(lambda _: self.laeufe.pop(kennung, None))
        return dict(eintrag)

    def get(self, kennung: str) -> dict:
        if kennung not in self.ziele:
            raise KeyError("Dieses Ziel gibt es nicht.")
        return dict(self.ziele[kennung])

    def liste(self, source: str = "") -> list[dict]:
        return [dict(z) for z in sorted(self.ziele.values(), key=lambda z: z["start"], reverse=True) if not source or z["source"] == source][:20]

    def laufend(self, source: str) -> dict | None:
        return next((dict(z) for z in self.ziele.values() if z["source"] == source and z["status"] == "laeuft"), None)

    async def stoppen(self, kennung: str) -> dict:
        eintrag = self.ziele[kennung]
        lauf = self.laeufe.get(kennung)
        if lauf and not lauf.done():
            lauf.cancel()
            await asyncio.gather(lauf, return_exceptions=True)
        return dict(eintrag)

    async def verfolgen(self, kennung: str, nach: int = 0):
        if kennung not in self.ziele:
            raise KeyError("Dieses Ziel gibt es nicht.")
        while True:
            signal = self.signale[kennung]
            signal.clear()
            for ereignis in list(self.ereignisse[kennung]):
                if ereignis["nr"] > nach:
                    nach = ereignis["nr"]
                    yield ereignis
            if self.ziele[kennung]["status"] != "laeuft" and any(e["art"] == "ende" for e in self.ereignisse[kennung]):
                return
            try:
                await asyncio.wait_for(signal.wait(), 15)
            except asyncio.TimeoutError:
                yield {"nr": nach, "art": "puls"}

    def _melden(self, eintrag: dict, art: str, **werte) -> None:
        liste = self.ereignisse[eintrag["id"]]
        liste.append({"nr": len(liste) + 1, "art": art, "zeit": time.time(), **werte})
        del liste[:-400]
        self.signale[eintrag["id"]].set()

    async def _lauf(self, eintrag: dict) -> None:
        from app.services.harness import get_harness_service

        harness = get_harness_service()
        auftrag = AUFTRAG.format(ziel=eintrag["ziel"])
        sitzung = ""
        aktuell = ""
        fehlversuche = 0
        try:
            for runde in range(1, RUNDEN + 1):
                eintrag["runde"] = runde
                self._melden(eintrag, "runde", runde=runde, von=RUNDEN)
                task = harness.start(auftrag, eintrag["root"], eintrag["source"], eintrag["provider"], eintrag["model"], thread=sitzung, modus=eintrag["modus"])
                aktuell = task["id"]
                sitzung = harness.sitzung_von(task)
                eintrag["root"] = task["root"]
                eintrag["aufgaben"].append(aktuell)
                async for ereignis in harness.stream(aktuell):
                    if ereignis.get("type") in WEITERGEBEN:
                        self._melden(eintrag, "schritt", typ=ereignis["type"], tool=ereignis.get("tool", ""), text=str(ereignis.get("message") or ereignis.get("command") or "")[:2400], pfad=str(ereignis.get("pfad") or ""))
                fertig = harness.get(aktuell)
                aktuell = ""
                eintrag["zusammenfassung"] = str(fertig.get("summary") or "")
                eintrag["dateien"] = _dateien(fertig, eintrag["dateien"])
                self._melden(eintrag, "runde_fertig", runde=runde, status=fertig["status"], zusammenfassung=eintrag["zusammenfassung"][:3000])
                if fertig["status"] == "cancelled":
                    eintrag["status"] = "abgebrochen"
                    break
                fehlversuche = fehlversuche + 1 if fertig["status"] == "failed" else 0
                if fehlversuche >= FEHLVERSUCHE:
                    eintrag.update(status="fehler", urteil="Zweimal hintereinander gescheitert: " + eintrag["zusammenfassung"][:300])
                    break
                urteil = await self._pruefen(eintrag, fertig)
                eintrag["urteil"] = urteil
                self._melden(eintrag, "urteil", runde=runde, text=urteil)
                if urteil.upper().startswith("ZIEL ERREICHT"):
                    eintrag["status"] = "erreicht"
                    break
                offen = urteil.split(":", 1)[1].strip() if ":" in urteil else ""
                auftrag = WEITER.format(ziel=eintrag["ziel"], stand=eintrag["zusammenfassung"][:1500] or "noch nichts", offen=offen or "prüfe selbst, was noch fehlt")
            else:
                eintrag["status"] = "angehalten"
        except asyncio.CancelledError:
            eintrag["status"] = "abgebrochen"
            if aktuell:
                await asyncio.gather(harness.cancel(aktuell), return_exceptions=True)
            raise
        except Exception as fehler:
            eintrag.update(status="fehler", urteil=str(fehler)[:500])
        finally:
            eintrag["ende"] = time.time()
            self._melden(eintrag, "ende", status=eintrag["status"], urteil=eintrag["urteil"], zusammenfassung=eintrag["zusammenfassung"][:4000], dateien=eintrag["dateien"], runden=eintrag["runde"], dauer=round(eintrag["ende"] - eintrag["start"]))

    async def _pruefen(self, eintrag: dict, task: dict) -> str:
        from app.services.harness.modell import Zugang, anfragen

        pruefungen = [f"{c.get('command', '')} → {c.get('exit_code', '?')}" for c in task.get("checks", [])][-6:]
        nachricht = PRUEFEN.format(
            ziel=eintrag["ziel"],
            status=task["status"],
            zusammenfassung=str(task.get("summary") or "")[:3000] or "keine",
            dateien=", ".join(eintrag["dateien"][-12:]) or "keine",
            pruefungen="; ".join(pruefungen) or "keine",
        )
        try:
            antwort = await anfragen(Zugang(task.get("provider", ""), task.get("model", "")), "Du prüfst streng und ehrlich, ob ein Ziel erreicht ist. Du antwortest mit genau einer Zeile.", nachricht)
        except Exception as fehler:
            return f"WEITER: Die Prüfung ging nicht ({str(fehler)[:120]}). Prüfe selbst, was noch fehlt."
        zeilen = [z.strip(" *`") for z in str(antwort.text or "").splitlines() if z.strip(" *`")]
        treffer = next((z for z in zeilen if z.upper().startswith(("ZIEL ERREICHT", "WEITER"))), "")
        return treffer or "WEITER: " + (zeilen[0][:300] if zeilen else "prüfe selbst, was noch fehlt")


def _dateien(task: dict, bisher: list[str]) -> list[str]:
    neu = [str(d.get("path") or "") for d in task.get("dateien", []) if isinstance(d, dict)]
    neu += [str(c.get("path") or "") for c in task.get("changes", []) if isinstance(c, dict)]
    alle = list(bisher)
    for pfad in neu:
        if pfad and pfad not in alle:
            alle.append(pfad)
    return alle[-30:]


def ende_text(eintrag: dict) -> str:
    status = eintrag.get("status")
    kopf = {
        "erreicht": "Ziel erreicht",
        "angehalten": f"Nach {eintrag.get('runden') or eintrag.get('runde') or RUNDEN} Runden angehalten",
        "abgebrochen": "Ziel abgebrochen",
        "fehler": "Ziel nicht erreicht",
    }.get(str(status), "Ziel beendet")
    teile = [f"{kopf}: {eintrag.get('ziel', '')}".strip()]
    if eintrag.get("zusammenfassung"):
        teile.append(str(eintrag["zusammenfassung"]).strip())
    if eintrag.get("urteil") and status != "erreicht":
        teile.append(str(eintrag["urteil"]).strip())
    if eintrag.get("dateien"):
        teile.append("Dateien:\n" + "\n".join(f"• {p}" for p in eintrag["dateien"][-10:]))
    if status == "angehalten":
        teile.append("Schreib /goal weiter, wenn ich weitermachen soll.")
    return "\n\n".join(teile)


_dienst: ZielModus | None = None


def get_ziel_modus() -> ZielModus:
    global _dienst
    if _dienst is None:
        _dienst = ZielModus()
    return _dienst
