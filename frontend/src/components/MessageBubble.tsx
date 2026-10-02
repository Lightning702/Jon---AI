import { AnimatePresence, motion } from "framer-motion";
import { Suspense, lazy, useState } from "react";
import { toolDetail, toolLabel } from "../lib/toolInfo";
import { ohneTabellen } from "../lib/text";
import type { MapsCardData } from "../lib/maps";
import type { BrowserTaskDaten, JonDatei, JonUhr, JonWecker, StudioWork } from "../lib/api";
import type { ZeitAnfrageDaten } from "./ZeitAnfrageCard";
import { harnessRequest } from "../lib/harness";

const MapsCard = lazy(() => import("./MapsCard"));
const DeepLearningCard = lazy(() => import("./DeepLearningCard"));
const BildCard = lazy(() => import("./BildCard"));
const DateiCard = lazy(() => import("./DateiCard"));
const BrowserCard = lazy(() => import("./BrowserCard"));
const ZeitCard = lazy(() => import("./ZeitCard"));
const ZeitAnfrageCard = lazy(() => import("./ZeitAnfrageCard"));
const Wochenbericht = lazy(() => import("./Wochenbericht"));
const FachteamKarte = lazy(() => import("./agenten/FachteamKarte"));
const HarnessKarte = lazy(() => import("./agenten/HarnessKarte"));

export interface ToolStep {
  name: string;
  done: boolean;
  ok?: boolean;
  args?: Record<string, unknown>;
  summary?: string;
}

export interface AttachmentChip {
  name: string;
  kind: string;
}

export type ChatCard =
  | { id: string; kind: "maps"; data: MapsCardData }
  | { id: string; kind: "deep_learning"; data: { id: string } }
  | { id: string; kind: "bild"; data: StudioWork }
  | { id: string; kind: "browser"; data: BrowserTaskDaten }
  | { id: string; kind: "datei"; data: { dateien: JonDatei[] } }
  | { id: string; kind: "zeit"; data: { uhren: JonUhr[]; wecker?: JonWecker[] } }
  | { id: string; kind: "zeitanfrage"; data: ZeitAnfrageDaten }
  | { id: string; kind: "wochenbericht"; data: { geraet: string; bis?: string } }
  | { id: string; kind: "agenten"; data: { id: string; aufgabe?: string } }
  | { id: string; kind: "harness"; data: { id: string } };

export interface ChatEntry {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning?: string;
  streaming?: boolean;
  tools?: ToolStep[];
  cards?: ChatCard[];
  attachments?: AttachmentChip[];
  attachmentText?: string;
}

interface BubbleProps {
  entry: ChatEntry;
  onOpenMaps?: (data: MapsCardData) => void;
  onOpenResearch?: (id: string) => void;
  onOpenStudio?: () => void;
  onOpenHarness?: (id: string) => void;
}

function JonDenkt({ text }: { text: string }) {
  return (
    <span className="flex items-center gap-2.5">
      <span className="jon-denkt" aria-hidden="true">
        <span />
        <i />
      </span>
      <span className="jon-schimmer text-[12.5px]">{text}</span>
    </span>
  );
}

export default function MessageBubble({
  entry,
  onOpenMaps,
  onOpenResearch,
  onOpenStudio,
  onOpenHarness,
}: BubbleProps) {
  const isUser = entry.role === "user";
  const [showReasoning, setShowReasoning] = useState(false);
  const [openTool, setOpenTool] = useState<number | null>(null);

  const expanded = openTool !== null ? entry.tools?.[openTool] : undefined;
  const detail = expanded ? toolDetail(expanded.name, expanded.args) : "";
  const laufend = entry.tools?.some((t) => !t.done) ?? false;
  const hatKarten = !isUser && !!entry.cards?.length;
  const zeigtBlase = isUser || !!entry.content || (entry.streaming && !hatKarten) || !!entry.attachments?.length;

  if (isUser) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 12, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ type: "spring", stiffness: 380, damping: 30 }}
        className="flex justify-end"
      >
        <div className="max-w-[92%] md:max-w-[76%] px-4 py-3 rounded-2xl rounded-br-md leading-relaxed whitespace-pre-wrap bg-gradient-to-br from-gold-light/90 to-gold-dark/90 text-black shadow-[0_10px_30px_rgba(154,123,31,0.18)]">
          {entry.attachments && entry.attachments.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-1.5">
              {entry.attachments.map((a, i) => (
                <span key={i} className="inline-flex items-center gap-1.5 text-[11px] px-2 py-1 rounded-lg border border-black/20 bg-black/10 text-black/80">
                  <span>{a.kind === "image" ? "🖼️" : a.kind === "pdf" ? "📄" : "📎"}</span>
                  <span className="max-w-[180px] truncate">{a.name}</span>
                </span>
              ))}
            </div>
          )}
          {entry.content}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.2, 0.8, 0.2, 1] }}
      className="flex justify-start"
    >
      <div className={`${hatKarten ? "max-w-[96%] w-full md:max-w-[86%] md:w-[560px]" : "max-w-[92%] md:max-w-[76%]"} flex flex-col items-start gap-2`}>
        {entry.tools && entry.tools.length > 0 && (
          <div className="w-full">
            <div className="flex flex-wrap gap-1.5">
              <AnimatePresence initial={false}>
                {entry.tools.map((t, i) => (
                  <motion.button
                    key={i}
                    layout
                    initial={{ opacity: 0, scale: 0.85, y: 4 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    transition={{ type: "spring", stiffness: 420, damping: 26 }}
                    onClick={() => setOpenTool((v) => (v === i ? null : i))}
                    title={t.summary || "Klicken für Details"}
                    className={`inline-flex items-center gap-1.5 text-[11px] pl-1.5 pr-2.5 py-1 rounded-full border transition-colors cursor-pointer ${
                      openTool === i
                        ? "bg-gold/25 border-gold/50 text-gold"
                        : !t.done
                          ? "bg-gold/10 border-gold/35 text-gold"
                          : t.ok
                            ? "bg-white/[0.04] border-white/10 text-white/70 hover:border-gold/30 hover:text-gold"
                            : "bg-red-500/10 border-red-400/25 text-red-200/90"
                    }`}
                  >
                    <span className="w-4 h-4 grid place-items-center">
                      {!t.done ? (
                        <span className="jon-chip-spinner" />
                      ) : (
                        <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 500, damping: 18 }} className={t.ok ? "text-emerald-300" : "text-red-300"}>
                          {t.ok ? "✓" : "✕"}
                        </motion.span>
                      )}
                    </span>
                    <span className={!t.done ? "jon-schimmer" : ""}>{toolLabel(t.name)}</span>
                  </motion.button>
                ))}
              </AnimatePresence>
            </div>
            <AnimatePresence initial={false}>
              {expanded && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden"
                >
                  <div className="mt-2 text-[12px] rounded-xl glass px-3 py-2 space-y-1.5">
                    {expanded.summary && <div className="text-white/70">{expanded.summary}</div>}
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
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
        {entry.reasoning && (
          <div>
            <button
              onClick={() => setShowReasoning((v) => !v)}
              className="text-[11px] text-gold/70 hover:text-gold transition"
            >
              {showReasoning ? "Denkprozess verbergen" : "Denkprozess anzeigen"}
            </button>
            <AnimatePresence initial={false}>
              {showReasoning && (
                <motion.pre
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-2 text-[12px] text-white/50 whitespace-pre-wrap border-l-2 border-gold/30 pl-3 overflow-hidden"
                >
                  {entry.reasoning}
                </motion.pre>
              )}
            </AnimatePresence>
          </div>
        )}
        {hatKarten && (
          <Suspense
            fallback={
              <div className="text-[12px] text-white/40">Ansicht wird geladen …</div>
            }
          >
            <div className="w-full space-y-2">
              {entry.cards!.map((card) =>
                card.kind === "maps" ? (
                  <MapsCard
                    key={card.id}
                    data={card.data}
                    onOpen={(data) => onOpenMaps?.(data)}
                  />
                ) : card.kind === "bild" ? (
                  <BildCard
                    key={card.id}
                    data={card.data}
                    onOpen={onOpenStudio ? () => onOpenStudio() : undefined}
                  />
                ) : card.kind === "browser" ? (
                  <BrowserCard key={card.id} data={card.data} />
                ) : card.kind === "datei" ? (
                  <DateiCard key={card.id} dateien={card.data.dateien ?? []} />
                ) : card.kind === "zeit" ? (
                  <ZeitCard
                    key={card.id}
                    uhren={card.data.uhren ?? []}
                    wecker={card.data.wecker}
                  />
                ) : card.kind === "zeitanfrage" ? (
                  <ZeitAnfrageCard key={card.id} data={card.data} />
                ) : card.kind === "wochenbericht" ? (
                  <Wochenbericht key={card.id} geraet={card.data.geraet} bis={card.data.bis} />
                ) : card.kind === "agenten" ? (
                  <FachteamKarte key={card.id} id={card.data.id} aufgabe={card.data.aufgabe} request={harnessRequest} />
                ) : card.kind === "harness" ? (
                  <HarnessKarte key={card.id} id={card.data.id} request={harnessRequest} onOeffnen={onOpenHarness} />
                ) : (
                  <DeepLearningCard
                    key={card.id}
                    id={card.data.id}
                    onOpen={(id) => onOpenResearch?.(id)}
                  />
                )
              )}
            </div>
          </Suspense>
        )}
        {zeigtBlase && (
          <div className="px-4 py-3 rounded-2xl rounded-bl-md leading-relaxed whitespace-pre-wrap glass text-white/90">
            {entry.streaming && !entry.content ? (
              <JonDenkt text={laufend ? "Jon arbeitet …" : "Jon denkt nach …"} />
            ) : (
              <>
                <span>{ohneTabellen(entry.content)}</span>
                {entry.streaming && (
                  <span className="inline-block w-2 h-4 ml-0.5 align-middle bg-gold animate-pulse rounded-sm" />
                )}
              </>
            )}
          </div>
        )}
        {entry.streaming && !entry.content && hatKarten && <JonDenkt text="Jon arbeitet mit seinem Team …" />}
      </div>
    </motion.div>
  );
}
