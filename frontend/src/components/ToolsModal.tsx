import { useEffect, useMemo, useState } from "react";
import { SkillKurz, Werkzeug, WerkzeugGruppe, werkzeuge } from "../lib/api";
import GeraetePanel from "./GeraetePanel";
import HandyModal from "./HandyModal";

const STUFENFARBE: Record<string, string> = {
  standard: "bg-emerald-500/15 text-emerald-200",
  persoenlich: "bg-sky-500/15 text-sky-200",
  sensibel: "bg-amber-500/15 text-amber-200",
};

const STUFENTEXT: Record<string, string> = {
  standard: "Standard",
  persoenlich: "Persönlich",
  sensibel: "Sensibel",
};

function Marke({ text, ton }: { text: string; ton: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] ${ton}`}>{text}</span>
  );
}

export default function ToolsModal({
  onClose,
  start,
}: {
  onClose: () => void;
  start?: string;
}) {
  const [gruppen, setGruppen] = useState<WerkzeugGruppe[]>([]);
  const [skills, setSkills] = useState<SkillKurz[]>([]);
  const [aktiv, setAktiv] = useState(start ?? "handy");
  const [suche, setSuche] = useState("");
  const [fehler, setFehler] = useState("");
  const [laedt, setLaedt] = useState(true);
  const [kopplung, setKopplung] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const daten = await werkzeuge();
        setGruppen(daten.gruppen);
        setSkills(daten.skills ?? []);
        const gewuenscht = start ?? "handy";
        if (!daten.gruppen.some((g) => g.id === gewuenscht)) {
          setAktiv(daten.gruppen[0]?.id ?? "");
        }
      } catch (e) {
        setFehler(e instanceof Error ? e.message : "Werkzeuge nicht ladbar");
      } finally {
        setLaedt(false);
      }
    })();
  }, []);

  const treffer = useMemo<Werkzeug[]>(() => {
    const text = suche.trim().toLowerCase();
    if (!text) return [];
    return gruppen
      .flatMap((g) => g.werkzeuge)
      .filter(
        (w) =>
          w.name.toLowerCase().includes(text) ||
          w.beschreibung.toLowerCase().includes(text)
      )
      .slice(0, 60);
  }, [suche, gruppen]);

  const gruppe = gruppen.find((g) => g.id === aktiv);
  const SKILL_ZU_GRUPPE: Record<string, string> = {
    handy: "handy",
    "pc-automation": "pc",
    "browser-automation": "browser",
    research: "wissen",
    telefonanruf: "kontakt",
    powerpoint: "medien",
    "web-design": "dateien",
    "game-design": "dateien",
  };
  const gruppenSkill = skills.find((s) => SKILL_ZU_GRUPPE[s.name] === aktiv);
  const liste = suche.trim() ? treffer : (gruppe?.werkzeuge ?? []);
  const gesamt = gruppen.reduce((summe, g) => summe + g.anzahl, 0);

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[720px] max-w-[94vw] h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <div>
            <div className="text-white/90 font-semibold">🧰 Werkzeuge</div>
            <div className="text-[11px] text-white/40">
              {gesamt} Werkzeuge, die Jon im Chat benutzen kann
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="px-5 pt-3">
          <input
            value={suche}
            onChange={(e) => setSuche(e.target.value)}
            placeholder="Suchen … z. B. Handy, Datei, Kalender"
            className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-[12px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50"
          />
        </div>

        <div className="flex-1 min-h-0 flex gap-3 px-5 py-3">
          {!suche.trim() && (
            <div className="w-[190px] shrink-0 overflow-y-auto pr-1 space-y-1">
              {gruppen.map((g) => (
                <button
                  key={g.id}
                  onClick={() => setAktiv(g.id)}
                  className={
                    "w-full flex items-center justify-between gap-2 px-2.5 py-2 rounded-lg border text-left transition-colors " +
                    (g.id === aktiv
                      ? "border-gold/40 bg-gold/10 text-gold/90"
                      : "border-white/10 bg-white/[0.03] text-white/70 hover:bg-white/[0.07]")
                  }
                >
                  <span className="text-[12px] truncate">
                    {g.symbol} {g.name}
                  </span>
                  <span className="text-[10px] text-white/35">{g.anzahl}</span>
                </button>
              ))}
            </div>
          )}

          <div className="flex-1 min-w-0 overflow-y-auto space-y-2">
            {laedt && (
              <div className="text-[12px] text-white/40">Wird geladen …</div>
            )}
            {fehler && (
              <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-[11px] text-red-200">
                {fehler}
              </div>
            )}

            {!suche.trim() && gruppenSkill && (
              <div className="rounded-xl border border-gold/25 bg-gold/[0.06] px-3 py-2.5">
                <div className="text-[11px] text-gold/90">
                  📚 Skill „{gruppenSkill.title || gruppenSkill.name}"
                </div>
                <div className="text-[10px] text-white/50 leading-relaxed mt-0.5">
                  Diese Anleitung liest Jon selbst, bevor er hier etwas macht. Ändern
                  kannst du sie unter Einstellungen → Skills oder in{" "}
                  <span className="font-mono">skills/{gruppenSkill.name}.md</span>.
                </div>
              </div>
            )}

            {!suche.trim() && aktiv === "handy" && (
              <GeraetePanel onPair={() => setKopplung(true)} />
            )}

            {liste.map((w) => (
              <div
                key={w.name}
                className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-[11px] text-gold/80 truncate">
                    {w.name}
                  </span>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {w.stufe && (
                      <Marke
                        text={STUFENTEXT[w.stufe] ?? w.stufe}
                        ton={STUFENFARBE[w.stufe] ?? "bg-white/10 text-white/50"}
                      />
                    )}
                    {w.frei === false && (
                      <Marke text="gesperrt" ton="bg-white/10 text-white/45" />
                    )}
                    {w.frei === true && (
                      <Marke text="frei" ton="bg-emerald-500/15 text-emerald-200" />
                    )}
                    {w.ohne_rueckfrage ? (
                      <Marke text="ohne Rückfrage" ton="bg-white/10 text-white/45" />
                    ) : (
                      <Marke text="fragt nach" ton="bg-white/10 text-white/45" />
                    )}
                  </div>
                </div>
                {w.beschreibung && (
                  <div className="text-[11px] text-white/60 leading-relaxed mt-1">
                    {w.beschreibung}
                  </div>
                )}
              </div>
            ))}

            {!laedt && liste.length === 0 && (
              <div className="text-[12px] text-white/40">
                {suche.trim()
                  ? "Nichts gefunden."
                  : "In dieser Gruppe ist gerade nichts frei."}
              </div>
            )}
          </div>
        </div>

        <div className="px-5 py-3 border-t border-white/10 text-[11px] text-white/40">
          „fragt nach" heißt: Jon holt sich im Chat erst deine Bestätigung, bevor
          er das Werkzeug ausführt. „gesperrt" heißt: erst oben freigeben.
        </div>
      </div>
      {kopplung && <HandyModal onClose={() => setKopplung(false)} />}
    </div>
  );
}
