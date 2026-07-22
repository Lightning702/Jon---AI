import { useEffect, useRef, useState } from "react";
import MessageBubble, { ChatEntry } from "./MessageBubble";
import {
  FileEntry,
  ProviderStatus,
  listDir,
  makeDir,
  openInVscode,
  pathInfo,
  pickFolderDialog,
  readFileBase64,
  readWorkspaceFile,
  streamChat,
  writeWorkspaceFile,
} from "../lib/api";

let cid = 0;
const nid = () => `ca${Date.now()}_${cid++}`;

const IMAGE_RE = /\.(png|jpe?g|gif|webp|bmp|svg|ico|avif)$/i;
const isImagePath = (p: string) => IMAGE_RE.test(p);
const isHtmlPath = (p: string) => /\.html?$/i.test(p);

const jonBridge = (window as unknown as {
  jon?: {
    pickFolder?: () => Promise<string | null>;
    openVscode?: (f: string) => Promise<boolean>;
    getPathForFile?: (f: File) => string;
  };
}).jon;

function parentDir(path: string): string {
  return path.replace(/[\\/][^\\/]*$/, "") || path;
}

function joinPath(base: string, name: string): string {
  return base.replace(/[\\/]+$/, "") + "/" + name.replace(/^[\\/]+/, "");
}

interface Props {
  providers: ProviderStatus[];
  provider: string;
  model: string;
  onModelChange: (provider: string, model: string) => void;
  onClose: () => void;
}

interface GoalStep {
  text: string;
  status: "offen" | "läuft" | "fertig" | "fehler";
}

function parsePlan(raw: string): { steps?: string[]; frage?: string } {
  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}");
  if (start < 0 || end <= start) return {};
  try {
    const data = JSON.parse(raw.slice(start, end + 1)) as {
      steps?: unknown;
      schritte?: unknown;
      frage?: unknown;
    };
    const list = Array.isArray(data.steps)
      ? data.steps
      : Array.isArray(data.schritte)
        ? data.schritte
        : undefined;
    const steps = list
      ?.map((s) => String(s).trim())
      .filter(Boolean)
      .slice(0, 12);
    const frage =
      typeof data.frage === "string" && data.frage.trim()
        ? data.frage.trim()
        : undefined;
    return { steps: steps && steps.length ? steps : undefined, frage };
  } catch {
    return {};
  }
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
  const [showManual, setShowManual] = useState(false);
  const [picking, setPicking] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [picker, setPicker] = useState<"model" | "provider" | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [filePath, setFilePath] = useState<string | null>(null);
  const [fileKind, setFileKind] = useState<"text" | "image">("text");
  const [fileContent, setFileContent] = useState("");
  const [imageSrc, setImageSrc] = useState("");
  const [dirty, setDirty] = useState(false);
  const [creating, setCreating] = useState<null | "file" | "folder">(null);
  const [newName, setNewName] = useState("");
  const [view, setView] = useState<"editor" | "preview">("editor");
  const [previewUrl, setPreviewUrl] = useState("http://localhost:3000");
  const [previewSrc, setPreviewSrc] = useState("");
  const [previewMode, setPreviewMode] = useState<"url" | "file">("url");
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [goal, setGoal] = useState("");
  const [goalSteps, setGoalSteps] = useState<GoalStep[]>([]);
  const [goalRunning, setGoalRunning] = useState(false);
  const [goalQuestion, setGoalQuestion] = useState("");
  const goalStopRef = useRef(false);
  const goalAbortRef = useRef<AbortController | null>(null);
  const chatRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const undoRef = useRef<{ stack: string[]; last: number }>({ stack: [], last: 0 });
  const contentRef = useRef("");
  const filePathRef = useRef<string | null>(null);
  const fileKindRef = useRef<"text" | "image">("text");
  const dirtyRef = useRef(false);
  const nameInputRef = useRef<HTMLInputElement>(null);

  contentRef.current = fileContent;
  filePathRef.current = filePath;
  fileKindRef.current = fileKind;
  dirtyRef.current = dirty;

  useEffect(() => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight });
  }, [entries]);

  useEffect(() => {
    if (creating) nameInputRef.current?.focus();
  }, [creating]);

  useEffect(() => {
    const prevent = (e: DragEvent) => e.preventDefault();
    window.addEventListener("dragover", prevent);
    window.addEventListener("drop", prevent);
    return () => {
      window.removeEventListener("dragover", prevent);
      window.removeEventListener("drop", prevent);
    };
  }, []);

  const pushUndo = (prev: string) => {
    const u = undoRef.current;
    const now = Date.now();
    if (u.stack.length === 0 || now - u.last > 400) {
      u.stack.push(prev);
      if (u.stack.length > 200) u.stack.shift();
    }
    u.last = now;
  };

  const undo = () => {
    const u = undoRef.current;
    if (!u.stack.length) return;
    const prev = u.stack.pop() as string;
    setFileContent(prev);
    setDirty(true);
    u.last = 0;
  };

  const saveFile = async () => {
    if (!filePathRef.current || fileKindRef.current !== "text") return;
    await writeWorkspaceFile(filePathRef.current, contentRef.current);
    setDirty(false);
  };
  const saveRef = useRef(saveFile);
  saveRef.current = saveFile;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        if (dirtyRef.current) void saveRef.current();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const pickFolder = async () => {
    if (picking) return;
    setPicking(true);
    try {
      if (jonBridge?.pickFolder) {
        const folder = await jonBridge.pickFolder();
        if (folder) setWorkspacePath(folder);
        return;
      }
      const folder = await pickFolderDialog();
      if (folder) setWorkspacePath(folder);
      else if (folder === null) setShowManual(true);
    } catch {
      setShowManual(true);
    } finally {
      setPicking(false);
    }
  };

  const setWorkspacePath = (p: string) => {
    setWorkspace(p);
    setManualPath(p);
    localStorage.setItem("jon_workspace", p);
    setFilePath(null);
    setFileContent("");
    setImageSrc("");
    setFileKind("text");
    setRefreshKey((k) => k + 1);
  };

  const openFile = async (p: string) => {
    undoRef.current = { stack: [], last: 0 };
    if (isImagePath(p)) {
      try {
        const { data, mime } = await readFileBase64(p);
        setFilePath(p);
        setFileKind("image");
        setImageSrc(`data:${mime};base64,${data}`);
        setFileContent("");
        setDirty(false);
        return;
      } catch {
        /* fall through to text */
      }
    }
    try {
      const content = await readWorkspaceFile(p);
      setFilePath(p);
      setFileKind("text");
      setImageSrc("");
      setFileContent(content);
      setDirty(false);
    } catch {
      setFilePath(p);
      setFileKind("text");
      setImageSrc("");
      setFileContent("[Datei konnte nicht gelesen werden]");
    }
  };

  const createEntry = async () => {
    const name = newName.trim();
    if (!name || !workspace) {
      setCreating(null);
      setNewName("");
      return;
    }
    const target = joinPath(workspace, name);
    try {
      if (creating === "folder") {
        await makeDir(target);
      } else {
        await writeWorkspaceFile(target, "");
      }
    } catch {
      /* ignore */
    }
    const kind = creating;
    setCreating(null);
    setNewName("");
    setRefreshKey((k) => k + 1);
    if (kind === "file") await openFile(target);
  };

  const loadPreview = () => {
    let u = previewUrl.trim();
    if (!u) return;
    if (!/^https?:\/\//i.test(u)) u = "http://" + u;
    setPreviewMode("url");
    setPreviewSrc(u);
    setView("preview");
  };

  const reloadPreview = () => {
    if (iframeRef.current && previewMode === "url") {
      const s = previewSrc;
      iframeRef.current.src = "about:blank";
      window.setTimeout(() => {
        if (iframeRef.current) iframeRef.current.src = s;
      }, 30);
    }
  };

  const openExternal = () => {
    let u = previewUrl.trim();
    if (!u) return;
    if (!/^https?:\/\//i.test(u)) u = "http://" + u;
    window.open(u, "_blank");
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const items = Array.from(e.dataTransfer.items || []);
    const files = Array.from(e.dataTransfer.files || []);
    const file =
      files[0] || (items[0]?.kind === "file" ? items[0].getAsFile() : null);
    if (!file) return;
    const path = jonBridge?.getPathForFile
      ? jonBridge.getPathForFile(file)
      : (file as File & { path?: string }).path || "";
    if (!path) {
      setShowManual(true);
      return;
    }
    const info = await pathInfo(path);
    if (info.is_dir) {
      setWorkspacePath(path);
    } else if (info.exists) {
      setWorkspacePath(info.parent || parentDir(path));
      await openFile(path);
    } else {
      setWorkspacePath(path);
    }
  };

  const sys = (text: string) =>
    setEntries((prev) => [...prev, { id: nid(), role: "assistant", content: text }]);

  const reloadOpenFile = async () => {
    setRefreshKey((k) => k + 1);
    if (filePathRef.current && fileKindRef.current === "text") {
      try {
        const next = await readWorkspaceFile(filePathRef.current);
        if (next !== contentRef.current) {
          pushUndo(contentRef.current);
          setFileContent(next);
          setDirty(false);
        }
      } catch {
        /* file may have been deleted */
      }
    }
  };

  const runGoalChat = async (
    history: { role: "user" | "assistant"; content: string }[]
  ): Promise<{ text: string; error: string }> => {
    const assistant: ChatEntry = {
      id: nid(),
      role: "assistant",
      content: "",
      streaming: true,
      tools: [],
    };
    setEntries((prev) => [...prev, assistant]);
    let text = "";
    let error = "";
    const controller = new AbortController();
    goalAbortRef.current = controller;
    try {
      await streamChat(
        {
          messages: history,
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
                e.id === assistant.id
                  ? { ...e, reasoning: (e.reasoning ?? "") + delta }
                  : e
              )
            ),
          onTool: (evt) =>
            setEntries((prev) =>
              prev.map((e) => {
                if (e.id !== assistant.id) return e;
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
            ),
          onContent: (delta) => {
            text += delta;
            setEntries((prev) =>
              prev.map((e) =>
                e.id === assistant.id ? { ...e, content: e.content + delta } : e
              )
            );
          },
          onError: (message) => {
            error = message;
            setEntries((prev) =>
              prev.map((e) =>
                e.id === assistant.id
                  ? { ...e, content: e.content + `\n\n[Fehler] ${message}` }
                  : e
              )
            );
          },
        },
        controller.signal
      );
    } catch {
      if (!error) error = "abgebrochen";
    }
    goalAbortRef.current = null;
    setEntries((prev) =>
      prev.map((e) => (e.id === assistant.id ? { ...e, streaming: false } : e))
    );
    await reloadOpenFile();
    return { text, error };
  };

  const finishGoal = (message: string) => {
    sys(message);
    setGoalRunning(false);
    setStreaming(false);
  };

  const startGoal = async (goalText: string, clarification = "") => {
    setGoal(goalText);
    setGoalSteps([]);
    setGoalQuestion("");
    setGoalRunning(true);
    setStreaming(true);
    goalStopRef.current = false;
    const history: { role: "user" | "assistant"; content: string }[] = [];
    const planPrompt = [
      `/goal-Modus. Mein Ziel: ${goalText}`,
      clarification ? `Meine Klärung dazu: ${clarification}` : "",
      "Sieh dich bei Bedarf kurz im Projekt um und zerlege das Ziel dann in 2 bis 8 konkrete, nacheinander ausführbare Schritte.",
      'Wenn das Ziel zu unklar ist, um loszulegen, stelle genau eine Rückfrage. Antworte am Ende NUR mit JSON, ohne Text davor oder danach: {"steps": ["Schritt 1", "Schritt 2"]} oder {"frage": "deine Rückfrage"}',
    ]
      .filter(Boolean)
      .join("\n");
    history.push({ role: "user", content: planPrompt });
    const plan = await runGoalChat(history);
    if (goalStopRef.current) {
      finishGoal("🛑 Ziel gestoppt.");
      return;
    }
    if (plan.error && !plan.text) {
      finishGoal(`Die Planung ist fehlgeschlagen: ${plan.error}`);
      return;
    }
    const parsed = parsePlan(plan.text);
    if (parsed.frage && !parsed.steps) {
      setGoalQuestion(parsed.frage);
      setGoalRunning(false);
      setStreaming(false);
      return;
    }
    if (!parsed.steps) {
      finishGoal(
        "Ich konnte keinen Plan aus der Antwort lesen. Formuliere das Ziel bitte etwas konkreter und starte /goal erneut."
      );
      return;
    }
    const steps: GoalStep[] = parsed.steps.map((text) => ({
      text,
      status: "offen",
    }));
    setGoalSteps(steps);
    history.push({
      role: "assistant",
      content: JSON.stringify({ steps: parsed.steps }),
    });
    let failure = "";
    for (let i = 0; i < steps.length; i++) {
      if (goalStopRef.current) break;
      setGoalSteps((prev) =>
        prev.map((s, j) => (j === i ? { ...s, status: "läuft" } : s))
      );
      history.push({
        role: "user",
        content: `Schritt ${i + 1}/${steps.length}: ${steps[i].text}\nFühre genau diesen Schritt jetzt aus. Fasse am Ende in 1-2 Sätzen zusammen, was du getan hast.`,
      });
      let result = await runGoalChat(history);
      if (result.error && !goalStopRef.current) {
        history.push({
          role: "assistant",
          content: (result.text || "Fehler.").slice(0, 1500),
        });
        history.push({
          role: "user",
          content: `Der Schritt schlug fehl: ${result.error}\nAnalysiere die Ursache, behebe sie und führe den Schritt danach erneut aus.`,
        });
        result = await runGoalChat(history);
      }
      history.push({
        role: "assistant",
        content: (result.text || "(keine Antwort)").slice(0, 1500),
      });
      if (goalStopRef.current) break;
      if (result.error) {
        setGoalSteps((prev) =>
          prev.map((s, j) => (j === i ? { ...s, status: "fehler" } : s))
        );
        failure = result.error;
        break;
      }
      setGoalSteps((prev) =>
        prev.map((s, j) => (j === i ? { ...s, status: "fertig" } : s))
      );
    }
    if (goalStopRef.current) {
      finishGoal("🛑 Ziel auf deinen Wunsch gestoppt.");
      return;
    }
    history.push({
      role: "user",
      content: failure
        ? `Das Ziel wurde nicht vollständig erreicht (letzter Fehler: ${failure}). Erstelle einen kurzen Abschlussbericht: was erledigt wurde, woran es scheiterte und was ich jetzt tun kann.`
        : "Alle Schritte sind erledigt. Erstelle einen kurzen Abschlussbericht: was wurde pro Schritt getan und was sollte ich noch prüfen.",
    });
    await runGoalChat(history);
    setGoalRunning(false);
    setStreaming(false);
  };

  const stopGoal = () => {
    goalStopRef.current = true;
    goalAbortRef.current?.abort();
  };

  const handleCommand = (raw: string): boolean => {
    const [cmd, ...rest] = raw.slice(1).split(/\s+/);
    const arg = rest.join(" ").trim();
    const c = cmd.toLowerCase();
    if (c === "help") {
      sys(
        "Befehle: /goal Zielbeschreibung, /model [name], /provider [name], /tools, /status, /clear, /help. " +
          "Mit /goal plant Jon die Schritte zu deinem Ziel, führt sie nacheinander aus und berichtet am Ende. " +
          "Oder beschreibe Jon einfach direkt, was er im Projekt tun soll."
      );
      return true;
    }
    if (c === "goal") {
      if (!arg) {
        sys(
          "Nutzung: /goal Zielbeschreibung — z. B. „/goal Erstelle eine Funktion zur Datenvalidierung“. " +
            "Jon zerlegt das Ziel in Schritte, arbeitet sie nacheinander ab, zeigt den Fortschritt und liefert einen Abschlussbericht."
        );
        return true;
      }
      if (!workspace) {
        sys("Wähle zuerst oben einen Projektordner.");
        return true;
      }
      if (goalRunning) {
        sys("Es läuft schon ein Ziel — stoppe es zuerst über den Stopp-Knopf.");
        return true;
      }
      setEntries((prev) => [
        ...prev,
        { id: nid(), role: "user", content: `/goal ${arg}` },
      ]);
      void startGoal(arg);
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
    if (goalQuestion) {
      setEntries((prev) => [...prev, { id: nid(), role: "user", content: text }]);
      void startGoal(goal, text);
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
          if (filePathRef.current && fileKindRef.current === "text") {
            try {
              const next = await readWorkspaceFile(filePathRef.current);
              if (next !== contentRef.current) {
                pushUndo(contentRef.current);
                setFileContent(next);
                setDirty(false);
              }
            } catch {
              /* file may have been deleted */
            }
          }
          if (view === "preview" && previewMode === "url") reloadPreview();
        },
      }
    );
  };

  const editorKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
      e.preventDefault();
      if (dirty) void saveFile();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === "x" || e.key.toLowerCase() === "z")) {
      e.preventDefault();
      undo();
    }
  };

  const showFilePreview = () => {
    setPreviewMode("file");
    setView("preview");
  };

  return (
    <div className="fixed inset-0 z-40 flex flex-col bg-ink-900">
      <div className="flex items-center gap-2 h-11 px-3 border-b border-white/10 bg-black/40">
        <span className="text-[13px] font-semibold gold-text mr-1">Jon Code</span>
        <button
          onClick={pickFolder}
          disabled={picking}
          className="text-[12px] px-3 py-1 rounded-lg bg-gold/80 text-black font-medium hover:bg-gold disabled:opacity-50 whitespace-nowrap"
        >
          {picking ? "Öffne …" : "📂 Ordner öffnen"}
        </button>
        {showManual ? (
          <>
            <input
              value={manualPath}
              onChange={(e) => setManualPath(e.target.value)}
              onKeyDown={(e) =>
                e.key === "Enter" &&
                manualPath.trim() &&
                setWorkspacePath(manualPath.trim())
              }
              placeholder="Pfad zum Ordner eingeben"
              className="flex-1 min-w-0 text-[12px] px-2 py-1 rounded-lg bg-black/30 border border-white/10 text-white/80 outline-none focus:border-gold/40"
            />
            <button
              onClick={() => manualPath.trim() && setWorkspacePath(manualPath.trim())}
              disabled={!manualPath.trim()}
              className="text-[12px] px-2.5 py-1 rounded-lg bg-white/10 border border-white/10 text-white/80 disabled:opacity-40 whitespace-nowrap"
            >
              OK
            </button>
          </>
        ) : (
          <span className="flex-1 min-w-0 text-[11px] text-white/45 truncate">
            {workspace || "Kein Ordner gewählt"}
          </span>
        )}
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

      <div
        className="flex flex-1 min-h-0 relative"
        onDragOver={(e) => {
          e.preventDefault();
          if (!dragOver) setDragOver(true);
        }}
        onDragLeave={(e) => {
          if (e.currentTarget === e.target) setDragOver(false);
        }}
        onDrop={handleDrop}
      >
        {dragOver && (
          <div className="absolute inset-0 z-30 flex items-center justify-center bg-black/70 border-2 border-dashed border-gold/50 pointer-events-none">
            <div className="text-center">
              <div className="text-3xl mb-2">📂</div>
              <div className="text-[14px] text-gold">Ordner oder Datei hier ablegen</div>
            </div>
          </div>
        )}
        <div className="w-56 border-r border-white/10 flex flex-col bg-black/20">
          <div className="flex items-center gap-1 px-2 py-2 border-b border-white/10">
            <button
              onClick={() => {
                setCreating("file");
                setNewName("");
              }}
              disabled={!workspace}
              className="flex-1 text-[11px] px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-white/70 hover:bg-white/10 disabled:opacity-40"
              title="Neue Datei"
            >
              ＋ Datei
            </button>
            <button
              onClick={() => {
                setCreating("folder");
                setNewName("");
              }}
              disabled={!workspace}
              className="flex-1 text-[11px] px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-white/70 hover:bg-white/10 disabled:opacity-40"
              title="Neuer Ordner"
            >
              ＋ Ordner
            </button>
          </div>
          {creating && (
            <div className="px-2 py-2 border-b border-white/10">
              <input
                ref={nameInputRef}
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void createEntry();
                  if (e.key === "Escape") {
                    setCreating(null);
                    setNewName("");
                  }
                }}
                placeholder={creating === "folder" ? "Ordnername" : "Dateiname (z.B. app.tsx)"}
                className="w-full text-[12px] px-2 py-1 rounded-lg bg-black/40 border border-gold/30 text-white/85 outline-none focus:border-gold/60"
              />
              <div className="flex gap-1 mt-1">
                <button
                  onClick={() => void createEntry()}
                  className="flex-1 text-[11px] px-2 py-1 rounded bg-gold/80 text-black font-medium"
                >
                  Anlegen
                </button>
                <button
                  onClick={() => {
                    setCreating(null);
                    setNewName("");
                  }}
                  className="text-[11px] px-2 py-1 rounded bg-white/5 border border-white/10 text-white/60"
                >
                  Abbrechen
                </button>
              </div>
            </div>
          )}
          <div className="flex-1 overflow-y-auto py-2">
            {workspace ? (
              <FileTree path={workspace} depth={0} onOpen={openFile} activePath={filePath} refreshKey={refreshKey} />
            ) : (
              <div className="text-[12px] text-white/40 px-3 py-4 text-center leading-relaxed">
                Kein Ordner gewählt.
                <br />
                <span className="text-white/30">
                  Zieh einen Ordner hierher oder klick oben auf „Ordner öffnen".
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 flex flex-col min-w-0 border-r border-white/10">
          <div className="flex items-center justify-between h-9 px-3 border-b border-white/10 bg-black/20 gap-2">
            <span className="text-[12px] text-white/60 truncate min-w-0">
              {filePath || "Keine Datei geöffnet"} {dirty ? "●" : ""}
            </span>
            <div className="flex items-center gap-1 flex-none">
              <div className="flex rounded-lg overflow-hidden border border-white/10">
                <button
                  onClick={() => setView("editor")}
                  className={`text-[11px] px-2.5 py-1 ${
                    view === "editor" ? "bg-gold/20 text-gold" : "text-white/60 hover:bg-white/10"
                  }`}
                >
                  Editor
                </button>
                <button
                  onClick={() => setView("preview")}
                  className={`text-[11px] px-2.5 py-1 border-l border-white/10 ${
                    view === "preview" ? "bg-gold/20 text-gold" : "text-white/60 hover:bg-white/10"
                  }`}
                >
                  Vorschau
                </button>
              </div>
              {filePath && isHtmlPath(filePath) && (
                <button
                  onClick={showFilePreview}
                  className="text-[11px] px-2 py-1 rounded bg-white/5 border border-white/10 text-white/60 hover:bg-white/10"
                  title="Diese HTML-Datei rendern"
                >
                  ▶ Datei
                </button>
              )}
              {view === "editor" && fileKind === "text" && filePath && (
                <button
                  onClick={() => void saveFile()}
                  disabled={!dirty}
                  className="text-[11px] px-2.5 py-1 rounded bg-gold/80 text-black font-medium disabled:opacity-40"
                  title="Speichern (Strg+S)"
                >
                  Speichern
                </button>
              )}
            </div>
          </div>

          {view === "editor" ? (
            fileKind === "image" ? (
              <div className="flex-1 overflow-auto bg-ink-900 flex items-center justify-center p-4">
                {imageSrc ? (
                  <img
                    src={imageSrc}
                    alt={filePath || ""}
                    className="max-w-full max-h-full object-contain"
                    style={{ imageRendering: "auto" }}
                  />
                ) : (
                  <span className="text-white/40 text-[12px]">Bild wird geladen …</span>
                )}
              </div>
            ) : (
              <textarea
                value={fileContent}
                onChange={(e) => {
                  pushUndo(fileContent);
                  setFileContent(e.target.value);
                  setDirty(true);
                }}
                onKeyDown={editorKeyDown}
                spellCheck={false}
                placeholder="Wähle links eine Datei, leg eine neue an oder lass Jon rechts eine erstellen."
                className="flex-1 bg-ink-900 text-white/85 font-mono text-[12.5px] leading-relaxed p-3 outline-none resize-none"
              />
            )
          ) : (
            <div className="flex-1 flex flex-col min-h-0 bg-white">
              <div className="flex items-center gap-1.5 px-2 py-1.5 bg-black/30 border-b border-white/10">
                <input
                  value={previewUrl}
                  onChange={(e) => setPreviewUrl(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && loadPreview()}
                  placeholder="http://localhost:3000"
                  className="flex-1 min-w-0 text-[12px] px-2 py-1 rounded bg-black/40 border border-white/10 text-white/85 outline-none focus:border-gold/40"
                />
                <button
                  onClick={loadPreview}
                  className="text-[11px] px-2.5 py-1 rounded bg-gold/80 text-black font-medium whitespace-nowrap"
                >
                  Laden
                </button>
                <button
                  onClick={reloadPreview}
                  className="text-[12px] px-2 py-1 rounded bg-white/5 border border-white/10 text-white/70 hover:bg-white/10"
                  title="Neu laden"
                >
                  ↻
                </button>
                <button
                  onClick={openExternal}
                  className="text-[11px] px-2 py-1 rounded bg-white/5 border border-white/10 text-white/70 hover:bg-white/10 whitespace-nowrap"
                  title="Im Browser öffnen"
                >
                  ↗
                </button>
              </div>
              {previewMode === "file" && filePath && isHtmlPath(filePath) ? (
                <iframe
                  title="Datei-Vorschau"
                  srcDoc={fileContent}
                  className="flex-1 w-full bg-white"
                  sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
                />
              ) : previewSrc ? (
                <iframe
                  ref={iframeRef}
                  title="Vorschau"
                  src={previewSrc}
                  className="flex-1 w-full bg-white"
                  sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
                />
              ) : (
                <div className="flex-1 flex items-center justify-center text-center p-6 bg-ink-900">
                  <div className="text-[12px] text-white/40 leading-relaxed">
                    Gib oben eine Adresse ein (z. B. <b className="text-white/60">http://localhost:3000</b>)
                    und klick „Laden", um deine laufende App zu sehen.
                    <br />
                    HTML-Dateien kannst du mit „▶ Datei" direkt rendern.
                  </div>
                </div>
              )}
            </div>
          )}
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
          {goal && (goalRunning || goalSteps.length > 0 || goalQuestion) && (
            <div className="border-b border-white/10 bg-black/30 px-3 py-2 max-h-48 overflow-y-auto flex-none">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[12px] text-gold truncate">🎯 {goal}</span>
                {goalRunning && (
                  <button
                    onClick={stopGoal}
                    className="text-[11px] px-2 py-0.5 rounded bg-red-500/20 border border-red-400/30 text-red-300 hover:bg-red-500/30 flex-none"
                  >
                    Stopp
                  </button>
                )}
              </div>
              {goalSteps.length > 0 && (
                <div className="mt-1.5 space-y-1">
                  {goalSteps.map((s, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-1.5 text-[11.5px] leading-snug"
                    >
                      <span className="flex-none">
                        {s.status === "fertig"
                          ? "✅"
                          : s.status === "läuft"
                            ? "▶️"
                            : s.status === "fehler"
                              ? "❌"
                              : "⚪"}
                      </span>
                      <span
                        className={
                          s.status === "fertig"
                            ? "text-white/40 line-through"
                            : s.status === "läuft"
                              ? "text-gold/90"
                              : s.status === "fehler"
                                ? "text-red-300"
                                : "text-white/60"
                        }
                      >
                        {s.text}
                      </span>
                    </div>
                  ))}
                </div>
              )}
              {goalQuestion && (
                <div className="mt-1.5 text-[11.5px] text-amber-300/90">
                  ❓ {goalQuestion} — antworte einfach unten im Chat.
                </div>
              )}
            </div>
          )}
          <div ref={chatRef} className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
            {entries.length === 0 && (
              <div className="text-[12px] text-white/40 leading-relaxed">
                Jon arbeitet hier direkt an deinem Projekt — Dateien lesen, ändern, Tests
                laufen lassen. Beschreib einfach dein Ziel, oder starte mit
                <b> /goal Ziel</b> den Ziel-Modus: Jon plant Schritte, führt sie aus und
                berichtet. Mit <b>/model</b> und <b>/provider</b> wechselst du das Modell.
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
                placeholder="Jon beauftragen … (/goal Ziel, /help)"
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
