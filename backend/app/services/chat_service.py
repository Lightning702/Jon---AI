from __future__ import annotations

from typing import AsyncIterator

from app.core.config import get_settings
from app.db.database import session_scope
from app.db.models import Conversation, Message
from app.providers.base import ChatMessage, ChatRequest, StreamChunk
from app.providers.registry import get_registry
from app.schemas import ChatIn
from app.services.approval_service import ToolDeniedError, get_approval_service
from app.services.memory_service import MemoryService
from app.services.tools import SAFE_TOOLS, ToolBox, describe_tool

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
    "run_powershell. Du hast ein dauerhaftes Gedaechtnis: Mit remember speicherst du "
    "wichtige Infos ueber den Nutzer (Name, Kontakte, Vorlieben, wiederkehrende "
    "Aufgaben), mit recall rufst du sie ab, mit forget loeschst du sie. Merke dir "
    "automatisch Merkenswertes, ohne dass der Nutzer explizit darum bittet. Antworte "
    "knapp, praezise und auf Deutsch."
)

TOOL_PROVIDERS = {"nvidia", "openai", "deepseek", "mistral", "glm", "qwen", "ollama"}


class ChatService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._registry = get_registry()
        self._memory = MemoryService()
        self._toolbox = ToolBox(memory=self._memory)

    def _system_prompt(self) -> str:
        block = self._memory.prompt_block()
        return f"{SYSTEM_PROMPT}\n\n{block}" if block else SYSTEM_PROMPT

    def resolve(self, payload: ChatIn) -> tuple[str, str]:
        provider = payload.provider or self._settings.default_provider
        model = payload.model or self._settings.default_model
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
                0, ChatMessage(role="system", content=self._system_prompt())
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
        try:
            chunk: StreamChunk
            async for chunk in provider.stream(request, executor):
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
        reasoning = "".join(reasoning_parts)
        if payload.persist and conversation_id and content:
            self._store_answer(conversation_id, content, reasoning)

        yield {"type": "done", "conversation_id": conversation_id}
