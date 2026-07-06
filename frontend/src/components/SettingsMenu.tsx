import { useState } from "react";
import { ToolMode } from "../lib/api";

export default function SettingsMenu({
  toolMode,
  onToolModeChange,
}: {
  toolMode: ToolMode;
  onToolModeChange: (mode: ToolMode) => void;
}) {
  const [open, setOpen] = useState(false);

  const options: { value: ToolMode; label: string; hint: string }[] = [
    {
      value: "ask",
      label: "Zuerst fragen",
      hint: "Jon fragt vor jeder PC-Aktion um Erlaubnis (Standard).",
    },
    {
      value: "allow",
      label: "Alles erlauben",
      hint: "Jon führt PC-Aktionen sofort ohne Nachfrage aus.",
    },
  ];

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        title="Einstellungen"
        className={`flex items-center justify-center w-7 h-7 rounded-full border transition-colors ${
          open
            ? "border-amber-400/40 bg-amber-400/10 text-amber-300"
            : "border-white/10 bg-white/5 text-white/40 hover:text-white/70"
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
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.09a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.09a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.09a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-9 z-50 w-72 glass rounded-2xl border border-white/15 px-4 py-3 text-left">
            <div className="text-[11px] uppercase tracking-wide text-white/40 mb-2">
              PC-Steuerung durch Jon
            </div>
            <div className="space-y-1.5">
              {options.map((o) => (
                <button
                  key={o.value}
                  onClick={() => {
                    onToolModeChange(o.value);
                    setOpen(false);
                  }}
                  className={`w-full text-left px-3 py-2 rounded-xl border transition-colors ${
                    toolMode === o.value
                      ? "border-gold/40 bg-gold/10"
                      : "border-white/10 bg-white/5 hover:bg-white/10"
                  }`}
                >
                  <div className="flex items-center gap-2 text-[12px] text-white/90">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        toolMode === o.value ? "bg-gold" : "bg-white/20"
                      }`}
                    />
                    {o.label}
                  </div>
                  <div className="text-[11px] text-white/45 mt-0.5 pl-4">
                    {o.hint}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
