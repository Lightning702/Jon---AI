import { motion, AnimatePresence } from "framer-motion";

export type VoiceUiState =
  | "idle"
  | "listening"
  | "recording"
  | "transcribing"
  | "armed"
  | "processing"
  | "speaking"
  | "done"
  | "error";

const CONFIG: Record<
  Exclude<VoiceUiState, "idle">,
  { label: string; dot: string; pulse: boolean }
> = {
  listening: { label: "Sag „Jon“ …", dot: "bg-white/40", pulse: false },
  recording: { label: "Höre …", dot: "bg-amber-400", pulse: true },
  transcribing: { label: "Verstehe …", dot: "bg-amber-400", pulse: true },
  armed: { label: "Jon hört zu …", dot: "bg-amber-400", pulse: true },
  processing: { label: "Jon verarbeitet …", dot: "bg-amber-400", pulse: true },
  speaking: { label: "Jon spricht …", dot: "bg-amber-400", pulse: true },
  done: { label: "Erledigt", dot: "bg-emerald-400", pulse: false },
  error: { label: "Nicht verstanden", dot: "bg-red-400", pulse: false },
};

export default function VoiceIndicator({
  state,
  detail,
}: {
  state: VoiceUiState;
  detail?: string;
}) {
  if (state === "idle") return null;
  const cfg = CONFIG[state];
  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 16 }}
        className="fixed bottom-24 right-6 z-50 max-w-xs"
      >
        <div className="flex items-center gap-2.5 rounded-full border border-white/10 bg-black/70 backdrop-blur-md px-4 py-2 shadow-lg shadow-black/40">
          <span className="relative flex h-2.5 w-2.5">
            {cfg.pulse && (
              <span
                className={`absolute inline-flex h-full w-full rounded-full ${cfg.dot} opacity-60 animate-ping`}
              />
            )}
            <span
              className={`relative inline-flex h-2.5 w-2.5 rounded-full ${cfg.dot}`}
            />
          </span>
          <div className="min-w-0">
            <div className="text-xs text-white/80">{cfg.label}</div>
            {detail && (
              <div className="text-[11px] text-white/45 truncate">{detail}</div>
            )}
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
