import { useRef, useState } from "react";
import { extractAttachment } from "../lib/api";
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
  const ref = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

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

  const onKey = (e: React.KeyboardEvent) => {
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
      className="p-4"
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
            className="flex items-center justify-center w-9 h-9 mb-0.5 rounded-xl border border-white/10 bg-white/5 text-white/40 hover:text-gold hover:border-gold/40 transition-colors disabled:opacity-40"
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
            className="flex-1 bg-transparent resize-none outline-none px-3 py-2 text-white/90 placeholder-white/30 max-h-44"
          />
          {streaming ? (
            <button
              onClick={onStop}
              className="px-4 py-2 rounded-xl bg-red-500/80 hover:bg-red-500 text-white font-medium transition"
            >
              Stop
            </button>
          ) : (
            <button
              onClick={submit}
              disabled={disabled || loading || (!text.trim() && ready.length === 0)}
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold shadow-gold disabled:opacity-40 hover:brightness-110 transition"
            >
              {loading ? "Lese …" : "Senden"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
