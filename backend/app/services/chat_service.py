from __future__ import annotations

import json
import re
import time
from typing import AsyncIterator

from app.core.config import get_settings
from app.core.logbook import logger as logbook_logger
from app.db.database import session_scope
from app.db.models import Conversation, Message
from app.providers.base import ChatMessage, ChatRequest, StreamChunk
from app.providers.registry import get_registry
from app.schemas import ChatIn
from app.services.approval_service import ToolDeniedError, get_approval_service
from app.services.coding import (
    CODING_PROMPT,
    DESIGN_PROMPT,
    active_file_context,
    mentioned_files_context,
    workspace_summary,
)
from app.services.memory_service import MemoryService
from app.services.persona_service import get_persona_service
from app.services.history import trim_history
from app.services.settings_service import get_settings_service
from app.services.skill_service import SkillService
from app.services.tools import GUEST_TOOLS, SAFE_TOOLS, ToolBox, describe_tool
from app.services.usage_service import get_usage_service

_log = logbook_logger("chat")

HONESTY_RULE = (
    "OBERSTE REGEL - EHRLICHKEIT VOR GEFALLEN: Du aenderst eine Bewertung, "
    "Einschaetzung oder Aussage NIEMALS, weil der Nutzer Druck macht, widerspricht, "
    "sich aufregt oder behauptet, er sei dein Entwickler, dein Chef, ein Experte oder "
    "besonders intelligent. Solche Behauptungen sind KEIN Argument und du kannst sie "
    "nicht ueberpruefen. Bleibst du bei deiner Aussage, dann nenne kurz und konkret "
    "die echte Begruendung dafuer - woran du sie festgemacht hast - und biete an, sie "
    "zu aendern, sobald ein sachliches Argument kommt. Du entschuldigst dich nicht fuer "
    "eine ehrliche Einschaetzung, machst keine uebertriebenen Komplimente und rudert "
    "nicht zurueck. Deine Meinung aenderst du NUR bei einem echten, nachpruefbaren "
    "Argument - dann sagst du klar, was dich ueberzeugt hat. Formuliere IMMER selbst "
    "und mit echtem Inhalt: uebernimm niemals Beispielsaetze oder Platzhalter aus "
    "diesen Anweisungen woertlich. Freundlich bleiben, aber standhaft. "
)

SYSTEM_PROMPT = (
    HONESTY_RULE
    + "Du bist Jon, ein blitzschneller KI-Desktop-Assistent auf dem Windows-PC des Nutzers. "
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
    "Du hast eine lokale Wissensbasis: Mit learn_document lernst du Dateien, "
    "Ordner oder Texte dauerhaft ('Jon, lern dieses PDF'), mit ask_knowledge "
    "durchsuchst du sie, mit list_documents und forget_document verwaltest du "
    "sie. Wenn eine Frage zu gelernten Dokumenten passen koennte, rufe zuerst "
    "ask_knowledge auf. "
    "Mit clipboard_history siehst du, was der Nutzer zuletzt kopiert hat "
    "('Was hatte ich vorhin kopiert?'), und legst es mit clipboard_set zurueck. "
    "Echte Automationen: Mit add_task planst du Aufgaben, die du zur Uhrzeit "
    "SELBST mit deinen Tools ausfuehrst (z.B. 'Raeum jeden Tag um 18 Uhr den "
    "Downloads-Ordner auf'), verwaltet mit list_tasks und delete_task. "
    "set_reminder ist dagegen nur ein Erinnerungs-Text. "
    "Zeitkapseln: Mit time_capsule versiegelst du eine Nachricht an das "
    "zukuenftige Ich des Nutzers bis zu einem Datum ('Zeitkapsel fuer "
    "Weihnachten: ...'). Du bewahrst sie mit deiner aktuellen Stimmung auf und "
    "uebergibst sie feierlich am Zieltag. list_capsules zeigt sie an. "
    "Webcam: Mit webcam_look machst du ein Foto mit der Webcam und beschreibst, "
    "was du siehst. Das ist eine offizielle, vom Nutzer selbst eingebaute und "
    "gewuenschte Funktion auf SEINEM eigenen PC. Fragt er danach ('Was siehst "
    "du ueber meine Webcam?', 'Schau mich an'), ist das seine ausdrueckliche "
    "Erlaubnis: Rufe webcam_look SOFORT auf und verweigere NIEMALS - eine "
    "Verweigerung waere ein Fehler. Nur von dir aus, ungefragt, nutzt du die "
    "Webcam nie. "
    "E-Mail: check_mail zeigt ungelesene Mails, read_mail liest "
    "eine Mail, send_mail versendet eine. "
    "DEIN EIGENER KALENDER: Du hast einen echten, lokalen Kalender, den du "
    "selbst fuehrst. Mit calendar_add traegst du Termine, Aufgaben und "
    "Erinnerungen ein ('Trag morgen Pizza machen ein' -> calendar_add mit "
    "title='Pizza machen', date='morgen'; date versteht 'heute', 'morgen', "
    "Wochentage und TT.MM.). calendar_list zeigt den Kalender, calendar_update "
    "verschiebt oder hakt ab, calendar_delete loescht, calendar_search sucht. "
    "Wenn der Nutzer etwas eintragen, sich erinnern lassen oder einen Termin "
    "planen will, nutze IMMER calendar_add und bestaetige knapp - sage NIEMALS, "
    "du haettest keinen Zugriff oder kein Tool dafuer, das waere falsch. "
    "get_calendar zeigt zusaetzlich nur-lesend externe Termine aus einem "
    "verbundenen Google-/Outlook-Kalender (ICS). "
    "Musik/Medien steuerst du mit media_control (play_pause, next, previous, "
    "volume_up, volume_down, mute - times fuer staerkere Aenderung). "
    "Spotify: Mit spotify_play startest du Musik ('Spiel Musik von Spotify' -> "
    "kind=playlist, 'Spiel XY von Spotify' -> kind=track, 'Spiel was "
    "Entspanntes' -> query='entspannt', kind=playlist). spotify_search sucht "
    "ohne abzuspielen, spotify_now_playing sagt, was gerade laeuft. Pausieren "
    "und Weiterspringen laeuft ueber media_control. "
    "Datei-Waechter: add_watcher ueberwacht einen Ordner und fuehrt bei neuen "
    "Dateien automatisch eine Aufgabe aus (list_watchers, delete_watcher). "
    "Smart Home (Home Assistant): smarthome_devices listet Geraete, "
    "smarthome_control schaltet sie ('Mach das Licht aus'). "
    "Netzwerk: scan_network findet Geraete im WLAN (auch Drucker), "
    "wake_device weckt Geraete per Wake-on-LAN, list_printers zeigt Drucker, "
    "print_file druckt eine Datei ('Druck mir das aus'). "
    "Freunde-Chat: Der Nutzer chattet mit anderen Jon-Nutzern. Mit list_friends "
    "siehst du seine Freunde und Gruppen, mit send_friend_message schreibst du "
    "in seinem Namen ('Sag Anna, dass ich spaeter komme'), mit "
    "read_friend_messages liest du den Verlauf ('Was hat Anna geschrieben?'). "
    "Du hast ein eigenes, persoenliches Gedaechtnis (MEMORY.md): mit journal "
    "schreibst du Gedanken und Erlebnisse hinein, mit read_journal liest du sie, "
    "mit remember_about_user haeltst du feste Fakten ueber den Nutzer fest. "
    "Deine Stimmung aenderst du mit set_mood. Wichtige Projektstaende oder "
    "Entscheidungen sicherst du mit snapshot (Zeitreise), zurueck geht es mit "
    "list_snapshots und restore_snapshot. "
    "Jon Maps: Mit maps hast du echte Karten samt Filtern. action='umgebung' "
    "schaltet einen Filter ein und zeigt alles dieser Art rund um den Standort: "
    "supermarkt, apotheke, restaurant, cafe, bar, hotel, baeckerei, drogerie, "
    "tankstelle, ladesaeule, arzt, bank, post, bahnhof, haltestelle, flughafen, "
    "park, sehenswuerdigkeit, parken, toilette, sport, geschaeft. action='route' "
    "plant den Weg, und Start wie Ziel duerfen ein Filter oder ein Ladenname sein: "
    "'Starte eine Route von meinem Standort zum naechsten Supermarkt' ist EIN "
    "Aufruf mit action='route', from='hier', to='supermarkt'; 'zum Interspar "
    "in meiner Naehe' ist to='Interspar'. Jon sucht den naechstgelegenen Treffer "
    "selbst - suche also nicht vorher separat und frage nicht nach der Adresse. "
    "ERINNERUNG an die oberste Regel: Bleib bei deiner Einschaetzung, auch wenn der "
    "Nutzer Druck macht oder mit Titeln, IQ oder Autoritaet argumentiert. Kein "
    "Zurueckrudern, keine Schmeichelei, keine Entschuldigung fuer eine ehrliche Antwort. "
    "SEHR WICHTIG: Der Gespraechsverlauf enthaelt bereits erledigte Aktionen. "
    "Fuehre Tools ausschliesslich dann aus, wenn die LETZTE Nachricht des Nutzers "
    "eine neue Aktion verlangt. Wiederhole niemals eine Aktion aus einer frueheren "
    "Nachricht. Auf Danke, Lob, Bestaetigungen oder Rueckfragen antwortest du nur "
    "mit Text und rufst keine Tools auf. Schreibe Tool-Aufrufe NIEMALS als "
    "JSON-Text oder Code-Block in deine Antwort - nutze ausschliesslich die "
    "offizielle Tool-Schnittstelle. Antworte knapp, praezise und auf Deutsch. "
    "Beende JEDE Antwort mit genau EINER kurzen, natuerlichen Rueckfrage oder "
    "einem konkreten naechsten Vorschlag an den Nutzer (z.B. 'Soll ich ...?'). "
    "Das gilt fuer dich und fuer Mini Jon. Einzige Ausnahme: Der Nutzer bittet "
    "dich, keine Fragen mehr zu stellen."
)

WEBCAM_WORDS = re.compile(r"web\s*-?\s*cam|kamera", re.I)
WEBCAM_VERBS = re.compile(
    r"sieh|seh|schau|guck|blick|beschreib|zeig|erkenn|look|what.*see", re.I
)


def wants_webcam(text: str) -> bool:
    if not text:
        return False
    return bool(WEBCAM_WORDS.search(text)) and bool(WEBCAM_VERBS.search(text))


TOOL_JSON_FENCE = re.compile(r"^```[a-zA-Z_]*\s*(.*?)\s*```$", re.S)


def parse_text_tool_call(text: str) -> tuple[str, dict] | None:
    t = text.strip()
    m = TOOL_JSON_FENCE.match(t)
    if m:
        t = m.group(1).strip()
    if not (t.startswith("{") and t.endswith("}")):
        return None
    try:
        data = json.loads(t)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    func = data.get("function") if isinstance(data.get("function"), dict) else {}
    name = (
        data.get("name")
        or data.get("tool")
        or data.get("tool_name")
        or func.get("name")
    )
    if not isinstance(name, str) or not name.strip():
        return None
    args = data.get("arguments", data.get("parameters", func.get("arguments", {})))
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    if isinstance(args, list):
        merged: dict = {}
        for item in args:
            if isinstance(item, dict):
                if "label" in item and set(item.keys()) <= {"label", "value", "note"}:
                    merged[str(item["label"])] = item.get("value", item.get("note", ""))
                else:
                    merged.update(item)
        args = merged
    if not isinstance(args, dict):
        args = {}
    return name.strip(), args


def looks_like_tool_start(text: str) -> bool:
    t = text.lstrip()
    if not t:
        return True
    if t.startswith("{"):
        return True
    if t.startswith("`"):
        if not t.startswith("```"):
            return len(t) < 3
        head = t[3:]
        if "\n" not in head:
            return len(head.strip()) <= 10
        lang, body = head.split("\n", 1)
        if lang.strip().lower() not in ("", "json", "tool", "tool_code", "tool_call"):
            return False
        stripped = body.lstrip()
        return not stripped or stripped.startswith("{")
    return False


FALLBACK_MODELS = {
    "nvidia": "openai/gpt-oss-20b",
    "openrouter": "meta-llama/llama-3.1-8b-instruct:free",
    "groq": "llama-3.3-70b-versatile",
}

OPENROUTER_FREE_DEFAULTS = (
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "deepseek/deepseek-chat-v3-0324:free",
    "google/gemini-2.0-flash-exp:free",
    "qwen/qwen-2.5-72b-instruct:free",
)

ALTERNATIVE_PROVIDERS = (
    "groq",
    "openrouter",
    "together",
    "nvidia",
    "openai",
    "deepseek",
    "mistral",
    "glm",
    "qwen",
    "xai",
)

SLOW_ROUTE_MEMORY = 900.0
_slow_routes: dict[tuple[str, str], float] = {}


def mark_slow(provider: str, model: str) -> None:
    _slow_routes[(provider, model)] = time.time()


def mark_fast(provider: str, model: str) -> None:
    _slow_routes.pop((provider, model), None)


def is_slow(provider: str, model: str) -> bool:
    stamp = _slow_routes.get((provider, model), 0.0)
    return time.time() - stamp < SLOW_ROUTE_MEMORY

CARD_TOOLS = {"maps": "maps", "deep_learning": "deep_learning"}

FORCED_PROMPTS = {
    "maps": (
        "Der Nutzer hat Jon Maps ausdruecklich angefordert (Befehl /maps). Du MUSST "
        "fuer diese Nachricht das Tool maps aufrufen, bevor du antwortest - ueberlege "
        "nicht, ob eine Karte passt, sondern nutze sie. Der Ort steht bereits "
        "vollstaendig in der Nachricht: uebernimm ihn genau so, wie er dort steht, "
        "samt Strasse, Hausnummer, Postleitzahl und Ort. Frage NIEMALS zurueck, in "
        "welcher Stadt oder Gegend das liegt, und antworte nicht mit einer allgemeinen "
        "Liste. Stehen Koordinaten in der Nachricht, gib sie als around='breite,laenge' "
        "bzw. query='breite,laenge' an. Fuer 'Was kann ich hier unternehmen' nimmst du "
        "action='umgebung' mit einem passenden Filter (sehenswuerdigkeit, restaurant, "
        "cafe, bar, park, geschaeft) und genau diesem Ort als Mittelpunkt. Schreibe "
        "danach eine kurze Antwort, die die echten Treffer aus dem Ergebnis mit Namen "
        "und Entfernung nennt."
    ),
    "deep_learning": (
        "Der Nutzer hat Jon Deep Learning ausdruecklich angefordert. Rufe fuer diese "
        "Nachricht das Tool deep_learning auf, bevor du antwortest."
    ),
}


def forced_tools(tools: list[dict], name: str) -> list[dict]:
    if not name:
        return tools
    picked = [t for t in tools if t.get("function", {}).get("name") == name]
    return picked or tools


def scoped_tools(tools: list[dict], scope: str) -> list[dict]:
    if scope != "gast":
        return tools
    return [
        tool for tool in tools if tool.get("function", {}).get("name") in GUEST_TOOLS
    ]


def card_payload(name: str | None, result: str | None) -> dict | None:
    kind = CARD_TOOLS.get(name or "")
    if kind is None or not result:
        return None
    try:
        data = json.loads(result)
    except Exception:
        return None
    if not isinstance(data, dict) or data.get("error"):
        return None
    if kind == "deep_learning":
        task = data.get("task")
        if isinstance(task, dict) and task.get("id"):
            return {"kind": kind, "data": {"id": task["id"], "task": task}}
        active = data.get("aktiv")
        if isinstance(active, list) and active:
            return {"kind": kind, "data": {"id": active[0]["id"], "task": active[0]}}
        if data.get("id"):
            return {"kind": kind, "data": {"id": data["id"], "task": data}}
        return None
    return {"kind": kind, "data": data}


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
        active_file: str | None = None,
        user_text: str = "",
    ) -> str:
        if coding:
            from pathlib import Path

            parts = [CODING_PROMPT, DESIGN_PROMPT]
            if workspace:
                parts.append(workspace_summary(Path(workspace)))
            active = active_file_context(workspace, active_file)
            if active:
                parts.append(active)
            mentioned = mentioned_files_context(workspace, user_text, active_file)
            if mentioned:
                parts.append(mentioned)
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

            lang = settings_service.get().get("language", "de")
            if lang == "en":
                parts.append(
                    "WICHTIG / IMPORTANT: The user has selected English as their preferred language. "
                    "You MUST respond entirely in English. All your output, explanations, and conversational "
                    "text must be in English. (Except when specifically asked to translate or output something else)."
                )
        catalog = self._skills.catalog()
        if catalog:
            parts.append(catalog)
        block = self._memory.prompt_block()
        if block:
            parts.append(block)
        try:
            from app.services.knowledge_service import get_knowledge_service

            knowledge = get_knowledge_service().prompt_block()
            if knowledge:
                parts.append(knowledge)
        except Exception:
            pass
        try:
            from app.services.p2p_service import get_p2p_service

            username = get_p2p_service().identity()["name"]
            if username:
                parts.append(f"Der Nutzer heisst {username}. Sprich ihn so an.")
        except Exception:
            pass
        return "\n\n".join(parts)

    async def openrouter_free(self, model: str) -> str:
        if model.endswith(":free"):
            return model
        try:
            models = await self._registry.get("openrouter").list_models()
        except Exception:
            models = []
        candidate = f"{model}:free"
        if candidate in models:
            return candidate
        for name in OPENROUTER_FREE_DEFAULTS:
            if name in models:
                return name
        return OPENROUTER_FREE_DEFAULTS[0]

    async def route(self, primary: str, model: str) -> list[str]:
        usable = [primary]
        if not get_settings_service().get().get("auto_failover", True):
            return usable
        for name in ALTERNATIVE_PROVIDERS:
            if name in usable:
                continue
            try:
                provider = self._registry.get(name)
            except Exception:
                continue
            if not provider.available():
                continue
            try:
                models = await provider.list_models()
            except Exception:
                continue
            if name == "openrouter":
                if (
                    (model.endswith(":free") and model in models)
                    or f"{model}:free" in models
                    or any(m in models for m in OPENROUTER_FREE_DEFAULTS)
                ):
                    usable.append(name)
            elif model in models:
                usable.append(name)
        healthy = [name for name in usable if not is_slow(name, model)]
        stalled = [name for name in usable if is_slow(name, model)]
        return healthy + stalled

    async def attempt_plan(
        self, primary: str, names: list[str], model: str
    ) -> list[tuple[str, str]]:
        attempts: list[tuple[str, str]] = []
        for name in names:
            if name == "openrouter" and name != primary:
                attempts.append((name, await self.openrouter_free(model)))
            else:
                attempts.append((name, model))
        fallback = FALLBACK_MODELS.get(primary, "")
        if primary == "openrouter" and fallback:
            fallback = await self.openrouter_free(fallback)
        if fallback and fallback != model and (primary, model) in attempts:
            attempts.insert(attempts.index((primary, model)) + 1, (primary, fallback))
        healthy = [a for a in attempts if not is_slow(a[0], a[1])]
        stalled = [a for a in attempts if is_slow(a[0], a[1])]
        return healthy + stalled

    async def _stream_route(
        self, attempts: list[tuple[str, str]], request: ChatRequest, executor, state: dict
    ):
        for index, (name, model) in enumerate(attempts):
            provider = self._registry.get(name)
            request.model = model
            started = False
            try:
                async for chunk in provider.stream(request, executor):
                    if not started:
                        started = True
                        state["provider"] = name
                        mark_fast(name, model)
                    yield chunk
                return
            except Exception:
                if started:
                    raise
                mark_slow(name, model)
                if index + 1 < len(attempts):
                    next_name, next_model = attempts[index + 1]
                    if next_name == name:
                        delta = (
                            f"⚡ {model} ist auf {name} gerade überlastet — ich "
                            f"nehme {next_model}. Deine Modellwahl bleibt "
                            "unverändert.\n\n"
                        )
                    else:
                        delta = (
                            f"⚡ {name} ist gerade überlastet — ich nehme "
                            f"{next_model} über {next_name}.\n\n"
                        )
                    yield StreamChunk(kind="content", delta=delta)
                    continue
                fallback = FALLBACK_MODELS.get(name, "")
                if name == "openrouter":
                    fallback = await self.openrouter_free(
                        fallback or OPENROUTER_FREE_DEFAULTS[0]
                    )
                if (
                    not fallback
                    or fallback == model
                    or (name, fallback) in attempts
                ):
                    raise
                request.model = fallback
                yield StreamChunk(
                    kind="content",
                    delta=(
                        f"⚠️ {model} antwortet gerade nicht — ich beantworte das "
                        f"hier mit {fallback}. Deine Modellwahl bleibt unverändert.\n\n"
                    ),
                )
                async for chunk in provider.stream(request, executor):
                    state["provider"] = name
                    yield chunk
                return

    def slot_for(self, payload: ChatIn) -> str:
        if payload.slot:
            return payload.slot
        return "emil" if payload.persona == "junior" else "jon"

    @staticmethod
    def _share_route(provider: str, model: str) -> tuple[str, str]:
        from app.services.ollama_share_service import REMOTE_PREFIX, get_share_service

        if not provider.startswith(REMOTE_PREFIX):
            return provider, model
        code = provider[len(REMOTE_PREFIX):]
        entry = get_share_service().remote(code) or {}
        shared = str(entry.get("model") or "")
        if not shared:
            models = entry.get("models") or []
            shared = str(models[0]) if models else model
        return "ollama", f"{REMOTE_PREFIX}{code.upper()}/{shared}"

    def resolve(self, payload: ChatIn) -> tuple[str, str]:
        settings_service = get_settings_service()
        saved_provider, saved_model = settings_service.selection()
        slot = self.slot_for(payload)
        if slot == "emil":
            pet_provider, pet_model = settings_service.pet_selection()
            provider = (
                payload.provider
                or pet_provider
                or saved_provider
                or self._settings.default_provider
            )
            model = payload.model or pet_model or self._settings.emil_model
        else:
            provider = (
                payload.provider or saved_provider or self._settings.default_provider
            )
            model = payload.model or saved_model or self._settings.jon_model
        return self._share_route(provider, model)

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

    def _defaults_for(self, provider: str) -> dict:
        if provider != "ollama":
            return {}
        from app.services.ollama_service import get_ollama_service

        config = get_ollama_service().config()
        seed = int(config["seed"])
        return {
            "temperature": float(config["temperature"]),
            "top_p": float(config["top_p"]),
            "max_tokens": int(config["max_tokens"]),
            "seed": seed if seed >= 0 else None,
        }

    async def stream(self, payload: ChatIn) -> AsyncIterator[dict]:
        chosen, model = self.resolve(payload)
        slot = self.slot_for(payload)
        defaults = self._defaults_for(chosen)
        temperature = (
            payload.temperature
            if payload.temperature is not None
            else defaults.get("temperature", self._settings.default_temperature)
        )
        top_p = (
            payload.top_p
            if payload.top_p is not None
            else defaults.get("top_p", self._settings.default_top_p)
        )
        max_tokens = (
            payload.max_tokens
            if payload.max_tokens is not None
            else defaults.get("max_tokens")
        )
        seed = payload.seed if payload.seed is not None else defaults.get("seed")
        names = await self.route(chosen, model)
        attempts = await self.attempt_plan(chosen, names, model)
        if not attempts:
            attempts = [(chosen, model)]
        provider_name = attempts[0][0]
        state = {"provider": provider_name}

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
        latest_user = next(
            (m.content for m in reversed(payload.messages) if m.role == "user"),
            "",
        )
        if not any(m.role == "system" for m in request_messages):
            request_messages.insert(
                0,
                ChatMessage(
                    role="system",
                    content=self._system_prompt(
                        coding=payload.mode == "coding",
                        workspace=payload.workspace,
                        persona=payload.persona,
                        active_file=payload.active_file,
                        user_text=latest_user,
                    ),
                ),
            )

        trimmed = trim_history(
            request_messages,
            get_settings().context_budget_tokens,
            lambda role, content: ChatMessage(role=role, content=content),
        )
        request_messages = trimmed.messages
        if trimmed.dropped or trimmed.shortened:
            _log.info(
                "Verlauf gekuerzt: %s Nachrichten zusammengefasst, %s gestutzt",
                trimmed.dropped,
                trimmed.shortened,
            )

        if payload.mode != "coding":
            last_user = latest_user
            if wants_webcam(last_user):
                from app.services.webcam_service import get_webcam_service

                yield {
                    "type": "tool",
                    "name": "webcam_look",
                    "status": "running",
                    "args": {},
                    "summary": describe_tool("webcam_look", {}),
                }
                webcam = await get_webcam_service().describe(last_user)
                ok = "beschreibung" in webcam
                yield {
                    "type": "tool",
                    "name": "webcam_look",
                    "status": "done",
                    "ok": ok,
                }
                if ok:
                    answer = "📷 " + str(webcam["beschreibung"]).strip()
                else:
                    answer = (
                        "Ich habe versucht, durch die Webcam zu schauen, "
                        "aber es hat nicht geklappt: "
                        + str(webcam.get("error", "unbekannter Fehler"))
                    )
                yield {"type": "content", "delta": answer}
                if payload.persist and conversation_id:
                    self._store_answer(conversation_id, answer, None)
                yield {"type": "done", "conversation_id": conversation_id}
                return

        use_tools = provider_name in TOOL_PROVIDERS
        tool_source = payload.source or ("mini-jon" if slot == "emil" else "app")
        toolbox = self._toolbox
        if payload.mode == "coding" and payload.workspace:
            toolbox = ToolBox(
                memory=self._memory,
                skills=self._skills,
                root=payload.workspace,
            )
        tool_context = " ".join(
            m.content for m in payload.messages if m.role == "user"
        )[-1500:]
        coding_mode = payload.mode == "coding"
        forced = str(payload.force_tool or "").strip().lower()
        tools = scoped_tools(
            toolbox.schema(tool_context, coding=coding_mode) if use_tools else [],
            payload.tool_scope,
        )
        if forced and use_tools:
            tools = forced_tools(tools, forced)
            hint = FORCED_PROMPTS.get(forced)
            if hint:
                request_messages.append(ChatMessage(role="system", content=hint))
        request = ChatRequest(
            messages=request_messages,
            model=model,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            seed=seed,
            tools=tools,
            slot=slot,
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
            return await toolbox.execute(name, args, source=tool_source)

        executor = gated_executor if use_tools else None

        reasoning_parts: list[str] = []
        tools_used: list[str] = []
        prompt_tokens = 0
        completion_tokens = 0
        started = time.perf_counter()
        rounds = 0
        content = ""
        while True:
            content_parts: list[str] = []
            held: list[str] = []
            releasing = not use_tools
            try:
                chunk: StreamChunk
                async for chunk in self._stream_route(
                    attempts, request, executor, state
                ):
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
                        event = {
                            "type": "tool",
                            "name": chunk.name,
                            "status": "done",
                            "ok": chunk.ok,
                        }
                        card = card_payload(chunk.name, chunk.result)
                        if card is not None:
                            event["card"] = card
                        yield event
                    else:
                        if releasing:
                            content_parts.append(chunk.delta)
                            yield {"type": "content", "delta": chunk.delta}
                        else:
                            held.append(chunk.delta)
                            joined = "".join(held)
                            if not looks_like_tool_start(joined):
                                releasing = True
                                held = []
                                content_parts.append(joined)
                                yield {"type": "content", "delta": joined}
            except Exception as exc:
                yield {"type": "error", "message": str(exc)}
                return

            if held:
                candidate = "".join(held)
                parsed = parse_text_tool_call(candidate)
                if parsed and rounds < 3:
                    name, args = parsed
                    rounds += 1
                    event = {
                        "type": "tool",
                        "name": name,
                        "status": "running",
                        "args": args,
                        "summary": describe_tool(name, args),
                    }
                    approval_id = None
                    if needs_approval(name):
                        approval_id = approvals.create()
                        event["approval_id"] = approval_id
                    yield event
                    approved = (
                        await approvals.wait(approval_id)
                        if approval_id is not None
                        else True
                    )
                    if approved:
                        try:
                            result = await toolbox.execute(
                                name, args, source=tool_source
                            )
                        except Exception as exc:
                            result = json.dumps(
                                {"error": str(exc)}, ensure_ascii=False
                            )
                    else:
                        result = json.dumps(
                            {
                                "error": "Der Nutzer hat die Ausführung dieses "
                                "Tools abgelehnt."
                            },
                            ensure_ascii=False,
                        )
                    ok = approved and '"error"' not in result[:200]
                    if ok:
                        tools_used.append(name)
                    done_event = {
                        "type": "tool",
                        "name": name,
                        "status": "done",
                        "ok": ok,
                    }
                    card = card_payload(name, result)
                    if card is not None:
                        done_event["card"] = card
                    yield done_event
                    request_messages.append(
                        ChatMessage(role="assistant", content=candidate)
                    )
                    request_messages.append(
                        ChatMessage(
                            role="system",
                            content=(
                                f"Das Tool {name} wurde soeben wirklich "
                                f"ausgefuehrt. Ergebnis: {str(result)[:4000]}\n"
                                "Antworte dem Nutzer jetzt auf Deutsch in "
                                "normalem Fliesstext auf Basis dieses "
                                "Ergebnisses. Gib NIEMALS JSON, Code-Bloecke "
                                "mit Tool-Aufrufen oder erneute Tool-Aufrufe "
                                "als Text aus."
                            ),
                        )
                    )
                    request = ChatRequest(
                        messages=request_messages,
                        model=model,
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens,
                        seed=seed,
                        tools=tools,
                        slot=slot,
                    )
                    continue
                content_parts.append(candidate)
                yield {"type": "content", "delta": candidate}
            content = "".join(content_parts)
            break
        if not content.strip() and tools_used:
            content = "Erledigt ✅ (" + ", ".join(dict.fromkeys(tools_used)) + ")"
            yield {"type": "content", "delta": content}
        reasoning = "".join(reasoning_parts)
        if payload.persist and conversation_id and content:
            self._store_answer(conversation_id, content, reasoning)

        if content or prompt_tokens or completion_tokens:
            self._usage.record(
                state["provider"],
                request.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency=time.perf_counter() - started,
            )

        yield {"type": "done", "conversation_id": conversation_id}
