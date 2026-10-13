import { motion } from "framer-motion";
import { Check, Copy, Laptop, LoaderCircle, Smartphone, Tablet, Watch, X } from "lucide-react";
import { useEffect, useState } from "react";
import { handyKopplungAntworten, handyKopplungStand, handyQrUrl } from "../lib/api";

export interface KopplungDaten {
  art: "handy" | "tablet" | "uhr" | "jon";
  code?: string;
  code_gruppiert?: string;
  nutzlast?: string;
  ablauf?: number;
  pc?: string;
  anleitung?: string;
  fertig?: boolean;
  uhr?: string;
  handy?: string;
  jon?: string;
  heimnetz?: boolean;
}

type Stand = "offen" | "wartet" | "verbunden" | "abgelehnt" | "abgelaufen" | "abgeloest";

const SYMBOLE = { handy: Smartphone, tablet: Tablet, uhr: Watch, jon: Laptop };
const TITEL = { handy: "Neues Handy verbinden", tablet: "Neues Tablet verbinden", uhr: "Smartwatch verbinden", jon: "Anderen Jon verbinden" };

export default function KopplungKarte({ data }: { data: KopplungDaten }) {
  const Symbol = SYMBOLE[data.art] ?? Smartphone;
  const [stand, setStand] = useState<Stand>(data.fertig ? "verbunden" : "offen");
  const [geraet, setGeraet] = useState<{ name?: string; plattform?: string } | null>(null);
  const [rest, setRest] = useState(() => Math.max(0, Math.round((data.ablauf ?? 0) - Date.now() / 1000)));
  const [busy, setBusy] = useState(false);
  const [fehler, setFehler] = useState("");
  const [kopiert, setKopiert] = useState(false);

  useEffect(() => {
    if (data.fertig || !data.code) return;
    let lebt = true;
    let zeit: ReturnType<typeof setTimeout>;
    const pruefen = async () => {
      try {
        const s = await handyKopplungStand();
        if (!lebt) return;
        if (s.code && s.code !== data.code) {
          setStand("abgeloest");
          return;
        }
        setRest(Math.max(0, Number(s.rest ?? 0)));
        setGeraet((s.geraet as { name?: string; plattform?: string }) ?? null);
        const neu = String(s.status) as Stand;
        if (["offen", "wartet", "verbunden", "abgelehnt", "abgelaufen"].includes(neu)) setStand(neu);
        if (neu === "verbunden" || neu === "abgelehnt" || neu === "abgelaufen") return;
      } catch {
        if (!lebt) return;
      }
      zeit = setTimeout(pruefen, 1500);
    };
    void pruefen();
    return () => {
      lebt = false;
      clearTimeout(zeit);
    };
  }, [data.code, data.fertig]);

  async function antworten(ja: boolean) {
    setBusy(true);
    setFehler("");
    try {
      const r = await handyKopplungAntworten(ja);
      setStand(r.status === "ok" ? "verbunden" : "abgelehnt");
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Das hat nicht geklappt.");
    } finally {
      setBusy(false);
    }
  }

  const minuten = Math.floor(rest / 60);
  const sekunden = String(rest % 60).padStart(2, "0");
  const zeigtQr = !!data.nutzlast && (data.art === "handy" || data.art === "tablet") && (stand === "offen" || stand === "wartet");
  const fertigText =
    data.art === "uhr" && data.fertig
      ? `${data.uhr || "Die Uhr"} ist über ${data.handy || "dein Handy"} verbunden.`
      : data.art === "jon" && data.fertig
        ? `${data.jon || "Der andere Jon"} ist jetzt im Verbund.`
        : `${geraet?.name || "Das Gerät"} ist mit ${data.pc || "Jon"} verbunden.`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 380, damping: 30 }}
      className="w-full max-w-[460px] overflow-hidden rounded-2xl border border-gold/25 bg-gradient-to-br from-[#1b2340]/80 to-black/40 p-4"
    >
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 flex-none items-center justify-center rounded-xl bg-gold/15 text-gold">
          <Symbol size={20} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="font-semibold text-white">{data.art === "jon" && data.heimnetz ? "PC im Heimnetz verbinden" : TITEL[data.art] ?? "Gerät verbinden"}</div>
          <div className="text-[12.5px] text-white/55">
            {stand === "verbunden"
              ? "Fertig verbunden"
              : stand === "abgelehnt"
                ? "Abgelehnt"
                : stand === "abgelaufen"
                  ? "Der Code ist abgelaufen"
                  : stand === "abgeloest"
                    ? "Inzwischen läuft eine neuere Kopplung"
                    : data.code
                      ? `Gültig noch ${minuten}:${sekunden}`
                      : ""}
          </div>
        </div>
      </div>

      {stand === "verbunden" ? (
        <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="mt-4 flex items-center gap-2 rounded-xl bg-emerald-500/12 px-3 py-2.5 text-[13.5px] text-emerald-200">
          <Check size={16} />
          {fertigText}
        </motion.div>
      ) : null}

      {zeigtQr ? (
        <div className="mt-4 flex flex-col items-center gap-3 sm:flex-row sm:items-start">
          <img src={handyQrUrl(data.nutzlast!)} alt="QR-Code zum Koppeln" className="h-[168px] w-[168px] flex-none rounded-xl bg-white p-2" />
          <div className="min-w-0 text-[13px] leading-relaxed text-white/75">{data.anleitung}</div>
        </div>
      ) : stand === "offen" || stand === "wartet" ? (
        <div className="mt-3 text-[13px] leading-relaxed text-white/75">{data.anleitung}</div>
      ) : null}

      {data.code && (stand === "offen" || stand === "wartet") ? (
        <button
          onClick={() => {
            void navigator.clipboard?.writeText(data.code_gruppiert || data.code || "");
            setKopiert(true);
            setTimeout(() => setKopiert(false), 1600);
          }}
          className="mt-3 flex w-full items-center justify-between rounded-xl border border-white/10 bg-black/30 px-3 py-2 font-mono text-[17px] tracking-[0.18em] text-gold transition hover:border-gold/40"
        >
          {data.code_gruppiert || data.code}
          <span className="flex items-center gap-1 font-sans text-[11.5px] tracking-normal text-white/50">
            {kopiert ? <Check size={13} /> : <Copy size={13} />}
            {kopiert ? "Kopiert" : "Kopieren"}
          </span>
        </button>
      ) : null}

      {stand === "wartet" ? (
        <div className="mt-3 rounded-xl border border-gold/30 bg-gold/10 p-3">
          <div className="text-[13.5px] text-white">
            <b>{geraet?.name || "Ein Gerät"}</b> möchte sich verbinden{geraet?.plattform ? ` (${geraet.plattform})` : ""}.
          </div>
          <div className="mt-2.5 flex gap-2">
            <button
              disabled={busy}
              onClick={() => void antworten(true)}
              className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-gold py-2 text-[13px] font-semibold text-black transition hover:brightness-110 disabled:opacity-60"
            >
              {busy ? <LoaderCircle size={14} className="animate-spin" /> : <Check size={14} />}
              Erlauben
            </button>
            <button
              disabled={busy}
              onClick={() => void antworten(false)}
              className="flex items-center justify-center gap-1.5 rounded-lg bg-white/8 px-4 py-2 text-[13px] text-white/80 transition hover:bg-white/15 disabled:opacity-60"
            >
              <X size={14} />
              Ablehnen
            </button>
          </div>
        </div>
      ) : stand === "offen" && data.code ? (
        <div className="mt-3 flex items-center gap-2 text-[12px] text-white/45">
          <LoaderCircle size={13} className="animate-spin" />
          Warte auf das Gerät …
        </div>
      ) : null}

      {fehler ? <div className="mt-2 text-[12.5px] text-red-300">{fehler}</div> : null}
    </motion.div>
  );
}
