from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from app.cli import kunst
from app.cli.kunst import (
    BLAU,
    FETT,
    GRAU,
    GRUEN,
    HELL,
    MATT,
    ROT,
    TIEF,
    TUERKIS,
    Stift,
)
from app.core.config import get_settings
from app.core.fehler import leise
from app.providers.base import ChatMessage, ChatRequest, StreamChunk
from app.providers.registry import get_registry
from app.services.chat_service import mark_fast, mark_slow
from app.services.coding import (
    CODING_PROMPT,
    DESIGN_PROMPT,
    mentioned_files_context,
    workspace_summary,
)
from app.services.memory_service import MemoryService
from app.services.settings_service import get_settings_service
from app.services.skill_service import SkillService
from app.services.tools import ToolBox
from app.services.usage_service import get_usage_service

UEBERSPRINGEN = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
}


VSCODE_MARKEN = (
    "VSCODE_PID",
    "VSCODE_CWD",
    "VSCODE_NONCE",
    "VSCODE_INJECTION",
    "VSCODE_IPC_HOOK_CLI",
    "VSCODE_GIT_IPC_HANDLE",
    "VSCODE_GIT_ASKPASS_NODE",
    "VSCODE_GIT_ASKPASS_MAIN",
    "VSCODE_SHELL_INTEGRATION",
)

EDITOREN = {
    "vscode": "VS Code",
    "vscode-insiders": "VS Code Insiders",
    "cursor": "Cursor",
    "windsurf": "Windsurf",
}

PROJEKTMARKEN = (
    ".git",
    ".vscode",
    "package.json",
    "pyproject.toml",
    "setup.py",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "CMakeLists.txt",
    "Makefile",
    "composer.json",
    "pubspec.yaml",
    "tsconfig.json",
    "index.html",
    "src",
)

CODE_ENDUNGEN = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".vue",
    ".svelte",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".java",
    ".kt",
    ".cs",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".rs",
    ".go",
    ".php",
    ".rb",
    ".swift",
    ".dart",
    ".lua",
    ".sh",
    ".ps1",
    ".sql",
}


def editor_name() -> str:
    programm = os.environ.get("TERM_PROGRAM", "").lower()
    if programm in EDITOREN:
        return EDITOREN[programm]
    if any(os.environ.get(marke) for marke in VSCODE_MARKEN):
        return "VS Code"
    if "vscode" in os.environ.get("GIT_ASKPASS", "").lower():
        return "VS Code"
    if os.environ.get("TERMINAL_EMULATOR", "").startswith("JetBrains"):
        return "JetBrains"
    return ""


def in_vscode() -> bool:
    return bool(editor_name())


def ist_projekt(ordner: Path) -> bool:
    if any((ordner / marke).exists() for marke in PROJEKTMARKEN):
        return True
    try:
        for eintrag in ordner.iterdir():
            if eintrag.is_file() and eintrag.suffix.lower() in CODE_ENDUNGEN:
                return True
    except OSError:
        return False
    return False


def git_zweig(ordner: Path) -> str:
    try:
        zeile = (ordner / ".git" / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if zeile.startswith("ref:"):
        return zeile.split("/")[-1]
    return zeile[:7]


def projekttyp(ordner: Path) -> str:
    from app.services.coding import PROJECT_MARKERS

    arten: list[str] = []
    for name, art in PROJECT_MARKERS.items():
        if (ordner / name).exists() and art not in arten:
            arten.append(art)
    return ", ".join(arten)


def mengentext(dateien: int, ordner: int) -> str:
    erste = "Datei" if dateien == 1 else "Dateien"
    zweite = "Verzeichnis" if ordner == 1 else "Verzeichnisse"
    return f"{dateien} {erste}, {ordner} {zweite}"


def baum(wurzel: Path, tiefe: int = 1) -> tuple[list[str], int, int]:
    dateien = 0
    ordner = 0
    zeilen: list[str] = []

    def gehen(pfad: Path, vorsatz: str, stufe: int) -> None:
        nonlocal dateien, ordner
        try:
            eintraege = sorted(
                pfad.iterdir(), key=lambda e: (e.is_file(), e.name.lower())
            )
        except OSError:
            return
        sichtbar = [
            e for e in eintraege if not e.name.startswith(".") or e.name == ".github"
        ]
        sichtbar = [e for e in sichtbar if e.name not in UEBERSPRINGEN]
        for i, eintrag in enumerate(sichtbar):
            letzte = i == len(sichtbar) - 1
            zweig = "└── " if letzte else "├── "
            if eintrag.is_dir():
                ordner += 1
                if stufe <= tiefe:
                    zeilen.append(f"{vorsatz}{zweig}{eintrag.name}/")
                    gehen(eintrag, vorsatz + ("    " if letzte else "│   "), stufe + 1)
                else:
                    gehen(eintrag, vorsatz, stufe + 1)
            else:
                dateien += 1
                if stufe <= tiefe:
                    zeilen.append(f"{vorsatz}{zweig}{eintrag.name}")

    gehen(wurzel, "", 1)
    return zeilen, dateien, ordner


class JonTerminal:
    def __init__(self, modus: str = "") -> None:
        self.stift = Stift()
        self.registry = get_registry()
        self.settings = get_settings()
        self.nutzer = get_settings_service()
        self.memory = MemoryService()
        self.skills = SkillService()
        self.toolbox = ToolBox(
            memory=self.memory, skills=self.skills, source="terminal"
        )
        self.usage = get_usage_service()
        self.ordner = Path.cwd()
        self.verlauf: list[ChatMessage] = []
        self.editor = editor_name()
        self.modus = modus or (
            "code" if self.editor or ist_projekt(self.ordner) else "chat"
        )
        self.codebox: ToolBox | None = None
        self.analysiert = False
        self.auftrag = ""
        self.anbieter = ""
        self.modell = ""
        self._anbieter_waehlen()

    def sag(self, text: str = "") -> None:
        print(text)

    def _box(self) -> ToolBox:
        if self.modus != "code":
            return self.toolbox
        if self.codebox is None:
            self.codebox = ToolBox(
                memory=self.memory,
                skills=self.skills,
                root=str(self.ordner),
                source="terminal",
            )
        return self.codebox

    def _verfuegbar(self) -> list[str]:
        return self.registry.available()

    def _anbieter_waehlen(self) -> None:
        frei = self._verfuegbar()
        gemerkt, modell = self.nutzer.terminal_selection()
        if not gemerkt:
            gemerkt, modell = self.nutzer.selection()
        gewuenscht = gemerkt or self.settings.default_provider
        self.anbieter = gewuenscht if gewuenscht in frei else (frei[0] if frei else gewuenscht)
        self.modell = modell if gemerkt and self.anbieter == gemerkt else ""
        if not self.modell:
            self.modell = self.settings.jon_model

    async def _wege(self) -> list[tuple[str, str]]:
        from app.services.chat_service import attempt_plan_for, route_providers

        namen = await route_providers(self.registry, self.anbieter, self.modell)
        return await attempt_plan_for(self.registry, self.anbieter, namen, self.modell)

    def _merken(self) -> None:
        try:
            self.nutzer.remember_terminal(self.anbieter, self.modell)
        except Exception as fehler:
            leise(fehler, "cli")

    async def _modell_pruefen(self) -> None:
        try:
            modelle = await self.registry.get(self.anbieter).list_models()
        except Exception as fehler:
            leise(fehler, "cli")
            return
        if modelle and self.modell not in modelle:
            self.modell = modelle[0]
            self._merken()

    def _prompt_text(self, text: str = "") -> str:
        from app.services.chat_service import heute_block

        if self.modus == "code":
            teile = [
                CODING_PROMPT,
                DESIGN_PROMPT,
                workspace_summary(self.ordner),
                heute_block(),
            ]
            try:
                from app.services.project_service import context_block

                projekt = context_block(str(self.ordner))
                if projekt:
                    teile.append(projekt)
            except Exception as fehler:
                leise(fehler, "cli")
            genannt = mentioned_files_context(str(self.ordner), text)
            if genannt:
                teile.append(genannt)
        else:
            from app.services.systemprompt import bauen

            teile = [bauen(), heute_block(), f"AKTUELLER ORDNER: {self.ordner}"]
        eigen, _art = self.nutzer.custom_prompt()
        if eigen.strip():
            teile.append(eigen.strip())
        block = self.memory.prompt_block()
        if block:
            teile.append(block)
        katalog = self.skills.catalog()
        if katalog:
            teile.append(katalog)
        teile.append(
            "Du laeufst gerade im Terminal. Antworte knapp und ohne Markdown-Tabellen, "
            "Ueberschriften und Sternchen - reiner Text mit kurzen Absaetzen."
        )
        from app.services.systemprompt import mit_herkunft

        return mit_herkunft("\n\n".join(teile))

    async def _runde(self, text: str) -> None:
        from app.services.tools import runde_beginnen

        runde_beginnen()
        self.verlauf.append(ChatMessage(role="user", content=text))
        nachrichten = [ChatMessage(role="system", content=self._prompt_text(text))]
        nachrichten.extend(self.verlauf)
        box = self._box()
        anfrage = ChatRequest(
            messages=nachrichten,
            model=self.modell,
            tools=box.schema(text, coding=self.modus == "code"),
        )
        teile: list[str] = []
        try:
            versuche = await self._wege()
        except Exception as fehler:
            self.sag(self.stift(f"Fehler: {fehler}", ROT))
            return
        gelaufen = False
        for stelle, (name, modell) in enumerate(versuche):
            anfrage.model = modell
            begonnen = False
            gezeigt = False
            beschriftet = False
            try:
                anbieter = self.registry.get(name)
            except Exception as fehler:
                leise(fehler, "cli")
                continue
            gelaufen = True
            try:
                async for stueck in anbieter.stream(anfrage, box.execute):
                    if not begonnen:
                        begonnen = True
                        mark_fast(name, modell)
                    if stueck.kind == "content":
                        gezeigt = True
                        if not beschriftet:
                            sys.stdout.write(self.stift("Jon  ", TUERKIS, FETT))
                            beschriftet = True
                        sys.stdout.write(stueck.delta)
                        sys.stdout.flush()
                        teile.append(stueck.delta)
                    elif stueck.kind == "tool":
                        if beschriftet:
                            sys.stdout.write("\n")
                            beschriftet = False
                        sys.stdout.write(
                            self.stift(f"  ⚙ {_werkzeugtext(stueck)}\n", BLAU)
                        )
                        sys.stdout.flush()
                    elif stueck.kind == "tool_result":
                        marke = "✓" if stueck.ok else "✕"
                        ton = GRUEN if stueck.ok else ROT
                        sauber = _sauberer_name(stueck.name or "")
                        sys.stdout.write(self.stift(f"  {marke} {sauber}\n", ton))
                        sys.stdout.flush()
                break
            except Exception as fehler:
                mark_slow(name, modell)
                if gezeigt:
                    self.sag("\n" + self.stift(f"Fehler: {fehler}", ROT))
                    return
                if stelle + 1 >= len(versuche):
                    self.sag(self.stift(f"Fehler: {fehler}", ROT))
                    return
                naechster, naechstes = versuche[stelle + 1]
                ueber = f" über {naechster}" if naechster != name else ""
                self.sag(
                    self.stift(
                        f"⚡ {modell} antwortet gerade nicht — ich nehme "
                        f"{naechstes}{ueber}.",
                        GRAU,
                    )
                )
        if not gelaufen:
            self.sag(
                self.stift(
                    f"Fehler: Der Anbieter {self.anbieter} ist nicht einsatzbereit — "
                    "„anbieter\" zeigt, was geht.",
                    ROT,
                )
            )
            return
        antwort = "".join(teile)
        if antwort:
            self.verlauf.append(ChatMessage(role="assistant", content=antwort))
        self.sag()

    def _codestart(self) -> None:
        if self.analysiert:
            self.sag(
                self.stift("Code-Modus läuft schon in ", TUERKIS)
                + self.stift(str(self.ordner), HELL)
            )
            self.sag(
                self.stift("Sag einfach, was ich bauen oder ändern soll.", MATT)
            )
            self.sag()
            return
        self.analysiert = True
        self.sag(self.stift("Jon Code-Modus aktiviert!", TUERKIS, FETT))
        vorwort = (
            f"{self.editor} erkannt — ich arbeite in "
            if self.editor
            else "Ich arbeite in "
        )
        self.sag(self.stift(vorwort, MATT) + self.stift(str(self.ordner), HELL))
        self.sag(self.stift("Ich analysiere dein Projekt ...", MATT))
        _zeilen, dateien, ordner = baum(self.ordner, 1)
        zweig = git_zweig(self.ordner)
        typ = projekttyp(self.ordner)
        geladen = f"Repository geladen (Zweig {zweig})" if zweig else "Ordner geladen"
        struktur = f"Code-Struktur analysiert ({mengentext(dateien, ordner)})"
        if typ:
            struktur += f" · {typ}"
        elif not dateien:
            struktur += " · noch leer, ich lege alles neu an"
        for satz in (geladen, struktur, "Bereit für deine Aufgabe"):
            self.sag(self.stift(" ✓ ", GRUEN) + self.stift(satz, HELL))
        self.sag(
            self.stift(
                "Sag einfach, was ich bauen oder ändern soll — ich schreibe direkt "
                "in die Dateien.",
                HELL,
            )
        )
        self.sag(self.stift("  „chat\" wechselt zurück ins normale Gespräch.", MATT))
        self.sag()

    def _projekte(self) -> None:
        self.sag(self.stift("Jon scannt das Projekt ...", MATT))
        zeilen, dateien, ordner = baum(self.ordner, 2)
        self.sag(self.stift(f"{self.ordner.name}/", TUERKIS, FETT))
        for zeile in zeilen[:60]:
            self.sag(self.stift(zeile, HELL))
        if len(zeilen) > 60:
            self.sag(self.stift(f"… {len(zeilen) - 60} weitere Einträge", MATT))
        self.sag(self.stift(mengentext(dateien, ordner), GRAU))
        self.sag()

    def _werkzeuge(self) -> None:
        coding = self.modus == "code"
        namen = sorted(
            t["function"]["name"] for t in self._box().schema(coding=coding)
        )
        titel = f"{len(namen)} Tools" + (" im Code-Modus" if coding else "")
        self.sag(self.stift(titel, TUERKIS, FETT))
        zeile = ""
        for name in namen:
            if len(zeile) + len(name) > kunst.breite() - 6:
                self.sag(self.stift("  " + zeile, HELL))
                zeile = ""
            zeile += name + "  "
        if zeile:
            self.sag(self.stift("  " + zeile, HELL))
        self.sag()

    def _gedaechtnis(self) -> None:
        eintraege = self.memory.list()
        if not eintraege:
            self.sag(self.stift("Noch nichts gemerkt.", MATT))
            self.sag()
            return
        self.sag(self.stift("Erinnerungen", TUERKIS, FETT))
        for eintrag in eintraege[:40]:
            self.sag(self.stift("  • ", BLAU) + self.stift(eintrag["content"], HELL))
        self.sag()

    def _einstellungen(self) -> None:
        zeilen = [
            ("Anbieter", self.anbieter),
            ("Modell", self.modell),
            ("Modus", "Code" if self.modus == "code" else "Chat"),
            ("Editor", self.editor or "keiner erkannt"),
            ("Ordner", str(self.ordner)),
            ("Bereit", ", ".join(self._verfuegbar()) or "keiner"),
        ]
        self.sag(self.stift("Einstellungen", TUERKIS, FETT))
        for name, wert in zeilen:
            self.sag(self.stift(f"  {name:<10}", GRAU) + self.stift(str(wert), HELL))
        self.sag()

    async def _modell_befehl(self, rest: str) -> None:
        modelle = await self.registry.get(self.anbieter).list_models()
        if rest.isdigit() and 1 <= int(rest) <= len(modelle):
            self.modell = modelle[int(rest) - 1]
            self._merken()
            self.sag(self.stift(f"Modell gemerkt: {self.modell}", TUERKIS))
            self.sag()
            return
        if rest and rest in modelle:
            self.modell = rest
            self._merken()
            self.sag(self.stift(f"Modell gemerkt: {self.modell}", TUERKIS))
            self.sag()
            return
        self.sag(self.stift(f"Modelle von {self.anbieter}", TUERKIS, FETT))
        for i, modell in enumerate(modelle, 1):
            marke = "●" if modell == self.modell else " "
            self.sag(self.stift(f"  {marke} {i}. {modell}", HELL))
        self.sag(self.stift("  Wechseln: modell <Nummer>", MATT))
        self.sag()

    async def _anbieter_befehl(self, rest: str) -> None:
        alle = list(self.registry.all().keys())
        frei = self._verfuegbar()
        if rest:
            if rest in alle:
                self.anbieter = rest
                self.modell = ""
                await self._modell_pruefen()
                self._merken()
                self.sag(
                    self.stift(
                        f"Anbieter gemerkt: {rest} · Modell: {self.modell}", TUERKIS
                    )
                )
            else:
                self.sag(self.stift(f"Unbekannter Anbieter: {rest}", ROT))
            self.sag()
            return
        self.sag(self.stift("Anbieter", TUERKIS, FETT))
        for name in alle:
            bereit = "✓" if name in frei else "·"
            marke = "●" if name == self.anbieter else " "
            self.sag(self.stift(f"  {marke} {bereit} {name}", HELL))
        self.sag(self.stift("  Wechseln: anbieter <name>", MATT))
        self.sag()

    async def _befehl(self, zeile: str) -> bool:
        roh = zeile.lstrip("/").strip()
        teile = roh.split(maxsplit=1)
        wort = teile[0].lower() if teile else ""
        rest = teile[1].strip() if len(teile) > 1 else ""
        if wort in ("ende", "exit", "quit", "beenden", "tschüss", "q"):
            return False
        if wort in ("hilfe", "help", "?"):
            self.sag(kunst.hilfe(self.stift, kunst.breite() < 152))
            self.sag()
        elif wort in ("neu", "clear", "reset"):
            self.verlauf.clear()
            self.sag(self.stift("Verlauf gelöscht.", MATT))
            self.sag()
        elif wort == "code":
            self.modus = "code"
            self._codestart()
            self.auftrag = rest
        elif wort == "chat":
            self.modus = "chat"
            self.sag(self.stift("Chat-Modus. Frag mich einfach.", TUERKIS))
            self.sag()
            self.auftrag = rest
        elif wort in ("projekte", "projekt"):
            self._projekte()
        elif wort in ("tools", "werkzeuge"):
            self._werkzeuge()
        elif wort in ("memory", "gedächtnis", "gedaechtnis"):
            self._gedaechtnis()
        elif wort in ("einstellungen", "settings", "status"):
            self._einstellungen()
        elif wort in ("modell", "model"):
            await self._modell_befehl(rest)
        elif wort in ("anbieter", "provider"):
            await self._anbieter_befehl(rest)
        elif wort == "agent":
            self.sag(
                self.stift("Agenten-Modus", TUERKIS, FETT)
                + self.stift(
                    "\n  Beschreib einfach dein Ziel — Jon plant, ändert Dateien, "
                    "startet Builds\n  und Tests und arbeitet, bis es fertig ist.",
                    HELL,
                )
            )
            self.sag()
        else:
            return True
        return True

    def _ist_befehl(self, zeile: str) -> bool:
        roh = zeile.lstrip("/").strip()
        if not roh:
            return False
        teile = roh.split()
        wort = teile[0].lower()
        if wort not in _BEFEHLE:
            return False
        if len(teile) == 1 or zeile.startswith("/"):
            return True
        return wort in _MIT_WERT and len(teile) == 2

    def _zeichen(self) -> str:
        marke = "Du (code)> " if self.modus == "code" else "Du> "
        return self.stift(marke, TUERKIS, FETT)

    async def laufen(self) -> None:
        name = os.environ.get("USERNAME") or os.environ.get("USER") or "du"
        self.sag()
        self.sag(kunst.kopf(self.stift, self.settings.app_version, name, kunst.breite() < 108))
        self.sag()
        if not self._verfuegbar():
            self.sag(
                self.stift(
                    "Kein Anbieter einsatzbereit — trag einen Schlüssel in die .env ein "
                    "oder starte Ollama. „anbieter\" zeigt den Stand.",
                    ROT,
                )
            )
            self.sag()
        await self._modell_pruefen()
        self.sag(
            self.stift(
                f"{self.anbieter} · {self.modell} · „hilfe\" für alles Weitere", MATT
            )
        )
        try:
            versuche = await self._wege()
        except Exception as fehler:
            leise(fehler, "cli")
            versuche = []
        if versuche and versuche[0] != (self.anbieter, self.modell):
            name, modell = versuche[0]
            ueber = f" über {name}" if name != self.anbieter else ""
            self.sag(
                self.stift(
                    f"⚡ {self.modell} war zuletzt überlastet — ich starte mit "
                    f"{modell}{ueber}. Deine Wahl bleibt gespeichert.",
                    GRAU,
                )
            )
        self.sag()
        if self.modus == "code":
            self._codestart()
        while True:
            try:
                zeile = await asyncio.to_thread(input, self._zeichen())
            except (EOFError, KeyboardInterrupt):
                self.sag()
                break
            zeile = zeile.strip()
            if not zeile:
                continue
            if self._ist_befehl(zeile):
                self.auftrag = ""
                if not await self._befehl(zeile):
                    break
                zeile, self.auftrag = self.auftrag, ""
                if not zeile:
                    continue
            await self._runde(zeile)
        self.sag(kunst.fuss(self.stift))


_MIT_WERT = {"modell", "model", "anbieter", "provider"}

_BEFEHLE = {
    "hilfe",
    "help",
    "?",
    "neu",
    "clear",
    "reset",
    "code",
    "chat",
    "projekte",
    "projekt",
    "tools",
    "werkzeuge",
    "memory",
    "gedächtnis",
    "gedaechtnis",
    "einstellungen",
    "settings",
    "status",
    "modell",
    "model",
    "anbieter",
    "provider",
    "agent",
    "ende",
    "exit",
    "quit",
    "beenden",
    "q",
}


def _sauberer_name(name: str) -> str:
    from app.services.tools import _name_saeubern

    return _name_saeubern(name)


def _werkzeugtext(stueck: StreamChunk) -> str:
    from app.services.tools import describe_tool

    return describe_tool(_sauberer_name(stueck.name or ""), stueck.args or {})
