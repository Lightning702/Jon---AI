# Architekturübersicht

```
Jon/
├── backend/                       FastAPI-Backend
│   └── app/
│       ├── core/                  Konfiguration (config.py) + Key-Manager (keys.py)
│       ├── providers/             LLM-Provider-Abstraktion
│       │   ├── base.py            ChatRequest/StreamChunk/LLMProvider
│       │   ├── openai_compatible.py   NVIDIA/OpenAI/DeepSeek/GLM/Qwen/Mistral/Ollama
│       │   ├── anthropic_provider.py  Claude
│       │   ├── gemini_provider.py     Gemini
│       │   └── registry.py        Baut Provider, löst Keys dynamisch auf
│       ├── db/                    SQLAlchemy-Modelle + Session
│       ├── services/
│       │   ├── chat_service.py    Orchestriert Stream, Tools, Freigabe, Usage
│       │   ├── tools.py           ToolBox: Schemas + Ausführung + Beschreibungen
│       │   ├── system_service.py  Shell, Dateien, Archive, Web, System
│       │   ├── automation_service.py  Maus/Tastatur/Fenster (PyAutoGUI)
│       │   ├── memory_service.py  Langzeitgedächtnis
│       │   ├── skill_service.py   Liest/Schreibt skills/*.md
│       │   ├── account_service.py Runtime-Keys, Modell-Auswahl, Status
│       │   ├── usage_service.py   Nutzungs-Tracking (data/usage.json)
│       │   ├── approval_service.py Freigabe-Warteschlange für Tools
│       │   └── voice_service.py   Sprache-zu-Text
│       ├── api/
│       │   ├── routes.py          Chat, Konten, Skills, Usage, Konversationen
│       │   └── system_routes.py   Direkte System-Endpoints + Transkription
│       └── main.py                App-Factory + Uvicorn
├── frontend/                      Electron + Vite + React + TypeScript
│   ├── electron/                  Main- und Preload-Prozess
│   └── src/
│       ├── components/            UI (Chat, Composer, Dialoge, Konten, Einstellungen)
│       └── lib/                   API-Client, Voice, TTS, Tool-Infos
├── skills/                        Bearbeitbare Markdown-Anleitungen
├── website/                       Netlify-Seite + Handy-App (PWA)
├── docs/                          Diese Dokumentation
└── data/                          SQLite-DB, usage.json, accounts.json (git-ignoriert)
```

## Datenfluss eines Chats

1. Frontend sendet `POST /api/chat` (SSE) mit Nachrichten, Provider, Modell, `tool_mode`.
2. `ChatService` baut den System-Prompt (Basis + Skill-Katalog + Gedächtnis), wählt den
   Provider über die `ProviderRegistry` und startet den Stream.
3. Der Provider streamt `content`/`reasoning`. Bei Tool-Aufrufen sendet er `tool`-Chunks
   mit Argumenten; `ChatService` fügt eine Freigabe-ID hinzu, wenn der Modus „ask" ist.
4. Das Frontend zeigt den Freigabe-Dialog; die Entscheidung geht an
   `POST /api/chat/approve`. Der `ApprovalService` gibt den wartenden Tool-Aufruf frei.
5. Nach Freigabe führt die `ToolBox` das Tool aus, das Ergebnis geht zurück ins Modell.
6. Am Ende erfasst der `UsageService` Tokens und Antwortzeit.

## Erweiterbarkeit

- **Neuer Provider:** Klasse mit `LLMProvider`-Interface, in `registry.py` registrieren.
  Für OpenAI-kompatible Dienste genügt eine `OpenAICompatibleProvider`-Instanz.
- **Neues Tool:** Schema in `ToolBox.schema()`, Ausführung in `ToolBox._execute()`,
  Beschreibung in `describe_tool()`. Reine Leseaktionen in `SAFE_TOOLS` aufnehmen.
- **Neuer Skill:** Markdown-Datei in `skills/` ablegen — kein Code nötig.
- **Neuer Anbieter im Konten-Bereich:** Eintrag in `account_service.SUPPORTED`.
