import { useEffect, useState } from "react";
import {
  VerbundGeraet,
  verbundGeraete,
  verbundKoppeln,
  verbundEntfernen,
  verbundPruefen,
  verbundBildUrl,
} from "../lib/api";

function seit(zeit: number): string {
  if (!zeit) return "noch nie";
  const sekunden = Math.max(0, Math.round(Date.now() / 1000 - zeit));
  if (sekunden < 90) return "gerade eben";
  if (sekunden < 5400) return `vor ${Math.round(sekunden / 60)} min`;
  if (sekunden < 172800) return `vor ${Math.round(sekunden / 3600)} h`;
  return `vor ${Math.round(sekunden / 86400)} Tagen`;
}

export default function VerbundModal({ onClose }: { onClose: () => void }) {
  const [geraete, setGeraete] = useState<VerbundGeraet[]>([]);
  const [code, setCode] = useState("");
  const [koppelt, setKoppelt] = useState(false);
  const [hinweis, setHinweis] = useState("");
  const [fehler, setFehler] = useState("");
  const [bild, setBild] = useState<{ id: string; name: string } | null>(null);
  const [stempel, setStempel] = useState(Date.now());

  const laden = async () => {
    try {
      setGeraete(await verbundGeraete());
    } catch {
      setFehler("Die Geräteliste ließ sich nicht laden.");
    }
  };

  useEffect(() => {
    void laden();
  }, []);

  useEffect(() => {
    if (!bild) return;
    const uhr = window.setInterval(() => setStempel(Date.now()), 2500);
    return () => window.clearInterval(uhr);
  }, [bild]);

  const koppeln = async () => {
    const sauber = code.trim();
    if (!sauber) return;
    setKoppelt(true);
    setFehler("");
    setHinweis(
      "Ich frage an — bestätige die Anfrage jetzt am anderen Gerät. Das kann bis zu vier Minuten offen bleiben."
    );
    try {
      const neu = await verbundKoppeln(sauber);
      setHinweis(`${neu.name} ist jetzt im Verbund. 🤝`);
      setCode("");
      await laden();
    } catch (e) {
      setHinweis("");
      setFehler(e instanceof Error ? e.message : "Kopplung fehlgeschlagen.");
    } finally {
      setKoppelt(false);
    }
  };

  const pruefen = async (id: string) => {
    setFehler("");
    try {
      const stand = await verbundPruefen(id);
      setHinweis(
        stand.erreichbar
          ? `${stand.name} antwortet (${stand.version || "?"}, ${stand.weg || "direkt"}).`
          : `${stand.name} antwortet gerade nicht.`
      );
      await laden();
    } catch {
      setFehler("Das Gerät ließ sich nicht erreichen.");
    }
  };

  const entfernen = async (id: string, name: string) => {
    if (!window.confirm(`${name} aus dem Verbund nehmen?`)) return;
    await verbundEntfernen(id);
    await laden();
  };

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg max-h-[86vh] overflow-y-auto rounded-2xl border border-gold/25 bg-[#0b0b0f] shadow-2xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 sticky top-0 bg-[#0b0b0f]">
          <div className="text-sm text-gold">Geräte im Verbund</div>
          <button
            onClick={onClose}
            className="text-white/50 hover:text-white text-lg leading-none px-2"
          >
            X
          </button>
        </div>
        <div className="p-4 space-y-4">
          <p className="text-[11.5px] leading-relaxed text-white/55">
            Verbinde diesen Jon mit deinen anderen Jons — dem Raspberry Pi, einem
            zweiten PC. Danach fragst du sie im Chat („frag den Pi, ob …"), siehst
            ihren Bildschirm und erreichst sie auch von unterwegs: die Verbindung
            läuft verschlüsselt über Jons Vermittler, im selben WLAN direkt.
          </p>

          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <div className="text-[11px] text-white/70">Neues Gerät dazunehmen</div>
            <ol className="mt-1.5 text-[10.5px] leading-relaxed text-white/45 list-decimal ml-4 space-y-0.5">
              <li>Am anderen Gerät Jon öffnen → Einstellungen → Handy verbinden.</li>
              <li>Den angezeigten Code hier eintragen.</li>
              <li>Am anderen Gerät die Anfrage bestätigen.</li>
            </ol>
            <div className="mt-2 flex gap-2">
              <input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void koppeln();
                }}
                placeholder="Code vom anderen Gerät"
                className="flex-1 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1.5 text-[11.5px] text-white/90 outline-none focus:border-gold/50"
              />
              <button
                onClick={() => void koppeln()}
                disabled={koppelt || !code.trim()}
                className="rounded-lg border border-gold/40 bg-gold/10 px-3 py-1.5 text-[11.5px] text-gold disabled:opacity-40 hover:bg-gold/20"
              >
                {koppelt ? "Verbinde…" : "Verbinden"}
              </button>
            </div>
          </div>

          {hinweis && (
            <div className="rounded-lg border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-[11px] text-emerald-200/90">
              {hinweis}
            </div>
          )}
          {fehler && (
            <div className="rounded-lg border border-red-400/25 bg-red-400/10 px-3 py-2 text-[11px] text-red-200/90">
              {fehler}
            </div>
          )}

          <div className="space-y-2">
            {geraete.length === 0 && (
              <div className="text-[11px] text-white/35">
                Noch kein zweites Gerät verbunden.
              </div>
            )}
            {geraete.map((g) => (
              <div
                key={g.id}
                className="rounded-xl border border-white/10 bg-white/[0.03] p-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <div className="text-[12px] text-white/85">{g.name}</div>
                    <div className="text-[10px] text-white/40">
                      {[g.version && `v${g.version}`, g.weg, seit(g.gesehen)]
                        .filter(Boolean)
                        .join(" · ")}
                    </div>
                  </div>
                  <div className="flex gap-1.5">
                    <button
                      onClick={() => void pruefen(g.id)}
                      className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[10.5px] text-white/60 hover:bg-white/10"
                    >
                      Prüfen
                    </button>
                    <button
                      onClick={() => {
                        setBild({ id: g.id, name: g.name });
                        setStempel(Date.now());
                      }}
                      className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[10.5px] text-white/60 hover:bg-white/10"
                    >
                      Bildschirm
                    </button>
                    <button
                      onClick={() => void entfernen(g.id, g.name)}
                      className="rounded-lg border border-red-400/20 bg-red-400/5 px-2 py-1 text-[10.5px] text-red-300/70 hover:bg-red-400/15"
                    >
                      Lösen
                    </button>
                  </div>
                </div>
                {bild?.id === g.id && (
                  <div className="mt-2">
                    <img
                      src={verbundBildUrl(g.id, stempel)}
                      alt={`Bildschirm von ${g.name}`}
                      className="w-full rounded-lg border border-white/10"
                    />
                    <button
                      onClick={() => setBild(null)}
                      className="mt-1.5 text-[10.5px] text-white/40 hover:text-white/70"
                    >
                      Ansicht schließen
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
