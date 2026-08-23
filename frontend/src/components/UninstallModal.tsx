import { useEffect, useState } from "react";
import { BASE } from "../lib/api";

interface Eintrag {
  id: string;
  titel: string;
  beschreibung: string;
  pfad: string;
  dateien: number;
  bytes: number;
  vorhanden: boolean;
}

interface Plan {
  bestaetigung: string;
  eintraege: Eintrag[];
  bytes_gesamt: number;
  dateien_gesamt: number;
  programm_entfernbar: boolean;
  programm_hinweis: string;
  quellordner: string;
}

interface Schritt {
  schritt: string;
  ok: boolean;
  hinweis: string;
}

function groesse(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export default function UninstallModal({ onClose }: { onClose: () => void }) {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [fehler, setFehler] = useState("");
  const [eingabe, setEingabe] = useState("");
  const [programm, setProgramm] = useState(true);
  const [laeuft, setLaeuft] = useState(false);
  const [schritte, setSchritte] = useState<Schritt[] | null>(null);

  useEffect(() => {
    let abgebrochen = false;
    fetch(`${BASE}/system/uninstall/plan`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d: Plan) => {
        if (!abgebrochen) setPlan(d);
      })
      .catch(() => {
        if (!abgebrochen) setFehler("Jon konnte nicht ermitteln, was gelöscht würde.");
      });
    return () => {
      abgebrochen = true;
    };
  }, []);

  const passt =
    plan != null &&
    eingabe.trim().toUpperCase() === plan.bestaetigung.toUpperCase();

  const loeschen = async () => {
    if (!passt || laeuft) return;
    setLaeuft(true);
    setFehler("");
    try {
      const res = await fetch(`${BASE}/system/uninstall`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bestaetigung: eingabe.trim(),
          programm_entfernen: programm && (plan?.programm_entfernbar ?? false),
        }),
      });
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(text || `HTTP ${res.status}`);
      }
      const d = await res.json();
      setSchritte(d.schritte ?? []);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
      setLaeuft(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[85] flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="glass rounded-2xl border border-red-500/40 w-[520px] max-w-[92vw] p-6 max-h-[88vh] overflow-y-auto">
        <div className="text-center mb-4">
          <div className="text-4xl mb-2">🗑️</div>
          <h2 className="text-xl font-semibold text-red-300">Jon deinstallieren</h2>
          <p className="text-[12px] text-white/50 mt-1">
            Das löscht alles, was Jon über dich weiß. Es gibt kein Zurück.
          </p>
        </div>

        {fehler && (
          <div className="text-[12px] text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 mb-3">
            {fehler}
          </div>
        )}

        {schritte ? (
          <div className="space-y-2">
            {schritte.map((s, i) => (
              <div key={i} className="flex items-center gap-2 text-[12px]">
                <span>{s.ok ? "✅" : "❌"}</span>
                <span className="text-white/80 flex-1">{s.schritt}</span>
                <span className="text-white/40">{s.hinweis}</span>
              </div>
            ))}
            <p className="text-[12px] text-white/60 pt-3 leading-relaxed">
              Jon beendet sich jetzt. Du kannst das Fenster schließen.
            </p>
          </div>
        ) : !plan ? (
          <p className="text-[12px] text-white/50 text-center py-6">Wird geprüft …</p>
        ) : (
          <>
            <div className="space-y-2 mb-4">
              {plan.eintraege.map((e) => (
                <div
                  key={e.id}
                  className="rounded-lg border border-white/10 bg-white/5 px-3 py-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[13px] text-white/85">{e.titel}</span>
                    <span className="text-[11px] text-white/40">
                      {e.dateien} {e.dateien === 1 ? "Datei" : "Dateien"} ·{" "}
                      {groesse(e.bytes)}
                    </span>
                  </div>
                  <div className="text-[11px] text-white/45 mt-0.5 leading-snug">
                    {e.beschreibung}
                  </div>
                  <div className="text-[10px] text-white/30 mt-1 font-mono break-all">
                    {e.pfad}
                  </div>
                </div>
              ))}
            </div>

            <div className="text-[11px] text-white/55 leading-relaxed mb-3">
              {plan.programm_hinweis}
            </div>

            {plan.programm_entfernbar && (
              <label className="flex items-center gap-2 mb-4 cursor-pointer">
                <input
                  type="checkbox"
                  checked={programm}
                  onChange={(e) => setProgramm(e.target.checked)}
                />
                <span className="text-[12px] text-white/70">
                  Programm anschließend entfernen
                </span>
              </label>
            )}

            <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-3 py-3 mb-4">
              <p className="text-[12px] text-white/70 mb-2">
                Tippe{" "}
                <span className="font-mono text-red-300">{plan.bestaetigung}</span>,
                um zu bestätigen:
              </p>
              <input
                value={eingabe}
                autoFocus
                spellCheck={false}
                onChange={(e) => setEingabe(e.target.value)}
                placeholder={plan.bestaetigung}
                className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/15 text-[13px] font-mono text-white/90 placeholder-white/25 outline-none focus:border-red-400/50"
              />
            </div>

            <div className="flex gap-2">
              <button
                onClick={onClose}
                disabled={laeuft}
                className="flex-1 py-2 rounded-lg border border-white/15 bg-white/5 text-[13px] text-white/80 hover:bg-white/10 transition disabled:opacity-40"
              >
                Abbrechen
              </button>
              <button
                onClick={() => void loeschen()}
                disabled={!passt || laeuft}
                className="flex-1 py-2 rounded-lg bg-red-500/80 text-[13px] font-semibold text-white hover:bg-red-500 transition disabled:opacity-30 disabled:cursor-not-allowed"
              >
                {laeuft ? "Löscht …" : "Endgültig löschen"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
