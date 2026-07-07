import { useEffect, useRef, useState } from "react";
import MessageBubble, { ChatEntry } from "./MessageBubble";
import {
  FileEntry,
  ProviderStatus,
  listDir,
  openInVscode,
  readWorkspaceFile,
  streamChat,
  writeWorkspaceFile,
} from "../lib/api";

let cid = 0;
const nid = () => `ca${Date.now()}_${cid++}`;

const jonBridge = (window as unknown as {
  jon?: { pickFolder?: () => Promise<string | null>; openVscode?: (f: string) => Promise<boolean> };
}).jon;

interface Props {
  providers: ProviderStatus[];
  provider: string;
  model: string;
  onModelChange: (provider: string, model: string) => void;
  onClose: () => void;
}

function FileTree({
  path,
  depth,
  onOpen,
  activePath,
  refreshKey,
}: {
  path: string;
  depth: number;
  onOpen: (p: string) => void;
  activePath: string | null;
  refreshKey: number;
}) {
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [open, setOpen] = useState<Record<string, boolean>>({});

  useEffect(() => {
    void listDir(path).then((e) =>
      setEntries(
        e.filter(
          (x) =>
            !x.name.startsWith(".") &&
            !["node_modules", "__pycache__", "dist", "venv", ".venv"].includes(x.name)
        )
      )
    );
  }, [path, refreshKey]);

  return (
    <div>
      {entries.map((e) => (
        <div key={e.path}>
          <div
            onClick={() => {
              if (e.is_dir) setOpen((o) => ({ ...o, [e.path]: !o[e.path] }));
              else onOpen(e.path);
            }}
            style={{ paddingLeft: depth * 12 + 8 }}
            className={`flex items-center gap-1.5 py-1 pr-2 text-[12px] cursor-pointer rounded hover:bg-white/5 ${
              activePath === e.path ? "bg-gold/10 text-gold" : "text-white/70"
            }`}
          >
            <span className="text-white/40 w-3">
              {e.is_dir ? (open[e.path] ? "▾" : "▸") : ""}
            </span>
            <span className="truncate">
              {e.is_dir ? "📁" : "📄"} {e.name}
            </span>
          </div>
          {e.is_dir && open[e.path] && (
            <FileTree
              path={e.path}
              depth={depth + 1}
              onOpen={onOpen}
              activePath={activePath}
              refreshKey={refreshKey}
            />
          )}
        </div>
      ))}
    </div>
  );
}

export default function CodeAgent({
  providers,
  provider,
  model,
  onModelChange,
  onClose,
}: Props) {
  const [workspace, setWorkspace] = useState<string>(
    () => localStorage.getItem("jon_workspace") || ""
  );
  const [manualPath, setManualPath] = useState(
    () => localStorage.getItem("jon_workspace") || ""
  );
  const [picker, setPicker] = useState<"model" | "provider" | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [filePath, setFilePath] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState("");
  const [dirty, setDirty] = useState(false);
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight });
  }, [entries]);

  const pickFolder = async () => {
    if (jonBridge?.pickFolder) {
      const folder = await jonBridge.pickFolder();
      if (folder) setWorkspacePath(folder);
    }
  };

  const setWorkspacePath = (p: string) => {
    setWorkspace(p);
    setManualPath(p);
    localStorage.setItem("jon_workspace", p);
    setFilePath(null);
    setFileContent("");
    setRefreshKey((k) => k + 1);
  };

  const openFile = async (p: string) => {
    try {
      const content = await readWorkspaceFile(p);
      setFilePath(p);
      setFileContent(content);
      setDirty(false);
    } catch {
      setFilePath(p);
      setFileContent("[Datei konnte nicht gelesen werden]");
    }
  };

  const saveFile = async () => {
    if (!filePath) return;
    await writeWorkspaceFile(filePath, fileContent);
    setDirty(false);
  };

  const sys = (text: string) =>
    setEntries((prev) => [...prev, { id: nid(), role: "assistant", content: text }]);

  const handleCommand = (raw: string): boolean => {
    const [cmd, ...rest] = raw.slice(1).split(/\s+/);
    const arg = rest.join(" ").trim();
    const c = cmd.toLowerCase();
    if (c === "help") {
      sys(
        "Befehle: /model [name], /provider [name], /tools, /status, /clear, /help. " +
          "Beschreibe Jon einfach, was er im Projekt tun soll."
      );
      return true;
    }
    if (c === "clear") {
      setEntries([]);
      return true;
    }
    if (c === "status") {
      sys(`Provider ${provider} · Modell ${model} · Workspace ${workspace || "—"}`);
      return true;
    }
    if (c === "tools") {
      sys("Jon nutzt: read_file, write_file, edit_file, search_files, list_dir, run_powershell, run_cmd, git u.v.m.");
      return true;
    }
    if (c === "model") {
      const active = providers.find((p) => p.provider === provider);
      const models = active?.models ?? [];
      if (arg) {
        const match =
          models.find((m) => m === arg) ||
          (/^\d+$/.test(arg) ? models[+arg - 1] : undefined);
        if (match) onModelChange(provider, match);
      } else {
        setPicker("model");
      }
      return true;
    }
    if (c === "provider") {
      if (arg) {
        const next = providers.find((p) => p.provider === arg);
        if (next) onModelChange(next.provider, next.models[0] ?? "");
      } else {
        setPicker("provider");
      }
      return true;
    }
    sys(`Unbekannter Befehl: /${c}`);
    return true;
  };

  const send = async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");
    if (text.startsWith("/")) {
      handleCommand(text);
      return;
    }
    if (!workspace) {
      sys("Wähle zuerst oben einen Projektordner.");
      return;
    }
    const userEntry: ChatEntry = { id: nid(), role: "user", content: text };
    const assistant: ChatEntry = {
      id: nid(),
      role: "assistant",
      content: "",
      streaming: true,
      tools: [],
    };
    const history = [...entries.filter((e) => e.role === "user" || e.role === "assistant"), userEntry];
    setEntries([...entries, userEntry, assistant]);
    setStreaming(true);

    await streamChat(
      {
        messages: history.map((e) => ({ role: e.role, content: e.content })),
        provider,
        model,
        persist: false,
        tool_mode: "allow",
        mode: "coding",
        workspace,
      },
      {
        onReasoning: (delta) =>
          setEntries((prev) =>
            prev.map((e) =>
              e.id === assistant.id ? { ...e, reasoning: (e.reasoning ?? "") + delta } : e
            )
          ),
        onTool: (evt) =>
          setEntries((prev) =>
            prev.map((e) => {
              if (e.id !== assistant.id) return e;
              const tools = [...(e.tools ?? [])];
              if (evt.status === "running") {
                tools.push({ name: evt.name ?? "tool", done: false, args: evt.args, summary: evt.summary });
              } else {
                const i = tools.map((t) => t.name).lastIndexOf(evt.name ?? "tool");
                if (i >= 0) tools[i] = { ...tools[i], done: true, ok: evt.ok };
              }
              return { ...e, tools };
            })
          ),
        onContent: (delta) =>
          setEntries((prev) =>
            prev.map((e) =>
              e.id === assistant.id ? { ...e, content: e.content + delta } : e
            )
          ),
        onError: (message) =>
          setEntries((prev) =>
            prev.map((e) =>
              e.id === assistant.id
                ? { ...e, content: e.content + `\n\n[Fehler] ${message}`, streaming: false }
                : e
            )
          ),
        onDone: async () => {
          setEntries((prev) =>
            prev.map((e) => (e.id === assistant.id ? { ...e, streaming: false } : e))
          );
          setStreaming(false);
          setRefreshKey((k) => k + 1);
          if (filePath) {
            try {
              setFileContent(await readWorkspaceFile(filePath));
              setDirty(false);
            } catch {
              /* file may have been deleted */
            }
          }
        },
      }
    );
  };

  return (
    <div className="fixed inset-0 z-40 flex flex-col bg-ink-900">
      <div className="flex items-center gap-2 h-11 px-3 border-b border-white/10 bg-black/40">
        <span className="text-[13px] font-semibold gold-text mr-1">Jon Code</span>
        {jonBridge?.pickFolder && (
          <button
            onClick={pickFolder}
            className="text-[12px] px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-white/80 hover:bg-white/10 whitespace-nowrap"
          >
            📂 Ordner wählen
          </button>
        )}
        <input
          value={manualPath}
          onChange={(e) => setManualPath(e.target.value)}
          onKeyDown={(e) =>
            e.key === "Enter" && manualPath.trim() && setWorkspacePath(manualPath.trim())
          }
          placeholder="Projektordner-Pfad (z. B. C:\Users\felix\mein-projekt)"
          className="flex-1 min-w-0 text-[12px] px-2 py-1 rounded-lg bg-black/30 border border-white/10 text-white/80 outline-none focus:border-gold/40"
        />
        <button
          onClick={() => manualPath.trim() && setWorkspacePath(manualPath.trim())}
          disabled={!manualPath.trim()}
          className="text-[12px] px-2.5 py-1 rounded-lg bg-gold/80 text-black font-medium disabled:opacity-40 whitespace-nowrap"
        >
          Öffnen
        </button>
        {workspace && (
          <button
            onClick={() => openInVscode(workspace)}
            className="text-[12px] px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-white/70 hover:bg-white/10 whitespace-nowrap"
            title="Ordner extern in VS Code öffnen"
          >
            VS Code ↗
          </button>
        )}
        <button
          onClick={onClose}
          className="text-[12px] px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-white/70 hover:bg-white/10 whitespace-nowrap"
        >
          ✕ Schließen
        </button>
      </div>

      <div className="flex flex-1 min-h-0">
        <div className="w-56 border-r border-white/10 overflow-y-auto py-2 bg-black/20">
          {workspace ? (
            <FileTree path={workspace} depth={0} onOpen={openFile} activePath={filePath} refreshKey={refreshKey} />
          ) : (
            <div className="text-[12px] text-white/40 px-3 py-2">
              Kein Ordner gewählt.
            </div>
          )}
        </div>

        <div className="flex-1 flex flex-col min-w-0 border-r border-white/10">
          <div className="flex items-center justify-between h-9 px-3 border-b border-white/10 bg-black/20">
            <span className="text-[12px] text-white/60 truncate">
              {filePath || "Keine Datei geöffnet"} {dirty ? "●" : ""}
            </span>
            {filePath && (
              <button
                onClick={saveFile}
                disabled={!dirty}
                className="text-[11px] px-2.5 py-1 rounded bg-gold/80 text-black font-medium disabled:opacity-40"
              >
                Speichern
              </button>
            )}
          </div>
          <textarea
            value={fileContent}
            onChange={(e) => {
              setFileContent(e.target.value);
              setDirty(true);
            }}
            spellCheck={false}
            placeholder="Wähle links eine Datei oder lass Jon rechts eine erstellen."
            className="flex-1 bg-ink-900 text-white/85 font-mono text-[12.5px] leading-relaxed p-3 outline-none resize-none"
          />
        </div>

        <div className="w-96 flex flex-col min-w-0 bg-black/20 relative">
          <div className="h-9 px-3 flex items-center gap-1.5 border-b border-white/10 text-[12px]">
            <span className="text-white/40">Jon ·</span>
            <button
              onClick={() => setPicker(picker === "provider" ? null : "provider")}
              className="text-gold/80 hover:text-gold"
              title="Provider wechseln"
            >
              {provider}
            </button>
            <span className="text-white/30">·</span>
            <button
              onClick={() => setPicker(picker === "model" ? null : "model")}
              className="text-white/70 hover:text-white truncate"
              title="Modell wechseln"
            >
              {model}
            </button>
          </div>
          {picker && (
            <div className="absolute top-9 left-0 right-0 z-10 max-h-64 overflow-y-auto glass border-b border-white/10 p-2">
              <div className="flex items-center justify-between px-1 mb-1.5">
                <span className="text-[11px] text-white/50">
                  {picker === "model"
                    ? `Modell wählen (${provider})`
                    : "Provider wählen"}
                </span>
                <button
                  onClick={() => setPicker(null)}
                  className="text-white/40 hover:text-white/80 text-sm leading-none"
                >
                  ×
                </button>
              </div>
              {picker === "provider"
                ? providers.map((p) => (
                    <button
                      key={p.provider}
                      disabled={!p.configured}
                      onClick={() => {
                        onModelChange(p.provider, p.models[0] ?? "");
                        setPicker(null);
                      }}
                      className={`w-full text-left text-[12px] px-2.5 py-1.5 rounded-lg transition disabled:opacity-40 ${
                        p.provider === provider
                          ? "bg-gold/15 text-gold"
                          : "text-white/75 hover:bg-white/10"
                      }`}
                    >
                      {p.provider}
                      {p.configured ? "" : " · kein Key"}
                    </button>
                  ))
                : (providers.find((p) => p.provider === provider)?.models ?? []).map(
                    (m) => (
                      <button
                        key={m}
                        onClick={() => {
                          onModelChange(provider, m);
                          setPicker(null);
                        }}
                        className={`w-full text-left text-[12px] px-2.5 py-1.5 rounded-lg transition truncate ${
                          m === model
                            ? "bg-gold/15 text-gold"
                            : "text-white/75 hover:bg-white/10"
                        }`}
                      >
                        {m}
                      </button>
                    )
                  )}
            </div>
          )}
          <div ref={chatRef} className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
            {entries.length === 0 && (
              <div className="text-[12px] text-white/40 leading-relaxed">
                Jon arbeitet hier direkt an deinem Projekt — Dateien lesen, ändern, Tests
                laufen lassen. Beschreib einfach dein Ziel. Mit <b>/model</b> und
                <b> /provider</b> wechselst du das Modell.
              </div>
            )}
            {entries.map((e) => (
              <MessageBubble key={e.id} entry={e} />
            ))}
          </div>
          <div className="p-2 border-t border-white/10">
            <div className="glass rounded-xl flex items-end gap-2 p-1.5">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void send();
                  }
                }}
                rows={1}
                placeholder="Jon beauftragen … (/help)"
                className="flex-1 bg-transparent resize-none outline-none px-2 py-1.5 text-[13px] text-white/90 placeholder-white/30 max-h-32"
              />
              <button
                onClick={() => void send()}
                disabled={streaming || !input.trim()}
                className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-gold-light to-gold-dark text-black text-[12px] font-semibold disabled:opacity-40"
              >
                {streaming ? "…" : "Senden"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
