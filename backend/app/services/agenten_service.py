from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import DATA_DIR
from app.core.store import atomic_write_text
from app.services.agent_profiles import BOUNDARIES, PROFILES

MAX_AGENTEN = 4
GESAMT_TIMEOUT_S = 1800
TERMINAL = {"done", "needs_review", "failed", "cancelled", "interrupted"}
PRIVAT_HALTEN_S = 900
MATERIAL_ZEICHEN = 60_000
TEIL_TOKENS = 8000
TEIL_TIMEOUT_S = 420
ORDNER_NAME = "Jon Agenten"
VOLLSTAENDIG = "Verlangt der Auftrag eine vollständige Liste, Sammlung, Abschrift, Übersetzung oder Tabelle (zum Beispiel alle Vokabeln), liefere wirklich alle Einträge aus dem Material, ohne Kürzung, ohne „usw.“ und ohne Auswahl. Arbeite ausschließlich mit dem mitgegebenen Material, wenn es vorhanden ist."


def kuerzen(text: str, grenze: int) -> str:
    if len(text) <= grenze:
        return text
    marke = f"\n\n[… {len(text) - grenze} Zeichen in der Mitte ausgelassen …]\n\n"
    rest = max(grenze - len(marke), 400)
    return text[: rest * 2 // 3] + marke + text[-(rest - rest * 2 // 3):]


def dateiname(text: str) -> str:
    sauber = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", text)
    sauber = re.sub(r"\s+", " ", sauber).strip(" .")
    return sauber[:60].strip(" .") or "Auftrag"


@dataclass
class Teilergebnis:
    titel: str
    auftrag: str
    werkzeug: str
    ergebnis: str = ""
    fehler: str = ""
    dauer: float = 0
    rolle: str = "general"

    def als_dict(self) -> dict:
        return {"titel": self.titel, "auftrag": self.auftrag, "werkzeug": self.werkzeug, "ergebnis": self.ergebnis[:80000], "fehler": self.fehler[:1000], "dauer": round(self.dauer, 1), "rolle": self.rolle, "status": "failed" if self.fehler else "done"}


class AgentenService:
    def __init__(self, directory: Path | None = None, complete=None) -> None:
        self.ablage = None if directory is None else directory / "ergebnisse"
        self.directory = directory or DATA_DIR / "fachteam"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.complete = complete
        self.runs: dict[str, dict] = {}
        self.running: dict[str, asyncio.Task] = {}
        for path in sorted(self.directory.glob("*.json"), key=lambda p: p.stat().st_mtime)[-50:]:
            try:
                run = json.loads(path.read_text(encoding="utf-8"))
                if path.stem != run["id"] or not re.fullmatch(r"[a-f0-9]{32}", run["id"]):
                    continue
                if run["status"] not in TERMINAL:
                    run.update(status="interrupted", ok=False, vollstaendig=False, fehler="Jon wurde neu gestartet. Der Auftrag wurde nicht automatisch wiederholt.")
                    for part in run.get("teile", []):
                        if part["status"] not in TERMINAL:
                            part.update(status="interrupted")
                    self._save(run)
                self.runs[run["id"]] = run
            except (OSError, ValueError, KeyError, TypeError):
                continue

    def _save(self, run: dict) -> None:
        run["updated_at"] = time.time()
        if run.get("persist", True):
            atomic_write_text(self.directory / (run["id"] + ".json"), json.dumps(run, ensure_ascii=False))

    @staticmethod
    def standard_ordner() -> Path:
        from app.services.verknuepfung_service import schreibtisch

        return schreibtisch() / ORDNER_NAME

    def ordner(self) -> Path:
        from app.services.settings_service import get_settings_service

        eigener = str(get_settings_service().get().get("agenten_ordner") or "").strip()
        if eigener:
            return Path(eigener).expanduser()
        return self.ablage or self.standard_ordner()

    def ordner_stand(self) -> dict:
        ziel = self.ordner()
        standard = self.ablage or self.standard_ordner()
        return {"pfad": str(ziel), "standard": str(standard), "eigener": ziel != standard, "vorhanden": ziel.is_dir()}

    def ordner_setzen(self, pfad: str) -> dict:
        from app.services.dateiraum_service import get_dateiraum_service
        from app.services.settings_service import get_settings_service

        text = str(pfad or "").strip()
        if text:
            ziel = Path(text).expanduser()
            if not ziel.is_absolute():
                raise ValueError("Bitte einen vollständigen Ordnerpfad angeben.")
            sperre = get_dateiraum_service().gesperrt(ziel.resolve())
            if sperre:
                raise ValueError(sperre)
            try:
                ziel.mkdir(parents=True, exist_ok=True)
                probe = ziel / ".jon-schreibtest"
                probe.write_text("ok", encoding="utf-8")
                probe.unlink()
            except OSError as exc:
                raise ValueError(f"In diesen Ordner kann Jon nicht schreiben: {exc}") from exc
            text = str(ziel.resolve())
        get_settings_service().update({"agenten_ordner": text})
        return self.ordner_stand()

    def _ablegen(self, run: dict) -> None:
        if not run.get("persist", True):
            return
        teile = [p for p in run.get("teile", []) if p.get("ergebnis")]
        if not run.get("antwort") and not teile:
            return
        try:
            ziel = self.ordner()
            ziel.mkdir(parents=True, exist_ok=True)
            zeit = time.strftime("%Y-%m-%d %H-%M", time.localtime(run["created_at"]))
            datei = ziel / f"{zeit} {dateiname(run['aufgabe'])}.md"
            if run.get("datei") and Path(run["datei"]).parent == ziel:
                datei = Path(run["datei"])
            zeilen = [f"# {run['aufgabe'][:300]}", "", f"Jon Fachteam · {time.strftime('%d.%m.%Y %H:%M', time.localtime(run['created_at']))} · Status: {run['status']}", ""]
            if run.get("antwort"):
                zeilen += ["## Ergebnis", "", run["antwort"], ""]
            if len(teile) > 1 or not run.get("antwort"):
                zeilen += ["## Teilergebnisse", ""]
                for teil in teile:
                    zeilen += [f"### {teil.get('titel', '')} ({teil.get('rolle_name') or teil.get('rolle', '')})", "", teil["ergebnis"], ""]
            pruefung = run.get("pruefung") or {}
            if pruefung.get("probleme"):
                zeilen += ["## Gegenprüfung", ""] + [f"- {p}" for p in pruefung["probleme"]] + [""]
            if run.get("fehler"):
                zeilen += ["## Hinweis", "", run["fehler"], ""]
            atomic_write_text(datei, "\n".join(zeilen))
            run["datei"] = str(datei)
        except Exception as exc:
            run["hinweis"] = ((run.get("hinweis") or "") + f" Ergebnis konnte nicht im Agenten-Ordner gespeichert werden: {exc}").strip()

    def get(self, run_id: str) -> dict:
        return json.loads(json.dumps(self.runs[run_id]))

    def list(self, brief: bool = False) -> list[dict]:
        values = [self.get(run["id"]) for run in sorted(self.runs.values(), key=lambda r: r["created_at"], reverse=True) if run.get("persist", True)]
        if brief:
            return [{k: r[k] for k in ("id", "aufgabe", "source", "status", "created_at", "updated_at")} for r in values]
        return values

    def delete(self, run_id: str) -> None:
        if self.runs[run_id]["status"] not in TERMINAL:
            raise ValueError("Bitte den laufenden Auftrag zuerst stoppen.")
        (self.directory / (run_id + ".json")).unlink(missing_ok=True)
        del self.runs[run_id]

    @staticmethod
    def _json(text: str) -> dict:
        raw = re.sub(r"^\x60\x60\x60(?:json)?\s*|\s*\x60\x60\x60$", "", (text or "").strip())
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("Keine gültige strukturierte Antwort.")
        return value

    def _selection(self, slot: str) -> dict:
        from app.services.settings_service import get_settings_service

        settings = get_settings_service()
        provider, model = settings.pet_selection() if slot == "emil" else settings.selection()
        return {"provider": provider or None, "model": model or None, "slot": slot}

    async def _model(self, system: str, data: dict, selection: dict, limit: int = 2200, timeout: float = 75) -> str:
        from app.services.llm import complete
        from app.core.kinderschutz import KINDER_ALTER, kinder_prompt

        if KINDER_ALTER.get():
            system += "\n" + kinder_prompt(KINDER_ALTER.get())

        if self.complete is None:
            from app.services.harness.modell import ERSTES_TOKEN_S, WARTEN, denken_entfernen, voruebergehend

            result = ""
            for versuch in range(len(WARTEN) + 1):
                try:
                    result = denken_entfernen(await asyncio.wait_for(complete(system, json.dumps(data, ensure_ascii=False), **selection, max_tokens=limit, temperature=0.2, first_token_timeout=ERSTES_TOKEN_S), max(timeout, ERSTES_TOKEN_S + 60)))
                    break
                except asyncio.CancelledError:
                    raise
                except Exception as fehler:
                    if versuch == len(WARTEN) or not voruebergehend(fehler):
                        raise
                    await asyncio.sleep(WARTEN[versuch])
        else:
            result = await asyncio.wait_for(self.complete(system, json.dumps(data, ensure_ascii=False), **selection, max_tokens=limit, temperature=0.2), timeout)
        if not isinstance(result, str) or not result.strip():
            raise ValueError("Das Modell hat keine Antwort geliefert.")
        return result.strip()

    async def _aufteilen(self, run: dict, selection: dict) -> list[dict]:
        allowed = run["roles"] or list(PROFILES)
        try:
            raw = await self._model(BOUNDARIES + '\nTeile den Auftrag in unabhängige Teilfragen. Antworte nur als JSON: {"teile":[{"titel":"...","auftrag":"...","rolle":"Profil-ID","werkzeug":"keins oder web_search"}]}. Verwende höchstens die gewünschte Anzahl. Für eine einfache Aufgabe genügt ein Fachagent. Soll ein mitgegebenes Material vollständig bearbeitet werden (alle Einträge herausschreiben, abschreiben, übersetzen, auflisten), nimm genau einen Fachagenten für das ganze Material. Jede Teilfrage muss zur ursprünglichen Aufgabe beitragen.', {"aufgabe": run["aufgabe"], "material_auszug": kuerzen(run.get("material", ""), 4000), "max_agenten": run["max_agenten"], "profile": {key: PROFILES[key]["name"] for key in allowed}, "internet_erlaubt": run["research"]}, selection, 1200, 60)
            parts = self._json(raw).get("teile")
            if not isinstance(parts, list):
                raise ValueError("Der Plan enthält keine Teilaufgaben.")
            result = []
            for part in parts[:run["max_agenten"]]:
                if not isinstance(part, dict) or not str(part.get("auftrag", "")).strip():
                    continue
                role = part.get("rolle") if part.get("rolle") in allowed else allowed[0]
                result.append({"titel": str(part.get("titel") or PROFILES[role]["name"])[:120], "auftrag": str(part["auftrag"])[:6000], "rolle": role, "rolle_name": PROFILES[role]["name"], "werkzeug": "web_search" if run["research"] and part.get("werkzeug") == "web_search" else "keins", "status": "queued"})
            if result:
                return result
        except Exception:
            run["hinweis"] = "Aufteilung nicht verfügbar; ein Fachagent bearbeitet die gesamte Aufgabe."
        return [{"titel": PROFILES[allowed[0]]["name"], "auftrag": run["aufgabe"], "rolle": allowed[0], "rolle_name": PROFILES[allowed[0]]["name"], "werkzeug": "keins", "status": "queued"}]

    async def _teil_ausfuehren(self, teil: dict, selection: dict | None = None, original: str = "", research: bool = False, material: str = "") -> Teilergebnis:
        from app.services.tool_result import succeeded
        from app.services.tools import ToolBox

        start = time.time()
        role = teil.get("rolle") if isinstance(teil.get("rolle"), str) and teil.get("rolle") in PROFILES else "general"
        title = str(teil.get("titel") or PROFILES[role]["name"])[:120]
        task = str(teil.get("auftrag") or title)[:10000]
        tool = "web_search" if research and teil.get("werkzeug") == "web_search" else "keins"
        try:
            sources = ""
            if tool == "web_search":
                sources = await asyncio.wait_for(ToolBox(source="agenten").execute(tool, {"query": task[:1500]}), 40)
                if not succeeded(sources):
                    raise ValueError("Die Recherche ist fehlgeschlagen: " + str(sources)[:500])
            answer = await self._model(BOUNDARIES + "\nFachprofil: " + PROFILES[role]["focus"] + "\n" + VOLLSTAENDIG, {"urspruenglicher_auftrag": original[:12000], "teilauftrag": task, "material": kuerzen(material, MATERIAL_ZEICHEN), "recherchematerial": str(sources)[:16000]}, selection or self._selection("jon"), TEIL_TOKENS, TEIL_TIMEOUT_S)
            return Teilergebnis(title, task, tool, answer, dauer=time.time()-start, rolle=role)
        except Exception as exc:
            return Teilergebnis(title, task, tool, fehler=str(exc) or type(exc).__name__, dauer=time.time()-start, rolle=role)

    def live(self) -> list[dict]:
        result = []
        for run in sorted(self.runs.values(), key=lambda r: r["created_at"], reverse=True):
            if run["status"] in TERMINAL and time.time() - run.get("updated_at", 0) > 8:
                continue
            result.append({"id": run["id"], "aufgabe": run["aufgabe"][:300], "source": run["source"], "status": run["status"], "created_at": run["created_at"], "updated_at": run.get("updated_at", 0), "teile": [{"titel": p.get("titel", ""), "rolle": p.get("rolle", "general"), "rolle_name": p.get("rolle_name", ""), "status": p.get("status", "queued")} for p in run.get("teile", [])]})
        return result[:6]

    def start(self, aufgabe: str, max_agenten: int = 3, source: str = "app", slot: str = "jon", research: bool = False, roles: list[str] | None = None, persist: bool = True, kinder: int | None = None, run_id: str | None = None, material: str = "") -> dict:
        from app.services.premium import get_premium

        get_premium().verbrauchen("fachteam")

        text = str(aufgabe).strip()
        if not text or len(text) > 12000:
            raise ValueError("Beschreibe eine Aufgabe mit höchstens 12.000 Zeichen.")
        if len(self.running) >= 2:
            raise ValueError("Zwei Fachteams arbeiten bereits. Warte auf ein Ergebnis oder stoppe einen Auftrag.")
        if any(key not in PROFILES for key in (roles or [])):
            raise ValueError("Unbekanntes Fachprofil.")
        while len(self.runs) >= 50:
            old = next((r for r in self.runs.values() if r["status"] in TERMINAL), None)
            if old is None:
                break
            self.delete(old["id"])
        key = run_id if isinstance(run_id, str) and re.fullmatch(r"[a-f0-9]{32}", run_id) and run_id not in self.runs else uuid.uuid4().hex
        run = {"id": key, "aufgabe": text, "material": kuerzen(str(material or ""), MATERIAL_ZEICHEN), "source": source, "slot": "emil" if slot == "emil" else "jon", "research": bool(research), "roles": list(dict.fromkeys(roles or [])), "max_agenten": max(1, min(int(max_agenten), MAX_AGENTEN)), "status": "planning", "teile": [], "antwort": "", "pruefung": None, "fehler": "", "hinweis": "", "ok": False, "vollstaendig": False, "persist": persist, "created_at": time.time(), "updated_at": time.time()}
        from app.core.kinderschutz import KINDER_ALTER

        run["kinder"] = kinder or KINDER_ALTER.get()
        self.runs[run["id"]] = run
        self._save(run)
        task = asyncio.create_task(self._run(run))
        self.running[run["id"]] = task
        task.add_done_callback(lambda _: self.running.pop(run["id"], None))
        return self.get(run["id"])

    async def _run(self, run: dict) -> None:
        from app.core.kinderschutz import KINDER_ALTER

        child_context = KINDER_ALTER.set(run.get("kinder"))
        try:
            async with asyncio.timeout(GESAMT_TIMEOUT_S):
                selection = self._selection(run["slot"])
                run.update(provider=selection["provider"], model=selection["model"])
                run["teile"] = await self._aufteilen(run, selection)
                run["status"] = "working"
                self._save(run)

                async def work(part):
                    part.update(status="working", begonnen=time.time())
                    self._save(run)
                    result = await self._teil_ausfuehren(part, selection, run["aufgabe"], run["research"], run.get("material", ""))
                    part.update(result.als_dict())
                    self._save(run)

                await asyncio.gather(*(work(part) for part in run["teile"]))
                successful = [p for p in run["teile"] if p["status"] == "done"]
                if not successful:
                    raise ValueError("Kein Fachagent konnte die Aufgabe abschließen. Prüfe Modell und Verbindung.")
                run.update(ok=True, status="verifying")
                self._save(run)
                try:
                    review = await self._model(BOUNDARIES + '\nPrüfe die Ergebnisse unabhängig am Originalauftrag. Kontrolliere Herleitungen, Widersprüche, fehlende Teilfragen und unbelegte Behauptungen. Antworte ausschließlich als JSON: {"ok":true oder false,"probleme":["konkreter Fehler oder offene Frage"],"korrektur":"begründete Korrektur oder leer"}. Eine fehlende oder fehlerhafte Teilantwort bedeutet ok=false. Lange Ergebnisse siehst du gekürzt; werte Kürzungen nicht als Fehler.', {"aufgabe": run["aufgabe"], "material_auszug": kuerzen(run.get("material", ""), 6000), "teile": [{**p, "ergebnis": kuerzen(str(p.get("ergebnis", "")), 6000)} for p in run["teile"]]}, selection, 1800, 180)
                    review = self._json(review)
                    if type(review.get("ok")) is not bool or not isinstance(review.get("probleme"), list) or not isinstance(review.get("korrektur"), str):
                        raise ValueError("Die Gegenprüfung lieferte kein gültiges Ergebnis.")
                    run["pruefung"] = {"ok": review["ok"] and not review["probleme"], "probleme": [str(x)[:1000] for x in review["probleme"][:12]], "korrektur": review["korrektur"][:6000]}
                except Exception as exc:
                    run["pruefung"] = {"ok": False, "probleme": ["Gegenprüfung nicht verfügbar: " + (str(exc) or type(exc).__name__)[:500]], "korrektur": ""}
                run["status"] = "summarizing"
                self._save(run)
                gesamt = sum(len(p["ergebnis"]) for p in successful)
                if len(successful) == 1 or gesamt > 14000:
                    run["antwort"] = successful[0]["ergebnis"] if len(successful) == 1 else "\n\n".join("## " + p["titel"] + "\n\n" + p["ergebnis"] for p in successful)
                    run["vollstaendig"] = len(successful) == len(run["teile"]) and run["pruefung"]["ok"]
                else:
                    try:
                        run["antwort"] = await self._model(BOUNDARIES + "\nFasse die Teilergebnisse zu einer konkreten, verständlichen Antwort auf die Originalfrage zusammen. " + VOLLSTAENDIG + " Beachte die Gegenprüfung, benenne ungelöste Widersprüche und fehlende Ergebnisse ausdrücklich. Keine erfundenen Quellen. Für MiniJon kurz und natürlich formulieren.", {"aufgabe": run["aufgabe"], "teile": run["teile"], "pruefung": run["pruefung"], "mini": run["slot"] == "emil"}, selection, TEIL_TOKENS, TEIL_TIMEOUT_S)
                        run["vollstaendig"] = len(successful) == len(run["teile"]) and run["pruefung"]["ok"]
                    except Exception as exc:
                        run["fehler"] = "Zusammenfassung nicht verfügbar: " + (str(exc) or type(exc).__name__)[:500]
                        run["antwort"] = "\n\n".join("## " + p["titel"] + "\n\n" + p["ergebnis"] for p in successful)
                run["status"] = "done" if run["vollstaendig"] else "needs_review"
        except asyncio.CancelledError:
            run.update(status="cancelled", vollstaendig=False, fehler="Gestoppt. Vorliegende Teilergebnisse bleiben erhalten.")
            raise
        except Exception as exc:
            run.update(status="needs_review" if run["ok"] else "failed", vollstaendig=False, fehler="Zeitlimit erreicht." if isinstance(exc, TimeoutError) else str(exc)[:1000])
        finally:
            KINDER_ALTER.reset(child_context)
            for part in run["teile"]:
                if part["status"] not in TERMINAL:
                    part.update(status="cancelled" if run["status"] == "cancelled" else "interrupted")
            run["dauer"] = round(time.time()-run["created_at"], 1)
            if run["status"] != "cancelled" or any(p.get("ergebnis") for p in run["teile"]):
                self._ablegen(run)
            self._save(run)

    async def cancel(self, run_id: str) -> dict:
        run = self.runs[run_id]
        task = self.running.get(run_id)
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            if run["status"] not in TERMINAL:
                run.update(status="cancelled", vollstaendig=False, fehler="Gestoppt.")
                self._save(run)
        return self.get(run_id)

    async def bearbeiten(self, aufgabe: str, max_agenten: int = MAX_AGENTEN, **kwargs) -> dict:
        run = self.start(aufgabe, max_agenten, **kwargs)
        try:
            await self.running[run["id"]]
            return self.get(run["id"])
        finally:
            if not run["persist"]:
                asyncio.get_running_loop().call_later(PRIVAT_HALTEN_S, self.runs.pop, run["id"], None)

    async def close(self) -> None:
        await asyncio.gather(*(self.cancel(key) for key in list(self.running)))


_service: AgentenService | None = None


def get_agenten_service() -> AgentenService:
    global _service
    if _service is None:
        _service = AgentenService()
    return _service
