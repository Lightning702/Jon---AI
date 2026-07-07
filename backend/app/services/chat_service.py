from __future__ import annotations

import time
from typing import AsyncIterator

from app.core.config import get_settings
from app.db.database import session_scope
from app.db.models import Conversation, Message
from app.providers.base import ChatMessage, ChatRequest, StreamChunk
from app.providers.registry import get_registry
from app.schemas import ChatIn
from app.services.approval_service import ToolDeniedError, get_approval_service
from app.services.coding import CODING_PROMPT, workspace_summary
from app.services.memory_service import MemoryService
from app.services.persona_service import get_persona_service
from app.services.settings_service import get_settings_service
from app.services.skill_service import SkillService
from app.services.tools import SAFE_TOOLS, ToolBox, describe_tool
from app.services.usage_service import get_usage_service

SYSTEM_PROMPT = (
    "Du bist Jon, ein blitzschneller KI-Desktop-Assistent auf dem Windows-PC des Nutzers. "
    "Du kannst den Computer wirklich steuern: PowerShell und CMD ausfuehren, Programme "
    "starten und beenden, Dateien lesen, schreiben, verschieben und loeschen, URLs und "
    "VS Code oeffnen. Ausserdem steuerst du Maus und Tastatur direkt: mouse_move, "
    "mouse_click, mouse_scroll, keyboard_type, keyboard_press, keyboard_hotkey, "
    "focus_window, list_windows, get_screen_info und wait. Nutze die Tools, wenn eine "
    "Aktion oder aktuelle Systeminfo noetig ist, statt sie nur zu beschreiben. "
    "Regeln fuer Maus/Tastatur: Rufe zuerst get_screen_info auf. Koordinaten kannst du "
    "als Bruchteile 0-1 angeben (x=0.5, y=0.5 = Mitte). Nach dem Oeffnen einer App oder "
    "Seite immer wait (2-4 Sekunden) und bei Apps focus_window, bevor du klickst oder "
    "tippst. Bevorzuge Tastatur statt blindem Klicken, das ist zuverlaessiger. "
    "Beispiel YouTube-Suche und erstes Video oeffnen: open_url mit "
    "https://www.youtube.com/results?search_query=SUCHBEGRIFF (Leerzeichen als +), "
    "wait 4, dann liegt das erste Video ungefaehr bei x=0.25 y=0.35 - mouse_click dort. "
    "Falls ein Cookie-Banner erscheinen koennte, weise den Nutzer darauf hin. "
    "Beispiel WhatsApp-Nachricht an einen Kontakt: start_program mit whatsapp (oder "
    "run_powershell 'Start-Process shell:AppsFolder\\\\$(Get-StartApps | Where-Object "
    "{$_.Name -eq \\\"WhatsApp\\\"} | Select-Object -ExpandProperty AppID)'), wait 4, "
    "focus_window WhatsApp, keyboard_hotkey ctrl+f fuer die Suche, keyboard_type mit dem "
    "Kontaktnamen, wait 1, keyboard_press down dann enter um den Kontakt zu oeffnen, "
    "dann keyboard_type mit der Nachricht und press_enter=true zum Senden. "
    "Fuer Systeminfos wie Uhrzeit, Prozesse, Laufwerke oder Netzwerk verwende "
    "run_powershell oder system_info/list_processes. Du beherrschst auch: Dateien "
    "suchen (search_files), Ordner anlegen (make_dir), kopieren (copy_path), ZIP "
    "packen/entpacken (zip_paths/unzip), Zwischenablage lesen/schreiben (clipboard_get/"
    "clipboard_set), Screenshots (screenshot), Webseiten/APIs abrufen (http_get), "
    "Dateien herunterladen (download_file) und den Bildschirm sperren (lock_screen). "
    "Du hast Skills (Anleitungen): Rufe list_skills und read_skill auf, bevor du eine "
    "passende Aufgabe startest (z.B. read_skill web-design, bevor du eine Website baust), "
    "und folge der Anleitung. Mit write_skill kannst du dir neue Arbeitsweisen merken. "
    "Du hast ein dauerhaftes Gedaechtnis: Mit remember speicherst du "
    "wichtige Infos ueber den Nutzer (Name, Kontakte, Vorlieben, wiederkehrende "
    "Aufgaben), mit recall rufst du sie ab, mit forget loeschst du sie. Merke dir "
    "automatisch Merkenswertes, ohne dass der Nutzer explizit darum bittet. "
    "Wecker und Timer: Nutze set_alarm fuer 'Stelle einen Wecker fuer 07:00' "
    "(time='07:00') oder 'Timer 10 Minuten' (in_minutes=10). Das ist ein echter "
    "Windows-Wecker mit Klingelton und Popup, er funktioniert auch, wenn Jon "
    "geschlossen ist. Mit list_alarms und delete_alarm verwaltest du Wecker. "
    "set_reminder ist nur fuer wiederkehrende Erinnerungen in der App. "
    "Windows-Einstellungen oeffnest du mit open_url und ms-settings: "
    "(z.B. ms-settings:display, ms-settings:sound, ms-settings:bluetooth). "
    "Fuer aktuelle Infos aus dem Internet (News, Preise, Fakten, "
    "Oeffnungszeiten) nutze web_search und oeffne bei Bedarf einen Treffer mit "
    "http_get. Wetter und Vorhersage holst du mit get_weather (Stadt noetig - "
    "merke dir die Stadt des Nutzers mit remember_about_user, wenn er sie nennt). "
    "PDF-Dateien liest und analysierst du mit read_pdf. "
    "Du hast ein eigenes, persoenliches Gedaechtnis (MEMORY.md): mit journal "
    "schreibst du Gedanken und Erlebnisse hinein, mit read_journal liest du sie, "
    "mit remember_about_user haeltst du feste Fakten ueber den Nutzer fest. "
    "Deine Stimmung aenderst du mit set_mood. Wichtige Projektstaende oder "
    "Entscheidungen sicherst du mit snapshot (Zeitreise), zurueck geht es mit "
    "list_snapshots und restore_snapshot. "
    "SEHR WICHTIG: Der Gespraechsverlauf enthaelt bereits erledigte Aktionen. "
    "Fuehre Tools ausschliesslich dann aus, wenn die LETZTE Nachricht des Nutzers "
    "eine neue Aktion verlangt. Wiederhole niemals eine Aktion aus einer frueheren "
    "Nachricht. Auf Danke, Lob, Bestaetigungen oder Rueckfragen antwortest du nur "
    "mit Text und rufst keine Tools auf. Antworte knapp, praezise und auf Deutsch."
)

TOOL_PROVIDERS = {
    "nvidia",
    "openai",
    "deepseek",
    "mistral",
    "glm",
    "qwen",
    "ollama",
    "lmstudio",
    "openrouter",
    "groq",
    "together",
    "xai",
}


class ChatService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._registry = get_registry()
        self._memory = MemoryService()
        self._skills = SkillService()
        self._toolbox = ToolBox(memory=self._memory, skills=self._skills)
        self._usage = get_usage_service()

    def _system_prompt(
        self,
        coding: bool = False,
        workspace: str | None = None,
        persona: str = "papa",
    ) -> str:
        if coding:
            from pathlib import Path

            base = CODING_PROMPT
            parts = [base]
            if workspace:
                parts.append(workspace_summary(Path(workspace)))
        else:
            settings_service = get_settings_service()
            custom, mode = settings_service.custom_prompt()
            if custom.strip() and mode == "replace":
                base = custom.strip()
            elif custom.strip():
                base = f"{SYSTEM_PROMPT}\n\n{custom.strip()}"
            else:
                base = SYSTEM_PROMPT
            if settings_service.personality():
                parts = [
                    get_persona_service().persona_block(variant=persona),
                    base,
                ]
            else:
                parts = [base]
        catalog = self._skills.catalog()
        if catalog:
            parts.append(catalog)
        block = self._memory.prompt_block()
        if block:
            parts.append(block)
        return "\n\n".join(parts)

    def resolve(self, payload: ChatIn) -> tuple[str, str]:
        saved_provider, saved_model = get_settings_service().selection()
        provider = payload.provider or saved_provider or self._settings.default_provider
        model = payload.model or saved_model or self._settings.default_model
        return provider, model

    def _ensure_conversation(self, payload: ChatIn, provider: str, model: str) -> str:
        with session_scope() as session:
            conv: Conversation | None = None
            if payload.conversation_id:
                conv = session.get(Conversation, payload.conversation_id)
            if conv is None:
                first_user = next(
                    (m.content for m in payload.messages if m.role == "user"), ""
                )
                title = (first_user.strip()[:60] or "Neue Unterhaltung")
                conv = Conversation(title=title, provider=provider, model=model)
                session.add(conv)
                session.flush()
            conv.provider = provider
            conv.model = model
            count = len(conv.messages)
            for idx, m in enumerate(payload.messages):
                exists = any(
                    em.role == m.role and em.content == m.content
                    for em in conv.messages
                )
                if not exists:
                    session.add(
                        Message(
                            conversation_id=conv.id,
                            role=m.role,
                            content=m.content,
                            position=count + idx,
                        )
                    )
            return conv.id

    def _store_answer(
        self, conversation_id: str, content: str, reasoning: str | None
    ) -> None:
        with session_scope() as session:
            conv = session.get(Conversation, conversation_id)
            if conv is None:
                return
            position = len(conv.messages)
            session.add(
                Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=content,
                    reasoning=reasoning or None,
                    position=position,
                )
            )

    async def stream(self, payload: ChatIn) -> AsyncIterator[dict]:
        provider_name, model = self.resolve(payload)
        provider = self._registry.get(provider_name)

        if payload.mode != "coding" and get_settings_service().personality():
            get_persona_service().touch()

        conversation_id = payload.conversation_id
        if payload.persist:
            conversation_id = self._ensure_conversation(payload, provider_name, model)

        yield {
            "type": "meta",
            "provider": provider_name,
            "model": model,
            "conversation_id": conversation_id,
        }

        request_messages = [
            ChatMessage(role=m.role, content=m.content) for m in payload.messages
        ]
        if not any(m.role == "system" for m in request_messages):
            request_messages.insert(
                0,
                ChatMessage(
                    role="system",
                    content=self._system_prompt(
                        coding=payload.mode == "coding",
                        workspace=payload.workspace,
                        persona=payload.persona,
                    ),
                ),
            )

        use_tools = provider_name in TOOL_PROVIDERS
        request = ChatRequest(
            messages=request_messages,
            model=model,
            temperature=payload.temperature,
            top_p=payload.top_p,
            max_tokens=payload.max_tokens,
            seed=payload.seed,
            tools=self._toolbox.schema() if use_tools else [],
        )

        ask_mode = payload.tool_mode != "allow"
        approvals = get_approval_service()
        pending_approvals: list[str] = []

        def needs_approval(name: str | None) -> bool:
            return ask_mode and name not in SAFE_TOOLS

        async def gated_executor(name: str, args: dict) -> str:
            if needs_approval(name):
                approval_id = (
                    pending_approvals.pop(0) if pending_approvals else None
                )
                approved = (
                    await approvals.wait(approval_id) if approval_id else False
                )
                if not approved:
                    raise ToolDeniedError(
                        "Der Nutzer hat die Ausführung dieses Tools abgelehnt."
                    )
            return await self._toolbox.execute(name, args)

        executor = gated_executor if use_tools else None

        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        tools_used: list[str] = []
        prompt_tokens = 0
        completion_tokens = 0
        started = time.perf_counter()
        try:
            chunk: StreamChunk
            async for chunk in provider.stream(request, executor):
                if chunk.kind == "usage":
                    prompt_tokens += chunk.prompt_tokens
                    completion_tokens += chunk.completion_tokens
                    continue
                if chunk.kind == "reasoning":
                    reasoning_parts.append(chunk.delta)
                    yield {"type": "reasoning", "delta": chunk.delta}
                elif chunk.kind == "tool":
                    event = {
                        "type": "tool",
                        "name": chunk.name,
                        "status": "running",
                        "args": chunk.args or {},
                        "summary": describe_tool(chunk.name or "", chunk.args or {}),
                    }
                    if needs_approval(chunk.name):
                        approval_id = approvals.create()
                        pending_approvals.append(approval_id)
                        event["approval_id"] = approval_id
                    yield event
                elif chunk.kind == "tool_result":
                    if chunk.ok and chunk.name:
                        tools_used.append(chunk.name)
                    yield {
                        "type": "tool",
                        "name": chunk.name,
                        "status": "done",
                        "ok": chunk.ok,
                    }
                else:
                    content_parts.append(chunk.delta)
                    yield {"type": "content", "delta": chunk.delta}
        except Exception as exc:
            yield {"type": "error", "message": str(exc)}
            return

        content = "".join(content_parts)
        if not content.strip() and tools_used:
            content = "Erledigt ✅ (" + ", ".join(dict.fromkeys(tools_used)) + ")"
            yield {"type": "content", "delta": content}
        reasoning = "".join(reasoning_parts)
        if payload.persist and conversation_id and content:
            self._store_answer(conversation_id, content, reasoning)

        if content or prompt_tokens or completion_tokens:
            self._usage.record(
                provider_name,
                model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency=time.perf_counter() - started,
            )

        yield {"type": "done", "conversation_id": conversation_id}
