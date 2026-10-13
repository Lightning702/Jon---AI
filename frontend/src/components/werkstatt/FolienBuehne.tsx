import { useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { ArrowRight, Check, Image as ImageIcon, Loader2, Trash2 } from "lucide-react";
import type { PptxAktion, RenderQuelle, WerkstattErgebnis, WerkstattFarben, WerkstattFolie } from "../../lib/werkstatt";
import { anteil, schnitt, useAblauf, useEchteSeiten } from "./ablauf";

const STANDARD_FARBEN: WerkstattFarben = {
  primary: "#1E2761",
  secondary: "#CADCFC",
  accent: "#F5B841",
  dark: "#121A3F",
  light: "#F7F9FF",
  muted: "#5B6486",
  soft: "#E8EDFB",
};

const GRUPPEN: Record<string, string> = {
  title: "titel",
  closing: "schluss",
  quote: "zitat",
  stat: "zahlen",
  stats: "zahlen",
  cards: "karten",
  two_columns: "spalten",
  columns: "spalten",
  compare: "spalten",
  vergleich: "spalten",
  timeline: "ablauf",
  table: "tabelle",
  tabelle: "tabelle",
  chart: "diagramm",
  diagramm: "diagramm",
  image: "bild",
};

export function farbStil(farben?: WerkstattFarben): CSSProperties {
  const f = farben ?? STANDARD_FARBEN;
  return {
    ["--f-p" as string]: f.primary,
    ["--f-s" as string]: f.secondary,
    ["--f-a" as string]: f.accent,
    ["--f-d" as string]: f.dark,
    ["--f-l" as string]: f.light,
    ["--f-m" as string]: f.muted,
    ["--f-w" as string]: f.soft,
  };
}

export function folienKosten(f: WerkstattFolie): number {
  let k = 5 + (f.titel?.length ?? 0) / 2 + (f.untertitel?.length ?? 0) / 3 + (f.text?.length ?? 0) / 4;
  for (const p of f.punkte ?? []) k += 5 + p.length / 4;
  for (const i of f.items ?? []) k += 6 + (i.titel.length + i.text.length) / 4 + i.punkte.reduce((s, p) => s + 3 + p.length / 5, 0);
  if (f.tabelle?.length) k += f.tabelle.length * 4;
  if (f.diagramm) k += 10;
  if (f.bild) k += 6;
  return k;
}

function Getippt({ text, wert, mini }: { text: string; wert: number; mini?: boolean }) {
  return (
    <>
      {schnitt(text, wert)}
      {!mini && wert > 0 && wert < 1 && <i className="lw-caret" />}
    </>
  );
}

function Bildfeld({ hinweis, wert, klasse = "" }: { hinweis: string; wert: number; klasse?: string }) {
  return (
    <div className={`lw-f-bild ${klasse}`} style={{ opacity: wert, transform: `scale(${0.92 + 0.08 * wert})` }}>
      <ImageIcon />
      <span>{hinweis}</span>
      {wert > 0 && wert < 1 && <em className="lw-f-bild-laden" />}
    </div>
  );
}

export function FolieBild({ folie, farben, fortschritt = Number.POSITIVE_INFINITY, nummer, mini = false }: { folie: WerkstattFolie; farben?: WerkstattFarben; fortschritt?: number; nummer: number; mini?: boolean }) {
  let rest = fortschritt - 5;
  const nimm = (kosten: number) => {
    const wert = anteil(rest, kosten);
    rest -= kosten;
    return wert;
  };
  const gruppe = GRUPPEN[folie.layout] ?? "liste";
  const rahmen = anteil(fortschritt, 5);
  const titelWert = nimm((folie.titel?.length ?? 0) / 2);
  const unterWert = nimm((folie.untertitel?.length ?? 0) / 3);
  const textWert = nimm((folie.text?.length ?? 0) / 4);
  const punktWerte = (folie.punkte ?? []).map((p) => nimm(5 + p.length / 4));
  const itemWerte = (folie.items ?? []).map((i) => nimm(6 + (i.titel.length + i.text.length) / 4 + i.punkte.reduce((s, p) => s + 3 + p.length / 5, 0)));
  const tabellenWert = folie.tabelle?.length ? nimm(folie.tabelle.length * 4) : 0;
  const diagrammWert = folie.diagramm ? nimm(10) : 0;
  const bildWert = folie.bild ? nimm(6) : 0;

  const titel = folie.titel ? <Getippt text={folie.titel} wert={titelWert} mini={mini} /> : null;
  const unter = folie.untertitel ? <Getippt text={folie.untertitel} wert={unterWert} mini={mini} /> : null;
  const intro = folie.text ? (
    <p className="lw-f-intro">
      <Getippt text={folie.text} wert={textWert} mini={mini} />
    </p>
  ) : null;
  const punkte = folie.punkte?.length ? (
    <ul className="lw-f-punkte">
      {folie.punkte.map((p, i) => (
        <li key={i} className={p.startsWith("  ") ? "unter" : ""} style={{ opacity: punktWerte[i] > 0 ? 1 : 0, transform: `translateX(${(1 - Math.min(1, punktWerte[i] * 3)) * -6}px)` }}>
          <Getippt text={p.trim()} wert={punktWerte[i]} mini={mini} />
        </li>
      ))}
    </ul>
  ) : null;

  let inhalt: ReactNode;
  if (gruppe === "titel" || gruppe === "schluss") {
    inhalt = (
      <div className="lw-f-mitte">
        <span className="lw-f-akzent" style={{ width: `${Math.max(0, Math.min(1, rahmen)) * 14}cqw` }} />
        <h3>{titel}</h3>
        {unter && <p className="lw-f-unter">{unter}</p>}
        {intro}
        {punkte}
      </div>
    );
  } else if (gruppe === "zitat") {
    inhalt = (
      <div className="lw-f-mitte">
        <span className="lw-f-zeichen">&ldquo;</span>
        <blockquote>{folie.text ? <Getippt text={folie.text} wert={textWert} mini={mini} /> : titel}</blockquote>
        {folie.text && titel && <p className="lw-f-unter">{titel}</p>}
      </div>
    );
  } else {
    const items = folie.items ?? [];
    let rumpf: ReactNode = punkte;
    if (gruppe === "karten" || gruppe === "zahlen" || (gruppe === "liste" && items.length && !punkte)) {
      rumpf = (
        <div className={`lw-f-karten ${gruppe === "zahlen" ? "zahlen" : ""}`} style={{ gridTemplateColumns: `repeat(${Math.min(3, Math.max(1, items.length))}, 1fr)` }}>
          {items.map((item, i) => (
            <div key={i} className="lw-f-karte" style={{ opacity: itemWerte[i] > 0 ? 1 : 0, transform: `translateY(${(1 - Math.min(1, itemWerte[i] * 2)) * 6}px)` }}>
              <b>
                <Getippt text={item.titel} wert={Math.min(1, itemWerte[i] * 2)} mini={mini} />
              </b>
              {item.text && (
                <span>
                  <Getippt text={item.text} wert={Math.max(0, itemWerte[i] * 2 - 1)} mini={mini} />
                </span>
              )}
            </div>
          ))}
        </div>
      );
    } else if (gruppe === "spalten") {
      rumpf = (
        <div className="lw-f-spalten">
          {items.map((item, i) => (
            <div key={i} className="lw-f-spalte" style={{ opacity: itemWerte[i] > 0 ? 1 : 0 }}>
              <b>{item.titel}</b>
              {item.text && <span>{item.text}</span>}
              <ul>
                {item.punkte.map((p, j) => (
                  <li key={j} style={{ opacity: itemWerte[i] >= (j + 1) / (item.punkte.length + 1) ? 1 : 0 }}>
                    {p.replace(/^–\s*/, "")}
                  </li>
                ))}
              </ul>
            </div>
          ))}
          {!items.length && punkte}
        </div>
      );
    } else if (gruppe === "ablauf") {
      rumpf = (
        <div className="lw-f-ablauf">
          <span className="lw-f-linie" style={{ transform: `scaleX(${items.length ? Math.max(0, ...itemWerte.map((w, i) => (w > 0 ? (i + w) / items.length : 0))) : 0})` }} />
          {items.map((item, i) => (
            <div key={i} className="lw-f-schritt" style={{ opacity: itemWerte[i] > 0 ? 1 : 0 }}>
              <i>{i + 1}</i>
              <b>{item.titel}</b>
              {item.text && <span>{schnitt(item.text, itemWerte[i])}</span>}
            </div>
          ))}
          {!items.length && punkte}
        </div>
      );
    } else if (gruppe === "tabelle" && folie.tabelle?.length) {
      const zeilen = Math.ceil(folie.tabelle.length * tabellenWert);
      rumpf = (
        <table className="lw-f-tabelle">
          <tbody>
            {folie.tabelle.slice(0, Math.max(0, zeilen)).map((zeile, i) => (
              <tr key={i} className={i === 0 ? "kopf" : ""}>
                {zeile.map((zelle, j) => (
                  <td key={j}>{zelle}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      );
    } else if (gruppe === "diagramm" && folie.diagramm) {
      const werte = folie.diagramm.werte.length ? folie.diagramm.werte : [3, 5, 4, 7];
      const hoechster = Math.max(...werte.map((w) => Math.abs(w)), 1);
      rumpf = (
        <div className="lw-f-diagramm">
          {werte.map((w, i) => (
            <div key={i} className="lw-f-saeule">
              <span style={{ height: `${(Math.abs(w) / hoechster) * 100 * diagrammWert}%` }} />
              <small>{folie.diagramm?.kategorien[i] ?? ""}</small>
            </div>
          ))}
        </div>
      );
    }
    const bild = folie.bild ? <Bildfeld hinweis={folie.bild} wert={bildWert} klasse={gruppe === "bild" ? "gross" : ""} /> : null;
    inhalt = (
      <>
        <div className="lw-f-kopf">
          <span className="lw-f-balken" style={{ transform: `scaleY(${rahmen})` }} />
          <h3>{titel}</h3>
        </div>
        {unter && <p className="lw-f-unter klein">{unter}</p>}
        <div className={`lw-f-rumpf ${bild ? "mit-bild" : ""} ${gruppe === "bild" ? "bild-gross" : ""}`}>
          <div className="lw-f-text">
            {intro}
            {rumpf}
            {!rumpf && !intro && items.length > 0 && punkte}
          </div>
          {bild}
        </div>
      </>
    );
  }

  return (
    <div className={`lw-folie lw-l-${gruppe} ${mini ? "mini" : ""}`} style={{ ...farbStil(farben), opacity: Math.max(0.0001, rahmen) }}>
      {inhalt}
      {!mini && folie.quelle && <span className="lw-f-quelle">{folie.quelle}</span>}
      <span className="lw-f-nr">{nummer}</span>
    </div>
  );
}

function Leiste({ anzahl, aktiv, onWahl, inhalt, bereit }: { anzahl: number; aktiv: number; onWahl: (i: number) => void; inhalt: (i: number) => ReactNode; bereit: (i: number) => boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const leiste = ref.current;
    const kind = leiste?.children[aktiv] as HTMLElement | undefined;
    if (!leiste || !kind) return;
    const ziel = kind.offsetLeft - leiste.clientWidth / 2 + kind.clientWidth / 2;
    leiste.scrollTo({ left: Math.max(0, ziel), behavior: "smooth" });
  }, [aktiv]);
  return (
    <div className="lw-leiste" ref={ref}>
      {Array.from({ length: anzahl }, (_, i) => (
        <button key={i} type="button" className={`lw-mini ${i === aktiv ? "aktiv" : ""} ${bereit(i) ? "" : "wartet"}`} onClick={() => bereit(i) && onWahl(i)} aria-label={`Folie ${i + 1}`}>
          {bereit(i) ? inhalt(i) : <span className="lw-mini-leer" />}
          <small>{i + 1}</small>
        </button>
      ))}
    </div>
  );
}

function EchtSchalter({ echt, setEcht }: { echt: boolean; setEcht: (v: boolean) => void }) {
  return (
    <span className="lw-schalter" role="group">
      <button type="button" className={!echt ? "an" : ""} onClick={() => setEcht(false)}>
        Entwurf
      </button>
      <button type="button" className={echt ? "an" : ""} onClick={() => setEcht(true)}>
        Echt
      </button>
    </span>
  );
}

function renderText(status: string | undefined, art: string): string {
  if (status === "laeuft" || status === "offen") return `Echte ${art} werden gerendert …`;
  if (status === "nicht_moeglich") return "Vorschau – zum Rendern fehlt PowerPoint oder LibreOffice";
  if (status === "fehler") return "Echte Ansicht nicht möglich – Entwurf wird gezeigt";
  return "";
}

export function FolienAnsicht({ titel, farben, folien, ergebnis, laeuft, animieren, render, kompakt }: { titel: string; farben: WerkstattFarben; folien: WerkstattFolie[]; ergebnis?: WerkstattErgebnis; laeuft: boolean; animieren: boolean; render?: RenderQuelle; kompakt?: boolean }) {
  const grenzen = useMemo(() => {
    let summe = 0;
    return folien.map((f) => (summe += folienKosten(f)));
  }, [folien]);
  const gesamt = grenzen.at(-1) ?? 0;
  const p = useAblauf(gesamt, animieren, laeuft, Math.min(34000, Math.max(3500, folien.length * 1800)));
  const fertigAnimiert = p >= gesamt;
  const aktuell = fertigAnimiert ? -1 : grenzen.findIndex((g) => g > p);
  const [wahl, setWahl] = useState<number | null>(null);
  const echt = useEchteSeiten(ergebnis?.pfad, !!ergebnis?.ok && !!ergebnis.office, render);
  const echtFertig = echt?.status === "fertig" && !!echt.seiten;
  const [zeigeEcht, setZeigeEcht] = useState(true);
  const mitEcht = echtFertig && zeigeEcht && !!ergebnis?.pfad;
  const anzahl = mitEcht ? echt?.seiten ?? 0 : folien.length;
  const index = Math.min(anzahl - 1, Math.max(0, wahl ?? (aktuell >= 0 ? aktuell : 0)));
  const fortschrittVon = (i: number) => (aktuell < 0 || i < aktuell ? Number.POSITIVE_INFINITY : i === aktuell ? p - (grenzen[i - 1] ?? 0) : 0);
  const bereit = (i: number) => mitEcht || aktuell < 0 || i <= aktuell;
  const seite = (i: number) => (render && ergebnis?.pfad && echt?.version !== undefined ? render.seite(ergebnis.pfad, i + 1, echt.version) : "");

  let zeile = "";
  if (aktuell >= 0) zeile = `Jon gestaltet Folie ${aktuell + 1} von ${folien.length}`;
  else if (laeuft) zeile = "Jon setzt die Präsentation zusammen, sucht Bilder und speichert …";
  else if (ergebnis && !ergebnis.ok) zeile = "Die Präsentation konnte nicht erstellt werden";
  else zeile = renderText(echt?.status, "Folien") || (mitEcht ? `Echte Folien · ${anzahl}` : `Fertig · ${ergebnis?.folien ?? folien.length} Folien`);
  const notiz = !mitEcht && !kompakt ? folien[index]?.notizen : "";

  if (!folien.length) return <div className="lw-leer">{titel || "Präsentation"} wird vorbereitet …</div>;

  return (
    <div className="lw-folien">
      <div className="lw-zeile">
        {(aktuell >= 0 || laeuft || echt?.status === "laeuft") && <Loader2 className="lw-dreh" />}
        <span>{zeile}</span>
        {echtFertig && <EchtSchalter echt={zeigeEcht} setEcht={setZeigeEcht} />}
      </div>
      <div className="lw-buehne">
        {mitEcht ? (
          <img className="lw-echt" src={seite(index)} alt={`Folie ${index + 1}`} draggable={false} />
        ) : (
          <FolieBild folie={folien[index]} farben={farben} fortschritt={fortschrittVon(index)} nummer={index + 1} />
        )}
      </div>
      {notiz && <p className="lw-notiz">Sprechernotiz: {notiz}</p>}
      {anzahl > 1 && (
        <Leiste
          anzahl={anzahl}
          aktiv={index}
          onWahl={setWahl}
          bereit={bereit}
          inhalt={(i) => (mitEcht ? <img src={seite(i)} alt="" loading="lazy" draggable={false} /> : <FolieBild folie={folien[i]} farben={farben} fortschritt={fortschrittVon(i)} nummer={i + 1} mini />)}
        />
      )}
      {!!ergebnis?.hinweise?.length && (
        <ul className="lw-hinweise">
          {ergebnis.hinweise.map((h, i) => (
            <li key={i}>{h}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function aenderungsKosten(a: PptxAktion): number {
  return 12 + ((a.text?.length ?? 0) + (a.alt?.length ?? 0) + (a.neu?.length ?? 0)) / 4 + (a.folie_inhalt ? folienKosten(a.folie_inhalt) : 0);
}

function farbe(wert?: string): string {
  const roh = String(wert || "").trim();
  if (/^[0-9a-f]{6}$/i.test(roh)) return "#" + roh;
  return roh || "#1E2761";
}

function AenderungsBild({ aktion, wert, farben }: { aktion: PptxAktion; wert: number; farben: WerkstattFarben }) {
  const art = aktion.art;
  if (art === "folie_neu" && aktion.folie_inhalt) {
    return <FolieBild folie={aktion.folie_inhalt} farben={farben} fortschritt={wert * (folienKosten(aktion.folie_inhalt) + 6)} nummer={(aktion.nach ?? 0) + 1} />;
  }
  const textWert = Math.max(0, wert * 1.25 - 0.15);
  let effekt: ReactNode = null;
  let hintergrund: string | undefined;
  if (art === "ersetzen") {
    effekt = (
      <div className="lw-ae-box">
        <s style={{ opacity: 1 - Math.max(0, wert * 2 - 1) * 0.6, backgroundSize: `${Math.min(1, wert * 2) * 100}% 2px` }}>{aktion.alt}</s>
        <ins>
          <Getippt text={aktion.neu ?? ""} wert={Math.max(0, wert * 2 - 1)} />
        </ins>
      </div>
    );
  } else if (art === "text" || art === "textfeld" || art === "schrift" || art === "format") {
    effekt = (
      <div className={`lw-ae-box ${art === "textfeld" ? "neu" : ""} ${art === "schrift" || art === "format" ? "format" : ""}`} style={art === "schrift" || art === "format" ? { fontWeight: wert > 0.5 ? 700 : 400 } : undefined}>
        {art === "schrift" || art === "format" ? <span>{aktion.text || "Formatierung"}</span> : <Getippt text={aktion.text ?? ""} wert={textWert} />}
      </div>
    );
  } else if (art === "notizen") {
    effekt = (
      <div className="lw-ae-notiz">
        <small>Notizen</small>
        <Getippt text={aktion.text ?? ""} wert={textWert} />
      </div>
    );
  } else if (art.startsWith("bild")) {
    effekt = <Bildfeld hinweis={aktion.text || "Bild"} wert={Math.min(1, wert * 1.4)} klasse={`pos-${(aktion.position || "rechts").replace(/[^a-z]/g, "")}`} />;
  } else if (art === "hintergrund") {
    hintergrund = farbe(aktion.farbe);
  } else if (art === "folie_loeschen" || art === "element_loeschen") {
    effekt = (
      <div className={`lw-ae-weg ${art === "folie_loeschen" ? "ganz" : ""}`} style={{ opacity: Math.min(1, wert * 2) }}>
        <Trash2 />
      </div>
    );
  } else if (art === "folie_verschieben" || art === "folie_duplizieren") {
    effekt = (
      <div className="lw-ae-reihe">
        <span className="lw-ae-mini">{aktion.folie ?? "?"}</span>
        <ArrowRight style={{ opacity: Math.min(1, wert * 2) }} />
        <span className="lw-ae-mini" style={{ opacity: Math.min(1, wert * 1.5), transform: `translateX(${(1 - Math.min(1, wert * 1.5)) * -20}px)` }}>
          {art === "folie_duplizieren" ? `${aktion.folie ?? "?"}′` : (aktion.nach ?? 0) + 1}
        </span>
      </div>
    );
  } else if (art === "diagramm") {
    effekt = (
      <div className="lw-f-diagramm klein">
        {[0.5, 0.8, 0.6, 1, 0.7].map((h, i) => (
          <div key={i} className="lw-f-saeule">
            <span style={{ height: `${h * 100 * Math.min(1, wert * 1.3)}%` }} />
          </div>
        ))}
      </div>
    );
  } else {
    effekt = <div className="lw-ae-box puls">{aktion.text || aktion.titel}</div>;
  }
  return (
    <div className="lw-folie lw-l-liste lw-ae" style={{ ...farbStil(farben), ...(hintergrund ? { background: `linear-gradient(135deg, ${hintergrund}, ${hintergrund})`, transition: "background 0.6s" } : {}) }}>
      <div className="lw-f-kopf">
        <span className="lw-f-balken" />
        <h3>
          <span className="lw-ae-platz w60" />
        </h3>
      </div>
      <div className="lw-ae-zeilen">
        <span className="lw-ae-platz w80" />
        <span className="lw-ae-platz w70" />
        <span className="lw-ae-platz w50" />
      </div>
      {effekt}
      <span className="lw-f-nr">{aktion.folie ?? ""}</span>
    </div>
  );
}

export function SchrittListe<T extends { titel: string }>({ aktionen, aktuell, fertig, beschreibung }: { aktionen: T[]; aktuell: number; fertig: boolean; beschreibung: (a: T) => string }) {
  return (
    <ol className="lw-schritte">
      {aktionen.map((a, i) => {
        const erledigt = fertig || (aktuell >= 0 ? i < aktuell : true);
        const dran = !fertig && i === aktuell;
        return (
          <li key={i} className={erledigt ? "erledigt" : dran ? "dran" : ""}>
            <i>{erledigt ? <Check /> : dran ? <Loader2 className="lw-dreh" /> : i + 1}</i>
            <span>
              <b>{a.titel}</b>
              {beschreibung(a) && <small>{beschreibung(a)}</small>}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function pptxBeschreibung(a: PptxAktion): string {
  const ort = [a.folie !== undefined ? `Folie ${a.folie}` : "", a.element !== undefined ? `Element ${a.element}` : ""].filter(Boolean).join(" · ");
  const inhalt = a.art === "ersetzen" ? `„${a.alt ?? ""}“ → „${a.neu ?? ""}“` : a.art === "folie_neu" ? a.folie_inhalt?.titel ?? "" : a.text ?? a.farbe ?? "";
  return [ort, inhalt].filter(Boolean).join(" – ").slice(0, 160);
}

export function FolienAenderungAnsicht({ pfad, aktionen, farben, ergebnis, laeuft, animieren, render }: { pfad: string; aktionen: PptxAktion[]; farben?: WerkstattFarben; ergebnis?: WerkstattErgebnis; laeuft: boolean; animieren: boolean; render?: RenderQuelle; kompakt?: boolean }) {
  const grenzen = useMemo(() => {
    let summe = 0;
    return aktionen.map((a) => (summe += aenderungsKosten(a)));
  }, [aktionen]);
  const gesamt = grenzen.at(-1) ?? 0;
  const p = useAblauf(gesamt, animieren, laeuft, Math.min(26000, Math.max(2500, aktionen.length * 1500)));
  const aktuell = p >= gesamt ? -1 : grenzen.findIndex((g) => g > p);
  const zeigen = aktuell >= 0 ? aktuell : Math.max(0, aktionen.length - 1);
  const start = grenzen[zeigen - 1] ?? 0;
  const wert = aktuell >= 0 ? anteil(p - start, (grenzen[zeigen] ?? 1) - start) : 1;
  const echt = useEchteSeiten(ergebnis?.pfad || pfad, !!ergebnis?.ok && !laeuft, render);
  const echtFertig = echt?.status === "fertig" && !!echt.seiten && !!render;
  const betroffen = useMemo(() => {
    const menge = new Set<number>();
    for (const a of aktionen) {
      if (a.art === "folie_neu") menge.add((a.nach ?? 0) + 1);
      else if (a.art !== "folie_loeschen" && a.folie) menge.add(a.folie);
    }
    return [...menge].sort((x, y) => x - y);
  }, [aktionen]);
  const seiten = echtFertig ? (betroffen.length ? betroffen.filter((n) => n <= (echt?.seiten ?? 0)) : Array.from({ length: echt?.seiten ?? 0 }, (_, i) => i + 1)) : [];
  const [wahl, setWahl] = useState(0);
  const quelle = ergebnis?.pfad || pfad;
  const f = farben ?? STANDARD_FARBEN;
  let zeile = aktuell >= 0 ? `Schritt ${aktuell + 1} von ${aktionen.length}: ${aktionen[aktuell].titel}` : laeuft ? "Jon speichert die Präsentation …" : ergebnis && !ergebnis.ok ? "Die Änderungen konnten nicht übernommen werden" : renderText(echt?.status, "Folien") || "Alle Änderungen übernommen";
  if (echtFertig) zeile = `Bearbeitete Folien · ${seiten.length}`;

  return (
    <div className="lw-aenderung">
      <div className="lw-zeile">
        {(aktuell >= 0 || laeuft || echt?.status === "laeuft") && <Loader2 className="lw-dreh" />}
        <span>{zeile}</span>
      </div>
      <div className="lw-zwei">
        <div className="lw-buehne">
          {echtFertig && seiten.length && render ? (
            <img className="lw-echt" src={render.seite(quelle, seiten[Math.min(wahl, seiten.length - 1)], echt?.version ?? "")} alt="" draggable={false} />
          ) : aktionen.length ? (
            <AenderungsBild aktion={aktionen[zeigen]} wert={wert} farben={f} />
          ) : null}
        </div>
        <SchrittListe aktionen={aktionen} aktuell={aktuell} fertig={!laeuft && aktuell < 0} beschreibung={pptxBeschreibung} />
      </div>
      {echtFertig && seiten.length > 1 && render && (
        <div className="lw-leiste">
          {seiten.map((n, i) => (
            <button key={n} type="button" className={`lw-mini ${i === wahl ? "aktiv" : ""}`} onClick={() => setWahl(i)}>
              <img src={render.seite(quelle, n, echt?.version ?? "")} alt="" loading="lazy" draggable={false} />
              <small>{n}</small>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
