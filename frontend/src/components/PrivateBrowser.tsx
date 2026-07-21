import { privatBrowserUrl } from "../lib/api";

interface Props {
  onClose: () => void;
  onPopOut?: () => void;
}

export default function PrivateBrowser({ onClose, onPopOut }: Props) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[94vw] h-[88vh] max-w-[1180px] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/10">
          <div className="flex items-center gap-2">
            <span className="text-[15px]">🕶️</span>
            <div>
              <div className="text-white/90 font-semibold text-[13px]">
                Privater Browser
              </div>
              <div className="text-[11px] text-white/40">
                Kein Verlauf, keine Cookies, keine Anmeldung — nichts wird gespeichert.
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {onPopOut && (
              <button
                onClick={onPopOut}
                title="In eigenem Fenster öffnen"
                className="flex items-center gap-1 px-2.5 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition-colors text-[11px]"
              >
                ↗ Eigenes Fenster
              </button>
            )}
            <button
              onClick={onClose}
              className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition-colors"
            >
              ✕
            </button>
          </div>
        </div>
        <iframe
          title="Privater Browser"
          src={`${privatBrowserUrl()}?embed=1`}
          className="flex-1 w-full border-none bg-white"
          referrerPolicy="no-referrer"
        />
      </div>
    </div>
  );
}
