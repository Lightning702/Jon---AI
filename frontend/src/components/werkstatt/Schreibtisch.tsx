import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Image as ImageIcon, Loader2 } from "lucide-react";
import type { DocxAktion, DokumentBlock, RenderQuelle, WerkstattErgebnis } from "../../lib/werkstatt";
import { anteil, schnitt, useAblauf, useEchteSeiten } from "./ablauf";
import { SchrittListe } from "./FolienBuehne";

function blockKosten(b: DokumentBlock): number {
  return b.typ === "leer" ? 1 : 2 + b.text.length / 3;
}

function Caret({ wert }: { wert: number }) {
  return wert > 0 && wert < 1 ? <i className="lw-caret dunkel" /> : null;
}

function inline(text: string): ReactNode {
  const teile = text.split(/(\*\*[^*]+\*\*)/g);
  return teile.map((teil, i) => (teil.startsWith("**") && teil.endsWith("**") && teil.length > 4 ? <b key={i}>{teil.slice(2, -2)}</b> : <span key={i}>{teil}</span>));
}

function Block({ block, wert, nummer }: { block: DokumentBlock; wert: number; nummer: number }) {
  const text = schnitt(block.text, wert);
  const inhalt = (
    <>
      {inline(text)}
      <Caret wert={wert} />
    </>
  );
  switch (block.typ) {
    case "h1":
      return <h1>{inhalt}</h1>;
    case "h2":
      return <h2>{inhalt}</h2>;
    case "h3":
    case "h4":
      return <h3>{inhalt}</h3>;
    case "punkt":
      return <p className="lw-d-punkt">{inhalt}</p>;
    case "nummer":
      return (
        <p className="lw-d-nummer">
          <span>{nummer}.</span>
          {inhalt}
        </p>
      );
    case "leer":
      return <div className="lw-d-leer" />;
    case "trenner":
      return <hr className="lw-d-trenner" />;
    case "tabelle": {
      const zeilen = text
        .split("\n")
        .map((z) => z.trim().replace(/^\||\|$/g, "").split("|").map((s) => s.trim()))
        .filter((z) => z.some((s) => s) && !z.every((s) => !s || /^:?-{2,}:?$/.test(s.replace(/\s/g, ""))));
      return (
        <table className="lw-d-tabelle">
          <tbody>
            {zeilen.map((z, r) => (
              <tr key={r}>
                {z.map((s, c) => (r === 0 ? <th key={c}>{inline(s)}</th> : <td key={c}>{inline(s)}</td>))}
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    default:
      return <p>{inhalt}</p>;
  }
}

function EchteSeiten({ pfad, render, version, seiten, wahl, setWahl }: { pfad: string; render: RenderQuelle; version: string; seiten: number; wahl: number; setWahl: (n: number) => void }) {
  return (
    <>
      <div className="lw-seite-echt">
        <img src={render.seite(pfad, wahl + 1, version)} alt={`Seite ${wahl + 1}`} draggable={false} />
      </div>
      {seiten > 1 && (
        <div className="lw-leiste hoch">
          {Array.from({ length: seiten }, (_, i) => (
            <button key={i} type="button" className={`lw-mini hoch ${i === wahl ? "aktiv" : ""}`} onClick={() => setWahl(i)}>
              <img src={render.seite(pfad, i + 1, version)} alt="" loading="lazy" draggable={false} />
              <small>{i + 1}</small>
            </button>
          ))}
        </div>
      )}
    </>
  );
}

const FORMATE: Record<string, string> = { docx: "Word", odt: "Writer", pdf: "PDF", md: "Markdown", markdown: "Markdown", txt: "Text", text: "Text", rtf: "RTF" };

export function formatName(format: string): string {
  return FORMATE[format] ?? format.toUpperCase();
}

export function DokumentAnsicht({ titel, format, bloecke, ergebnis, laeuft, animieren, render, kompakt }: { titel: string; format: string; bloecke: DokumentBlock[]; ergebnis?: WerkstattErgebnis; laeuft: boolean; animieren: boolean; render?: RenderQuelle; kompakt?: boolean }) {
  const grenzen = useMemo(() => {
    let summe = 0;
    return bloecke.map((b) => (summe += blockKosten(b)));
  }, [bloecke]);
  const titelKosten = titel.length / 3 + 2;
  const gesamt = (grenzen.at(-1) ?? 0) + titelKosten;
  const p = useAblauf(gesamt, animieren, laeuft, Math.min(16000, Math.max(2500, gesamt * 28)));
  const tippt = p < gesamt;
  const seite = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (tippt && seite.current) seite.current.scrollTop = seite.current.scrollHeight;
  }, [p, tippt]);
  const echt = useEchteSeiten(ergebnis?.pfad, !!ergebnis?.ok && !!ergebnis.office, render);
  const echtFertig = echt?.status === "fertig" && !!echt.seiten && !!render && !!ergebnis?.pfad;
  const [zeigeEcht, setZeigeEcht] = useState(true);
  const [wahl, setWahl] = useState(0);
  const titelWert = anteil(p, titelKosten);
  let nummer = 0;
  const art = formatName(format);
  const zeile = tippt ? `Jon schreibt das ${art === "PDF" ? "PDF" : "Dokument"} …` : laeuft ? "Jon speichert die Datei …" : echt?.status === "laeuft" || echt?.status === "offen" ? "Echte Seiten werden gerendert …" : echtFertig && zeigeEcht ? `Echte Seiten · ${echt?.seiten}` : "Fertig geschrieben";

  return (
    <div className="lw-dokument">
      <div className="lw-zeile">
        {(tippt || laeuft || echt?.status === "laeuft") && <Loader2 className="lw-dreh" />}
        <span>{zeile}</span>
        {echtFertig && (
          <span className="lw-schalter" role="group">
            <button type="button" className={!zeigeEcht ? "an" : ""} onClick={() => setZeigeEcht(false)}>
              Entwurf
            </button>
            <button type="button" className={zeigeEcht ? "an" : ""} onClick={() => setZeigeEcht(true)}>
              Echt
            </button>
          </span>
        )}
      </div>
      {echtFertig && zeigeEcht && render && ergebnis?.pfad ? (
        <EchteSeiten pfad={ergebnis.pfad} render={render} version={echt?.version ?? ""} seiten={echt?.seiten ?? 0} wahl={Math.min(wahl, (echt?.seiten ?? 1) - 1)} setWahl={setWahl} />
      ) : (
        <div className={`lw-papier ${kompakt ? "kompakt" : ""}`} ref={seite}>
          <div className="lw-blatt">
            {titel && (
              <h1 className="lw-d-titel">
                {schnitt(titel, titelWert)}
                <Caret wert={titelWert} />
              </h1>
            )}
            {bloecke.map((b, i) => {
              const start = (grenzen[i - 1] ?? 0) + titelKosten;
              if (p < start) return null;
              nummer = b.typ === "nummer" ? nummer + 1 : 0;
              return <Block key={i} block={b} wert={anteil(p - start, blockKosten(b))} nummer={nummer} />;
            })}
          </div>
        </div>
      )}
    </div>
  );
}

const SPALTEN = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

export function TabellenAnsicht({ zeilen, laeuft, animieren }: { zeilen: string[][]; laeuft: boolean; animieren: boolean }) {
  const breite = Math.max(1, ...zeilen.map((z) => z.length));
  const zellen = zeilen.length * breite;
  const p = useAblauf(zellen, animieren, laeuft, Math.min(12000, Math.max(1800, zellen * 70)));
  const zeile = p < zellen ? `Jon füllt Zeile ${Math.floor(p / breite) + 1} von ${zeilen.length}` : laeuft ? "Jon speichert die Tabelle …" : `Fertig · ${zeilen.length} Zeilen, ${breite} Spalten`;
  return (
    <div className="lw-tabelle">
      <div className="lw-zeile">
        {(p < zellen || laeuft) && <Loader2 className="lw-dreh" />}
        <span>{zeile}</span>
      </div>
      <div className="lw-blattgitter">
        <table>
          <thead>
            <tr>
              <th />
              {Array.from({ length: breite }, (_, j) => (
                <th key={j}>{SPALTEN[j] ?? j + 1}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {zeilen.map((zeileWerte, i) => (
              <tr key={i} className={i === 0 ? "kopf" : ""}>
                <th>{i + 1}</th>
                {Array.from({ length: breite }, (_, j) => {
                  const nr = i * breite + j;
                  const aktiv = Math.floor(p) === nr && p < zellen;
                  return (
                    <td key={j} className={aktiv ? "aktiv" : ""}>
                      {nr < p ? zeileWerte[j] ?? "" : ""}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function docxKosten(a: DocxAktion): number {
  return 10 + ((a.text?.length ?? 0) + (a.alt?.length ?? 0) + (a.neu?.length ?? 0)) / 4 + (a.tabelle?.length ?? 0) * 3;
}

function docxBeschreibung(a: DocxAktion): string {
  const ort = a.nr !== undefined ? `Absatz ${a.nr}` : a.nach !== undefined ? `nach Absatz ${a.nach}` : "";
  const inhalt = a.art === "ersetzen" ? `„${a.alt ?? ""}“ → „${a.neu ?? ""}“` : a.text ?? a.stil ?? "";
  return [ort, inhalt.replace(/\s+/g, " ")].filter(Boolean).join(" – ").slice(0, 160);
}

function AenderungsSeite({ aktion, wert }: { aktion: DocxAktion; wert: number }) {
  const art = aktion.art;
  let effekt: ReactNode;
  if (art === "ersetzen") {
    effekt = (
      <p className="lw-d-aenderung">
        <s style={{ backgroundSize: `${Math.min(1, wert * 2) * 100}% 2px` }}>{aktion.alt}</s> <ins>{schnitt(aktion.neu ?? "", Math.max(0, wert * 2 - 1))}</ins>
        <Caret wert={Math.max(0, wert * 2 - 1)} />
      </p>
    );
  } else if (art === "loeschen") {
    effekt = <p className="lw-d-aenderung weg" style={{ opacity: 1 - wert * 0.7 }}>Absatz {aktion.nr ?? ""} wird entfernt</p>;
  } else if (art === "bild") {
    effekt = (
      <div className="lw-d-bild" style={{ opacity: Math.min(1, wert * 1.4) }}>
        <ImageIcon />
        <span>{aktion.text || "Bild"}</span>
      </div>
    );
  } else if (art === "tabelle" && aktion.tabelle?.length) {
    const sichtbar = Math.ceil(aktion.tabelle.length * wert);
    effekt = (
      <table className="lw-d-tabelle">
        <tbody>
          {aktion.tabelle.slice(0, sichtbar).map((z, i) => (
            <tr key={i}>
              {z.map((zelle, j) => (
                <td key={j}>{zelle}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  } else if (art === "format") {
    effekt = <p className={`lw-d-aenderung format ${wert > 0.5 ? "an" : ""}`}>Absatz {aktion.nr ?? ""} {aktion.stil ? `→ ${aktion.stil}` : "wird formatiert"}</p>;
  } else {
    const istTitel = aktion.stil && /^(titel|h1|h2|h3)$/.test(aktion.stil);
    effekt = (
      <p className={`lw-d-aenderung neu ${istTitel ? "titel" : ""}`}>
        {schnitt(aktion.text ?? "", wert)}
        <Caret wert={wert} />
      </p>
    );
  }
  return (
    <div className="lw-papier klein">
      <div className="lw-blatt">
        <span className="lw-ae-platz dunkel w60" />
        <span className="lw-ae-platz dunkel w90" />
        <span className="lw-ae-platz dunkel w80" />
        {effekt}
        <span className="lw-ae-platz dunkel w70" />
        <span className="lw-ae-platz dunkel w50" />
      </div>
    </div>
  );
}

export function DokumentAenderungAnsicht({ pfad, aktionen, ergebnis, laeuft, animieren, render }: { pfad: string; aktionen: DocxAktion[]; ergebnis?: WerkstattErgebnis; laeuft: boolean; animieren: boolean; render?: RenderQuelle; kompakt?: boolean }) {
  const grenzen = useMemo(() => {
    let summe = 0;
    return aktionen.map((a) => (summe += docxKosten(a)));
  }, [aktionen]);
  const gesamt = grenzen.at(-1) ?? 0;
  const p = useAblauf(gesamt, animieren, laeuft, Math.min(22000, Math.max(2500, aktionen.length * 1400)));
  const aktuell = p >= gesamt ? -1 : grenzen.findIndex((g) => g > p);
  const zeigen = aktuell >= 0 ? aktuell : Math.max(0, aktionen.length - 1);
  const start = grenzen[zeigen - 1] ?? 0;
  const wert = aktuell >= 0 ? anteil(p - start, (grenzen[zeigen] ?? 1) - start) : 1;
  const quelle = ergebnis?.pfad || pfad;
  const echt = useEchteSeiten(quelle, !!ergebnis?.ok && !laeuft, render);
  const echtFertig = echt?.status === "fertig" && !!echt.seiten && !!render;
  const [wahl, setWahl] = useState(0);
  const zeile = aktuell >= 0 ? `Schritt ${aktuell + 1} von ${aktionen.length}: ${aktionen[aktuell].titel}` : laeuft ? "Jon speichert das Dokument …" : echt?.status === "laeuft" || echt?.status === "offen" ? "Echte Seiten werden gerendert …" : echtFertig ? `Bearbeitetes Dokument · ${echt?.seiten} Seiten` : "Alle Änderungen übernommen";

  return (
    <div className="lw-aenderung">
      <div className="lw-zeile">
        {(aktuell >= 0 || laeuft || echt?.status === "laeuft") && <Loader2 className="lw-dreh" />}
        <span>{zeile}</span>
      </div>
      {echtFertig && render ? (
        <EchteSeiten pfad={quelle} render={render} version={echt?.version ?? ""} seiten={echt?.seiten ?? 0} wahl={Math.min(wahl, (echt?.seiten ?? 1) - 1)} setWahl={setWahl} />
      ) : (
        <div className="lw-zwei">
          <div className="lw-buehne papier">{aktionen.length ? <AenderungsSeite aktion={aktionen[zeigen]} wert={wert} /> : null}</div>
          <SchrittListe aktionen={aktionen} aktuell={aktuell} fertig={!laeuft && aktuell < 0} beschreibung={docxBeschreibung} />
        </div>
      )}
    </div>
  );
}
