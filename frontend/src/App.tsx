import { useEffect, useRef, useState } from "react";
import TitleBar from "./components/TitleBar";
import Sidebar from "./components/Sidebar";
import MessageBubble, { ChatEntry } from "./components/MessageBubble";
import Composer, { PendingAttachment } from "./components/Composer";
import ClipboardPanel from "./components/ClipboardPanel";
import ModelPicker from "./components/ModelPicker";
import VoiceIndicator, { VoiceUiState } from "./components/VoiceIndicator";
import ApprovalDialog, { ApprovalRequest } from "./components/ApprovalDialog";
import SettingsMenu from "./components/SettingsMenu";
import AccountsModal from "./components/AccountsModal";
import CodeAgent from "./components/CodeAgent";
import PetConfig from "./components/PetConfig";
import ProfileModal from "./components/ProfileModal";
import FriendsChat from "./components/FriendsChat";
import FriendRequestPopup from "./components/FriendRequestPopup";
import Humanizer from "./components/Humanizer";
import Downloader from "./components/Downloader";
import EveningShow from "./components/EveningShow";
import RoutineBanner from "./components/RoutineBanner";
import Journal from "./components/Journal";
import Cleanup from "./components/Cleanup";
import Recipe from "./components/Recipe";
import Flashcards from "./components/Flashcards";
import ScreenExplain from "./components/ScreenExplain";
import Notes from "./components/Notes";
import Vault from "./components/Vault";
import Search from "./components/Search";
import SetupWizard from "./components/SetupWizard";
import CalendarPanel from "./components/CalendarPanel";
import { VoiceListener } from "./lib/voice";
import { initTts, setNaturalVoice, speak, stopSpeaking } from "./lib/tts";
import {
  ConversationSummary,
  P2PIdentity,
  P2PRequest,
  ProviderStatus,
  StreamEvent,
  ToolMode,
  addDream,
  getActions,
  getAppUsage,
  getCalendar,
  getCalendarDue,
  meetingStart,
  meetingStatus,
  meetingStop,
  getTrash,
  restoreTrash,
  undoTrash,
  answerRequest,
  checkUpdate,
  getChatNotifications,
  getIdentity,
  getP2PInfo,
  getRequests,
  approveTool,
  createSnapshot,
  deleteConversation,
  getBriefing,
  getConversation,
  getConversations,
  getDreamReports,
  getDueCapsules,
  getDueReminders,
  getHealth,
  blockweltUrl,
  getHealthCheck,
  getProviders,
  getTaskReports,
  getTasks,
  getUserSettings,
  getWatcherReports,
  getWeekly,
  listSnapshots,
  observeScreen,
  observeWebcam,
  saveUserSettings,
  runDreams,
  runSimulation,
  runTeam,
  streamChat,
  BASE,
} from "./lib/api";

const jonDesktop = (window as unknown as {
  jon?: {
    togglePet?: () => void;
    flashWindow?: () => void;
    focusWindow?: () => void;
    onExplainScreen?: (cb: () => void) => void;
  };
}).jon;

function chatPing() {
  try {
    const ctx = new AudioContext();
    const now = ctx.currentTime;
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(0.16, now + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.45);
    gain.connect(ctx.destination);
    [880, 1320].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, now + i * 0.12);
      osc.connect(gain);
      osc.start(now + i * 0.12);
      osc.stop(now + i * 0.12 + 0.3);
    });
    window.setTimeout(() => void ctx.close(), 800);
  } catch {
    void 0;
  }
}

let idc = 0;
const nextId = () => `m${Date.now()}_${idc++}`;

const BRIEFING_PROMPT =
  "Erstelle ein kurzes Tagesbriefing: Begrüße den Nutzer passend zur Tageszeit, " +
  "nenne Wochentag und Datum (system_info). Hole das Wetter für die Stadt des " +
  "Nutzers (recall nach der Stadt; ist keine gespeichert, lass das Wetter weg und " +
  "bitte ihn freundlich, dir einmal seine Stadt zu nennen). Nenne fällige " +
  "Erinnerungen (list_reminders) und gestellte Wecker (list_alarms), falls " +
  "vorhanden. Maximal 8 kurze Zeilen.";

const CHECK_PROMPT = (data: Record<string, unknown>) =>
  "Hier ist der frische PC-Gesundheitscheck:\n" +
  JSON.stringify(data) +
  "\n\nErkläre dem Nutzer auf Deutsch kurz und verständlich, wie es seinem PC " +
  "geht: Speicherplatz, Arbeitsspeicher, größte RAM-Fresser, Autostart-" +
  "Programme, Laufzeit, Größe des Temp-Ordners. Nenne dann 2-4 konkrete " +
  "Aufräum-Vorschläge und biete an, sie direkt umzusetzen. Rufe KEINE Tools " +
  "auf, alle Daten stehen oben. Maximal 12 Zeilen.";

const WEEKLY_PROMPT = (data: Record<string, unknown>) =>
  "Hier sind die Daten deiner gemeinsamen Woche mit dem Nutzer:\n" +
  JSON.stringify(data) +
  "\n\nSchreibe ihm einen persönlichen, warmen Wochenrückblick auf Deutsch: " +
  "Woran ihr gearbeitet habt, was geschafft wurde, was noch offen ist, und " +
  "ein Ausblick auf die neue Woche. Sprich als Jon, der die Woche miterlebt " +
  "hat. Rufe KEINE Tools auf. Maximal 12 Zeilen.";

const briefingPrompt = (data: Record<string, unknown>) =>
  "Hier sind die frisch gesammelten Daten für dein Tagesbriefing:\n" +
  JSON.stringify(data) +
  "\n\nErstelle daraus ein kurzes, persönliches Tagesbriefing auf Deutsch: " +
  "Begrüßung passend zur Uhrzeit, Wochentag und Datum, das Wetter (falls " +
  "vorhanden, sonst erwähne kurz, dass die Stadt im Zahnrad-Menü eingetragen " +
  "werden kann), heutige Erinnerungen, Wecker und geplante Automationen (nur " +
  "falls vorhanden). Falls in_abwesenheit_getan Einträge enthält, fasse sie " +
  "unter „Was ich in deiner Abwesenheit getan habe“ in 1-3 Zeilen zusammen. " +
  "Rufe KEINE Tools auf, alle Daten stehen oben. Maximal 10 kurze Zeilen.";

import { useT } from "./hooks/useT";

export default function App() {
  const { t } = useT();
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [provider, setProvider] = useState("nvidia");
  const [model, setModel] = useState("openai/gpt-oss-120b");
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [online, setOnline] = useState(false);
  const [voiceOn, setVoiceOn] = useState(
    () => localStorage.getItem("jon_voice") !== "0"
  );
  const [voiceState, setVoiceState] = useState<VoiceUiState>("idle");
  const [voiceDetail, setVoiceDetail] = useState<string | undefined>();
  const [toolMode, setToolMode] = useState<ToolMode>(() =>
    localStorage.getItem("jon_tool_mode") === "allow" ? "allow" : "ask"
  );
  const [approval, setApproval] = useState<ApprovalRequest | null>(null);
  const [accountsTab, setAccountsTab] = useState<
    "accounts" | "usage" | "skills" | null
  >(null);
  const [codeOpen, setCodeOpen] = useState(false);
  const [humanizerOpen, setHumanizerOpen] = useState(false);
  const [downloaderOpen, setDownloaderOpen] = useState(false);
  const [showOpen, setShowOpen] = useState(false);
  const [journalOpen, setJournalOpen] = useState(false);
  const [cleanupOpen, setCleanupOpen] = useState(false);
  const [recipeOpen, setRecipeOpen] = useState(false);
  const [flashcardsOpen, setFlashcardsOpen] = useState(false);
  const [explainOpen, setExplainOpen] = useState(false);
  const [notesOpen, setNotesOpen] = useState(false);
  const [vaultOpen, setVaultOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [toolsMenuOpen, setToolsMenuOpen] = useState(false);
  const [petConfigOpen, setPetConfigOpen] = useState(false);
  const [clipboardOpen, setClipboardOpen] = useState(false);
  const [identity, setIdentity] = useState<P2PIdentity | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [firstRun, setFirstRun] = useState(false);
  const [friendsOpen, setFriendsOpen] = useState(false);
  const [friendsPeer, setFriendsPeer] = useState<string | null>(null);
  const [friendRequests, setFriendRequests] = useState<P2PRequest[]>([]);
  const [requestBusy, setRequestBusy] = useState(false);
  const [requestError, setRequestError] = useState("");
  const [unread, setUnread] = useState(0);
  const [setupOpen, setSetupOpen] = useState(false);
  const [version, setVersion] = useState("");
  const [update, setUpdate] = useState<{ latest: string; url: string } | null>(
    null
  );
  const [screenOn, setScreenOn] = useState(
    () => localStorage.getItem("jon_screen") === "1"
  );
  const [calendarOpen, setCalendarOpen] = useState(false);
  const trashListRef = useRef<string[]>([]);
  const lastScreenRef = useRef("");
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const providerRef = useRef(provider);
  const modelRef = useRef(model);
  const streamingRef = useRef(false);
  const toolModeRef = useRef(toolMode);
  const listenerRef = useRef<VoiceListener | null>(null);
  const voiceTimerRef = useRef<number | null>(null);
  const voiceHistoryRef = useRef<{ role: "user" | "assistant"; content: string }[]>(
    []
  );

  useEffect(() => {
    jonDesktop?.onExplainScreen?.(() => setExplainOpen(true));
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  useEffect(() => {
    providerRef.current = provider;
  }, [provider]);
  useEffect(() => {
    modelRef.current = model;
  }, [model]);
  useEffect(() => {
    streamingRef.current = streaming;
  }, [streaming]);
  useEffect(() => {
    toolModeRef.current = toolMode;
  }, [toolMode]);

  const changeToolMode = (mode: ToolMode) => {
    setToolMode(mode);
    localStorage.setItem("jon_tool_mode", mode);
  };

  const changeModel = (p: string, m: string) => {
    setProvider(p);
    setModel(m);
    void saveUserSettings({ provider: p, model: m });
  };

  const toggleScreen = () => {
    setScreenOn((v) => {
      const next = !v;
      localStorage.setItem("jon_screen", next ? "1" : "0");
      return next;
    });
  };

  const handleApprovalEvent = (evt: StreamEvent) => {
    if (evt.status === "running" && evt.approval_id) {
      setApproval({
        id: evt.approval_id,
        name: evt.name ?? "tool",
        args: evt.args,
        summary: evt.summary,
      });
    }
  };

  const decideApproval = async (approved: boolean) => {
    if (!approval) return;
    const id = approval.id;
    setApproval(null);
    await approveTool(id, approved);
  };

  const refreshConversations = async () => {
    setConversations(await getConversations());
  };

  useEffect(() => {
    let cancelled = false;
    const connect = async () => {
      const health = await getHealth();
      setOnline(true);
      setVersion(health.version);
      setProvider(health.default_provider);
      setModel(health.default_model);
      const provs = await getProviders();
      if (!provs.length) throw new Error("keine Provider");
      setProviders(provs);
      const saved = await getUserSettings();
      if (saved.theme) {
        localStorage.setItem("jon_theme", saved.theme);
        document.documentElement.classList.toggle("light", saved.theme === "light");
      }
      const savedProv = provs.find(
        (p) =>
          p.provider === saved.provider &&
          (p.configured ||
            p.models.length > 0 ||
            p.provider === "ollama" ||
            p.provider === "lmstudio")
      );
      if (saved.provider && saved.model && savedProv) {
        setProvider(saved.provider);
        setModel(saved.model);
      } else {
        const preferred = provs.find(
          (p) => p.provider === health.default_provider && p.configured
        );
        const chosen = preferred ?? provs.find((p) => p.configured);
        if (chosen) {
          setProvider(chosen.provider);
          const model =
            chosen.provider === health.default_provider &&
            chosen.models.includes(health.default_model)
              ? health.default_model
              : chosen.models[0] ?? health.default_model;
          setModel(model);
        }
      }
      setNaturalVoice(saved.natural_voice !== false);
      await refreshConversations();
      const now = new Date();
      const today = now.toISOString().slice(0, 10);
      void (async () => {
        if (localStorage.getItem("jon_briefing") !== today) {
          localStorage.setItem("jon_briefing", today);
          await runBriefing();
        }
        if (now.getDay() === 0 && localStorage.getItem("jon_weekly") !== today) {
          localStorage.setItem("jon_weekly", today);
          await runDataPrompt(async () => WEEKLY_PROMPT(await getWeekly()));
        }
      })();
    };
    (async () => {
      while (!cancelled) {
        try {
          await connect();
          return;
        } catch {
          setOnline(false);
          await new Promise((r) => setTimeout(r, 2000));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!online) return;
    void (async () => {
      try {
        const me = await getIdentity();
        setIdentity(me);
        if (!me.name.trim()) {
          setFirstRun(true);
          setProfileOpen(true);
        }
      } catch {
      }
      try {
        const info = await checkUpdate();
        if (info.update) setUpdate({ latest: info.latest, url: info.url });
      } catch {
      }
    })();
  }, [online]);

  useEffect(() => {
    if (!online || providers.length === 0) return;
    if (!providers.some((p) => p.configured || p.models.length > 0)) {
      setSetupOpen(true);
    }
  }, [online, providers]);

  useEffect(() => {
    if (!online || !identity?.name || friendsOpen) {
      if (friendsOpen) setUnread(0);
      return;
    }
    if ("Notification" in window && Notification.permission === "default") {
      void Notification.requestPermission();
    }
    const tick = async () => {
      setUnread((await getP2PInfo()).unread);
      const news = await getChatNotifications();
      if (news.length === 0) return;
      chatPing();
      jonDesktop?.flashWindow?.();
      for (const n of news) {
        const preview =
          n.text.trim() ||
          (n.media_kind === "image"
            ? "📷 Foto"
            : n.media_kind === "video"
              ? "🎬 Video"
              : "📎 Datei");
        if ("Notification" in window && Notification.permission === "granted") {
          const note = new Notification(`${n.avatar} ${n.sender_name}`, {
            body: preview.slice(0, 140),
            tag: n.peer_id,
          });
          note.onclick = () => {
            jonDesktop?.focusWindow?.();
            setFriendsOpen(true);
            note.close();
          };
        }
      }
    };
    void tick();
    const timer = window.setInterval(() => void tick(), 3000);
    return () => window.clearInterval(timer);
  }, [online, identity, friendsOpen]);

  useEffect(() => {
    if (!online || !identity?.name) return;
    const tick = async () => {
      const incoming = await getRequests();
      setFriendRequests(incoming);
      if (incoming.length > 0) jonDesktop?.flashWindow?.();
    };
    void tick();
    const timer = window.setInterval(() => void tick(), 3000);
    return () => window.clearInterval(timer);
  }, [online, identity]);

  const decideRequest = async (action: "accept" | "reject" | "block") => {
    const request = friendRequests[0];
    if (!request || requestBusy) return;
    setRequestBusy(true);
    setRequestError("");
    try {
      await answerRequest(request.id, action);
      setFriendRequests((prev) => prev.filter((r) => r.id !== request.id));
      if (action === "accept") {
        setFriendsPeer(request.id);
        setFriendsOpen(true);
      }
    } catch (e) {
      setRequestError(e instanceof Error ? e.message : String(e));
    } finally {
      setRequestBusy(false);
    }
  };

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [entries]);

  useEffect(() => {
    const timer = window.setInterval(async () => {
      try {
        await getHealth();
        setOnline(true);
      } catch {
        setOnline(false);
      }
    }, 4000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!online) return;
    if ("Notification" in window && Notification.permission === "default") {
      void Notification.requestPermission();
    }
    const fire = async () => {
      const due = await getDueReminders();
      for (const r of due) {
        setEntries((prev) => [
          ...prev,
          { id: nextId(), role: "assistant", content: `🔔 Erinnerung: ${r.text}` },
        ]);
        if ("Notification" in window && Notification.permission === "granted") {
          new Notification("Jon — Erinnerung", { body: r.text });
        }
      }
      const calendarDue = await getCalendarDue();
      for (const e of calendarDue) {
        setEntries((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            content: `📅 Termin jetzt: **${e.title}** (${e.time} Uhr)`,
          },
        ]);
        if ("Notification" in window && Notification.permission === "granted") {
          new Notification("Jon — Termin", { body: `${e.title} (${e.time} Uhr)` });
        }
      }
      const reports = await getDreamReports();
      for (const t of reports) {
        setEntries((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            content: `🌙 Dream Mode — „${t.task}"\n\n${t.result ?? ""}`,
          },
        ]);
        if ("Notification" in window && Notification.permission === "granted") {
          new Notification("Jon — Dream Mode fertig", { body: t.task });
        }
      }
      const taskReports = await getTaskReports();
      for (const t of taskReports) {
        setEntries((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            content: `🤖 Automation erledigt — „${t.task}"\n\n${t.last_result ?? ""}`,
          },
        ]);
        if ("Notification" in window && Notification.permission === "granted") {
          new Notification("Jon — Automation erledigt", { body: t.task });
        }
      }
      const watchers = await getWatcherReports();
      for (const w of watchers) {
        setEntries((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            content: `👀 Datei-Wächter (${w.path})\n\n${w.last_result ?? ""}`,
          },
        ]);
        if ("Notification" in window && Notification.permission === "granted") {
          new Notification("Jon — Datei-Wächter", { body: w.task });
        }
      }
      const capsules = await getDueCapsules();
      for (const c of capsules) {
        const written = new Date(c.created_at).toLocaleDateString("de-DE");
        const mood = c.mood ? `\n\n_(Jon damals: ${c.mood})_` : "";
        setEntries((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            content:
              `🎁 Eine Zeitkapsel ist angekommen!\n\nDu hast sie am ${written} ` +
              `versiegelt, und ich habe sie seitdem gehütet. Hier ist sie:\n\n` +
              `„${c.text ?? ""}"${mood}`,
          },
        ]);
        if ("Notification" in window && Notification.permission === "granted") {
          new Notification("Jon — Zeitkapsel geöffnet 🎁", {
            body: `Deine Nachricht vom ${written} ist da.`,
          });
        }
      }
    };
    void fire();
    const timer = window.setInterval(() => void fire(), 60000);
    return () => window.clearInterval(timer);
  }, [online]);

  useEffect(() => {
    if (!online || !screenOn) return;
    let stopped = false;
    const tick = async () => {
      if (stopped || streamingRef.current) return;
      const r = await observeScreen(providerRef.current, modelRef.current);
      if (stopped) return;
      const obs = (r.observation || "").trim();
      if (obs && obs !== lastScreenRef.current) {
        lastScreenRef.current = obs;
        setEntries((prev) => [
          ...prev,
          { id: nextId(), role: "assistant", content: `👁️ ${obs}` },
        ]);
      }
    };
    void tick();
    const timer = window.setInterval(() => void tick(), 30000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [online, screenOn]);

  const runVoiceCommand = async (text: string) => {
    if (streamingRef.current) return;
    const listener = listenerRef.current;
    listener?.setBusy(true);
    if (voiceTimerRef.current) window.clearTimeout(voiceTimerRef.current);
    setVoiceDetail(text);
    setVoiceState("processing");
    let answer = "";
    let failed = false;
    const outgoing = [
      ...voiceHistoryRef.current,
      { role: "user" as const, content: text },
    ];
    try {
      await streamChat(
        {
          messages: outgoing,
          provider: providerRef.current,
          model: modelRef.current,
          conversation_id: null,
          persist: false,
          tool_mode: toolModeRef.current,
        },
        {
          onContent: (delta) => {
            answer += delta;
          },
          onTool: handleApprovalEvent,
          onError: (message) => {
            failed = true;
            if (!answer) answer = message;
          },
        }
      );
    } catch {
      failed = true;
    }
    setApproval(null);
    if (!failed && answer) {
      voiceHistoryRef.current = [
        ...outgoing,
        { role: "assistant" as const, content: answer },
      ].slice(-12);
    }
    const snippet = answer.replace(/\s+/g, " ").trim().slice(0, 140) || undefined;
    if (!failed && answer) {
      setVoiceState("speaking");
      setVoiceDetail(snippet);
      listener?.setSpeaking(true, answer);
      await speak(answer);
      listener?.setSpeaking(false);
    }
    listener?.setBusy(false);
    setVoiceState(failed ? "error" : "done");
    setVoiceDetail(snippet);
    voiceTimerRef.current = window.setTimeout(() => {
      setVoiceDetail(undefined);
      setVoiceState(listenerRef.current ? "listening" : "idle");
    }, 8000);
  };

  useEffect(() => {
    initTts();
  }, []);

  useEffect(() => {
    if (!online || !voiceOn) {
      stopSpeaking();
      setVoiceState("idle");
      setVoiceDetail(undefined);
      return;
    }
    let cancelled = false;
    const listener = new VoiceListener({
      onState: (s) => {
        if (cancelled) return;
        if (s === "recording" || s === "armed") setVoiceDetail(undefined);
        setVoiceState((prev) =>
          prev === "processing" || prev === "speaking" ? prev : s
        );
      },
      onCommand: (text) => {
        void runVoiceCommand(text);
      },
      onBargeIn: () => {
        stopSpeaking();
        listenerRef.current?.setSpeaking(false);
        listenerRef.current?.setBusy(false);
        setVoiceState("listening");
      },
    });
    listenerRef.current = listener;
    listener.start().catch(() => {
      if (!cancelled) setVoiceState("idle");
    });
    return () => {
      cancelled = true;
      listenerRef.current = null;
      listener.stop();
    };
  }, [online, voiceOn]);

  const toggleVoice = () => {
    setVoiceOn((v) => {
      const next = !v;
      localStorage.setItem("jon_voice", next ? "1" : "0");
      return next;
    });
  };

  const loadConversation = async (id: string) => {
    setActiveId(id);
    const detail = await getConversation(id);
    setProvider(detail.provider);
    setModel(detail.model);
    setEntries(
      detail.messages
        .filter((m: any) => m.role !== "system")
        .map((m: any) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          reasoning: m.reasoning ?? undefined,
        }))
    );
  };

  const startNew = () => {
    setActiveId(null);
    setEntries([]);
  };

  const removeConversation = async (id: string) => {
    await deleteConversation(id);
    if (id === activeId) startNew();
    await refreshConversations();
  };

  const runDataPrompt = async (
    build: () => Promise<string>,
    userLabel?: string
  ) => {
    if (streamingRef.current) return;
    const assistantEntry: ChatEntry = {
      id: nextId(),
      role: "assistant",
      content: "",
      streaming: true,
      tools: [],
    };
    setEntries((prev) =>
      userLabel
        ? [
            ...prev,
            { id: nextId(), role: "user", content: userLabel },
            assistantEntry,
          ]
        : [...prev, assistantEntry]
    );
    setStreaming(true);
    let prompt: string;
    try {
      prompt = await build();
    } catch (e) {
      setEntries((prev) =>
        prev.map((en) =>
          en.id === assistantEntry.id
            ? {
                ...en,
                content: `[Fehler] ${e instanceof Error ? e.message : String(e)}`,
                streaming: false,
              }
            : en
        )
      );
      setStreaming(false);
      return;
    }
    await streamChat(
      {
        messages: [{ role: "user", content: prompt }],
        provider: providerRef.current,
        model: modelRef.current,
        conversation_id: null,
        persist: false,
        tool_mode: toolModeRef.current,
      },
      {
        onTool: (evt) => {
          handleApprovalEvent(evt);
          setEntries((prev) =>
            prev.map((e) => {
              if (e.id !== assistantEntry.id) return e;
              const tools = [...(e.tools ?? [])];
              if (evt.status === "running") {
                tools.push({
                  name: evt.name ?? "tool",
                  done: false,
                  args: evt.args,
                  summary: evt.summary,
                });
              } else {
                const i = tools.map((t) => t.name).lastIndexOf(evt.name ?? "tool");
                if (i >= 0) tools[i] = { ...tools[i], done: true, ok: evt.ok };
              }
              return { ...e, tools };
            })
          );
        },
        onContent: (delta) =>
          setEntries((prev) =>
            prev.map((e) =>
              e.id === assistantEntry.id
                ? { ...e, content: e.content + delta }
                : e
            )
          ),
        onError: (message) => {
          setApproval(null);
          setEntries((prev) =>
            prev.map((e) =>
              e.id === assistantEntry.id
                ? { ...e, content: e.content + `\n\n[Fehler] ${message}`, streaming: false }
                : e
            )
          );
        },
        onDone: () => {
          setApproval(null);
          setEntries((prev) =>
            prev.map((e) =>
              e.id === assistantEntry.id ? { ...e, streaming: false } : e
            )
          );
          setStreaming(false);
        },
      }
    );
  };

  const runBriefing = () =>
    runDataPrompt(async () => {
      try {
        return briefingPrompt(await getBriefing());
      } catch {
        return BRIEFING_PROMPT;
      }
    });

  const runSlashJob = async (
    commandText: string,
    placeholder: string,
    job: () => Promise<string>
  ) => {
    const userEntry: ChatEntry = {
      id: nextId(),
      role: "user",
      content: commandText,
    };
    const assistantEntry: ChatEntry = {
      id: nextId(),
      role: "assistant",
      content: placeholder,
      streaming: true,
    };
    setEntries((prev) => [...prev, userEntry, assistantEntry]);
    setStreaming(true);
    let result = "";
    try {
      result = await job();
    } catch (e) {
      result = `[Fehler] ${e instanceof Error ? e.message : String(e)}`;
    }
    setEntries((prev) =>
      prev.map((en) =>
        en.id === assistantEntry.id
          ? { ...en, content: result, streaming: false }
          : en
      )
    );
    setStreaming(false);
  };

  const exportChat = () => {
    if (entries.length === 0) return;
    const md = entries
      .filter((e) => e.content.trim() !== "")
      .map((e) => `**${e.role === "user" ? "Du" : "Jon"}:**\n\n${e.content.trim()}`)
      .join("\n\n---\n\n");
    const blob = new Blob([`# Jon — Unterhaltung\n\n${md}\n`], {
      type: "text/markdown;charset=utf-8",
    });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `jon-chat-${new Date().toISOString().slice(0, 10)}.md`;
    link.click();
    URL.revokeObjectURL(link.href);
  };

  const send = async (text: string, attachments: PendingAttachment[] = []) => {
    const command = text.trim().toLowerCase();
    if (command === "/usage" || command === "/nutzung") {
      setAccountsTab("usage");
      return;
    }
    if (command === "/clipboard" || command === "/zwischenablage") {
      setClipboardOpen(true);
      return;
    }
    if (command === "/human" || command === "/humanize") {
      setHumanizerOpen(true);
      return;
    }
    if (command === "/download" || command === "/dl") {
      setDownloaderOpen(true);
      return;
    }
    if (command === "/show" || command === "/abendshow") {
      setShowOpen(true);
      return;
    }
    if (command === "/spiel" || command === "/blockwelt" || command === "/game") {
      window.open(blockweltUrl(), "_blank");
      return;
    }
    if (command === "/tagebuch" || command === "/journal") {
      setJournalOpen(true);
      return;
    }
    if (command === "/aufraeumen" || command === "/cleanup") {
      setCleanupOpen(true);
      return;
    }
    if (command === "/kochen" || command === "/rezept") {
      setRecipeOpen(true);
      return;
    }
    if (command === "/lernen" || command === "/karten" || command === "/quiz") {
      setFlashcardsOpen(true);
      return;
    }
    if (command === "/erklaer" || command === "/erklaere" || command === "/screen") {
      setExplainOpen(true);
      return;
    }
    if (command === "/notizen" || command === "/notes") {
      setNotesOpen(true);
      return;
    }
    if (command === "/tresor" || command === "/vault" || command === "/passwort") {
      setVaultOpen(true);
      return;
    }
    if (command === "/suche" || command === "/search" || command === "/find") {
      setSearchOpen(true);
      return;
    }
    if (command === "/check" || command === "/pc") {
      void runDataPrompt(
        async () => CHECK_PROMPT(await getHealthCheck()),
        text
      );
      return;
    }
    if (command === "/woche" || command === "/weekly" || command === "/week") {
      void runDataPrompt(async () => WEEKLY_PROMPT(await getWeekly()), text);
      return;
    }
    if (command === "/tasks" || command === "/automationen") {
      void runSlashJob(text, "🤖 Lade Automationen …", async () => {
        const tasks = await getTasks();
        if (!tasks.length)
          return "Keine Automationen geplant. Sag mir einfach: „Räum jeden Tag um 18 Uhr meinen Downloads-Ordner auf“ — ich erledige das dann wirklich.";
        return (
          "**🤖 Deine Automationen:**\n\n" +
          tasks
            .map(
              (t) =>
                `- **${t.time}** · ${t.repeat} · ${t.task}${
                  t.active ? "" : " _(inaktiv)_"
                }${t.last_run_at ? `\n  Zuletzt: ${new Date(t.last_run_at).toLocaleString("de-DE")}` : ""}`
            )
            .join("\n")
        );
      });
      return;
    }
    if (command === "/konten" || command === "/accounts" || command === "/login") {
      setAccountsTab("accounts");
      return;
    }
    if (command === "/skills") {
      setAccountsTab("skills");
      return;
    }
    if (command === "/briefing") {
      void runBriefing();
      return;
    }
    if (command === "/meeting" || command === "/mitschrift") {
      const st = await meetingStatus();
      if (st.running) {
        void runSlashJob(text, "📝 Beende Mitschrift und fasse zusammen …", async () => {
          const r = await meetingStop();
          if (r.error) return `Das ging nicht: ${r.error}`;
          const todos =
            r.todos && r.todos.length
              ? "\n\n**✅ In den Kalender eingetragen:**\n" +
                r.todos.map((t: string) => `- ${t}`).join("\n")
              : "";
          return `**📝 Meeting-Zusammenfassung**\n\n${r.zusammenfassung || "—"}${todos}`;
        });
      } else {
        const r = await meetingStart();
        if (r.error) {
          setEntries((prev) => [
            ...prev,
            { id: nextId(), role: "user", content: text },
            { id: nextId(), role: "assistant", content: `Das ging nicht: ${r.error}` },
          ]);
        } else {
          setEntries((prev) => [
            ...prev,
            { id: nextId(), role: "user", content: text },
            {
              id: nextId(),
              role: "assistant",
              content: `🔴 Mitschrift läuft (Mikro: ${r.mikrofon}). Ich höre System-Ton und dein Mikrofon mit. Schreib nochmal \`/meeting\`, um zu stoppen und eine Zusammenfassung mit To-dos zu bekommen.`,
            },
          ]);
        }
      }
      return;
    }
    if (command === "/fokus" || command === "/focus" || command === "/stats") {
      void runSlashJob(text, "📊 Werte deine App-Zeiten aus …", async () => {
        const r = await getAppUsage(7);
        if (!r.apps.length)
          return "Noch keine App-Zeiten erfasst. Aktiviere „App-Nutzung erfassen“ im Zahnrad-Menü — dann sehe ich, wo deine Zeit hingeht (alles bleibt lokal).";
        const max = r.apps[0].minuten || 1;
        const fmt = (m: number) =>
          m >= 60 ? `${Math.floor(m / 60)} h ${Math.round(m % 60)} min` : `${Math.round(m)} min`;
        const bars = r.apps
          .map((a) => {
            const filled = Math.max(1, Math.round((a.minuten / max) * 16));
            return `\`${"█".repeat(filled)}${"░".repeat(16 - filled)}\` **${a.app}** · ${fmt(a.minuten)}`;
          })
          .join("\n");
        return (
          `**📊 Deine App-Zeiten (letzte 7 Tage)**\n\nGesamt: ${fmt(r.gesamt_minuten)}\n\n${bars}\n\n` +
          "_Nur lokal erfasst. Abschaltbar im Zahnrad-Menü._"
        );
      });
      return;
    }
    if (command === "/kalender" || command === "/calendar") {
      void runSlashJob(text, "📅 Lade Kalender …", async () => {
        const events = await getCalendar("", 7);
        if (!events.length)
          return "Die nächsten 7 Tage sind frei. 📅 öffnet den Kalender — oder sag mir einfach: „Trag Freitag 15 Uhr Zahnarzt ein.“";
        const byDay = new Map<string, typeof events>();
        for (const e of events) {
          const list = byDay.get(e.datum) ?? [];
          list.push(e);
          byDay.set(e.datum, list);
        }
        const icons: Record<string, string> = {
          jon: "🟡",
          automation: "🤖",
          erinnerung: "🔔",
          ics: "🔵",
        };
        return (
          "**📅 Deine nächsten 7 Tage:**\n\n" +
          [...byDay.entries()]
            .map(
              ([day, list]) =>
                `**${new Date(day).toLocaleDateString("de-DE", { weekday: "long", day: "2-digit", month: "2-digit" })}**\n` +
                list
                  .map(
                    (e) =>
                      `- ${icons[e.quelle] ?? "▪️"} ${e.zeit ? `${e.zeit} · ` : ""}${e.erledigt ? `~~${e.titel}~~` : e.titel}`
                  )
                  .join("\n")
            )
            .join("\n\n")
        );
      });
      return;
    }
    if (command === "/undo") {
      void runSlashJob(text, "↩️ Stelle wieder her …", async () => {
        const r = await undoTrash();
        return r.error
          ? `Das ging nicht: ${r.error}`
          : `↩️ Wiederhergestellt: \`${r.restored}\``;
      });
      return;
    }
    if (command === "/papierkorb" || command === "/trash") {
      void runSlashJob(text, "🗑️ Lade Papierkorb …", async () => {
        const items = await getTrash();
        trashListRef.current = items.map((e) => e.id);
        if (!items.length)
          return "Der Papierkorb ist leer. Gelöschte, überschriebene und verschobene Dateien landen hier und bleiben 30 Tage erhalten.";
        return (
          "**🗑️ Papierkorb** (wird nach 30 Tagen geleert):\n\n" +
          items
            .slice(0, 20)
            .map(
              (e, i) =>
                `${i + 1}. **${e.name || "?"}** · ${e.action} · ${(e.deleted_at ?? "").replace("T", " ")}\n   \`${e.original}\``
            )
            .join("\n") +
          "\n\nWiederherstellen: `/restore <Nummer>` — oder `/undo` für die letzte Aktion."
        );
      });
      return;
    }
    if (command === "/export") {
      exportChat();
      return;
    }
    if (command === "/update") {
      const id = Date.now().toString();
      setEntries((prev) => [
        ...prev,
        { id: `u-${id}`, role: "user", content: text },
        { id: `s-${id}`, role: "assistant", content: t("update_progress") },
      ]);
      const appendTo = (extra: string) =>
        setEntries((prev) =>
          prev.map((e) =>
            e.id === `s-${id}` ? { ...e, content: e.content + extra } : e
          )
        );
      try {
        const res = await fetch(`${BASE}/update`, { method: "POST" });
        if (res.status === 405 || res.status === 404) {
          appendTo(
            "\n⚠️ Dein Backend läuft noch mit einer älteren Version und kennt " +
              "das Update noch nicht.\nStarte Jon einmal neu (start-jon.bat) — " +
              "danach funktioniert /update.\nAuf dem Raspberry Pi: `sudo " +
              "systemctl restart jon`."
          );
          return;
        }
        if (!res.ok || !res.body) {
          const detail = await res.text().catch(() => "");
          throw new Error(detail || `HTTP ${res.status}`);
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          appendTo(decoder.decode(value, { stream: true }));
        }
      } catch (err) {
        appendTo(
          `\n❌ Fehler: ${err instanceof Error ? err.message : String(err)}`
        );
      }
      return;
    }
    const arg = text.trim().slice(text.trim().indexOf(" ") + 1).trim();
    if (command.startsWith("/restore") || command.startsWith("/wiederherstellen")) {
      void runSlashJob(text, "↩️ Stelle wieder her …", async () => {
        const nr = parseInt(arg, 10);
        const id = trashListRef.current[nr - 1];
        if (!id)
          return "Nutzung: erst `/papierkorb` anzeigen, dann `/restore <Nummer>`.";
        const r = await restoreTrash(id);
        return r.error
          ? `Das ging nicht: ${r.error}`
          : `↩️ Wiederhergestellt: \`${r.restored}\``;
      });
      return;
    }
    if (command.startsWith("/log")) {
      void runSlashJob(text, "📜 Lade Aktionsprotokoll …", async () => {
        const known = ["app", "mini-jon", "telegram", "automation", "watcher"];
        let source = "";
        let day = "";
        if (command !== "/log") {
          for (const part of arg.split(/\s+/)) {
            const val = part.toLowerCase();
            if (known.includes(val)) source = val;
            else if (val === "mini" || val === "emil") source = "mini-jon";
            else if (val) day = val;
          }
        }
        const actions = await getActions(source, day, 30);
        if (!actions.length)
          return source || day
            ? "Keine Aktionen im Protokoll für diesen Filter."
            : "Das Aktionsprotokoll ist noch leer.";
        const icons: Record<string, string> = {
          app: "💻",
          "mini-jon": "🙂",
          telegram: "✈️",
          automation: "🤖",
          watcher: "👀",
        };
        return (
          "**📜 Aktionsprotokoll** (neueste zuerst):\n\n" +
          actions
            .map(
              (a) =>
                `- ${a.ok ? "✅" : "❌"} ${icons[a.source] ?? "▪️"} \`${a.tool}\` · ${a.created_at.replace("T", " ").slice(0, 16)}${a.args ? `\n  ${a.args.slice(0, 110)}` : ""}`
            )
            .join("\n") +
          "\n\nFilter: `/log telegram`, `/log automation heute`, `/log gestern`"
        );
      });
      return;
    }
    if (command.startsWith("/webcam") || command.startsWith("/kamera")) {
      void runSlashJob(text, "📷 Jon schaut durch die Webcam …", async () => {
        const question =
          command === "/webcam" || command === "/kamera" ? "" : arg;
        const r = await observeWebcam(question);
        if (r.error) return `Das hat nicht geklappt: ${r.error}`;
        return `📷 ${r.beschreibung ?? ""}`;
      });
      return;
    }
    if (command.startsWith("/team")) {
      void runSlashJob(text, "🧑‍🤝‍🧑 KI-Team berät …", async () => {
        if (!arg || command === "/team") return "Nutzung: /team <Frage oder Thema>";
        const r = await runTeam(arg, providerRef.current, modelRef.current);
        const voices = r.voices
          .map((v) => `${v.emoji} **${v.role} (${v.name}):** ${v.text}`)
          .join("\n\n");
        return `${voices}\n\n---\n\n**🧭 Jons Empfehlung:**\n\n${r.recommendation}`;
      });
      return;
    }
    if (command.startsWith("/simulate") || command.startsWith("/simuliere")) {
      void runSlashJob(text, "🔮 Jon simuliert …", async () => {
        if (!arg || command === "/simulate" || command === "/simuliere")
          return "Nutzung: /simulate <Was wäre wenn …>";
        const r = await runSimulation(arg, providerRef.current, modelRef.current);
        return r.result;
      });
      return;
    }
    if (command === "/snapshots" || command === "/zeitreise") {
      void runSlashJob(text, "⏳ Lade Snapshots …", async () => {
        const snaps = await listSnapshots();
        if (!snaps.length)
          return "Noch keine Snapshots. Erstelle einen mit `/snapshot <Name>` oder bitte Jon darum.";
        return (
          "**⏳ Deine Zeitreise-Snapshots:**\n\n" +
          snaps
            .map(
              (s) =>
                `- **${s.label}** · ${new Date(s.created_at).toLocaleString(
                  "de-DE"
                )}${s.files ? ` · ${s.files} Dateien` : ""}${
                  s.note ? `\n  ${s.note}` : ""
                }`
            )
            .join("\n")
        );
      });
      return;
    }
    if (command.startsWith("/snapshot")) {
      void runSlashJob(text, "⏳ Speichere Snapshot …", async () => {
        const label = arg || `Snapshot ${new Date().toLocaleString("de-DE")}`;
        const s = await createSnapshot(label);
        return `⏳ Snapshot **${s.label}** gespeichert. Mit \`/snapshots\` siehst du alle.`;
      });
      return;
    }
    if (command === "/dreams" || command === "/traeume") {
      void runSlashJob(text, "🌙 Jon arbeitet an deinen Dream-Aufgaben …", async () => {
        const r = await runDreams();
        if (!r.started) return "Es gibt gerade keine offenen Dream-Aufgaben.";
        const reports = await getDreamReports();
        if (!reports.length) return "Fertig, aber es gab nichts zu berichten.";
        return (
          "**🌙 Ergebnisse aus dem Dream Mode:**\n\n" +
          reports.map((t) => `**${t.task}**\n\n${t.result}`).join("\n\n---\n\n")
        );
      });
      return;
    }
    if (command.startsWith("/dream") || command.startsWith("/traum")) {
      void runSlashJob(text, "🌙 Lege Dream-Aufgabe an …", async () => {
        if (!arg) return "Nutzung: /dream <Aufgabe, die Jon im Hintergrund erledigen soll>";
        await addDream(arg);
        return `🌙 Notiert. Ich arbeite daran, wenn du weg bist – oder starte es sofort mit \`/dreams\`.`;
      });
      return;
    }
    const attachmentText = attachments.length
      ? attachments
          .map(
            (a) =>
              `[Anhang „${a.name}" (${a.kind === "image" ? "Bildbeschreibung" : a.kind})]\n${a.content ?? ""}`
          )
          .join("\n\n")
      : undefined;
    const userEntry: ChatEntry = {
      id: nextId(),
      role: "user",
      content: text,
      attachments: attachments.map((a) => ({ name: a.name, kind: a.kind })),
      attachmentText,
    };
    const assistantEntry: ChatEntry = {
      id: nextId(),
      role: "assistant",
      content: "",
      streaming: true,
      tools: [],
    };
    const history = [...entries, userEntry];
    setEntries([...history, assistantEntry]);
    setStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    const messages = history
      .filter(
        (e) =>
          e.content.trim() !== "" ||
          (e.tools?.length ?? 0) > 0 ||
          !!e.attachmentText
      )
      .map((e) => {
        let content =
          e.content.trim() !== ""
            ? e.content
            : (e.tools?.length ?? 0) > 0
              ? `[Bereits erledigt: ${(e.tools ?? [])
                  .map((t) => t.summary ?? t.name)
                  .join("; ")}]`
              : "";
        if (e.attachmentText)
          content = content
            ? `${content}\n\n${e.attachmentText}`
            : e.attachmentText;
        return { role: e.role, content };
      });

    let convId = activeId;

    await streamChat(
      { messages, provider, model, conversation_id: activeId, tool_mode: toolMode },
      {
        onMeta: (e) => {
          if (e.conversation_id) convId = e.conversation_id;
        },
        onReasoning: (delta) =>
          setEntries((prev) =>
            prev.map((e) =>
              e.id === assistantEntry.id
                ? { ...e, reasoning: (e.reasoning ?? "") + delta }
                : e
            )
          ),
        onTool: (evt) => {
          handleApprovalEvent(evt);
          setEntries((prev) =>
            prev.map((e) => {
              if (e.id !== assistantEntry.id) return e;
              const tools = [...(e.tools ?? [])];
              if (evt.status === "running") {
                tools.push({
                  name: evt.name ?? "tool",
                  done: false,
                  args: evt.args,
                  summary: evt.summary,
                });
              } else {
                const i = tools.map((t) => t.name).lastIndexOf(evt.name ?? "tool");
                if (i >= 0) tools[i] = { ...tools[i], done: true, ok: evt.ok };
              }
              return { ...e, tools };
            })
          );
        },
        onContent: (delta) =>
          setEntries((prev) =>
            prev.map((e) =>
              e.id === assistantEntry.id
                ? { ...e, content: e.content + delta }
                : e
            )
          ),
        onError: (message) => {
          setApproval(null);
          setEntries((prev) =>
            prev.map((e) =>
              e.id === assistantEntry.id
                ? { ...e, content: e.content + `\n\n[Fehler] ${message}`, streaming: false }
                : e
            )
          );
        },
        onDone: async () => {
          setApproval(null);
          setEntries((prev) =>
            prev.map((e) =>
              e.id === assistantEntry.id ? { ...e, streaming: false } : e
            )
          );
          setStreaming(false);
          if (convId && convId !== activeId) setActiveId(convId);
          await refreshConversations();
        },
      },
      controller.signal
    );
  };

  const stop = () => {
    abortRef.current?.abort();
    setStreaming(false);
    setApproval(null);
    setEntries((prev) =>
      prev.map((e) => (e.streaming ? { ...e, streaming: false } : e))
    );
  };

  return (
    <div className="flex flex-col h-screen">
      <TitleBar />
      <div className="flex flex-1 min-h-0">
        <Sidebar
          conversations={conversations}
          activeId={activeId}
          version={version}
          onSelect={loadConversation}
          onNew={startNew}
          onDelete={removeConversation}
        />
        <main className="flex-1 flex flex-col min-w-0">
          <div className="flex items-center justify-between px-6 h-14 border-b border-white/10">
            <ModelPicker
              providers={providers}
              provider={provider}
              model={model}
              onChange={changeModel}
            />
            <div className="flex items-center gap-3 text-xs">
              {jonDesktop?.togglePet && (
                <div className="flex items-center rounded-full border border-gold/30 bg-gold/10 text-gold/90 overflow-hidden">
                  <button
                    onClick={() => jonDesktop.togglePet?.()}
                    title="Mini Jon auf dem Bildschirm ein/aus (Strg+Alt+K)"
                    className="flex items-center gap-1.5 pl-2.5 pr-2 h-7 hover:bg-gold/20 transition-colors"
                  >
                    <span className="text-[13px] leading-none">🙂</span>
                    <span className="text-[11px] font-medium">{t("header_mini_jon")}</span>
                  </button>
                  <button
                    onClick={() => setPetConfigOpen(true)}
                    title="Mini Jon anpassen"
                    className="flex items-center justify-center w-7 h-7 border-l border-gold/30 hover:bg-gold/20 transition-colors"
                  >
                    <span className="text-[12px] leading-none">🎨</span>
                  </button>
                </div>
              )}
              <button
                onClick={() => setCalendarOpen(true)}
                title="Jons Kalender — Termine, Tasks und Erinnerungen"
                className="flex items-center gap-1 px-2.5 h-7 rounded-full border border-white/10 bg-white/5 text-white/40 hover:text-white/70 transition-colors"
              >
                <span className="text-[12px] leading-none">📅</span>
                <span className="text-[11px] font-medium">{t("header_calendar")}</span>
              </button>
              <div className="relative">
                <button
                  onClick={() => setToolsMenuOpen((v) => !v)}
                  title="Werkzeuge & Apps"
                  className={`relative flex items-center gap-1 px-2.5 h-7 rounded-full border transition-colors ${
                    toolsMenuOpen
                      ? "border-gold/40 bg-gold/10 text-gold"
                      : "border-white/10 bg-white/5 text-white/40 hover:text-white/70"
                  }`}
                >
                  <span className="text-[12px] leading-none">🧰</span>
                  <span className="text-[11px] font-medium">{t("header_tools")}</span>
                  {unread > 0 && !toolsMenuOpen && (
                    <span className="absolute -top-1 -right-1 min-w-[15px] h-[15px] px-1 rounded-full bg-gold text-black text-[9px] font-bold flex items-center justify-center">
                      {unread}
                    </span>
                  )}
                </button>
                {toolsMenuOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setToolsMenuOpen(false)} />
                    <div className="absolute right-0 top-9 z-50 w-56 glass rounded-xl border border-white/15 p-1.5 text-left max-h-[calc(100vh-6rem)] overflow-y-auto overscroll-contain">
                      {([
                        {
                          title: t("tools_work"),
                          items: [
                            { icon: "🔎", label: "Alles durchsuchen", hint: "Strg+K", act: () => setSearchOpen(true) },
                            { icon: "</>", label: "Jon Code", act: () => setCodeOpen(true) },
                            { icon: "✍️", label: "Humanisierer", act: () => setHumanizerOpen(true) },
                            { icon: "📌", label: "Haftnotizen", act: () => setNotesOpen(true) },
                            { icon: "🔒", label: "Passwort-Tresor", act: () => setVaultOpen(true) },
                            { icon: "📔", label: "Sprach-Tagebuch", act: () => setJournalOpen(true) },
                            { icon: "🎴", label: "Lern-Karteikarten", act: () => setFlashcardsOpen(true) },
                          ],
                        },
                        {
                          title: t("tools_pc"),
                          items: [
                            { icon: "🔍", label: "Bildschirm erklären", hint: "Strg+Alt+E", act: () => setExplainOpen(true) },
                            { icon: "🧹", label: "Ordner aufräumen", act: () => setCleanupOpen(true) },
                            { icon: "⬇️", label: "Downloader", act: () => setDownloaderOpen(true) },
                            { icon: "🍳", label: "Kochassistent", act: () => setRecipeOpen(true) },
                            { icon: "📋", label: "Clipboard-Historie", act: () => setClipboardOpen(true) },
                          ],
                        },
                        {
                          title: t("tools_fun"),
                          items: [
                            { icon: "🎙️", label: "Abend-Show", act: () => setShowOpen(true) },
                            { icon: "🎮", label: "Blockwelt-Spiel", act: () => window.open(blockweltUrl(), "_blank") },
                            { icon: "💬", label: "Freunde-Chat", badge: unread, act: () => setFriendsOpen(true) },
                            { icon: "👤", label: "Konten & Nutzung", act: () => setAccountsTab("accounts") },
                          ],
                        },
                      ] as {
                        title: string;
                        items: {
                          icon: string;
                          label: string;
                          hint?: string;
                          badge?: number;
                          act: () => void;
                        }[];
                      }[]).map((group) => (
                        <div key={group.title} className="mb-1 last:mb-0">
                          <div className="text-[9px] uppercase tracking-wider text-white/30 px-2.5 pt-1.5 pb-1">
                            {group.title}
                          </div>
                          {group.items.map((it) => (
                            <button
                              key={it.label}
                              onClick={() => { it.act(); setToolsMenuOpen(false); }}
                              className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-white/75 hover:bg-white/10 hover:text-white transition-colors text-left"
                            >
                              <span className="text-[13px] w-5 text-center">{it.icon}</span>
                              <span className="text-[12px] flex-1">{it.label}</span>
                              {it.badge ? (
                                <span className="min-w-[15px] h-[15px] px-1 rounded-full bg-gold text-black text-[9px] font-bold flex items-center justify-center">
                                  {it.badge}
                                </span>
                              ) : it.hint ? (
                                <span className="text-[9.5px] text-white/30">{it.hint}</span>
                              ) : null}
                            </button>
                          ))}
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
              <button
                onClick={toggleScreen}
                title={screenOn ? t("live_screen_on") : t("live_screen_off")}
                className={`flex items-center justify-center w-7 h-7 rounded-full border transition-colors ${
                  screenOn
                    ? "border-sky-400/40 bg-sky-400/10 text-sky-300"
                    : "border-white/10 bg-white/5 text-white/30"
                }`}
              >
                <svg
                  width="13"
                  height="13"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" />
                  <circle cx="12" cy="12" r="3" />
                  {!screenOn && <line x1="3" y1="3" x2="21" y2="21" />}
                </svg>
              </button>
              <SettingsMenu toolMode={toolMode} onToolModeChange={changeToolMode} />
              <button
                onClick={toggleVoice}
                title={
                  voiceOn
                    ? "Sprachsteuerung an — sag „Jon“, um zu sprechen"
                    : "Sprachsteuerung aus"
                }
                className={`flex items-center justify-center w-7 h-7 rounded-full border transition-colors ${
                  voiceOn
                    ? "border-amber-400/40 bg-amber-400/10 text-amber-300"
                    : "border-white/10 bg-white/5 text-white/30"
                }`}
              >
                <svg
                  width="13"
                  height="13"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect x="9" y="2" width="6" height="12" rx="3" />
                  <path d="M5 10a7 7 0 0 0 14 0" />
                  <line x1="12" y1="19" x2="12" y2="22" />
                  {!voiceOn && <line x1="3" y1="3" x2="21" y2="21" />}
                </svg>
              </button>
              <div className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full ${
                    online ? "bg-emerald-400" : "bg-red-400"
                  }`}
                />
                <span className="text-white/50">
                  {online ? "Verbunden" : "Backend offline"}
                </span>
              </div>
            </div>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
            <RoutineBanner />
            {entries.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center">
                <h1 className="text-4xl font-bold gold-text mb-3">
                  {t("empty_title")}
                </h1>
                <p className="text-white/40 max-w-md">{t("empty_hint")}</p>
              </div>
            )}
            {entries.map((e) => (
              <MessageBubble key={e.id} entry={e} />
            ))}
          </div>

          <Composer
            disabled={!online || streaming}
            streaming={streaming}
            onSend={send}
            onStop={stop}
          />
        </main>
      </div>
      <VoiceIndicator state={voiceState} detail={voiceDetail} />
      {approval && (
        <ApprovalDialog request={approval} onDecide={decideApproval} />
      )}
      {accountsTab && (
        <AccountsModal
          initialTab={accountsTab}
          onClose={() => setAccountsTab(null)}
        />
      )}
      {codeOpen && (
        <CodeAgent
          providers={providers}
          provider={provider}
          model={model}
          onModelChange={changeModel}
          onClose={() => setCodeOpen(false)}
        />
      )}
      {humanizerOpen && (
        <Humanizer
          provider={provider}
          model={model}
          onClose={() => setHumanizerOpen(false)}
        />
      )}
      {downloaderOpen && <Downloader onClose={() => setDownloaderOpen(false)} />}
      {showOpen && (
        <EveningShow
          provider={provider}
          model={model}
          onClose={() => setShowOpen(false)}
        />
      )}
      {journalOpen && <Journal onClose={() => setJournalOpen(false)} />}
      {cleanupOpen && <Cleanup onClose={() => setCleanupOpen(false)} />}
      {recipeOpen && <Recipe onClose={() => setRecipeOpen(false)} />}
      {flashcardsOpen && <Flashcards onClose={() => setFlashcardsOpen(false)} />}
      {explainOpen && <ScreenExplain onClose={() => setExplainOpen(false)} />}
      {notesOpen && <Notes onClose={() => setNotesOpen(false)} />}
      {vaultOpen && <Vault onClose={() => setVaultOpen(false)} />}
      {searchOpen && (
        <Search
          onOpenConversation={(id) => void loadConversation(id)}
          onClose={() => setSearchOpen(false)}
        />
      )}
      {petConfigOpen && <PetConfig onClose={() => setPetConfigOpen(false)} />}
      {clipboardOpen && (
        <ClipboardPanel
          onClose={() => setClipboardOpen(false)}
          onAsk={(text) => {
            setClipboardOpen(false);
            void send(text);
          }}
        />
      )}
      {friendsOpen && identity && (
        <FriendsChat
          identity={identity}
          initialPeerId={friendsPeer}
          onEditProfile={() => setProfileOpen(true)}
          onClose={() => {
            setFriendsOpen(false);
            setFriendsPeer(null);
          }}
        />
      )}
      {friendRequests.length > 0 && (
        <FriendRequestPopup
          request={friendRequests[0]}
          busy={requestBusy}
          error={requestError}
          onDecide={(action) => void decideRequest(action)}
        />
      )}
      {update && (
        <div className="fixed bottom-4 right-4 z-40 glass rounded-2xl border border-gold/30 px-4 py-3 flex items-center gap-3 max-w-[340px]">
          <span className="text-xl">🚀</span>
          <div className="flex-1 min-w-0">
            <div className="text-[13px] text-white/90">
              Version {update.latest} ist da
            </div>
            <div className="text-[11px] text-white/45">
              Du nutzt eine ältere Version von Jon.
            </div>
          </div>
          <div className="flex flex-col gap-1.5 items-end">
            <button
              onClick={() => {
                setUpdate(null);
                void send("/update");
              }}
              className="px-2.5 py-1 rounded-lg bg-gold/15 text-gold text-[11px] hover:bg-gold/25 font-semibold"
            >
              Auto-Update
            </button>
            <div className="flex items-center gap-3">
              <a
                href={update.url}
                target="_blank"
                rel="noreferrer"
                className="text-[10px] text-white/45 hover:text-white/70"
              >
                Manuell
              </a>
              <button
                onClick={() => setUpdate(null)}
                className="text-white/30 hover:text-white/70 text-[12px]"
              >
                ✕
              </button>
            </div>
          </div>
        </div>
      )}
      {calendarOpen && <CalendarPanel onClose={() => setCalendarOpen(false)} />}
      {setupOpen && <SetupWizard onDone={() => setSetupOpen(false)} />}
      {profileOpen && identity && (
        <ProfileModal
          identity={identity}
          firstRun={firstRun}
          onSaved={(next) => {
            setIdentity(next);
            setProfileOpen(false);
            setFirstRun(false);
          }}
          onClose={() => setProfileOpen(false)}
        />
      )}
    </div>
  );
}
