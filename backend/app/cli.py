from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from app.core.config import get_settings
from app.providers.base import ChatMessage, ChatRequest, StreamChunk
from app.providers.registry import get_registry
from app.services.coding import CODING_PROMPT, workspace_summary
from app.services.memory_service import MemoryService
from app.services.settings_service import get_settings_service
from app.services.skill_service import SkillService
from app.services.tools import ToolBox
from app.services.usage_service import get_usage_service

GOLD = "\033[38;5;179m"
DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
RED = "\033[31m"
RESET = "\033[0m"

class JonCLI:
    def __init__(self) -> None:
        self.registry = get_registry()
        self.settings = get_settings()
        self.user_settings = get_settings_service()
        self.toolbox = ToolBox()
        self.memory = MemoryService()
        self.skills = SkillService()
        self.usage = get_usage_service()
        self.workspace = Path.cwd()
        self.messages: list[ChatMessage] = []
        self.auto_run = True
        self.provider_name = ""
        self.model = ""
        self._select_default_provider()

    def _available(self) -> list[str]:
        return self.registry.available()

    def _select_default_provider(self) -> None:
        available = self._available()
        preferred = self.settings.default_provider
        self.provider_name = preferred if preferred in available else (
            available[0] if available else preferred
        )
        self.model = self.settings.jon_model

    async def _resolve_model(self) -> None:
        provider = self.registry.get(self.provider_name)
        models = await provider.list_models()
        if self.model not in models and models:
            self.model = models[0]

    def _system_prompt(self) -> str:
        parts = [CODING_PROMPT, workspace_summary(self.workspace)]
        custom, mode = self.user_settings.custom_prompt()
        if custom.strip():
            parts.append(custom.strip())
        block = self.memory.prompt_block()
        if block:
            parts.append(block)
        catalog = self.skills.catalog()
        if catalog:
            parts.append(catalog)
        return "\n\n".join(parts)

    async def _run_turn(self, text: str) -> None:
        self.messages.append(ChatMessage(role="user", content=text))
        request_messages = [ChatMessage(role="system", content=self._system_prompt())]
        request_messages.extend(self.messages)
        request = ChatRequest(
            messages=request_messages,
            model=self.model,
            tools=self.toolbox.schema(),
        )
        try:
            provider = self.registry.get(self.provider_name)
        except Exception as exc:
            print(f"{RED}Fehler: {exc}{RESET}")
            return

        parts: list[str] = []
        printed_label = False
        try:
            async for chunk in provider.stream(request, self.toolbox.execute):
                if chunk.kind == "content":
                    if not printed_label:
                        sys.stdout.write(f"{GOLD}Jon{RESET} ")
                        printed_label = True
                    sys.stdout.write(chunk.delta)
                    sys.stdout.flush()
                    parts.append(chunk.delta)
                elif chunk.kind == "tool":
                    detail = _tool_line(chunk)
                    sys.stdout.write(f"\n{CYAN}⚙ {detail}{RESET}\n")
                    sys.stdout.flush()
                elif chunk.kind == "tool_result":
                    mark = "✓" if chunk.ok else "✕"
                    sys.stdout.write(f"{DIM}  {mark} {chunk.name}{RESET}\n")
                    sys.stdout.flush()
        except Exception as exc:
            print(f"\n{RED}Fehler: {exc}{RESET}")
            return
        answer = "".join(parts)
        if answer:
            self.messages.append(ChatMessage(role="assistant", content=answer))
        print()

    async def _cmd_model(self, arg: str) -> None:
        provider = self.registry.get(self.provider_name)
        models = await provider.list_models()
        if arg.isdigit() and 1 <= int(arg) <= len(models):
            self.model = models[int(arg) - 1]
            print(f"{GOLD}Modell: {self.model}{RESET}")
            return
        if arg and arg in models:
            self.model = arg
            print(f"{GOLD}Modell: {self.model}{RESET}")
            return
        print(f"{BOLD}Modelle von {self.provider_name}:{RESET}")
        for i, m in enumerate(models, 1):
            mark = "●" if m == self.model else " "
            print(f"  {mark} {i}. {m}")
        print(f"{DIM}Wechseln: /model <Nummer>{RESET}")

    async def _cmd_provider(self, arg: str) -> None:
        all_providers = list(self.registry.all().keys())
        available = self._available()
        if arg:
            if arg in all_providers:
                self.provider_name = arg
                await self._resolve_model()
                print(f"{GOLD}Provider: {arg} · Modell: {self.model}{RESET}")
            else:
                print(f"{RED}Unbekannter Provider: {arg}{RESET}")
            return
        print(f"{BOLD}Provider:{RESET}")
        for p in all_providers:
            ok = "✓" if p in available else "·"
            mark = "●" if p == self.provider_name else " "
            print(f"  {mark} {ok} {p}")
        print(f"{DIM}Wechseln: /provider <name>. ✓ = einsatzbereit{RESET}")

    def _cmd_usage(self) -> None:
        summary = self.usage.summary()
        if not summary:
            print(f"{DIM}Noch keine Nutzung erfasst.{RESET}")
            return
        for provider, u in summary.items():
            print(f"{BOLD}{provider}{RESET}")
            print(
                f"  Tokens: {u['total_tokens']} (Prompt {u['prompt_tokens']}, "
                f"Completion {u['completion_tokens']})"
            )
            print(
                f"  Anfragen: {u['requests']} · Ø {u['avg_latency']}s · "
                f"Modell {u['last_model']}"
            )

    def _cmd_tools(self) -> None:
        names = [t["function"]["name"] for t in self.toolbox.schema()]
        print(f"{BOLD}{len(names)} Tools:{RESET}")
        print("  " + ", ".join(names))

    def _cmd_memory(self) -> None:
        items = self.memory.list()
        if not items:
            print(f"{DIM}Kein Gedächtnis gespeichert.{RESET}")
            return
        for m in items:
            print(f"  • {m['content']}")

    def _cmd_plugins(self) -> None:
        skills = self.skills.list()
        print(f"{BOLD}Skills:{RESET}")
        for s in skills:
            print(f"  • {s['name']} — {s['title']}")

    def _cmd_settings(self, arg: str) -> None:
        if arg == "autorun":
            self.auto_run = not self.auto_run
        print(f"{BOLD}Einstellungen:{RESET}")
        print(f"  Provider: {self.provider_name}")
        print(f"  Modell: {self.model}")
        print(f"  Workspace: {self.workspace}")
        custom, mode = self.user_settings.custom_prompt()
        print(f"  Eigenes Prompt: {'ja (' + mode + ')' if custom.strip() else 'nein'}")

    def _cmd_status(self) -> None:
        print(f"{BOLD}Jon Coding-Agent{RESET}")
        print(f"  Provider: {self.provider_name}")
        print(f"  Modell: {self.model}")
        print(f"  Workspace: {self.workspace}")
        print(f"  Nachrichten: {len(self.messages)}")
        print(f"  Verfügbare Provider: {', '.join(self._available()) or '—'}")

    def _cmd_help(self) -> None:
        print(f"{BOLD}Befehle:{RESET}")
        rows = [
            ("/help", "diese Hilfe"),
            ("/clear", "Verlauf löschen"),
            ("/status", "Status anzeigen"),
            ("/usage", "Nutzung anzeigen"),
            ("/model [n]", "Modelle des Providers / wechseln"),
            ("/provider [name]", "Provider anzeigen / wechseln"),
            ("/agents", "Agenten-Modus erklären"),
            ("/tools", "verfügbare Tools"),
            ("/memory", "Langzeitgedächtnis"),
            ("/plugins", "Skills"),
            ("/settings", "Einstellungen"),
            ("/exit", "beenden"),
        ]
        for cmd, desc in rows:
            print(f"  {GOLD}{cmd:<18}{RESET} {desc}")

    def _cmd_agents(self) -> None:
        print(
            f"{BOLD}Agenten-Modus{RESET}\n"
            "  Jon plant und arbeitet selbstständig: Er analysiert Dateien, ändert Code,\n"
            "  startet Builds/Tests, erkennt Fehler und behebt sie, bis die Aufgabe fertig\n"
            "  ist. Beschreibe einfach dein Ziel — z.B. 'Behebe alle Type-Fehler und lass\n"
            "  die Tests grün werden.'"
        )

    async def _handle_command(self, line: str) -> bool:
        parts = line[1:].split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        arg = parts[1].strip() if len(parts) > 1 else ""
        if cmd in ("exit", "quit", "q"):
            return False
        if cmd == "help":
            self._cmd_help()
        elif cmd == "clear":
            self.messages.clear()
            print(f"{DIM}Verlauf gelöscht.{RESET}")
        elif cmd == "status":
            self._cmd_status()
        elif cmd == "usage":
            self._cmd_usage()
        elif cmd == "model":
            await self._cmd_model(arg)
        elif cmd == "provider":
            await self._cmd_provider(arg)
        elif cmd == "agents":
            self._cmd_agents()
        elif cmd == "tools":
            self._cmd_tools()
        elif cmd == "memory":
            self._cmd_memory()
        elif cmd == "plugins":
            self._cmd_plugins()
        elif cmd == "settings":
            self._cmd_settings(arg)
        else:
            print(f"{RED}Unbekannter Befehl: /{cmd}{RESET} — /help für Hilfe")
        return True

    async def run(self) -> None:
        print(f"{GOLD}{BOLD}Jon{RESET} Coding-Agent · {self.workspace.name}")
        if not self._available():
            print(
                f"{RED}Kein Provider einsatzbereit.{RESET} Setze einen API-Key in der "
                ".env oder starte Ollama lokal. /provider zeigt den Status."
            )
        await self._resolve_model()
        print(f"{DIM}Provider {self.provider_name} · Modell {self.model} · /help für Befehle{RESET}\n")
        while True:
            try:
                line = await asyncio.to_thread(input, f"{BOLD}› {RESET}")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            line = line.strip()
            if not line:
                continue
            if line.startswith("/"):
                keep = await self._handle_command(line)
                if not keep:
                    break
                continue
            await self._run_turn(line)
        print(f"{DIM}Tschüss.{RESET}")


def _tool_line(chunk: StreamChunk) -> str:
    from app.services.tools import describe_tool

    return describe_tool(chunk.name or "", chunk.args or {})


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if sys.platform == "win32":
        import os

        os.system("")
    try:
        asyncio.run(JonCLI().run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
