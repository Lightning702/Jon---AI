import { motion } from "framer-motion";
import { useState } from "react";

export interface ToolStep {
  name: string;
  done: boolean;
  ok?: boolean;
}

export interface ChatEntry {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning?: string;
  streaming?: boolean;
  tools?: ToolStep[];
}

const TOOL_LABELS: Record<string, string> = {
  run_powershell: "PowerShell",
  run_cmd: "CMD",
  open_url: "URL öffnen",
  start_program: "Programm starten",
  kill_program: "Programm beenden",
  open_explorer: "Explorer",
  list_dir: "Ordner lesen",
  read_file: "Datei lesen",
  write_file: "Datei schreiben",
  move_path: "Verschieben",
  delete_path: "Löschen",
  open_in_vscode: "VS Code",
};

export default function MessageBubble({ entry }: { entry: ChatEntry }) {
  const isUser = entry.role === "user";
  const [showReasoning, setShowReasoning] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div className={`max-w-[76%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`px-4 py-3 rounded-2xl leading-relaxed whitespace-pre-wrap ${
            isUser
              ? "bg-gradient-to-br from-gold-light/90 to-gold-dark/90 text-black rounded-br-md"
              : "glass text-white/90 rounded-bl-md"
          }`}
        >
          {entry.tools && entry.tools.length > 0 && !isUser && (
            <div className="mb-2 flex flex-wrap gap-1.5">
              {entry.tools.map((t, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1.5 text-[11px] px-2 py-1 rounded-lg bg-gold/10 border border-gold/25 text-gold/90"
                >
                  {!t.done ? (
                    <span className="w-2 h-2 rounded-full bg-gold animate-pulse" />
                  ) : (
                    <span>{t.ok ? "✓" : "✕"}</span>
                  )}
                  {TOOL_LABELS[t.name] ?? t.name}
                </span>
              ))}
            </div>
          )}
          {entry.reasoning && !isUser && (
            <div className="mb-2">
              <button
                onClick={() => setShowReasoning((v) => !v)}
                className="text-[11px] text-gold/70 hover:text-gold transition"
              >
                {showReasoning ? "Denkprozess verbergen" : "Denkprozess anzeigen"}
              </button>
              {showReasoning && (
                <pre className="mt-2 text-[12px] text-white/50 whitespace-pre-wrap border-l-2 border-gold/30 pl-3">
                  {entry.reasoning}
                </pre>
              )}
            </div>
          )}
          <span>{entry.content}</span>
          {entry.streaming && (
            <span className="inline-block w-2 h-4 ml-0.5 align-middle bg-gold animate-pulse rounded-sm" />
          )}
        </div>
      </div>
    </motion.div>
  );
}
