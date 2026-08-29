import { useEffect, useMemo, useRef, useState } from "react";
import { extractAttachment } from "../lib/api";
import { SlashCommand, matchCommands } from "../lib/commands";
import { useT } from "../hooks/useT";

export interface PendingAttachment {
  id: string;
  name: string;
  kind: string;
  status: "loading" | "ready" | "error";
  content?: string;
  error?: string;
}

interface Props {
  disabled: boolean;
  onSend: (text: string, attachments: PendingAttachment[]) => void;
  onStop: () => void;
  streaming: boolean;
}

let attId = 0;
const nextAttId = () => `a${Date.now()}_${attId++}`;

const COMMAND_INPUT = /^\/[a-zA-Z0-9äöüßÄÖÜ_-]*$/;

const kindIcon = (kind: string, status: string) => {
  if (status === "loading") return "⏳";
  if (status === "error") return "⚠️";
  if (kind === "image") return "🖼️";
  if (kind === "pdf") return "📄";
  return "📎";
};

export default function Composer({ disabled, onSend, onStop, streaming }: Props) {
  const { t } = useT();
  const [text, setText] = useState("");
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [dragging, setDragging] = useState(false);
  const [closedFor, setClosedFor] = useState("");
  const [active, setActive] = useState(0);
  const ref = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const query = COMMAND_INPUT.test(text.trim()) ? text.trim() : "";
  const matches = useMemo(
    () => (query && closedFor !== query ? matchCommands(query) : []),
    [query, closedFor]
  );

  useEffect(() => {
    setActive(0);
  }, [query]);

  useEffect(() => {
    const item = listRef.current?.children[active] as HTMLElement | undefined;
    item?.scrollIntoView({ block: "nearest" });
  }, [active, matches.length]);

  const addFiles = (files: FileList | File[]) => {
    for (const file of Array.from(files)) {
      const id = nextAttId();
      const mime = file.type || "";
      const kind = mime.startsWith("image/")
        ? "image"
        : mime === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")
          ? "pdf"
          : "text";
      setAttachments((prev) => [
        ...prev,
        { id, name: file.name, kind, status: "loading" },
      ]);
      const reader = new FileReader();
      reader.onload = async () => {
        const result = String(reader.result ?? "");
        const base64 = result.slice(result.indexOf(",") + 1);
        try {
          const extracted = await extractAttachment(file.name, mime, base64);
          setAttachments((prev) =>
            prev.map((a) =>
              a.id === id
                ? {
                    ...a,
                    status: "ready",
                    kind: extracted.kind,
                    content: extracted.content,
                  }
                : a
            )
          );
        } catch (e) {
          setAttachments((prev) =>
            prev.map((a) =>
              a.id === id
                ? {
                    ...a,
                    status: "error",
                    error: e instanceof Error ? e.message : String(e),
                  }
                : a
            )
          );
        }
      };
      reader.onerror = () =>
        setAttachments((prev) =>
          prev.map((a) =>
            a.id === id ? { ...a, status: "error", error: "Lesefehler" } : a
          )
        );
      reader.readAsDataURL(file);
    }
  };

  const removeAttachment = (id: string) =>
    setAttachments((prev) => prev.filter((a) => a.id !== id));

  const loading = attachments.some((a) => a.status === "loading");
  const ready = attachments.filter((a) => a.status === "ready");

  const submit = () => {
    const value = text.trim();
    if ((!value && ready.length === 0) || disabled || loading) return;
    onSend(value, ready);
    setText("");
    setAttachments([]);
    if (ref.current) ref.current.style.height = "auto";
  };

  const pick = (command: SlashCommand) => {
    if (command.arg) {
      setText(`${command.cmd} `);
      setClosedFor(command.cmd);
      ref.current?.focus();
      return;
    }
    if (disabled) {
      setText(command.cmd);
      setClosedFor(command.cmd);
      ref.current?.focus();
      return;
    }
    onSend(command.cmd, ready);
    setText("");
    setAttachments([]);
    setClosedFor("");
    if (ref.current) ref.current.style.height = "auto";
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (matches.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActive((i) => (i + 1) % matches.length);
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActive((i) => (i - 1 + matches.length) % matches.length);
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        setClosedFor(query);
        return;
      }
      if (e.key === "Tab" || (e.key === "Enter" && !e.shiftKey)) {
        e.preventDefault();
        pick(matches[Math.min(active, matches.length - 1)]);
        return;
      }
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const onPaste = (e: React.ClipboardEvent) => {
    const files = e.clipboardData?.files;
    if (files && files.length > 0) {
      e.preventDefault();
      addFiles(files);
    }
  };

  return (
    <div
      className="p-2 md:p-4 safe-bottom"
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (e.dataTransfer.files.length > 0) addFiles(e.dataTransfer.files);
      }}
    >
      <div className="relative">
        {matches.length > 0 && (
          <div className="absolute bottom-full left-0 right-0 mb-2 z-50 glass rounded-2xl border border-white/15 overflow-hidden">
            <div className="flex items-center justify-between px-3 py-1.5 border-b border-white/10">
              <span className="text-[10px] uppercase tracking-wider text-white/35">
                Befehle
              </span>
              <span className="text-[10px] text-white/30">
                ↑↓ wählen · ⏎ ausführen · Esc schließen
              </span>
            </div>
            <div ref={listRef} className="max-h-[46vh] overflow-y-auto overscroll-contain py-1">
              {matches.map((command, index) => (
                <button
                  key={command.cmd}
                  onMouseEnter={() => setActive(index)}
                  onClick={() => pick(command)}
                  className={`w-full flex items-center gap-2.5 px-3 py-1.5 text-left transition-colors ${
                    index === active ? "bg-gold/15 text-white" : "text-white/70 hover:bg-white/5"
                  }`}
                >
                  <span className="text-[13px] w-5 text-center shrink-0">
                    {command.icon}
                  </span>
                  <span className="text-[12.5px] font-medium text-gold/90 shrink-0">
                    {command.cmd}
                    {command.arg ? (
                      <span className="text-white/30 font-normal"> &lt;{command.arg}&gt;</span>
                    ) : null}
                  </span>
                  <span className="text-[11.5px] text-white/45 truncate flex-1">
                    {command.title}
                  </span>
                  {command.aliases.length > 0 && (
                    <span className="hidden md:inline text-[10px] text-white/25 shrink-0">
                      {command.aliases.join(" ")}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}
        <div
          className={`glass rounded-2xl p-2 transition-colors ${
            dragging ? "border border-gold/60 bg-gold/10" : ""
          }`}
        >
          {attachments.length > 0 && (
            <div className="flex flex-wrap gap-1.5 px-2 pt-1 pb-2">
              {attachments.map((a) => (
                <span
                  key={a.id}
                  title={a.error ?? a.name}
                  className={`inline-flex items-center gap-1.5 text-[11px] px-2 py-1 rounded-lg border ${
                    a.status === "error"
                      ? "border-red-400/40 bg-red-400/10 text-red-300"
                      : "border-gold/30 bg-gold/10 text-gold/90"
                  }`}
                >
                  <span>{kindIcon(a.kind, a.status)}</span>
                  <span className="max-w-[180px] truncate">{a.name}</span>
                  <button
                    onClick={() => removeAttachment(a.id)}
                    className="text-white/40 hover:text-white/80 transition-colors"
                  >
                    ✕
                  </button>
                </span>
              ))}
            </div>
          )}
          <div className="flex items-end gap-2">
            <input
              ref={fileRef}
              type="file"
              multiple
              accept=".pdf,.txt,.md,.csv,.json,.log,.py,.js,.ts,.tsx,.html,.css,image/*"
              className="hidden"
              onChange={(e) => {
                if (e.target.files) addFiles(e.target.files);
                e.target.value = "";
              }}
            />
            <button
              onClick={() => fileRef.current?.click()}
              disabled={disabled}
              title="Datei anhängen (PDF, Bild, Text) — oder einfach reinziehen"
              className="flex items-center justify-center w-11 h-11 md:w-9 md:h-9 mb-0.5 shrink-0 rounded-xl border border-white/10 bg-white/5 text-white/40 hover:text-gold hover:border-gold/40 transition-colors disabled:opacity-40"
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
              </svg>
            </button>
            <textarea
              ref={ref}
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = Math.min(e.target.scrollHeight, 180) + "px";
              }}
              onKeyDown={onKey}
              onPaste={onPaste}
              rows={1}
              placeholder={dragging ? t("drop_file") : t("chat_placeholder")}
              className="flex-1 min-w-0 bg-transparent resize-none outline-none px-2 md:px-3 py-2.5 md:py-2 text-[16px] md:text-[15px] text-white/90 placeholder-white/30 max-h-44"
            />
            {streaming ? (
              <button
                onClick={onStop}
                className="px-4 py-2.5 md:py-2 shrink-0 rounded-xl bg-red-500/80 hover:bg-red-500 text-white font-medium transition"
              >
                Stop
              </button>
            ) : (
              <button
                onClick={submit}
                disabled={disabled || loading || (!text.trim() && ready.length === 0)}
                className="px-4 md:px-5 py-2.5 md:py-2 shrink-0 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold shadow-gold disabled:opacity-40 hover:brightness-110 transition"
              >
                {loading ? "Lese …" : "Senden"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
