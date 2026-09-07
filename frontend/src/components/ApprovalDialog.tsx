import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { toolDetail, toolLabel } from "../lib/toolInfo";
import { useT } from "../hooks/useT";

export interface ApprovalRequest {
  id: string;
  name: string;
  args?: Record<string, unknown>;
  summary?: string;
  risiko?: string;
}

const RISIKO_SCHLUESSEL = {
  niedrig: "ap_risk_low",
  mittel: "ap_risk_mid",
  hoch: "ap_risk_high",
} as const;

export default function ApprovalDialog({
  request,
  onDecide,
}: {
  request: ApprovalRequest;
  onDecide: (approved: boolean) => void;
}) {
  const [showDetail, setShowDetail] = useState(false);
  const detail = toolDetail(request.name, request.args);
  const { t } = useT();
  const erlaubenRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    erlaubenRef.current?.focus();
    const taste = (ereignis: KeyboardEvent) => {
      if (ereignis.key === "Escape") {
        ereignis.preventDefault();
        onDecide(false);
      }
      if (ereignis.key === "Enter" && ereignis.ctrlKey) {
        ereignis.preventDefault();
        onDecide(true);
      }
    };
    window.addEventListener("keydown", taste);
    return () => window.removeEventListener("keydown", taste);
  }, [onDecide, request.id]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={t("ap_title")}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.18 }}
        className="glass rounded-2xl border border-gold/30 max-w-md w-[92%] px-6 py-5"
      >
        <div className="flex items-center gap-2 mb-3">
          <span
            className={`w-2 h-2 rounded-full animate-pulse ${
              request.risiko === "hoch" ? "bg-red-400" : "bg-gold"
            }`}
          />
          <h2 className="text-sm font-semibold gold-text flex-1">
            {t("ap_title")}
          </h2>
          {request.risiko && (
            <span
              className={`text-[10px] px-2 py-0.5 rounded-lg border ${
                request.risiko === "hoch"
                  ? "border-red-400/40 bg-red-400/10 text-red-300"
                  : "border-white/15 bg-white/5 text-white/50"
              }`}
            >
              {t(
                RISIKO_SCHLUESSEL[
                  request.risiko as keyof typeof RISIKO_SCHLUESSEL
                ] ?? "ap_risk_low",
              )}
            </span>
          )}
        </div>
        <div className="text-[13px] text-white/85 mb-1 whitespace-pre-line">
          <span className="inline-block text-[11px] px-2 py-0.5 rounded-lg bg-gold/10 border border-gold/25 text-gold/90 mr-2">
            {toolLabel(request.name)}
          </span>
          {request.summary ?? ""}
        </div>
        {detail && (
          <div className="mb-3">
            <button
              onClick={() => setShowDetail((v) => !v)}
              className="text-[11px] text-gold/70 hover:text-gold transition"
            >
              {showDetail ? t("ap_details_hide") : t("ap_details_show")}
            </button>
            {showDetail && (
              <pre className="mt-2 text-[11px] text-gold/80 whitespace-pre-wrap break-all font-mono rounded-lg bg-black/30 border border-gold/20 px-3 py-2 max-h-40 overflow-y-auto">
                {detail}
              </pre>
            )}
          </div>
        )}
        <div className="flex justify-end gap-2 mt-4">
          <button
            onClick={() => onDecide(false)}
            className="text-[12px] px-4 py-2 rounded-xl border border-white/15 text-white/70 hover:bg-white/5 transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-gold/70"
          >
            {t("ap_deny")}
          </button>
          <button
            ref={erlaubenRef}
            onClick={() => onDecide(true)}
            className="text-[12px] px-4 py-2 rounded-xl bg-gradient-to-br from-gold-light/90 to-gold-dark/90 text-black font-semibold hover:opacity-90 transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
          >
            {t("ap_allow")}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
