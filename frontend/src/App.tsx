import { useEffect, useRef, useState } from "react";
import TitleBar from "./components/TitleBar";
import Sidebar from "./components/Sidebar";
import MessageBubble, { ChatEntry } from "./components/MessageBubble";
import Composer from "./components/Composer";
import ModelPicker from "./components/ModelPicker";
import VoiceIndicator, { VoiceUiState } from "./components/VoiceIndicator";
import ApprovalDialog, { ApprovalRequest } from "./components/ApprovalDialog";
import SettingsMenu from "./components/SettingsMenu";
import { VoiceListener } from "./lib/voice";
import { initTts, speak, stopSpeaking } from "./lib/tts";
import {
  ConversationSummary,
  ProviderStatus,
  StreamEvent,
  ToolMode,
  approveTool,
  deleteConversation,
  getConversation,
  getConversations,
  getHealth,
  getProviders,
  streamChat,
} from "./lib/api";

let idc = 0;
const nextId = () => `m${Date.now()}_${idc++}`;

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
    (async () => {
      try {
        const health = await getHealth();
        setOnline(true);
        setProvider(health.default_provider);
        setModel(health.default_model);
        const provs = await getProviders();
        setProviders(provs);
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
        await refreshConversations();
      } catch {
        setOnline(false);
      }
    })();
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [entries]);

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

  const send = async (text: string) => {
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

    const messages = history.map((e) => ({
      role: e.role,
      content: e.content,
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
              onChange={(p, m) => {
                setProvider(p);
                setModel(m);
              }}
            />
            <div className="flex items-center gap-3 text-xs">
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
    </div>
  );
}
