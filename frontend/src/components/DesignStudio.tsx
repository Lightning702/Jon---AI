import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import {
  Check,
  CloudFog,
  Dices,
  Droplets,
  Film,
  Heart,
  Image as BildSymbol,
  Link,
  MessageSquare,
  MoonStar,
  Network,
  Palette,
  RotateCcw,
  Save,
  SlidersHorizontal,
  Sparkles,
  Sunrise,
  Trash2,
  Undo2,
  Upload,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  ANNA,
  AUTOMATISCH,
  Design,
  DesignFeld,
  GRENZEN,
  HintergrundArt,
  HintergrundDatei,
  LiveArt,
  SCHRIFTEN,
  STANDARD,
  VORLAGEN,
  Vorlage,
  WIDMUNG_LAENGE,
  akzentDunkel,
  akzentHell,
  designAendern,
  designHolen,
  designSetzen,
  eigenesAktiv,
  eigenesAnwenden,
  eigenesLoeschen,
  eigenesSpeichern,
  geheimOeffnen,
  hintergrundHochladen,
  hintergrundLoeschen,
  hintergrundUrl,
  hintergruendeLaden,
  mischen,
  useDesign,
  useEigene,
  useGeheim,
  vorlageAktiv,
  vorlageAnwenden,
  wirksam,
  zoomMoeglich,
} from "../lib/design";
import type { Theme } from "../lib/theme";
import { herzenSteigen } from "../lib/herzen";
import "./design-studio.css";

type Reiter = "vorlagen" | "farben" | "chat" | "hintergrund" | "anzeige";

const REITER: { id: Reiter; name: string; symbol: LucideIcon }[] = [
  { id: "vorlagen", name: "Vorlagen", symbol: Sparkles },
  { id: "farben", name: "Farben", symbol: Palette },
  { id: "chat", name: "Chat", symbol: MessageSquare },
  { id: "hintergrund", name: "Hintergrund", symbol: BildSymbol },
  { id: "anzeige", name: "Anzeige", symbol: SlidersHorizontal },
];

const AKZENTE = ["#d4af37", "#f59e0b", "#fb923c", "#ef4444", "#f472b6", "#a78bfa", "#5b8cff", "#38bdf8", "#22d3ee", "#34d399", "#a3e635", "#e4e4e7"];

const LIVE: { wert: LiveArt; name: string; symbol: LucideIcon; vorschau: string }[] = [
  { wert: "aurora", name: "Aurora", symbol: Sunrise, vorschau: "radial-gradient(circle at 25% 35%, var(--a) 0%, transparent 55%), radial-gradient(circle at 75% 65%, var(--b) 0%, transparent 60%), var(--g)" },
  { wert: "sterne", name: "Sterne", symbol: MoonStar, vorschau: "radial-gradient(1px 1px at 20% 30%, #fff, transparent), radial-gradient(1px 1px at 70% 20%, #fff, transparent), radial-gradient(1.5px 1.5px at 45% 70%, #fff, transparent), radial-gradient(1px 1px at 85% 60%, var(--a), transparent), radial-gradient(1px 1px at 30% 80%, #fff, transparent), linear-gradient(135deg, var(--g), var(--l))" },
  { wert: "wellen", name: "Wellen", symbol: Droplets, vorschau: "radial-gradient(120% 60% at 50% 120%, var(--a) 0%, transparent 70%), radial-gradient(140% 50% at 30% 130%, var(--b) 0%, transparent 70%), linear-gradient(180deg, var(--g), var(--l))" },
  { wert: "partikel", name: "Netz", symbol: Network, vorschau: "linear-gradient(35deg, transparent 48%, var(--a) 49%, transparent 51%), linear-gradient(-20deg, transparent 48%, var(--a) 49%, transparent 51%), radial-gradient(circle at 30% 20%, var(--l), var(--g))" },
  { wert: "nebel", name: "Nebel", symbol: CloudFog, vorschau: "radial-gradient(circle at 30% 40%, var(--a), transparent 60%), radial-gradient(circle at 80% 70%, var(--b), transparent 55%), radial-gradient(circle at 60% 10%, var(--l), transparent 60%), var(--g)" },
  { wert: "herzen", name: "Herzen", symbol: Heart, vorschau: "radial-gradient(circle at 50% 115%, var(--a) 0%, transparent 60%), radial-gradient(circle at 20% 20%, var(--b) 0%, transparent 40%), radial-gradient(circle at 50% 100%, var(--l), var(--g))" },
];

const HERZ_STELLEN = [
  { x: 14, y: 70, g: 9 },
  { x: 38, y: 30, g: 6 },
  { x: 62, y: 62, g: 11 },
  { x: 84, y: 22, g: 7 },
  { x: 90, y: 74, g: 8 },
];

function HerzStreu() {
  return (
    <>
      {HERZ_STELLEN.map((stelle, index) => (
        <Heart
          key={index}
          size={stelle.g}
          className="ds-mini-herz"
          style={{ left: `${stelle.x}%`, top: `${stelle.y}%` }}
          fill="currentColor"
          strokeWidth={0}
        />
      ))}
    </>
  );
}

const ARTEN: { wert: HintergrundArt; name: string; symbol: LucideIcon }[] = [
  { wert: "farbe", name: "Farbe", symbol: Palette },
  { wert: "bild", name: "Bild", symbol: BildSymbol },
  { wert: "video", name: "Video", symbol: Film },
  { wert: "live", name: "Live", symbol: Sparkles },
];

const VIDEO_ENDUNG = /\.(mp4|m4v|webm|mov|ogv)(?:$|[?#])/i;
const BILD_ENDUNG = /\.(jpe?g|png|webp|gif|avif|bmp|svg)(?:$|[?#])/i;
const MAX_DATEI = 300 * 1024 * 1024;

function geaendert(d: Design, felder: DesignFeld[]): boolean {
  return felder.some((feld) => d[feld] !== STANDARD[feld]);
}

function zuruecksetzen(felder: DesignFeld[]): void {
  const teil: Record<string, unknown> = {};
  for (const feld of felder) teil[feld] = STANDARD[feld];
  designAendern(teil as Partial<Design>);
}

function rgbText(hex: string): string {
  const zahl = parseInt(hex.slice(1), 16);
  return `${(zahl >> 16) & 255} ${(zahl >> 8) & 255} ${zahl & 255}`;
}

function zufallsFarbe(ton: number, saettigung: number, helligkeit: number): string {
  const s = saettigung / 100;
  const l = helligkeit / 100;
  const k = (n: number) => (n + ton / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  return "#" + [f(0), f(8), f(4)].map((w) => Math.round(w * 255).toString(16).padStart(2, "0")).join("");
}

function alpha(hex: string, anteil: number): string {
  return hex + Math.round(Math.max(0, Math.min(1, anteil)) * 255).toString(16).padStart(2, "0");
}

function Schalter({ an, onClick, titel }: { an: boolean; onClick: () => void; titel: string }) {
  return (
    <button type="button" role="switch" aria-checked={an} aria-label={titel} title={titel} className={`ds-schalter ${an ? "an" : ""}`} onClick={onClick}>
      <span />
    </button>
  );
}

function ZurueckKnopf({ aktiv, onClick, titel = "Auf Standard zurücksetzen" }: { aktiv: boolean; onClick: () => void; titel?: string }) {
  return (
    <button type="button" className="ds-zurueck" disabled={!aktiv} onClick={onClick} title={titel} aria-label={titel}>
      <RotateCcw size={13} />
    </button>
  );
}

function Gruppe({ titel, felder, extra, onReset, children }: { titel: string; felder: DesignFeld[]; extra?: boolean; onReset?: () => void; children: ReactNode }) {
  const d = useDesign();
  const anders = geaendert(d, felder) || !!extra;
  return (
    <section className="ds-gruppe">
      <div className="ds-gruppe-kopf">
        <h3>{titel}</h3>
        {(felder.length > 0 || onReset) && (
          <button
            type="button"
            className="ds-leise"
            disabled={!anders}
            onClick={() => {
              zuruecksetzen(felder);
              onReset?.();
            }}
            title={`${titel} auf Standard zurücksetzen`}
          >
            <RotateCcw size={11} />
            Standard
          </button>
        )}
      </div>
      {children}
    </section>
  );
}

function FarbFeld({ feld, titel, hinweis, autoText }: { feld: DesignFeld; titel: string; hinweis?: string; autoText?: string }) {
  const d = useDesign();
  const wert = wirksam(d, feld);
  const auto = AUTOMATISCH.has(feld) && !d[feld];
  const [entwurf, setEntwurf] = useState(wert);

  useEffect(() => setEntwurf(wert), [wert]);

  return (
    <div className="ds-zeile">
      <div className="ds-titel">
        <b>
          {titel}
          {auto && <span className="ds-auto">Auto</span>}
        </b>
        {(auto ? autoText : hinweis) && <small>{auto ? autoText : hinweis}</small>}
      </div>
      <label className="ds-farbe" style={{ background: wert }} title={`${titel} wählen`}>
        <input type="color" value={wert} onChange={(e) => designAendern({ [feld]: e.target.value.toLowerCase() } as Partial<Design>)} aria-label={titel} />
      </label>
      <input
        className="ds-hex"
        value={entwurf}
        spellCheck={false}
        maxLength={7}
        aria-label={`${titel} als Hex-Wert`}
        onChange={(e) => {
          const neu = e.target.value.startsWith("#") ? e.target.value : "#" + e.target.value;
          setEntwurf(neu);
          if (/^#[0-9a-f]{6}$/i.test(neu)) designAendern({ [feld]: neu.toLowerCase() } as Partial<Design>);
        }}
        onBlur={() => setEntwurf(wert)}
      />
      <ZurueckKnopf aktiv={d[feld] !== STANDARD[feld]} onClick={() => zuruecksetzen([feld])} />
    </div>
  );
}

function Regler({ feld, titel, hinweis, einheit = "%", schritt = 1 }: { feld: DesignFeld; titel: string; hinweis?: string; einheit?: string; schritt?: number }) {
  const d = useDesign();
  const [min, max] = GRENZEN[feld] ?? [0, 100];
  const wert = d[feld] as number;
  const anteil = ((wert - min) / (max - min)) * 100;
  return (
    <div className="ds-regel">
      <div className="ds-regel-kopf">
        <div className="ds-titel">
          <b>{titel}</b>
          {hinweis && <small>{hinweis}</small>}
        </div>
        <span className="ds-wert">
          {wert}
          {einheit}
        </span>
        <ZurueckKnopf aktiv={wert !== STANDARD[feld]} onClick={() => zuruecksetzen([feld])} />
      </div>
      <input
        type="range"
        className="ds-regler"
        min={min}
        max={max}
        step={schritt}
        value={wert}
        aria-label={titel}
        style={{ "--ds-anteil": `${anteil}%` } as CSSProperties}
        onChange={(e) => designAendern({ [feld]: Number(e.target.value) } as Partial<Design>)}
        onDoubleClick={() => zuruecksetzen([feld])}
      />
    </div>
  );
}

function Wahl<T extends string>({ wert, optionen, onWahl }: { wert: T; optionen: { wert: T; name: string; symbol?: LucideIcon }[]; onWahl: (wert: T) => void }) {
  return (
    <div className="ds-wahl" role="radiogroup">
      {optionen.map((option) => {
        const Symbol = option.symbol;
        return (
          <button key={option.wert} type="button" role="radio" aria-checked={wert === option.wert} className={wert === option.wert ? "aktiv" : ""} onClick={() => onWahl(option.wert)}>
            {Symbol && <Symbol size={13} />}
            {option.name}
          </button>
        );
      })}
    </div>
  );
}

function Vorschau() {
  const d = useDesign();
  const url = d.hintergrundArt === "bild" || d.hintergrundArt === "video" ? hintergrundUrl(d.quelle) : "";
  const grund: CSSProperties = {
    background:
      d.hintergrundArt === "live"
        ? `radial-gradient(circle at 25% 30%, ${d.akzent}55 0%, transparent 55%), radial-gradient(circle at 80% 75%, ${d.leuchten} 0%, transparent 60%), ${d.hintergrund}`
        : `radial-gradient(circle at 20% 0%, ${d.leuchten} 0%, ${d.hintergrund} 55%, ${mischen(d.hintergrund, "#000000", 0.55)} 100%)`,
  };
  const medien: CSSProperties = {
    filter: [d.bildHelligkeit !== 100 ? `brightness(${d.bildHelligkeit / 100})` : "", d.bildUnschaerfe ? `blur(${d.bildUnschaerfe / 3}px)` : ""].filter(Boolean).join(" ") || undefined,
    objectFit: d.anpassung,
  };
  return (
    <div className="ds-vorschau" style={{ "--weiss-rgb": rgbText(d.text) } as CSSProperties} aria-label="Vorschau">
      <div className="ds-vorschau-grund" style={grund}>
        {d.hintergrundArt === "bild" && url && <img src={url} alt="" style={medien} />}
        {d.hintergrundArt === "video" && url && <video key={url} src={`${url}#t=0.5`} style={medien} muted playsInline preload="metadata" />}
        {d.hintergrundArt !== "farbe" && d.abdunkeln > 0 && <div className="absolute inset-0" style={{ background: d.hintergrund, opacity: d.abdunkeln / 100 }} />}
      </div>
      <div className="flex h-full">
        <div className="glass-strong w-[27%] h-full border-y-0 border-l-0 p-2 flex flex-col gap-1.5">
          <div className="bg-gradient-to-r from-gold-light to-gold-dark text-black rounded-lg text-[9px] font-semibold text-center py-1">Neuer Chat</div>
          <div className="h-2 rounded-full bg-white/10" />
          <div className="h-2 w-3/4 rounded-full bg-white/10" />
          <div className="h-2 w-5/6 rounded-full bg-white/[0.06]" />
        </div>
        <div className="flex-1 min-w-0 flex flex-col gap-1.5 p-2.5">
          <div className="self-end jon-nutzerblase rounded-2xl rounded-br-md px-2.5 py-1.5 text-[10.5px] max-w-[85%]">Wie sieht mein Jon aus?</div>
          <div className="self-start glass jon-jonblase rounded-2xl rounded-bl-md px-2.5 py-1.5 text-[10.5px] max-w-[90%]">Ganz nach deinem Geschmack.</div>
          <div className="mt-auto glass jon-eingabe rounded-xl p-1 flex items-center gap-1.5">
            <span className="flex-1 min-w-0 truncate pl-1.5 text-[10px] text-white/35">Schreib Jon etwas …</span>
            <span className="jon-senden rounded-lg px-2.5 py-1 text-[10px] font-semibold">Senden</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function MiniVorschau({ werte }: { werte: Design }) {
  const hell = akzentHell(werte);
  const dunkel = akzentDunkel(werte);
  const live = LIVE.find((eintrag) => eintrag.wert === werte.live) ?? LIVE[0];
  const datei = werte.hintergrundArt === "bild" || werte.hintergrundArt === "video";
  const url = datei ? hintergrundUrl(werte.quelle) : "";
  const r = werte.rundung / 100;
  const rand = alpha(werte.rand, werte.randDeckkraft / 100);
  const farben = {
    "--a": `${werte.akzent}cc`,
    "--b": `${mischen(werte.akzent, "#ffffff", 0.3)}88`,
    "--g": werte.hintergrund,
    "--l": werte.leuchten,
  } as CSSProperties;
  const grund =
    werte.hintergrundArt === "live"
      ? live.vorschau
      : `radial-gradient(circle at 20% 0%, ${werte.leuchten} 0%, ${werte.hintergrund} 60%, ${mischen(werte.hintergrund, "#000000", 0.55)} 100%)`;
  const filter =
    [
      werte.helligkeit !== 100 ? `brightness(${werte.helligkeit / 100})` : "",
      werte.kontrast !== 100 ? `contrast(${werte.kontrast / 100})` : "",
      werte.saettigung !== 100 ? `saturate(${werte.saettigung / 100})` : "",
      werte.farbton !== 0 ? `hue-rotate(${werte.farbton}deg)` : "",
    ]
      .filter(Boolean)
      .join(" ") || undefined;
  const herzen = werte.herzen || (werte.hintergrundArt === "live" && werte.live === "herzen");
  return (
    <div className="ds-mini" style={{ ...farben, filter }}>
      <div className="ds-mini-grund" style={{ background: grund }}>
        {werte.hintergrundArt === "bild" && url && <img src={url} alt="" loading="lazy" style={{ objectFit: werte.anpassung }} />}
        {werte.hintergrundArt === "video" && url && <video src={`${url}#t=0.5`} muted preload="metadata" style={{ objectFit: werte.anpassung }} />}
        {werte.hintergrundArt !== "farbe" && werte.abdunkeln > 0 && <div className="absolute inset-0" style={{ background: werte.hintergrund, opacity: werte.abdunkeln / 100 }} />}
        {herzen && <HerzStreu />}
      </div>
      <div className="ds-mini-leiste" style={{ background: alpha(werte.leiste, werte.leisteDeckkraft / 100), borderColor: rand }}>
        <i style={{ background: `linear-gradient(90deg, ${hell}, ${dunkel})`, borderRadius: 4 * r }} />
        <b style={{ background: alpha(werte.text, 0.2) }} />
        <b style={{ background: alpha(werte.text, 0.13), width: "70%" }} />
        {werte.widmung && werte.widmungText.trim() && <u style={{ background: alpha(hell, 0.85) }} />}
      </div>
      <div className="ds-mini-chat">
        <span
          className="ds-mini-du"
          style={{
            background: `linear-gradient(135deg, ${werte.nutzerBlase || hell}, ${werte.nutzerBlase2 || dunkel})`,
            borderRadius: `${7 * r}px ${7 * r}px ${2 * r}px ${7 * r}px`,
          }}
        >
          <em style={{ background: alpha(werte.nutzerText, 0.55) }} />
        </span>
        <span
          className="ds-mini-jon"
          style={{
            background: alpha(werte.jonBlase || werte.flaeche, Math.max(0.05, werte.jonBlaseDeckkraft / 100)),
            borderColor: rand,
            borderRadius: `${7 * r}px ${7 * r}px ${7 * r}px ${2 * r}px`,
          }}
        >
          <em style={{ background: alpha(werte.jonText || werte.text, 0.6) }} />
        </span>
        <span
          className="ds-mini-eingabe"
          style={{
            background: alpha(werte.eingabe || werte.flaeche, Math.max(0.05, werte.eingabeDeckkraft / 100)),
            borderColor: rand,
            borderRadius: 5 * r,
          }}
        >
          <em style={{ background: `linear-gradient(90deg, ${werte.senden || hell}, ${werte.senden2 || dunkel})`, borderRadius: 3 * r }} />
        </span>
      </div>
    </div>
  );
}

function VorlagenReiter() {
  const d = useDesign();
  const geheim = useGeheim();
  const eigene = useEigene();
  const [name, setName] = useState("");
  const [gespeichert, setGespeichert] = useState("");
  const [fragt, setFragt] = useState("");
  const vorschlag = `Mein Design ${eigene.length + 1}`;
  const vorlagen = geheim ? [ANNA, ...VORLAGEN] : VORLAGEN;

  const speichern = () => {
    const eintrag = eigenesSpeichern(name.trim() || vorschlag);
    if (!eintrag) return;
    setGespeichert(eintrag.name);
    setName("");
  };

  const loeschen = (id: string) => {
    if (fragt !== id) {
      setFragt(id);
      window.setTimeout(() => setFragt((alt) => (alt === id ? "" : alt)), 3500);
      return;
    }
    setFragt("");
    eigenesLoeschen(id);
  };

  const ueberraschen = () => {
    const ton = Math.floor(Math.random() * 360);
    const live: LiveArt[] = ["aurora", "sterne", "wellen", "partikel", "nebel"];
    const mitLive = Math.random() < 0.6;
    vorlageAnwenden({
      name: "Zufall",
      beschreibung: "",
      werte: {
        akzent: zufallsFarbe(ton, 75, 62),
        hintergrund: zufallsFarbe(ton, 30, 3.5),
        leuchten: zufallsFarbe((ton + 25) % 360, 45, 13),
        text: zufallsFarbe(ton, 60, 97),
        rundung: [60, 100, 140][Math.floor(Math.random() * 3)],
        ...(mitLive ? { hintergrundArt: "live" as const, live: live[Math.floor(Math.random() * live.length)], abdunkeln: 15 } : {}),
      },
    });
  };

  return (
    <>
      <Gruppe titel="Meine Designs" felder={[]}>
        <div className="ds-link">
          <input
            value={name}
            maxLength={40}
            placeholder={vorschlag}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") speichern();
            }}
            aria-label="Name für dein Design"
          />
          <button type="button" className="ds-knopf gold" onClick={speichern}>
            <Save size={13} />
            Speichern
          </button>
        </div>
        {gespeichert && <div className="ds-meldung mb-1.5">„{gespeichert}“ ist gespeichert und bleibt auch nach einem Neustart erhalten.</div>}
        {eigene.length > 0 ? (
          <div className="ds-raster pb-1.5">
            {eigene.map((eintrag) => {
              const aktiv = eigenesAktiv(eintrag, d);
              return (
                <div key={eintrag.id} className={`ds-karte ${aktiv ? "aktiv" : ""}`}>
                  <button type="button" className="flex flex-col gap-1.5 text-left min-w-0" onClick={() => eigenesAnwenden(eintrag)} title={`${eintrag.name} anwenden`}>
                    <MiniVorschau werte={eintrag.werte} />
                    <b className="truncate">{eintrag.name}</b>
                    <small>{new Date(eintrag.zeit).toLocaleDateString("de-DE")}</small>
                  </button>
                  {aktiv && (
                    <span className="ds-haken">
                      <Check size={12} strokeWidth={3} />
                    </span>
                  )}
                  <button
                    type="button"
                    className={`ds-kachel-weg ${fragt === eintrag.id ? "fragt" : ""}`}
                    onClick={() => loeschen(eintrag.id)}
                    title={fragt === eintrag.id ? "Nochmal klicken zum Löschen" : "Design löschen"}
                    aria-label={`${eintrag.name} löschen`}
                  >
                    <Trash2 size={11} />
                    {fragt === eintrag.id && "Löschen?"}
                  </button>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="ds-meldung mb-1.5">Speichere dein aktuelles Design. Es erscheint hier mit Vorschau und bleibt dauerhaft erhalten, auch nach einem Neustart.</div>
        )}
      </Gruppe>
      <div className="ds-raster">
        {vorlagen.map((vorlage: Vorlage) => {
          const werte = { ...STANDARD, ...vorlage.werte };
          const aktiv = vorlageAktiv(vorlage, d);
          const besonders = vorlage === ANNA;
          return (
            <button key={vorlage.name} type="button" className={`ds-karte ${aktiv ? "aktiv" : ""} ${besonders ? "geheim" : ""}`} onClick={() => vorlageAnwenden(vorlage)}>
              <MiniVorschau werte={werte} />
              <b>{vorlage.name}</b>
              <small>{vorlage.beschreibung}</small>
              {besonders && !aktiv && (
                <span className="ds-geheim">
                  <Heart size={9} fill="currentColor" strokeWidth={0} />
                  Geheim
                </span>
              )}
              {aktiv && (
                <span className="ds-haken">
                  <Check size={12} strokeWidth={3} />
                </span>
              )}
            </button>
          );
        })}
      </div>
      <button type="button" className="ds-knopf w-full" onClick={ueberraschen}>
        <Dices size={14} />
        Überrasch mich
      </button>
      <div className="ds-meldung">Vorlagen ändern Farben und Formen. Dein eigenes Hintergrundbild und dein Text unten links bleiben, außer die Vorlage bringt eigene mit.</div>
    </>
  );
}

function FarbenReiter() {
  const d = useDesign();
  return (
    <>
      <Gruppe titel="Akzentfarbe" felder={["akzent"]}>
        <FarbFeld feld="akzent" titel="Akzent" hinweis="Knöpfe, Schalter, Markierungen und alles, was golden leuchtet." />
        <div className="ds-muster">
          {AKZENTE.map((farbe) => (
            <button key={farbe} type="button" className={d.akzent === farbe ? "aktiv" : ""} style={{ background: farbe }} onClick={() => designAendern({ akzent: farbe })} title={farbe} aria-label={`Akzent ${farbe}`} />
          ))}
        </div>
      </Gruppe>
      <Gruppe titel="Schrift" felder={["text"]}>
        <FarbFeld feld="text" titel="Textfarbe" hinweis="Alle Texte, Symbole und feinen Linien der App." />
      </Gruppe>
      <Gruppe titel="Flächen & Karten" felder={["flaeche", "flaecheDeckkraft"]}>
        <FarbFeld feld="flaeche" titel="Farbe" hinweis="Karten, Fenster und das Glas über dem Hintergrund." />
        <Regler feld="flaecheDeckkraft" titel="Deckkraft" hinweis="Höher macht Flächen kräftiger und Text auf Bildern lesbarer." />
      </Gruppe>
      <Gruppe titel="Ränder" felder={["rand", "randDeckkraft"]}>
        <FarbFeld feld="rand" titel="Farbe" />
        <Regler feld="randDeckkraft" titel="Deckkraft" />
      </Gruppe>
      <Gruppe titel="Seitenleiste" felder={["leiste", "leisteDeckkraft"]}>
        <FarbFeld feld="leiste" titel="Farbe" hinweis="Leiste mit deinen Unterhaltungen." />
        <Regler feld="leisteDeckkraft" titel="Deckkraft" />
      </Gruppe>
    </>
  );
}

function ChatReiter() {
  return (
    <>
      <Gruppe titel="Deine Nachrichten" felder={["nutzerBlase", "nutzerBlase2", "nutzerText"]}>
        <FarbFeld feld="nutzerBlase" titel="Farbe oben" autoText="Folgt der Akzentfarbe." />
        <FarbFeld feld="nutzerBlase2" titel="Farbe unten" autoText="Folgt der Akzentfarbe." />
        <FarbFeld feld="nutzerText" titel="Text" />
      </Gruppe>
      <Gruppe titel="Jons Antworten" felder={["jonBlase", "jonBlaseDeckkraft", "jonText"]}>
        <FarbFeld feld="jonBlase" titel="Farbe" autoText="Folgt der Flächenfarbe." />
        <Regler feld="jonBlaseDeckkraft" titel="Deckkraft" />
        <FarbFeld feld="jonText" titel="Text" autoText="Folgt der Textfarbe." />
      </Gruppe>
      <Gruppe titel="Eingabefeld" felder={["eingabe", "eingabeDeckkraft"]}>
        <FarbFeld feld="eingabe" titel="Farbe" autoText="Folgt der Flächenfarbe." />
        <Regler feld="eingabeDeckkraft" titel="Deckkraft" />
      </Gruppe>
      <Gruppe titel="Senden-Knopf" felder={["senden", "senden2", "sendenText"]}>
        <FarbFeld feld="senden" titel="Farbe links" autoText="Folgt der Akzentfarbe." />
        <FarbFeld feld="senden2" titel="Farbe rechts" autoText="Folgt der Akzentfarbe." />
        <FarbFeld feld="sendenText" titel="Schrift" />
      </Gruppe>
    </>
  );
}

function passtZurArt(quelle: string, art: HintergrundArt, liste: HintergrundDatei[]): boolean {
  if (!quelle) return false;
  const eigene = liste.find((eintrag) => eintrag.name === quelle);
  if (eigene) return eigene.art === art;
  if (art === "video") return !BILD_ENDUNG.test(quelle);
  return !VIDEO_ENDUNG.test(quelle);
}

function HintergrundReiter() {
  const d = useDesign();
  const geheim = useGeheim();
  const [liste, setListe] = useState<HintergrundDatei[]>([]);
  const [meldung, setMeldung] = useState("");
  const [fehler, setFehler] = useState(false);
  const [laedt, setLaedt] = useState(false);
  const [zieht, setZieht] = useState(false);
  const [fragt, setFragt] = useState("");
  const [link, setLink] = useState(/^https?:\/\//i.test(d.quelle) ? d.quelle : "");
  const waehler = useRef<HTMLInputElement>(null);
  const datei = d.hintergrundArt === "bild" || d.hintergrundArt === "video";

  const laden = async () => {
    try {
      setListe(await hintergruendeLaden());
    } catch (grund) {
      setFehler(true);
      setMeldung(grund instanceof Error ? grund.message : String(grund));
    }
  };

  useEffect(() => {
    void laden();
  }, []);

  const artWaehlen = (art: HintergrundArt) => {
    if (art === "bild" || art === "video") {
      if (passtZurArt(d.quelle, art, liste)) {
        designAendern({ hintergrundArt: art });
        return;
      }
      const erste = liste.find((eintrag) => eintrag.art === art);
      designAendern({ hintergrundArt: art, quelle: erste ? erste.name : "" });
      return;
    }
    designAendern({ hintergrundArt: art });
  };

  const hochladen = async (dateien: FileList | null) => {
    const wahl = dateien?.[0];
    if (!wahl) return;
    const art = wahl.type.startsWith("video/") || VIDEO_ENDUNG.test(wahl.name) ? "video" : wahl.type.startsWith("image/") || BILD_ENDUNG.test(wahl.name) ? "bild" : "";
    if (!art) {
      setFehler(true);
      setMeldung("Das ist weder ein Bild noch ein Video.");
      return;
    }
    if (wahl.size > MAX_DATEI) {
      setFehler(true);
      setMeldung("Die Datei ist größer als 300 MB.");
      return;
    }
    setLaedt(true);
    setFehler(false);
    setMeldung(`Lade „${wahl.name}“ hoch …`);
    try {
      const eintrag = await hintergrundHochladen(wahl);
      setListe((alt) => [eintrag, ...alt.filter((e) => e.name !== eintrag.name)]);
      designAendern({ hintergrundArt: eintrag.art, quelle: eintrag.name });
      setMeldung("");
    } catch (grund) {
      setFehler(true);
      setMeldung(grund instanceof Error ? grund.message : String(grund));
    } finally {
      setLaedt(false);
    }
  };

  const loeschen = async (eintrag: HintergrundDatei) => {
    if (fragt !== eintrag.name) {
      setFragt(eintrag.name);
      window.setTimeout(() => setFragt((alt) => (alt === eintrag.name ? "" : alt)), 3500);
      return;
    }
    setFragt("");
    try {
      await hintergrundLoeschen(eintrag.name);
      const rest = liste.filter((e) => e.name !== eintrag.name);
      setListe(rest);
      if (d.quelle === eintrag.name) {
        const naechste = rest.find((e) => e.art === eintrag.art);
        designAendern(naechste ? { quelle: naechste.name } : { quelle: "", hintergrundArt: "farbe" });
      }
    } catch (grund) {
      setFehler(true);
      setMeldung(grund instanceof Error ? grund.message : String(grund));
    }
  };

  const linkUebernehmen = () => {
    const adresse = link.trim();
    if (!/^https?:\/\/\S+$/i.test(adresse)) {
      setFehler(true);
      setMeldung("Der Link muss mit http:// oder https:// beginnen.");
      return;
    }
    setFehler(false);
    setMeldung("");
    designAendern({ hintergrundArt: VIDEO_ENDUNG.test(adresse) ? "video" : d.hintergrundArt === "video" ? "video" : "bild", quelle: adresse });
  };

  const passende = liste.filter((eintrag) => eintrag.art === d.hintergrundArt);
  const liveArten = LIVE.filter((eintrag) => eintrag.wert !== "herzen" || geheim || d.live === "herzen");
  const farbenLive = {
    "--a": `${d.akzent}cc`,
    "--b": `${mischen(d.akzent, "#ffffff", 0.3)}88`,
    "--g": d.hintergrund,
    "--l": d.leuchten,
  } as CSSProperties;

  return (
    <>
      <Gruppe titel="Art des Hintergrunds" felder={["hintergrundArt", "quelle", "live"]}>
        <div className="py-1">
          <Wahl wert={d.hintergrundArt} optionen={ARTEN} onWahl={artWaehlen} />
        </div>
      </Gruppe>

      {datei && (
        <Gruppe titel={d.hintergrundArt === "video" ? "Deine Videos" : "Deine Bilder"} felder={[]}>
          <div
            className={`ds-ablage ${zieht ? "zieht" : ""}`}
            role="button"
            tabIndex={0}
            onClick={() => waehler.current?.click()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") waehler.current?.click();
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setZieht(true);
            }}
            onDragLeave={() => setZieht(false)}
            onDrop={(e) => {
              e.preventDefault();
              setZieht(false);
              void hochladen(e.dataTransfer.files);
            }}
          >
            <Upload size={18} />
            <strong>{laedt ? "Lädt hoch …" : d.hintergrundArt === "video" ? "Video hochladen" : "Bild hochladen"}</strong>
            <span>Klicken oder hierher ziehen · bis 300 MB</span>
          </div>
          <input
            ref={waehler}
            type="file"
            className="hidden"
            accept={d.hintergrundArt === "video" ? "video/*,.mp4,.webm,.mov,.m4v" : "image/*"}
            onChange={(e) => {
              void hochladen(e.target.files);
              e.target.value = "";
            }}
          />
          {meldung && <div className={`ds-meldung ${fehler ? "fehler" : ""}`}>{meldung}</div>}
          {passende.length > 0 && (
            <div className="ds-galerie">
              {passende.map((eintrag) => {
                const adresse = hintergrundUrl(eintrag.name);
                return (
                  <div key={eintrag.name} className={`ds-kachel ${d.quelle === eintrag.name ? "aktiv" : ""}`}>
                    <button type="button" className="block w-full h-full" onClick={() => designAendern({ hintergrundArt: eintrag.art, quelle: eintrag.name })} title="Als Hintergrund nehmen">
                      {eintrag.art === "video" ? <video src={`${adresse}#t=0.5`} muted preload="metadata" /> : <img src={adresse} alt="" loading="lazy" />}
                    </button>
                    <button
                      type="button"
                      className={`ds-kachel-weg ${fragt === eintrag.name ? "fragt" : ""}`}
                      onClick={() => void loeschen(eintrag)}
                      title={fragt === eintrag.name ? "Nochmal klicken zum Löschen" : "Löschen"}
                      aria-label="Hintergrund löschen"
                    >
                      <Trash2 size={11} />
                      {fragt === eintrag.name && "Löschen?"}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
          <div className="ds-link">
            <input
              value={link}
              placeholder="Oder Link einfügen: https://…"
              onChange={(e) => setLink(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") linkUebernehmen();
              }}
              aria-label="Link zu Bild oder Video"
            />
            <button type="button" className="ds-knopf" onClick={linkUebernehmen} disabled={!link.trim()}>
              <Link size={13} />
              Nehmen
            </button>
          </div>
        </Gruppe>
      )}

      {d.hintergrundArt === "live" && (
        <Gruppe titel="Live-Hintergrund" felder={["live"]}>
          <div className="ds-raster drei py-1" style={farbenLive}>
            {liveArten.map((eintrag) => {
              const Symbol = eintrag.symbol;
              const aktiv = d.live === eintrag.wert;
              return (
                <button key={eintrag.wert} type="button" className={`ds-karte ${aktiv ? "aktiv" : ""}`} onClick={() => designAendern({ live: eintrag.wert })}>
                  <div className="ds-karte-bild" style={{ background: eintrag.vorschau, height: 48 }}>
                    {eintrag.wert === "herzen" && <HerzStreu />}
                  </div>
                  <b className="flex items-center gap-1.5">
                    <Symbol size={12} />
                    {eintrag.name}
                  </b>
                </button>
              );
            })}
          </div>
          <div className="ds-meldung mb-1">Live-Hintergründe bewegen sich sanft in deiner Akzentfarbe. Wer „Bewegung reduzieren“ in Windows eingeschaltet hat, sieht ein ruhiges Standbild.</div>
        </Gruppe>
      )}

      <Gruppe titel="Grundfarbe" felder={["hintergrund", "leuchten"]}>
        <FarbFeld feld="hintergrund" titel="Hintergrund" hinweis={d.hintergrundArt === "farbe" ? "Die Farbe hinter allem." : "Liegt unter dem Bild und färbt das Abdunkeln."} />
        <FarbFeld feld="leuchten" titel="Leuchten" hinweis="Sanfter Schein oben links und Farbe der Live-Hintergründe." />
      </Gruppe>

      {d.hintergrundArt !== "farbe" && (
        <Gruppe titel="Wirkung" felder={["anpassung", "bildHelligkeit", "bildUnschaerfe", "abdunkeln", "tempo", "fluessig"]}>
          {d.hintergrundArt === "video" && (
            <div className="ds-zeile">
              <div className="ds-titel">
                <b>Flüssig-Modus</b>
                <small>Fenster werden über dem Video abgedunkelt statt weichgezeichnet. Das spart am meisten Rechenleistung und verhindert Ruckeln.</small>
              </div>
              <Schalter an={d.fluessig} onClick={() => designAendern({ fluessig: !d.fluessig })} titel="Flüssig-Modus" />
              <ZurueckKnopf aktiv={d.fluessig !== STANDARD.fluessig} onClick={() => zuruecksetzen(["fluessig"])} />
            </div>
          )}
          {datei && (
            <div className="py-1.5 flex items-center gap-2">
              <div className="flex-1">
                <Wahl
                  wert={d.anpassung}
                  optionen={[
                    { wert: "cover", name: "Füllen" },
                    { wert: "contain", name: "Ganz zeigen" },
                    { wert: "fill", name: "Strecken" },
                  ]}
                  onWahl={(anpassung) => designAendern({ anpassung })}
                />
              </div>
              <ZurueckKnopf aktiv={d.anpassung !== STANDARD.anpassung} onClick={() => zuruecksetzen(["anpassung"])} />
            </div>
          )}
          <Regler feld="bildHelligkeit" titel="Helligkeit" />
          <Regler feld="bildUnschaerfe" titel="Unschärfe" einheit=" px" />
          <Regler feld="abdunkeln" titel="Abdunkeln" hinweis="Legt die Grundfarbe darüber, damit Text gut lesbar bleibt." />
          {(d.hintergrundArt === "video" || d.hintergrundArt === "live") && <Regler feld="tempo" titel="Tempo" schritt={5} />}
        </Gruppe>
      )}
    </>
  );
}

function AnzeigeReiter({ theme, onTheme }: { theme: Theme; onTheme: (theme: Theme) => void }) {
  const d = useDesign();
  const geheim = useGeheim();
  return (
    <>
      <Gruppe titel="Text unten links" felder={["widmung", "widmungText"]}>
        <div className="ds-zeile">
          <div className="ds-titel">
            <b>Neben der Version zeigen</b>
            <small>Steht unten links in der Seitenleiste, bei jedem Hintergrund und jeder Vorlage.</small>
          </div>
          <Schalter an={d.widmung} onClick={() => designAendern({ widmung: !d.widmung })} titel="Eigenen Text anzeigen" />
          <ZurueckKnopf aktiv={d.widmung !== STANDARD.widmung} onClick={() => zuruecksetzen(["widmung"])} />
        </div>
        <div className="ds-zeile">
          <input
            className="ds-text"
            value={d.widmungText}
            maxLength={WIDMUNG_LAENGE}
            placeholder="Dein eigener Text"
            onChange={(e) => designAendern({ widmungText: e.target.value, widmung: d.widmung || !d.widmungText })}
            aria-label="Eigener Text unten links"
          />
          <ZurueckKnopf aktiv={d.widmungText !== STANDARD.widmungText} onClick={() => zuruecksetzen(["widmungText"])} />
        </div>
      </Gruppe>
      {geheim && (
        <Gruppe titel="Herzen" felder={["herzen"]}>
          <div className="ds-zeile">
            <div className="ds-titel">
              <b>Herz-Extras</b>
              <small>Herz statt Punkt im Logo, Herzen beim Senden und Herzaugen im App-Symbol.</small>
            </div>
            <Schalter an={d.herzen} onClick={() => designAendern({ herzen: !d.herzen })} titel="Herz-Extras" />
            <ZurueckKnopf aktiv={d.herzen !== STANDARD.herzen} onClick={() => zuruecksetzen(["herzen"])} />
          </div>
        </Gruppe>
      )}
      <Gruppe titel="Grundstil" felder={[]} extra={theme !== "dark"} onReset={() => onTheme("dark")}>
        <div className="py-1">
          <Wahl
            wert={theme}
            optionen={[
              { wert: "dark", name: "Dunkel" },
              { wert: "light", name: "Hell" },
              { wert: "cozy", name: "Cozy" },
            ]}
            onWahl={onTheme}
          />
        </div>
        {theme !== "dark" && <div className="ds-meldung mb-1">Hell und Cozy drehen alle Farben der App um. Deine eigenen Farben wirken am besten mit „Dunkel“.</div>}
      </Gruppe>
      <Gruppe titel="Bild der ganzen App" felder={["helligkeit", "kontrast", "saettigung", "farbton"]}>
        <Regler feld="helligkeit" titel="Helligkeit" />
        <Regler feld="kontrast" titel="Kontrast" />
        <Regler feld="saettigung" titel="Sättigung" hinweis="0 % macht Jon schwarz-weiß." />
        <Regler feld="farbton" titel="Farbton drehen" einheit="°" hinweis="Verschiebt alle Farben gleichzeitig." />
      </Gruppe>
      <Gruppe titel="Form" felder={["rundung", "glas", "groesse"]}>
        <Regler feld="rundung" titel="Rundung der Ecken" hinweis="0 % ist kantig, 250 % ganz weich." schritt={5} />
        <Regler feld="glas" titel="Glas-Unschärfe" hinweis="Wie stark der Hintergrund hinter Fenstern verschwimmt." schritt={5} />
        {zoomMoeglich() ? (
          <Regler feld="groesse" titel="Größe der Oberfläche" schritt={5} />
        ) : (
          <div className="ds-meldung my-1">Größe der Oberfläche: im Browser mit Strg + Plus und Strg + Minus.</div>
        )}
      </Gruppe>
      <Gruppe titel="Schriftart" felder={["schrift"]}>
        <div className="ds-schriften">
          {SCHRIFTEN.map((schrift) => (
            <button key={schrift.wert} type="button" className={d.schrift === schrift.wert ? "aktiv" : ""} onClick={() => designAendern({ schrift: schrift.wert })}>
              <span style={{ fontFamily: schrift.familie }}>Aa</span>
              <small>{schrift.name}</small>
            </button>
          ))}
        </div>
      </Gruppe>
    </>
  );
}

export default function DesignStudio({ onClose, theme, onTheme }: { onClose: () => void; theme: Theme; onTheme: (theme: Theme) => void }) {
  const d = useDesign();
  const [reiter, setReiter] = useState<Reiter>(() => {
    try {
      const gespeichert = localStorage.getItem("jon_design_reiter");
      return REITER.some((r) => r.id === gespeichert) ? (gespeichert as Reiter) : "vorlagen";
    } catch {
      return "vorlagen";
    }
  });
  const [vorher, setVorher] = useState<Design | null>(null);
  const [vorherTheme, setVorherTheme] = useState<Theme>("dark");
  const [entdeckt, setEntdeckt] = useState(false);
  const inhalt = useRef<HTMLDivElement>(null);
  const panel = useRef<HTMLElement>(null);
  const klicks = useRef<number[]>([]);
  const allesStandard = useMemo(() => JSON.stringify(d) === JSON.stringify(STANDARD) && theme === "dark", [d, theme]);

  const entdecken = () => {
    setVorher(designHolen());
    setVorherTheme(theme);
    geheimOeffnen();
    vorlageAnwenden(ANNA);
    if (theme !== "dark") onTheme("dark");
    wechseln("vorlagen");
    setEntdeckt(true);
    const rahmen = panel.current?.getBoundingClientRect();
    if (rahmen) {
      for (let i = 0; i < 5; i++) herzenSteigen(rahmen.left + rahmen.width * (0.12 + i * 0.19), rahmen.top + rahmen.height * 0.3, 7, 1.6);
    }
    herzenSteigen(window.innerWidth * 0.3, window.innerHeight * 0.75, 16, 2.4);
    herzenSteigen(window.innerWidth * 0.12, window.innerHeight * 0.5, 10, 2);
  };
  const entdeckenRef = useRef(entdecken);
  entdeckenRef.current = entdecken;

  const logoKlick = () => {
    const jetzt = Date.now();
    klicks.current = [...klicks.current.filter((zeit) => jetzt - zeit < 2500), jetzt];
    if (klicks.current.length >= 5) {
      klicks.current = [];
      entdeckenRef.current();
    }
  };

  useEffect(() => {
    let puffer = "";
    const taste = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      const ziel = e.target as HTMLElement | null;
      if (ziel && (ziel.tagName === "INPUT" || ziel.tagName === "TEXTAREA" || ziel.isContentEditable)) return;
      if (e.key.length !== 1 || e.ctrlKey || e.altKey || e.metaKey) return;
      puffer = (puffer + e.key.toLowerCase()).slice(-4);
      if (puffer === "anna") {
        puffer = "";
        entdeckenRef.current();
      }
    };
    window.addEventListener("keydown", taste);
    return () => window.removeEventListener("keydown", taste);
  }, [onClose]);

  useEffect(() => {
    if (!entdeckt) return;
    const timer = window.setTimeout(() => setEntdeckt(false), 8000);
    return () => window.clearTimeout(timer);
  }, [entdeckt]);

  useEffect(() => {
    if (!vorher) return;
    const timer = window.setTimeout(() => setVorher(null), 8000);
    return () => window.clearTimeout(timer);
  }, [vorher]);

  const wechseln = (neu: Reiter) => {
    setReiter(neu);
    inhalt.current?.scrollTo({ top: 0 });
    try {
      localStorage.setItem("jon_design_reiter", neu);
    } catch {
      return;
    }
  };

  const allesZuruecksetzen = () => {
    setVorher(d);
    setVorherTheme(theme);
    designSetzen({ ...STANDARD });
    if (theme !== "dark") onTheme("dark");
  };

  return (
    <aside ref={panel} className="ds-panel" role="dialog" aria-label="Design-Studio">
      <div className="flex items-center gap-3 px-4 pt-3.5 pb-3">
        <button type="button" onClick={logoKlick} aria-label="Design-Studio" className="w-9 h-9 rounded-xl grid place-items-center bg-gradient-to-br from-gold-light to-gold-dark text-black shrink-0">
          <Palette size={17} />
        </button>
        <div className="min-w-0 flex-1">
          <div className="text-[14px] font-semibold text-white/95">Design-Studio</div>
          <div className="text-[11px] text-white/45">Jede Änderung siehst du sofort in der ganzen App.</div>
        </div>
        <button type="button" onClick={onClose} className="ds-zurueck" title="Schließen (Esc)" aria-label="Design-Studio schließen">
          <X size={15} />
        </button>
      </div>
      {entdeckt && (
        <div className="ds-entdeckt" role="status">
          <Heart size={15} fill="currentColor" strokeWidth={0} />
          <span>
            Geheimes Design entdeckt: <b>{ANNA.name}</b>
          </span>
        </div>
      )}
      <Vorschau />
      <div className="ds-reiter" role="tablist">
        {REITER.map((eintrag) => {
          const Symbol = eintrag.symbol;
          return (
            <button key={eintrag.id} type="button" role="tab" aria-selected={reiter === eintrag.id} className={reiter === eintrag.id ? "aktiv" : ""} onClick={() => wechseln(eintrag.id)}>
              <Symbol size={15} />
              {eintrag.name}
            </button>
          );
        })}
      </div>
      <div ref={inhalt} className="ds-inhalt" role="tabpanel">
        {reiter === "vorlagen" && <VorlagenReiter />}
        {reiter === "farben" && <FarbenReiter />}
        {reiter === "chat" && <ChatReiter />}
        {reiter === "hintergrund" && <HintergrundReiter />}
        {reiter === "anzeige" && <AnzeigeReiter theme={theme} onTheme={onTheme} />}
      </div>
      <div className="ds-fuss">
        {vorher ? (
          <button
            type="button"
            className="ds-knopf"
            onClick={() => {
              designSetzen(vorher);
              if (vorherTheme !== theme) onTheme(vorherTheme);
              setVorher(null);
            }}
          >
            <Undo2 size={13} />
            Rückgängig
          </button>
        ) : (
          <button type="button" className="ds-knopf" onClick={allesZuruecksetzen} disabled={allesStandard} title="Setzt Farben, Hintergrund, Schrift und Anzeige auf Jons Standard zurück.">
            <RotateCcw size={13} />
            Alles auf Standard
          </button>
        )}
        <div className="flex-1" />
        <button type="button" className="ds-knopf gold" onClick={onClose}>
          <Check size={14} />
          Fertig
        </button>
      </div>
    </aside>
  );
}
