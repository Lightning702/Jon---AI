import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  DenkSelbstbild,
  DenkVerlauf,
  DenkVorschlag,
  DenkZiel,
  DenkZustand,
  addZiel,
  deleteZiel,
  getDenkVerlauf,
  getDenkZustand,
  getSelbstbild,
  getVorschlaege,
  getZiele,
  initiativeLauf,
  updateZiel,
  vorschlagEntscheiden,
} from "../lib/api";

type Reiter = "ziele" | "verlauf" | "vorschlaege" | "selbst";

const REITER: { id: Reiter; label: string; icon: string }[] = [
  { id: "ziele", label: "Ziele", icon: "🎯" },
  { id: "verlauf", label: "Was war", icon: "🕓" },
  { id: "vorschlaege", label: "Vorschläge", icon: "💡" },
  { id: "selbst", label: "Selbstbild", icon: "🧭" },
];

const ZEITRAEUME = ["heute", "gestern", "letzte woche"];

export default function DenkenPanel({ onClose }: { onClose: () => void }) {
  const [reiter, setReiter] = useState<Reiter>("ziele");
  const [ziele, setZiele] = useState<DenkZiel[]>([]);
  const [verlauf, setVerlauf] = useState<DenkVerlauf | null>(null);
  const [zeitraum, setZeitraum] = useState("heute");
  const [vorschlaege, setVorschlaege] = useState<DenkVorschlag[]>([]);
  const [selbst, setSelbst] = useState<DenkSelbstbild | null>(null);
  const [zustand, setZustand] = useState<DenkZustand | null>(null);
  const [neu, setNeu] = useState("");
  const [frist, setFrist] = useState("");
  const [busy, setBusy] = useState(false);

  const laden = async () => {
    setZustand(await getDenkZustand());
    if (reiter === "ziele") setZiele((await getZiele()).offen);
    if (reiter === "verlauf") setVerlauf(await getDenkVerlauf(zeitraum));
    if (reiter === "vorschlaege") setVorschlaege(await getVorschlaege());
    if (reiter === "selbst") setSelbst(await getSelbstbild());
  };

  useEffect(() => {
    void laden();
  }, [reiter, zeitraum]);

  const zielAnlegen = async () => {
    if (!neu.trim()) return;
    setBusy(true);
    await addZiel(neu.trim(), frist.trim());
    setNeu("");
    setFrist("");
    setZiele((await getZiele()).offen);
    setBusy(false);
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.97, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="glass rounded-2xl border border-gold/25 w-[92%] max-w-2xl max-h-[86vh] overflow-hidden flex flex-col"
        role="dialog"
        aria-modal="true"
        aria-label="Jons Denken"
      >
        <div className="flex items-center gap-2 px-5 py-3 border-b border-white/10">
          <span className="text-sm font-semibold gold-text flex-1">🧠 Jons Denken</span>
          {zustand?.netz && !zustand.netz.online && (
            <span className="text-[10px] text-red-300">offline</span>
          )}
          <button
            onClick={onClose}
            className="text-[12px] px-3 py-1 rounded-lg border border-white/15 text-white/70 hover:bg-white/5"
          >
            Schließen
          </button>
        </div>

        <div className="flex gap-1 px-4 pt-3">
          {REITER.map((eintrag) => (
            <button
              key={eintrag.id}
              onClick={() => setReiter(eintrag.id)}
              className={`flex-1 text-[11px] py-1.5 rounded-lg border transition-colors ${
                reiter === eintrag.id
                  ? "border-gold/40 bg-gold/15 text-gold"
                  : "border-white/10 bg-white/5 text-white/50 hover:bg-white/10"
              }`}
            >
              {eintrag.icon} {eintrag.label}
            </button>
          ))}
        </div>

        <div className="px-5 py-4 overflow-y-auto text-[12.5px] text-white/85 space-y-3">
          {reiter === "ziele" && (
            <>
              <div className="flex gap-2">
                <input
                  value={neu}
                  onChange={(e) => setNeu(e.target.value)}
                  placeholder="Neues Ziel"
                  className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-1.5 text-[12px]"
                />
                <input
                  value={frist}
                  onChange={(e) => setFrist(e.target.value)}
                  placeholder="Frist (morgen, 24.12.)"
                  className="w-40 bg-black/30 border border-white/10 rounded-lg px-3 py-1.5 text-[12px]"
                />
                <button
                  onClick={() => void zielAnlegen()}
                  disabled={busy}
                  className="text-[12px] px-3 py-1.5 rounded-lg bg-gold/80 text-black font-semibold"
                >
                  +
                </button>
              </div>
              {ziele.length === 0 && (
                <div className="text-white/40">
                  Noch keine Ziele. Sag Jon einfach, was du vorhast — er legt sie
                  selbst an.
                </div>
              )}
              {ziele.map((ziel) => (
                <div
                  key={ziel.id}
                  className="rounded-lg border border-white/10 bg-white/5 px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="flex-1 font-medium">{ziel.titel}</span>
                    {ziel.frist && (
                      <span className="text-[10px] text-gold/80">
                        {ziel.tage_bis_frist !== null && ziel.tage_bis_frist <= 1
                          ? "bald fällig"
                          : ziel.frist.slice(0, 10)}
                      </span>
                    )}
                    <button
                      onClick={async () => {
                        await updateZiel(ziel.id, { zustand: "erledigt" });
                        setZiele((await getZiele()).offen);
                      }}
                      className="text-[11px] text-white/50 hover:text-gold"
                      aria-label="Ziel erledigt"
                    >
                      ✓
                    </button>
                    <button
                      onClick={async () => {
                        await deleteZiel(ziel.id);
                        setZiele((await getZiele()).offen);
                      }}
                      className="text-[11px] text-white/40 hover:text-red-300"
                      aria-label="Ziel löschen"
                    >
                      ✕
                    </button>
                  </div>
                  {ziel.naechster_schritt && (
                    <div className="text-[11px] text-white/50 mt-1">
                      Nächster Schritt: {ziel.naechster_schritt}
                    </div>
                  )}
                </div>
              ))}
            </>
          )}

          {reiter === "verlauf" && (
            <>
              <div className="flex gap-1">
                {ZEITRAEUME.map((raum) => (
                  <button
                    key={raum}
                    onClick={() => setZeitraum(raum)}
                    className={`text-[11px] px-3 py-1 rounded-lg border ${
                      zeitraum === raum
                        ? "border-gold/40 bg-gold/15 text-gold"
                        : "border-white/10 bg-white/5 text-white/50"
                    }`}
                  >
                    {raum}
                  </button>
                ))}
              </div>
              {verlauf && (
                <div className="space-y-2">
                  <div className="text-white/60">
                    {verlauf.anzahl} Ereignisse ({verlauf.zeitraum.beschreibung})
                  </div>
                  {verlauf.hoehepunkte.map((eintrag, index) => (
                    <div
                      key={`${eintrag.zeit}-${index}`}
                      className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5"
                    >
                      <span className="text-gold/80 font-mono text-[11px]">
                        {eintrag.zeit}
                      </span>{" "}
                      <span className="text-white/50 text-[11px]">
                        [{eintrag.art}]
                      </span>{" "}
                      {eintrag.titel}
                      {eintrag.detail && (
                        <div className="text-[11px] text-white/45">
                          {eintrag.detail}
                        </div>
                      )}
                    </div>
                  ))}
                  {verlauf.fehler.length > 0 && (
                    <div className="text-[11px] text-red-300/80">
                      Schiefgegangen: {verlauf.fehler.join(", ")}
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {reiter === "vorschlaege" && (
            <>
              <button
                onClick={async () => {
                  setBusy(true);
                  await initiativeLauf();
                  setVorschlaege(await getVorschlaege());
                  setBusy(false);
                }}
                disabled={busy}
                className="text-[12px] px-3 py-1.5 rounded-lg border border-gold/30 text-gold/90 hover:bg-gold/10"
              >
                {busy ? "denkt nach …" : "Jetzt überlegen, was ansteht"}
              </button>
              {vorschlaege.length === 0 && (
                <div className="text-white/40">
                  Noch keine Vorschläge. Schalte „Eigeninitiative" in den
                  Einstellungen ein, damit Jon von selbst vorausdenkt.
                </div>
              )}
              {vorschlaege.map((vorschlag) => (
                <div
                  key={vorschlag.id}
                  className="rounded-lg border border-white/10 bg-white/5 px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="flex-1 font-medium">{vorschlag.titel}</span>
                    <span className="text-[10px] text-white/40">{vorschlag.wann}</span>
                  </div>
                  {vorschlag.warum && (
                    <div className="text-[11px] text-white/55 mt-1">
                      {vorschlag.warum}
                    </div>
                  )}
                  {vorschlag.zustand === "offen" && (
                    <div className="flex gap-2 mt-2">
                      {vorschlag.selbst_machbar && (
                        <button
                          onClick={async () => {
                            await vorschlagEntscheiden(vorschlag.id, true, true);
                            setVorschlaege(await getVorschlaege());
                          }}
                          className="text-[11px] px-2 py-1 rounded-lg bg-gold/70 text-black font-semibold"
                        >
                          Mach das
                        </button>
                      )}
                      <button
                        onClick={async () => {
                          await vorschlagEntscheiden(vorschlag.id, false);
                          setVorschlaege(await getVorschlaege());
                        }}
                        className="text-[11px] px-2 py-1 rounded-lg border border-white/15 text-white/60"
                      >
                        Nein danke
                      </button>
                    </div>
                  )}
                  {vorschlag.zustand !== "offen" && (
                    <div className="text-[11px] text-white/40 mt-1">
                      {vorschlag.zustand}
                    </div>
                  )}
                </div>
              ))}
            </>
          )}

          {reiter === "selbst" && selbst && (
            <div className="space-y-3">
              <div>
                <span className="text-white/50">Werkzeuge:</span> {selbst.werkzeuge} ·{" "}
                <span className="text-white/50">Skills:</span> {selbst.skills.length}
              </div>
              {selbst.bilanz.aktionen > 0 && (
                <div>
                  <div className="text-white/50 mb-1">
                    Zuletzt {selbst.bilanz.aktionen} Aktionen
                  </div>
                  {selbst.bilanz.schwaechste.map((eintrag) => (
                    <div key={eintrag.werkzeug} className="text-[11px]">
                      {eintrag.werkzeug}:{" "}
                      <span
                        className={
                          eintrag.erfolgsquote < 0.6 ? "text-red-300" : "text-white/60"
                        }
                      >
                        {Math.round(eintrag.erfolgsquote * 100)}% ({eintrag.laeufe}x)
                      </span>
                    </div>
                  ))}
                </div>
              )}
              <div>
                <div className="text-white/50 mb-1">Grenzen</div>
                {selbst.grenzen.map((grenze) => (
                  <div key={grenze} className="text-[11px] text-white/60">
                    · {grenze}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
