import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import DeepLearningCard from "./DeepLearningCard";
import "../maps/glass.css";
import {
  ResearchSummary,
  STATUS_LABELS,
  deleteResearch,
  formatSpan,
  listResearch,
  researchFile,
  researchFiles,
  startResearch,
} from "../lib/research";
import type { MapsTheme } from "../lib/maps";

interface Props {
  onClose: () => void;
  openTaskId?: string;
}

function readTheme(): MapsTheme {
  return document.documentElement.classList.contains("light") ? "light" : "dark";
}

const PRESETS = [
  { label: "30 Minuten", minutes: 30 },
  { label: "1 Stunde", minutes: 60 },
  { label: "2 Stunden", minutes: 120 },
  { label: "4 Stunden", minutes: 240 },
];

export default function DeepLearning({ onClose, openTaskId }: Props) {
  const [topic, setTopic] = useState("");
  const [minutes, setMinutes] = useState(60);
  const [depth, setDepth] = useState<"schnell" | "normal" | "tief">("normal");
  const [history, setHistory] = useState<ResearchSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(openTaskId ?? null);
  const [files, setFiles] = useState<{ name: string; chars: number }[]>([]);
  const [openFile, setOpenFile] = useState<{ name: string; inhalt: string } | null>(
    null
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const data = await listResearch();
      setHistory(data.aufgaben);
      if (!activeId && data.aktiv.length > 0) setActiveId(data.aktiv[0].id);
    } catch {
      setError("Der Research-Dienst antwortet nicht.");
    }
  }, [activeId]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 6000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    if (!activeId) {
      setFiles([]);
      return;
    }
    researchFiles(activeId)
      .then((data) => setFiles(data.dateien))
      .catch(() => setFiles([]));
  }, [activeId, history]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (openFile) setOpenFile(null);
        else onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, openFile]);

  const launch = async () => {
    const text = topic.trim();
    if (!text) return;
    setBusy(true);
    setError("");
    try {
      const task = await startResearch(text, minutes, depth);
      setActiveId(task.id);
      setTopic("");
      await refresh();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message.slice(0, 200) : "Start fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: string) => {
    await deleteResearch(id).catch(() => undefined);
    if (activeId === id) setActiveId(null);
    await refresh();
  };

  return (
    <motion.div
      className="jm-root"
      data-jm-theme={readTheme()}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 80,
        display: "grid",
        placeItems: "center",
        background: "var(--jm-backdrop)",
        backdropFilter: "blur(22px) saturate(140%)",
        WebkitBackdropFilter: "blur(22px) saturate(140%)",
      }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <motion.div
        className="jm-glass"
        style={{
          width: "min(1080px, calc(100vw - 48px))",
          height: "min(760px, calc(100vh - 64px))",
          display: "flex",
          overflow: "hidden",
        }}
        initial={{ scale: 0.96, y: 18, filter: "blur(16px)" }}
        animate={{ scale: 1, y: 0, filter: "blur(0px)" }}
        exit={{ scale: 0.97, y: 12, filter: "blur(12px)" }}
        transition={{ duration: 0.44, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="jm-specular" />

        <div
          style={{
            width: 320,
            display: "flex",
            flexDirection: "column",
            borderRight: "1px solid var(--jm-hairline)",
            flex: "0 0 auto",
          }}
        >
          <div style={{ padding: "18px 18px 14px" }}>
            <div className="jm-brand" style={{ marginBottom: 14 }}>
              <span className="jm-brand-mark">🧠</span>
              Deep Learning
            </div>

            <div
              className="jm-glass jm-glass--thin"
              style={{ padding: "11px 13px", borderRadius: 18 }}
            >
              <textarea
                className="jm-field"
                value={topic}
                onChange={(event) => setTopic(event.target.value)}
                placeholder="Was soll Jon lernen? z. B. „Werde Spezialist für neuronale Netze“"
                rows={3}
                style={{ resize: "none", lineHeight: 1.5, fontSize: 13 }}
              />
            </div>

            <div style={{ display: "flex", gap: 5, marginTop: 10, flexWrap: "wrap" }}>
              {PRESETS.map((preset) => (
                <button
                  key={preset.minutes}
                  className="jm-chip"
                  data-active={minutes === preset.minutes}
                  onClick={() => setMinutes(preset.minutes)}
                >
                  {preset.label}
                </button>
              ))}
            </div>

            <div style={{ display: "flex", gap: 5, marginTop: 7 }}>
              {(["schnell", "normal", "tief"] as const).map((item) => (
                <button
                  key={item}
                  className="jm-chip"
                  data-tone="nav"
                  data-active={depth === item}
                  style={{ flex: 1, justifyContent: "center" }}
                  onClick={() => setDepth(item)}
                >
                  {item}
                </button>
              ))}
            </div>

            <button
              className="jm-chip jm-press"
              data-active="true"
              style={{
                width: "100%",
                justifyContent: "center",
                marginTop: 11,
                padding: "11px 14px",
                fontSize: 13,
              }}
              disabled={busy || !topic.trim()}
              onClick={() => void launch()}
            >
              {busy ? "Startet …" : "🚀 Recherche starten"}
            </button>

            {error && (
              <div
                style={{
                  marginTop: 9,
                  fontSize: 11.5,
                  color: "rgb(var(--jm-gold))",
                }}
              >
                {error}
              </div>
            )}
          </div>

          <div style={{ height: 1, background: "var(--jm-hairline)" }} />

          <div style={{ padding: "12px 16px 8px" }}>
            <span className="jm-title">Verlauf</span>
          </div>
          <div className="jm-scroll" style={{ flex: 1, padding: "0 10px 12px" }}>
            {history.length === 0 && (
              <div
                style={{
                  padding: "10px 8px",
                  fontSize: 12,
                  color: "var(--jm-text-faint)",
                  lineHeight: 1.55,
                }}
              >
                Noch keine Recherche. Gib Jon ein Thema und ein Zeitbudget — er
                sucht, liest, vergleicht und legt daraus einen Skill an.
              </div>
            )}
            {history.map((entry) => (
              <div
                key={entry.id}
                className="jm-row"
                data-active={entry.id === activeId}
                onClick={() => {
                  setActiveId(entry.id);
                  setOpenFile(null);
                }}
                style={{ marginBottom: 3, alignItems: "flex-start" }}
              >
                <span style={{ width: 18, textAlign: "center", fontSize: 14 }}>
                  {entry.status === "fertig"
                    ? "✅"
                    : entry.status === "fehler"
                      ? "⚠️"
                      : entry.status === "laeuft" || entry.status === "planung"
                        ? "🔄"
                        : entry.status === "pausiert"
                          ? "⏸️"
                          : "⏹️"}
                </span>
                <span style={{ flex: 1, minWidth: 0 }}>
                  <span
                    style={{
                      display: "block",
                      fontSize: 12.5,
                      fontWeight: 560,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {entry.titel}
                  </span>
                  <span
                    style={{
                      display: "block",
                      fontSize: 10.5,
                      color: "var(--jm-text-faint)",
                    }}
                  >
                    {STATUS_LABELS[entry.status]} · {formatSpan(entry.verbraucht_s)} ·{" "}
                    {entry.quellen} Quellen · {entry.dateien} Dateien
                    {entry.skill ? " · 1 Skill" : ""}
                  </span>
                </span>
                <button
                  className="jm-dock-btn"
                  style={{ width: 22, height: 22, fontSize: 10 }}
                  onClick={(event) => {
                    event.stopPropagation();
                    void remove(entry.id);
                  }}
                  title="Löschen"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>

        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            minWidth: 0,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "14px 18px",
              borderBottom: "1px solid var(--jm-hairline)",
            }}
          >
            <span className="jm-title" style={{ flex: 1 }}>
              {openFile ? openFile.name : "Live-Fortschritt"}
            </span>
            {openFile && (
              <button className="jm-chip" onClick={() => setOpenFile(null)}>
                ← Zurück
              </button>
            )}
            <button
              className="jm-dock-btn"
              style={{ width: 30, height: 30 }}
              onClick={onClose}
              title="Schließen (Esc)"
            >
              ✕
            </button>
          </div>

          <div className="jm-scroll" style={{ flex: 1, padding: 16 }}>
            <AnimatePresence mode="wait">
              {openFile ? (
                <motion.pre
                  key={openFile.name}
                  initial={{ opacity: 0, y: 10, filter: "blur(8px)" }}
                  animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.32 }}
                  style={{
                    whiteSpace: "pre-wrap",
                    fontSize: 12.5,
                    lineHeight: 1.65,
                    margin: 0,
                    fontFamily: "inherit",
                  }}
                >
                  {openFile.inhalt}
                </motion.pre>
              ) : activeId ? (
                <motion.div
                  key={activeId}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.32 }}
                >
                  <DeepLearningCard id={activeId} />
                  {files.length > 0 && (
                    <div style={{ marginTop: 16 }}>
                      <span className="jm-title">Wissensdateien</span>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))",
                          gap: 8,
                          marginTop: 10,
                        }}
                      >
                        {files.map((file) => (
                          <button
                            key={file.name}
                            className="jm-glass jm-glass--thin jm-press"
                            style={{
                              padding: "12px 13px",
                              borderRadius: 16,
                              textAlign: "left",
                              border: "none",
                              color: "inherit",
                            }}
                            onClick={() => {
                              if (!activeId) return;
                              void researchFile(activeId, file.name)
                                .then(setOpenFile)
                                .catch(() => undefined);
                            }}
                          >
                            <div style={{ fontSize: 12.5, fontWeight: 560 }}>
                              📄 {file.name}
                            </div>
                            <div
                              style={{
                                fontSize: 10.5,
                                color: "var(--jm-text-faint)",
                                marginTop: 3,
                              }}
                            >
                              {Math.round(file.chars / 1024)} KB
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </motion.div>
              ) : (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  style={{
                    height: "100%",
                    display: "grid",
                    placeItems: "center",
                    textAlign: "center",
                  }}
                >
                  <div style={{ maxWidth: 420 }}>
                    <div style={{ fontSize: 40, marginBottom: 12 }}>🧠</div>
                    <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>
                      Jon lernt selbstständig
                    </div>
                    <div
                      style={{
                        fontSize: 12.5,
                        lineHeight: 1.65,
                        color: "var(--jm-text-soft)",
                      }}
                    >
                      Gib ihm ein Thema und ein Zeitbudget. Er zerlegt es in
                      Unterthemen, sucht echte Quellen, liest und vergleicht sie,
                      erkennt Widersprüche, schreibt das Wissen in
                      Markdown-Dateien und legt daraus einen Skill an, den er ab
                      dann von selbst nutzt.
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
