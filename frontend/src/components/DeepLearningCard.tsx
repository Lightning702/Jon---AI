import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import "../maps/glass.css";
import {
  ACTIVE_STATES,
  ResearchTask,
  STATUS_LABELS,
  controlResearch,
  formatClock,
  getResearch,
  watchResearch,
} from "../lib/research";
import type { MapsTheme } from "../lib/maps";

interface Props {
  id: string;
  initial?: ResearchTask;
  onOpen?: (id: string) => void;
}

function readTheme(): MapsTheme {
  return document.documentElement.classList.contains("light") ? "light" : "dark";
}

const KIND_TONE: Record<string, string> = {
  fehler: "rgb(var(--jm-gold))",
  uebersprungen: "var(--jm-text-faint)",
  speichern: "rgb(var(--jm-nav))",
  skill: "rgb(var(--jm-gold))",
  fertig: "rgb(var(--jm-nav))",
};

export default function DeepLearningCard({ id, initial, onOpen }: Props) {
  const [task, setTask] = useState<ResearchTask | null>(initial ?? null);
  const [busy, setBusy] = useState(false);
  const [tick, setTick] = useState(0);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    getResearch(id)
      .then((data) => {
        if (alive) setTask(data);
      })
      .catch(() => undefined);
    const stop = watchResearch(id, (data) => {
      if (alive) setTask(data);
    });
    return () => {
      alive = false;
      stop();
    };
  }, [id]);

  useEffect(() => {
    if (!task || !ACTIVE_STATES.includes(task.status)) return;
    const timer = window.setInterval(() => setTick((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [task?.status]);

  useEffect(() => {
    const holder = logRef.current;
    if (holder) holder.scrollTop = holder.scrollHeight;
  }, [task?.protokoll.length]);

  if (!task) {
    return (
      <div
        className="jm-root"
        data-jm-theme={readTheme()}
        style={{ height: "auto", marginTop: 4 }}
      >
        <div className="jm-glass" style={{ padding: 16, borderRadius: 20 }}>
          <div className="jm-sheen-sweep" />
          <span style={{ fontSize: 12.5, color: "var(--jm-text-faint)" }}>
            Deep Learning wird geladen …
          </span>
        </div>
      </div>
    );
  }

  const running = ACTIVE_STATES.includes(task.status);
  const drift = running && task.status === "laeuft" ? tick % 2 : 0;
  const remaining = Math.max(0, task.verbleibend_s - drift);
  const percent = Math.round(task.fortschritt * 100);
  const blocks = 20;
  const filled = Math.max(0, Math.min(blocks, Math.round(task.fortschritt * blocks)));
  const usedSources = task.quellen.filter((s) => s.status === "genutzt").length;

  const control = async (
    action: "pause" | "resume" | "stop" | "resume_task"
  ) => {
    setBusy(true);
    try {
      setTask(await controlResearch(task.id, action));
    } catch {
      try {
        setTask(await getResearch(task.id));
      } catch {
        return;
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <motion.div
      className="jm-root"
      data-jm-theme={readTheme()}
      style={{ height: "auto", marginTop: 4 }}
      initial={{ opacity: 0, y: 12, filter: "blur(10px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      transition={{ duration: 0.44, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="jm-glass" style={{ borderRadius: 20, overflow: "hidden" }}>
        <div className="jm-specular" />
        {running && <div className="jm-sheen-sweep" />}

        <div style={{ padding: "13px 15px 11px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
            <span
              className="jm-brand-mark"
              style={{ width: 22, height: 22, fontSize: 11 }}
            >
              🧠
            </span>
            <span
              className="jm-title"
              style={{ flex: 1, fontSize: 10.5, letterSpacing: "0.14em" }}
            >
              Jon Deep Learning
            </span>
            <span
              className="jm-chip"
              style={{ cursor: "default", padding: "4px 10px", fontSize: 10.5 }}
              data-active={running}
            >
              {STATUS_LABELS[task.status]}
            </span>
          </div>

          <div
            style={{
              fontSize: 16,
              fontWeight: 640,
              marginTop: 9,
              textTransform: "uppercase",
              letterSpacing: "0.02em",
            }}
          >
            {task.titel}
          </div>

          <div
            className="jm-mono"
            style={{
              marginTop: 9,
              fontSize: 12,
              letterSpacing: "0.06em",
              color: "rgb(var(--jm-gold))",
              overflow: "hidden",
              whiteSpace: "nowrap",
            }}
          >
            {"█".repeat(filled)}
            <span style={{ color: "var(--jm-text-faint)" }}>
              {"░".repeat(blocks - filled)}
            </span>
            <span style={{ color: "var(--jm-text-soft)", marginLeft: 10 }}>
              {percent}%
            </span>
          </div>

          <div className="jm-bar" style={{ marginTop: 8 }}>
            <div className="jm-bar-fill" style={{ width: `${percent}%` }} />
          </div>

          <div
            style={{
              display: "flex",
              gap: 14,
              marginTop: 10,
              fontSize: 11.5,
              color: "var(--jm-text-soft)",
              flexWrap: "wrap",
            }}
          >
            <span>
              ⏳ Noch <b className="jm-mono">{formatClock(remaining)}</b>
            </span>
            <span>🌐 {usedSources} Quellen</span>
            <span>💾 {task.dateien.length} Dateien</span>
            {task.skill && <span>🧠 Skill {task.skill}</span>}
          </div>

          <div style={{ marginTop: 10, fontSize: 12, lineHeight: 1.55 }}>
            <div>
              <span style={{ color: "var(--jm-text-faint)" }}>
                Aktuelles Thema:{" "}
              </span>
              {task.aktuelles_thema || task.titel}
            </div>
            <div>
              <span style={{ color: "var(--jm-text-faint)" }}>Status: </span>
              {task.phase}
            </div>
          </div>
        </div>

        <div style={{ height: 1, background: "var(--jm-hairline)" }} />

        <div
          ref={logRef}
          className="jm-scroll"
          style={{ maxHeight: 186, padding: "8px 10px" }}
        >
          <AnimatePresence initial={false}>
            {task.protokoll.slice(-40).map((entry, index) => (
              <div
                key={`${entry.ts}-${index}`}
                className="jm-log-line"
                style={{ color: KIND_TONE[entry.kind] ?? "var(--jm-text)" }}
              >
                <span style={{ width: 18, textAlign: "center", flex: "0 0 auto" }}>
                  {entry.icon}
                </span>
                <span style={{ minWidth: 0, flex: 1 }}>
                  <span style={{ fontWeight: 550 }}>{entry.title}</span>
                  {entry.detail && (
                    <span
                      style={{
                        display: "block",
                        color: "var(--jm-text-faint)",
                        fontSize: 11,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {entry.detail}
                    </span>
                  )}
                </span>
                <span
                  className="jm-mono"
                  style={{ color: "var(--jm-text-faint)", flex: "0 0 auto" }}
                >
                  {new Date(entry.ts * 1000).toLocaleTimeString("de-DE", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </span>
              </div>
            ))}
          </AnimatePresence>
        </div>

        <div style={{ height: 1, background: "var(--jm-hairline)" }} />

        <div style={{ display: "flex", gap: 7, padding: "10px 12px 12px" }}>
          {task.status === "laeuft" && (
            <button
              className="jm-chip"
              disabled={busy}
              onClick={() => void control("pause")}
            >
              ⏸️ Pause
            </button>
          )}
          {task.status === "pausiert" && (
            <button
              className="jm-chip"
              data-active="true"
              disabled={busy}
              onClick={() => void control("resume")}
            >
              ▶️ Fortsetzen
            </button>
          )}
          {running && (
            <button
              className="jm-chip"
              disabled={busy}
              onClick={() => void control("stop")}
            >
              ⏹️ Abbrechen
            </button>
          )}
          {!running && task.status !== "fertig" && (
            <button
              className="jm-chip"
              data-active="true"
              disabled={busy}
              onClick={() => void control("resume_task")}
            >
              🔁 Weiterforschen
            </button>
          )}
          <div style={{ flex: 1 }} />
          {onOpen && (
            <button className="jm-chip" onClick={() => onOpen(task.id)}>
              📚 Wissen öffnen
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}
