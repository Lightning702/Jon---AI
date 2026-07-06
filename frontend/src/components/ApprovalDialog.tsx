import { motion } from "framer-motion";
import { useState } from "react";
import { toolDetail, toolLabel } from "../lib/toolInfo";

export interface ApprovalRequest {
  id: string;
  name: string;
  args?: Record<string, unknown>;
  summary?: string;
}

export default function ApprovalDialog({
  request,
  onDecide,
}: {
  request: ApprovalRequest;
  onDecide: (approved: boolean) => void;
}) {
  const [showDetail, setShowDetail] = useState(false);
  const detail = toolDetail(request.name, request.args);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.18 }}
        className="glass rounded-2xl border border-gold/30 max-w-md w-[92%] px-6 py-5"
      >
        <div className="flex items-center gap-2 mb-3">
          <span className="w-2 h-2 rounded-full bg-gold animate-pulse" />
          <h2 className="text-sm font-semibold gold-text">
            Jon möchte etwas ausführen
          </h2>
        </div>
        <div className="text-[13px] text-white/85 mb-1">
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
              {showDetail ? "Details verbergen" : "Details anzeigen"}
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
            className="text-[12px] px-4 py-2 rounded-xl border border-white/15 text-white/70 hover:bg-white/5 transition"
          >
            Ablehnen
          </button>
          <button
            onClick={() => onDecide(true)}
            className="text-[12px] px-4 py-2 rounded-xl bg-gradient-to-br from-gold-light/90 to-gold-dark/90 text-black font-semibold hover:opacity-90 transition"
          >
            Erlauben
          </button>
        </div>
      </motion.div>
    </div>
  );
}
