import { useState } from "react";
import { getProviders } from "../lib/api";
import { setToken } from "../lib/token";

export default function TokenGate({ open }: { open: boolean }) {
  const [wert, setWert] = useState("");
  const [fehler, setFehler] = useState("");
  const [pruefe, setPruefe] = useState(false);

  if (!open) return null;

  const verbinden = async () => {
    const schluessel = wert.trim();
    if (!schluessel) return;
    setPruefe(true);
    setFehler("");
    const vorher = window.localStorage.getItem("jon.token") ?? "";
    setToken(schluessel);
    try {
      await getProviders();
      window.location.reload();
    } catch {
      setToken(vorher);
      setFehler("Dieser Schlüssel passt nicht.");
      setPruefe(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[95] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-sm rounded-2xl border border-gold/25 bg-[#0b0b0f] p-5">
        <div className="text-sm text-gold">Geräte-Schlüssel nötig</div>
        <p className="mt-2 text-[12px] leading-relaxed text-white/60">
          Jon läuft, lässt dich aber noch nicht herein. Öffne die Adresse mit
          angehängtem Schlüssel — <span className="text-white/80">…/app/?token=…</span> —
          oder trag ihn hier ein.
        </p>
        <p className="mt-2 text-[11px] leading-relaxed text-white/40">
          Am Raspberry Pi steht er in <span className="text-white/60">~/.jon/data/access.token</span>,
          am PC unter Einstellungen → Diagnose.
        </p>
        <input
          value={wert}
          onChange={(e) => setWert(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void verbinden();
          }}
          placeholder="Schlüssel einfügen"
          autoFocus
          className="mt-3 w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[12px] text-white/90 outline-none focus:border-gold/50"
        />
        {fehler && (
          <div className="mt-2 text-[11.5px] text-red-300">{fehler}</div>
        )}
        <button
          onClick={() => void verbinden()}
          disabled={pruefe || !wert.trim()}
          className="mt-3 w-full rounded-xl border border-gold/40 bg-gold/10 px-3 py-2 text-[12.5px] text-gold disabled:opacity-40 hover:bg-gold/20"
        >
          {pruefe ? "Prüfe…" : "Verbinden"}
        </button>
      </div>
    </div>
  );
}
