import { useEffect, useMemo, useState } from "react";
import { AudioLines, BookOpen, ChevronRight, Code2, Eye, LifeBuoy, Search, Users, Wrench, X } from "lucide-react";
import { SkillKurz, Werkzeug, WerkzeugGruppe, werkzeuge } from "../lib/api";
import GeraetePanel from "./GeraetePanel";
import HandyModal from "./HandyModal";
import HarnessPanel from "./HarnessPanel";
import AgentTeam from "./AgentTeam";
import BeobachtenPanel from "./BeobachtenPanel";
import SupportPanel from "./SupportPanel";
import MediaPanel from "./MediaPanel";
import "./beobachten.css";
import "./werkzeuge.css";
import {harnessRequest} from "../lib/harness";

const STUFENFARBE: Record<string, string> = {
  standard: "wz-marke-gruen",
  persoenlich: "wz-marke-blau",
  sensibel: "wz-marke-gelb",
};

const STUFENTEXT: Record<string, string> = {
  standard: "Standard",
  persoenlich: "Persönlich",
  sensibel: "Sensibel",
};

const SPEZIAL = [
  { id: "harness", name: "Jon Harness", text: "Coding-Agent", icon: Code2, suche: /harness|agent|minijon|mitarbeiten|coden|coding/ },
  { id: "agents", name: "Jon Fachteam", text: "Fachagenten", icon: Users, suche: /team|agent|latein|lernen|fach|planung/ },
  { id: "medien", name: "Stimmen & Transkripte", text: "Audio, YouTube, Vorlesen", icon: AudioLines, suche: /stimme|transkri|audio|youtube|vorlesen|mp3|podcast|untertitel/ },
  { id: "beobachten", name: "Beobachten", text: "Jon meldet sich", icon: Eye, suche: /beobacht|erinner|bescheid|release|rauskommt/ },
  { id: "support", name: "Support", text: "Fehler & Ideen", icon: LifeBuoy, suche: /support|hilfe|fehler|problem|vorschlag|kontakt|mail/ },
] as const;
const SPEZIAL_IDS: string[] = SPEZIAL.map(s => s.id);

function Marke({ text, ton }: { text: string; ton: string }) {
  return <span className={"wz-marke " + ton}>{text}</span>;
}

export default function ToolsModal({
  onClose,
  start,
  onHarness,
}: {
  onClose: () => void;
  start?: string;
  onHarness?: () => void;
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
        if (!SPEZIAL_IDS.includes(gewuenscht) && !daten.gruppen.some((g) => g.id === gewuenscht)) {
          setAktiv(daten.gruppen[0]?.id ?? "");
        }
      } catch (e) {
        setFehler(e instanceof Error ? e.message : "Werkzeuge nicht ladbar");
      } finally {
        setLaedt(false);
      }
    })();
  }, []);

  useEffect(() => {
    const taste = (e: KeyboardEvent) => {if (e.key === "Escape" && !kopplung) onClose();};
    window.addEventListener("keydown", taste);
    return () => window.removeEventListener("keydown", taste);
  }, [onClose, kopplung]);

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
  const sucht = !!suche.trim();
  const spezial = !sucht && SPEZIAL_IDS.includes(aktiv);
  const liste = sucht ? treffer : spezial ? [] : (gruppe?.werkzeuge ?? []);
  const gesamt = gruppen.reduce((summe, g) => summe + g.anzahl, 0);
  const vorschlaege = sucht ? SPEZIAL.filter(s => s.suche.test(suche.toLowerCase())) : [];
  const waehlen = (id: string) => {
    setSuche("");
    if (id === "harness" && onHarness) onHarness();
    else setAktiv(id);
  };

  return (
    <div className="wz-schleier" onMouseDown={(e) => {if (e.target === e.currentTarget) onClose();}}>
      <div className="werkzeug-fenster wz-fenster" role="dialog" aria-modal="true" aria-label="Werkzeuge">
        <header className="wz-kopf">
          <span className="wz-emblem"><Wrench size={18} /></span>
          <div className="wz-kopf-text">
            <h2>Werkzeuge</h2>
            <p>{gesamt ? `${gesamt} Werkzeuge, die Jon im Chat benutzen kann` : "Alles, was Jon für dich erledigen kann"}</p>
          </div>
          <label className="wz-suche">
            <Search size={14} />
            <input
              aria-label="Werkzeuge durchsuchen"
              type="search"
              value={suche}
              onChange={(e) => setSuche(e.target.value)}
              placeholder="Suchen … z. B. Handy, Datei, Kalender"
            />
          </label>
          <button onClick={onClose} className="wz-zu" aria-label="Werkzeuge schließen"><X size={17} /></button>
        </header>

        <div className="wz-koerper">
          {!sucht && (
            <nav className="werkzeug-scroll wz-nav" aria-label="Bereiche">
              <div className="wz-nav-titel">Jon</div>
              {SPEZIAL.map((s) => (
                <button key={s.id} className={"wz-nav-spezial " + (aktiv === s.id ? "an" : "")} onClick={() => waehlen(s.id)}>
                  <span className="wz-nav-icon"><s.icon size={15} /></span>
                  <span className="wz-nav-text"><b>{s.name}</b><small>{s.text}</small></span>
                </button>
              ))}
              <div className="wz-nav-titel">Werkzeug-Gruppen</div>
              {gruppen.map((g) => (
                <button key={g.id} onClick={() => setAktiv(g.id)} className={"wz-nav-gruppe " + (g.id === aktiv ? "an" : "")}>
                  <span className="wz-nav-symbol">{g.symbol}</span>
                  <span className="wz-nav-name">{g.name}</span>
                  <span className="wz-nav-zahl">{g.anzahl}</span>
                </button>
              ))}
              {laedt && <div className="wz-nav-laedt">Lädt …</div>}
            </nav>
          )}

          <div className={"werkzeug-scroll wz-inhalt " + (spezial ? "wz-inhalt-spezial" : "")}>
            {fehler && <div className="wz-fehler">{fehler}</div>}

            {vorschlaege.map(s => <button key={s.id} className="wz-vorschlag" onClick={() => waehlen(s.id)}><span className="wz-nav-icon"><s.icon size={15} /></span><span><b>{s.name} öffnen</b><small>{s.text}</small></span><ChevronRight size={15} /></button>)}

            {!sucht && aktiv === "harness" && <HarnessPanel />}
            {!sucht && aktiv === "agents" && <AgentTeam request={harnessRequest}/>}
            {!sucht && aktiv === "medien" && <MediaPanel eingebettet />}
            {!sucht && aktiv === "beobachten" && <BeobachtenPanel/>}
            {!sucht && aktiv === "support" && <SupportPanel/>}

            {!sucht && !spezial && gruppe && (
              <div className="wz-gruppen-kopf">
                <span className="wz-gruppen-symbol">{gruppe.symbol}</span>
                <div><h3>{gruppe.name}</h3><p>{gruppe.anzahl} {gruppe.anzahl === 1 ? "Werkzeug" : "Werkzeuge"}</p></div>
              </div>
            )}

            {!sucht && !spezial && gruppenSkill && (
              <div className="wz-skill">
                <BookOpen size={15} />
                <div>
                  <b>Skill „{gruppenSkill.title || gruppenSkill.name}“</b>
                  <p>Diese Anleitung liest Jon selbst, bevor er hier etwas macht. Ändern kannst du sie unter Einstellungen → Skills oder in <code>skills/{gruppenSkill.name}.md</code>.</p>
                </div>
              </div>
            )}

            {!sucht && aktiv === "handy" && (
              <GeraetePanel onPair={() => setKopplung(true)} />
            )}

            {liste.length > 0 && <div className="wz-liste">
              {liste.map((w, i) => (
                <div key={w.name} className="wz-werkzeug" style={{ ["--i" as string]: i }}>
                  <div className="wz-werkzeug-kopf">
                    <code>{w.name}</code>
                    <div className="wz-marken">
                      {w.stufe && <Marke text={STUFENTEXT[w.stufe] ?? w.stufe} ton={STUFENFARBE[w.stufe] ?? ""} />}
                      {w.frei === false && <Marke text="gesperrt" ton="" />}
                      {w.frei === true && <Marke text="frei" ton="wz-marke-gruen" />}
                      <Marke text={w.ohne_rueckfrage ? "ohne Rückfrage" : "fragt nach"} ton="" />
                    </div>
                  </div>
                  {w.beschreibung && <p>{w.beschreibung}</p>}
                </div>
              ))}
            </div>}

            {!laedt && !spezial && liste.length === 0 && !vorschlaege.length && (
              <div className="wz-leer">
                {sucht ? "Nichts gefunden." : "In dieser Gruppe ist gerade nichts frei."}
              </div>
            )}
          </div>
        </div>

        {!spezial && <footer className="wz-fuss">
          „fragt nach“ heißt: Jon holt sich im Chat erst deine Bestätigung, bevor er das Werkzeug ausführt. „gesperrt“ heißt: erst oben freigeben.
        </footer>}
      </div>
      {kopplung && <HandyModal onClose={() => setKopplung(false)} />}
    </div>
  );
}
