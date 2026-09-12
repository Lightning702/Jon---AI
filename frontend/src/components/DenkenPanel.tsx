import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  DenkFertigkeit,
  DenkFrage,
  DenkKalibrierung,
  DenkPlan,
  DenkSelbstbild,
  DenkUeberraschung,
  DenkVerlauf,
  DenkVorschlag,
  DenkZiel,
  DenkZustand,
  addFertigkeit,
  addFrage,
  addPlan,
  addZiel,
  deleteFertigkeit,
  deleteZiel,
  frageKlaeren,
  frageVerwerfen,
  getDenkVerlauf,
  getDenkZustand,
  getErwartung,
  getFertigkeitVorschlaege,
  getFertigkeiten,
  getFragen,
  getPlaene,
  getSelbstbild,
  getVorschlaege,
  getZiele,
  initiativeLauf,
  planAbbrechen,
  planLauf,
  updateZiel,
  vorschlagEntscheiden,
} from "../lib/api";

type Reiter =
  | "ziele"
  | "verlauf"
  | "vorschlaege"
  | "lernen"
  | "fragen"
  | "plaene"
  | "selbst";

const REITER: { id: Reiter; label: string; icon: string }[] = [
  { id: "ziele", label: "Ziele", icon: "🎯" },
  { id: "verlauf", label: "Was war", icon: "🕓" },
  { id: "vorschlaege", label: "Vorschläge", icon: "💡" },
  { id: "lernen", label: "Gelernt", icon: "📈" },
  { id: "fragen", label: "Offen", icon: "❓" },
  { id: "plaene", label: "Pläne", icon: "🗺️" },
  { id: "selbst", label: "Selbstbild", icon: "🧭" },
];

type FertigVorschlag = {
  name: string;
  anzahl: number;
  beschreibung: string;
  schritte: unknown[];
};

const ZUSTAND_ZEICHEN: Record<string, string> = {
  offen: "⚪",
  erledigt: "✅",
  fehler: "❌",
  uebersprungen: "⏭️",
};

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
  const [kalibrierung, setKalibrierung] = useState<DenkKalibrierung | null>(null);
  const [ueberraschungen, setUeberraschungen] = useState<DenkUeberraschung[]>([]);
  const [fertigkeiten, setFertigkeiten] = useState<DenkFertigkeit[]>([]);
  const [fertigVorschlaege, setFertigVorschlaege] = useState<FertigVorschlag[]>([]);
  const [fragen, setFragen] = useState<DenkFrage[]>([]);
  const [geklaert, setGeklaert] = useState<DenkFrage[]>([]);
  const [plaene, setPlaene] = useState<DenkPlan[]>([]);
  const [auftrag, setAuftrag] = useState("");
  const [meldung, setMeldung] = useState("");

  const laden = async () => {
    setZustand(await getDenkZustand());
    if (reiter === "ziele") setZiele((await getZiele()).offen);
    if (reiter === "verlauf") setVerlauf(await getDenkVerlauf(zeitraum));
    if (reiter === "vorschlaege") setVorschlaege(await getVorschlaege());
    if (reiter === "selbst") setSelbst(await getSelbstbild());
    if (reiter === "lernen") {
      const erwartung = await getErwartung();
      setKalibrierung(erwartung?.kalibrierung ?? null);
      setUeberraschungen(erwartung?.ueberraschungen ?? []);
      setFertigkeiten((await getFertigkeiten())?.fertigkeiten ?? []);
    }
    if (reiter === "fragen") {
      const daten = await getFragen();
      setFragen(daten?.offen ?? []);
      setGeklaert(daten?.beantwortet ?? []);
    }
    if (reiter === "plaene") setPlaene(await getPlaene());
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

        <div className="flex flex-wrap gap-1 px-4 pt-3">
          {REITER.map((eintrag) => (
            <button
              key={eintrag.id}
              onClick={() => setReiter(eintrag.id)}
              className={`flex-1 min-w-[84px] text-[11px] py-1.5 rounded-lg border transition-colors ${
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

          {reiter === "lernen" && (
            <>
              <div className="rounded-lg border border-gold/20 bg-gold/5 px-3 py-2">
                <div className="text-gold/90 font-medium">
                  {kalibrierung?.text ?? "Noch keine Vorhersagen."}
                </div>
                {kalibrierung && kalibrierung.anzahl > 0 && (
                  <div className="text-[11px] text-white/55 mt-1">
                    {kalibrierung.anzahl} Vorhersagen ·{" "}
                    {Math.round((kalibrierung.treffer ?? 0) * 100)}% davon richtig ·
                    mittlere Überraschung {kalibrierung.ueberraschung}
                  </div>
                )}
                {kalibrierung?.schwaechste.map((eintrag) => (
                  <div key={eintrag.werkzeug} className="text-[11px] text-white/50">
                    · {eintrag.werkzeug} überrascht ihn am häufigsten (
                    {eintrag.ueberraschung})
                  </div>
                ))}
              </div>
              <div className="text-white/50">Zuletzt anders gelaufen als gedacht</div>
              {ueberraschungen.length === 0 && (
                <div className="text-white/40">
                  Nichts Überraschendes — Jon lag zuletzt richtig.
                </div>
              )}
              {ueberraschungen.map((eintrag) => (
                <div
                  key={eintrag.id}
                  className="rounded-lg border border-white/10 bg-white/5 px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="flex-1 font-medium">
                      {eintrag.gelungen ? "✅" : "❌"} {eintrag.werkzeug}
                    </span>
                    <span className="text-[10px] text-gold/70">
                      erwartet {Math.round(eintrag.zutrauen * 100)}%
                    </span>
                  </div>
                  {eintrag.notiz && (
                    <div className="text-[11px] text-white/50 mt-1">
                      {eintrag.notiz}
                    </div>
                  )}
                </div>
              ))}
              <div className="flex items-center gap-2 pt-1">
                <span className="text-white/50 flex-1">Gelernte Fertigkeiten</span>
                <button
                  onClick={async () => {
                    setBusy(true);
                    setFertigVorschlaege(await getFertigkeitVorschlaege());
                    setBusy(false);
                  }}
                  disabled={busy}
                  className="text-[11px] px-2 py-1 rounded-lg border border-gold/30 text-gold/90 hover:bg-gold/10"
                >
                  {busy ? "sucht …" : "Muster suchen"}
                </button>
              </div>
              {fertigkeiten.length === 0 && fertigVorschlaege.length === 0 && (
                <div className="text-white/40">
                  Noch keine. Lass Jon oben nach Abläufen suchen, die du immer wieder
                  gleich machst — die merkt er sich als einen Handgriff.
                </div>
              )}
              {fertigkeiten.map((eintrag) => (
                <div
                  key={eintrag.id}
                  className="rounded-lg border border-white/10 bg-white/5 px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="flex-1 font-medium">{eintrag.name}</span>
                    {eintrag.erfolgsquote !== null && (
                      <span className="text-[10px] text-white/50">
                        {Math.round(eintrag.erfolgsquote * 100)}% ({eintrag.versuche}x)
                      </span>
                    )}
                    <button
                      onClick={async () => {
                        await deleteFertigkeit(eintrag.name);
                        await laden();
                      }}
                      className="text-[11px] text-white/40 hover:text-red-300"
                      aria-label="Fertigkeit löschen"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="text-[11px] text-white/45 mt-1">
                    {eintrag.schritte.map((schritt) => schritt.werkzeug).join(" → ")}
                  </div>
                </div>
              ))}
              {fertigVorschlaege.map((vorschlag) => (
                <div
                  key={vorschlag.name}
                  className="rounded-lg border border-gold/20 bg-gold/5 px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="flex-1">{vorschlag.name}</span>
                    <span className="text-[10px] text-white/50">
                      {vorschlag.anzahl}x
                    </span>
                    <button
                      onClick={async () => {
                        await addFertigkeit(
                          vorschlag.name,
                          vorschlag.schritte,
                          vorschlag.beschreibung
                        );
                        setFertigVorschlaege(
                          fertigVorschlaege.filter((e) => e.name !== vorschlag.name)
                        );
                        await laden();
                      }}
                      className="text-[11px] px-2 py-1 rounded-lg bg-gold/70 text-black font-semibold"
                    >
                      Merken
                    </button>
                  </div>
                </div>
              ))}
            </>
          )}

          {reiter === "fragen" && (
            <>
              <div className="flex gap-2">
                <input
                  value={neu}
                  onChange={(e) => setNeu(e.target.value)}
                  placeholder="Frage, die Jon klären soll"
                  className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-1.5 text-[12px]"
                />
                <button
                  onClick={async () => {
                    if (!neu.trim()) return;
                    setBusy(true);
                    await addFrage(neu.trim());
                    setNeu("");
                    await laden();
                    setBusy(false);
                  }}
                  disabled={busy}
                  className="text-[12px] px-3 py-1.5 rounded-lg bg-gold/80 text-black font-semibold"
                >
                  +
                </button>
              </div>
              {fragen.length === 0 && (
                <div className="text-white/40">
                  Gerade nichts offen. Sobald Jon etwas nicht weiß, landet es hier —
                  statt in einer geratenen Antwort.
                </div>
              )}
              {fragen.map((frage) => (
                <div
                  key={frage.id}
                  className="rounded-lg border border-white/10 bg-white/5 px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="flex-1">{frage.text}</span>
                    <span className="text-[10px] text-white/40">{frage.quelle}</span>
                  </div>
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={async () => {
                        setBusy(true);
                        setMeldung("Jon sucht nach einer Antwort …");
                        const ergebnis = await frageKlaeren(frage.id);
                        setMeldung(
                          ergebnis?.antwort
                            ? ergebnis.antwort
                            : "Diesmal kam nichts Brauchbares heraus."
                        );
                        await laden();
                        setBusy(false);
                      }}
                      disabled={busy}
                      className="text-[11px] px-2 py-1 rounded-lg bg-gold/70 text-black font-semibold"
                    >
                      Klären
                    </button>
                    <button
                      onClick={async () => {
                        await frageVerwerfen(frage.id);
                        await laden();
                      }}
                      className="text-[11px] px-2 py-1 rounded-lg border border-white/15 text-white/60"
                    >
                      Egal
                    </button>
                  </div>
                </div>
              ))}
              {meldung && (
                <div className="text-[11px] text-gold/80 border-l-2 border-gold/40 pl-2">
                  {meldung}
                </div>
              )}
              {geklaert.length > 0 && (
                <div className="pt-2">
                  <div className="text-white/50 mb-1">Schon geklärt</div>
                  {geklaert.map((frage) => (
                    <div key={frage.id} className="text-[11px] text-white/55 mb-1">
                      · {frage.text}
                      <div className="text-white/40">{frage.antwort}</div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {reiter === "plaene" && (
            <>
              <div className="flex gap-2">
                <input
                  value={auftrag}
                  onChange={(e) => setAuftrag(e.target.value)}
                  placeholder="Auftrag, den Jon zerlegen soll"
                  className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-1.5 text-[12px]"
                />
                <button
                  onClick={async () => {
                    if (!auftrag.trim()) return;
                    setBusy(true);
                    setMeldung("Jon zerlegt den Auftrag …");
                    const plan = await addPlan(auftrag.trim());
                    setMeldung(plan ? "" : "Das ließ sich nicht zerlegen.");
                    setAuftrag("");
                    await laden();
                    setBusy(false);
                  }}
                  disabled={busy}
                  className="text-[12px] px-3 py-1.5 rounded-lg bg-gold/80 text-black font-semibold"
                >
                  Planen
                </button>
              </div>
              {meldung && <div className="text-[11px] text-gold/80">{meldung}</div>}
              {plaene.length === 0 && (
                <div className="text-white/40">
                  Noch keine Pläne. Größere Aufträge zerlegt Jon hier in Schritte und
                  plant selbst um, wenn einer schiefgeht.
                </div>
              )}
              {plaene.map((plan) => (
                <div
                  key={plan.id}
                  className="rounded-lg border border-white/10 bg-white/5 px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="flex-1 font-medium">{plan.auftrag}</span>
                    <span className="text-[10px] text-white/50">
                      {plan.erledigt}/{plan.anzahl}
                    </span>
                    <span className="text-[10px] text-gold/80">{plan.zustand}</span>
                  </div>
                  {plan.schritte.map((schritt) => (
                    <div key={schritt.id} className="text-[11px] text-white/60 mt-1">
                      {ZUSTAND_ZEICHEN[schritt.zustand] ?? "⚪"} {schritt.titel}
                      <span className="text-white/35"> · {schritt.werkzeug}</span>
                    </div>
                  ))}
                  {plan.umplanungen > 0 && (
                    <div className="text-[11px] text-gold/70 mt-1">
                      {plan.umplanungen}x neu geplant, nachdem ein Schritt scheiterte
                    </div>
                  )}
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={async () => {
                        setBusy(true);
                        setMeldung("Jon arbeitet den Plan ab …");
                        const ergebnis = await planLauf(plan.id);
                        const freigabe = ergebnis?.ereignisse?.find(
                          (e) => e.art === "freigabe"
                        );
                        setMeldung(
                          freigabe
                            ? "Der Plan enthält riskante Schritte — nimm „Mit Freigabe“, wenn du sie willst."
                            : ""
                        );
                        await laden();
                        setBusy(false);
                      }}
                      disabled={busy}
                      className="text-[11px] px-2 py-1 rounded-lg bg-gold/70 text-black font-semibold"
                    >
                      Loslegen
                    </button>
                    <button
                      onClick={async () => {
                        setBusy(true);
                        await planLauf(plan.id, true);
                        await laden();
                        setBusy(false);
                      }}
                      disabled={busy}
                      className="text-[11px] px-2 py-1 rounded-lg border border-gold/25 text-gold/80"
                    >
                      Mit Freigabe
                    </button>
                    <button
                      onClick={async () => {
                        await planAbbrechen(plan.id);
                        await laden();
                      }}
                      className="text-[11px] px-2 py-1 rounded-lg border border-white/15 text-white/60"
                    >
                      Abbrechen
                    </button>
                  </div>
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
