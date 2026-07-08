import { useEffect, useRef, useState } from "react";
import TitleBar from "./components/TitleBar";
import Sidebar from "./components/Sidebar";
import MessageBubble, { ChatEntry } from "./components/MessageBubble";
import Composer from "./components/Composer";
import ModelPicker from "./components/ModelPicker";
import VoiceIndicator, { VoiceUiState } from "./components/VoiceIndicator";
import ApprovalDialog, { ApprovalRequest } from "./components/ApprovalDialog";
import SettingsMenu from "./components/SettingsMenu";
import AccountsModal from "./components/AccountsModal";
import CodeAgent from "./components/CodeAgent";
import PetConfig from "./components/PetConfig";
import { VoiceListener } from "./lib/voice";
import { initTts, speak, stopSpeaking } from "./lib/tts";
import {
  ConversationSummary,
  ProviderStatus,
  StreamEvent,
  ToolMode,
  addDream,
  approveTool,
  createSnapshot,
  deleteConversation,
  getConversation,
  getConversations,
  getDreamReports,
  getDueReminders,
  getHealth,
  getProviders,
  getUserSettings,
  listSnapshots,
  observeScreen,
  saveUserSettings,
  runDreams,
  runSimulation,
  runTeam,
  streamChat,
} from "./lib/api";

const jonDesktop = (window as unknown as {
  jon?: { togglePet?: () => void };
}).jon;

let idc = 0;
const nextId = () => `m${Date.now()}_${idc++}`;

const BRIEFING_PROMPT =
  "Erstelle ein kurzes Tagesbriefing: Begrüße den Nutzer passend zur Tageszeit, " +
  "nenne Wochentag und Datum (system_info). Hole das Wetter für die Stadt des " +
  "Nutzers (recall nach der Stadt; ist keine gespeichert, lass das Wetter weg und " +
  "bitte ihn freundlich, dir einmal seine Stadt zu nennen). Nenne fällige " +
  "Erinnerungen (list_reminders) und gestellte Wecker (list_alarms), falls " +
  "vorhanden. Maximal 8 kurze Zeilen.";

export default function App() {
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
  const [petConfigOpen, setPetConfigOpen] = useState(false);
  const [screenOn, setScreenOn] = useState(
    () => localStorage.getItem("jon_screen") === "1"
  );
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
        (p) => p.provider === saved.provider && p.configured
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
      await refreshConversations();
      const today = new Date().toISOString().slice(0, 10);
      if (localStorage.getItem("jon_briefing") !== today) {
        localStorage.setItem("jon_briefing", today);
        void runBriefing();
      }
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
      await speak(answer);
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

  const runBriefing = async () => {
    if (streamingRef.current) return;
    const assistantEntry: ChatEntry = {
      id: nextId(),
      role: "assistant",
      content: "",
      streaming: true,
      tools: [],
    };
    setEntries((prev) => [...prev, assistantEntry]);
    setStreaming(true);
    await streamChat(
      {
        messages: [{ role: "user", content: BRIEFING_PROMPT }],
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

  const send = async (text: string) => {
    const command = text.trim().toLowerCase();
    if (command === "/usage" || command === "/nutzung") {
      setAccountsTab("usage");
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
    if (command === "/export") {
      exportChat();
      return;
    }
    const arg = text.trim().slice(text.trim().indexOf(" ") + 1).trim();
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
    const userEntry: ChatEntry = { id: nextId(), role: "user", content: text };
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
      .filter((e) => e.content.trim() !== "" || (e.tools?.length ?? 0) > 0)
      .map((e) => ({
        role: e.role,
        content:
          e.content.trim() !== ""
            ? e.content
            : `[Bereits erledigt: ${(e.tools ?? [])
                .map((t) => t.summary ?? t.name)
                .join("; ")}]`,
      }));

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
                    title="Kleiner Jon auf dem Bildschirm ein/aus (Strg+Alt+K)"
                    className="flex items-center gap-1.5 pl-2.5 pr-2 h-7 hover:bg-gold/20 transition-colors"
                  >
                    <span className="text-[13px] leading-none">🙂</span>
                    <span className="text-[11px] font-medium">Mini Jon</span>
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
                onClick={() => setCodeOpen(true)}
                title="Jon Code — Coding-Agent im Editor"
                className="flex items-center gap-1.5 px-2.5 h-7 rounded-full border border-gold/30 bg-gold/10 text-gold/90 hover:bg-gold/20 transition-colors"
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
                  <polyline points="16 18 22 12 16 6" />
                  <polyline points="8 6 2 12 8 18" />
                </svg>
                <span className="text-[11px] font-medium">Code</span>
              </button>
              <button
                onClick={() => setAccountsTab("accounts")}
                title="Konten, Nutzung & Skills"
                className="flex items-center justify-center w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/40 hover:text-white/70 transition-colors"
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
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              </button>
              <button
                onClick={toggleScreen}
                title={
                  screenOn
                    ? "Live Screen an — Jon schaut mit und meldet sich, wenn er etwas Hilfreiches sieht"
                    : "Live Screen aus"
                }
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
            {entries.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center">
                <h1 className="text-4xl font-bold gold-text mb-3">Jon</h1>
                <p className="text-white/40 max-w-md">
                  Dein moderner KI-Desktop-Assistent. Wähle ein Modell und beginne
                  eine Unterhaltung.
                </p>
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
      {petConfigOpen && <PetConfig onClose={() => setPetConfigOpen(false)} />}
    </div>
  );
}
