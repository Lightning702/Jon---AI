import { motion } from "framer-motion";
import { useState } from "react";
import { toolDetail, toolLabel } from "../lib/toolInfo";

export interface ToolStep {
  name: string;
  done: boolean;
  ok?: boolean;
  args?: Record<string, unknown>;
  summary?: string;
}

export interface ChatEntry {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning?: string;
  streaming?: boolean;
  tools?: ToolStep[];
}

export default function MessageBubble({ entry }: { entry: ChatEntry }) {
  const isUser = entry.role === "user";
  const [showReasoning, setShowReasoning] = useState(false);
  const [openTool, setOpenTool] = useState<number | null>(null);

  const expanded = openTool !== null ? entry.tools?.[openTool] : undefined;
  const detail = expanded ? toolDetail(expanded.name, expanded.args) : "";

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
            <div className="mb-2">
              <div className="flex flex-wrap gap-1.5">
                {entry.tools.map((t, i) => (
                  <button
                    key={i}
                    onClick={() => setOpenTool((v) => (v === i ? null : i))}
                    title="Klicken für Details"
                    className={`inline-flex items-center gap-1.5 text-[11px] px-2 py-1 rounded-lg border transition-colors cursor-pointer ${
                      openTool === i
                        ? "bg-gold/25 border-gold/50 text-gold"
                        : "bg-gold/10 border-gold/25 text-gold/90 hover:bg-gold/20"
                    }`}
                  >
                    {!t.done ? (
                      <span className="w-2 h-2 rounded-full bg-gold animate-pulse" />
                    ) : (
                      <span>{t.ok ? "✓" : "✕"}</span>
                    )}
                    {toolLabel(t.name)}
                  </button>
                ))}
              </div>
              {expanded && (
                <div className="mt-2 text-[12px] rounded-lg bg-black/30 border border-gold/20 px-3 py-2 space-y-1.5">
                  {expanded.summary && (
                    <div className="text-white/70">{expanded.summary}</div>
                  )}
                  {detail && (
                    <pre className="text-gold/80 whitespace-pre-wrap break-all font-mono text-[11px] border-l-2 border-gold/30 pl-2">
                      {detail}
                    </pre>
                  )}
                  {expanded.done && (
                    <div className="text-white/40">
                      {expanded.ok ? "Erfolgreich ausgeführt" : "Fehlgeschlagen oder abgelehnt"}
                    </div>
                  )}
                </div>
              )}
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
