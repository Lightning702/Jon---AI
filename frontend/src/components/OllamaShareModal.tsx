import OllamaSharePanel from "./OllamaSharePanel";

export default function OllamaShareModal({
  onClose,
  onChanged,
}: {
  onClose: () => void;
  onChanged?: () => void;
}) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[560px] max-w-[92vw] max-h-[86vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <div>
            <div className="text-white/90 font-semibold">🤝 Ollama teilen</div>
            <div className="text-[11px] text-white/40">
              Gib deinen Ollama-Server frei oder verbinde dich mit dem eines
              anderen. Freigegeben wird nur das Antworten des Modells.
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition-colors"
          >
            ✕
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
          <OllamaSharePanel onModelsChanged={onChanged} />
        </div>
      </div>
    </div>
  );
}
