import { Fragment, MouseEvent, ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Check,
  ChevronLeft,
  ChevronRight,
  Download,
  ExternalLink,
  FolderOpen,
  Loader2,
  MessageSquarePlus,
  MousePointerClick,
  RefreshCw,
  Send,
  Trash2,
  Undo2,
  X,
} from "lucide-react";
import {
  AnsichtBlock,
  AnsichtFolie,
  AnsichtForm,
  DateiInhalt,
  DateiKommentar,
  DateiStelle,
  JonDatei,
  RenderStand,
  ansichtBildUrl,
  ansichtDocBildUrl,
  ansichtSeiteUrl,
  dateiAnsicht,
  dateiAnsichtStand,
  dateiInhaltUrl,
  dateiOeffnen,
  kommentarAendern,
  kommentarAnlegen,
  kommentarLoeschen,
  kommentareLaden,
} from "../lib/api";
import "./datei-ansicht.css";

interface Auswahl extends DateiStelle {
  titel: string;
}

const SPALTEN = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

function spalte(index: number): string {
  let name = "";
  let rest = index + 1;
  while (rest > 0) {
    const ziffer = (rest - 1) % 26;
    name = SPALTEN[ziffer] + name;
    rest = Math.floor((rest - 1) / 26);
  }
  return name;
}

function endung(name: string): string {
  const teil = name.split(".").pop()?.toLowerCase();
  return teil && teil !== name.toLowerCase() ? teil : "";
}

function stelleText(stelle: DateiStelle): string {
  const teile: string[] = [];
  if (stelle.folie) teile.push(`Folie ${stelle.folie}`);
  if (stelle.seite) teile.push(`Seite ${stelle.seite}`);
  if (stelle.blatt) teile.push(`Blatt ${stelle.blatt}`);
  if (stelle.zelle) teile.push(`Zelle ${stelle.zelle}`);
  if (stelle.form !== undefined) teile.push(stelle.bezeichnung || `Element ${stelle.form}`);
  if (stelle.block !== undefined) teile.push(`Absatz ${stelle.block}`);
  if (stelle.zeile) teile.push(`Zeile ${stelle.zeile}`);
  if (!teile.length && stelle.x !== undefined) teile.push("Markierte Stelle");
  return teile.join(" · ") || "Ganze Datei";
}

function kurz(text: string | undefined, laenge = 90): string {
  const sauber = (text || "").replace(/\s+/g, " ").trim();
  return sauber.length > laenge ? sauber.slice(0, laenge - 1) + "…" : sauber;
}

function inline(text: string): ReactNode {
  const teile = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return teile.map((teil, i) => {
    if (teil.startsWith("**") && teil.endsWith("**")) return <strong key={i}>{teil.slice(2, -2)}</strong>;
    if (teil.startsWith("*") && teil.endsWith("*") && teil.length > 2) return <em key={i}>{teil.slice(1, -1)}</em>;
    return <Fragment key={i}>{teil}</Fragment>;
  });
}

function formText(form: AnsichtForm): string {
  if (form.absaetze?.length) return form.absaetze.map((a) => a.text).join(" ");
  if (form.zeilen?.length) return form.zeilen.map((z) => z.join(" | ")).join(" / ");
  if (form.titel) return form.titel;
  return "";
}

function formArt(form: AnsichtForm): string {
  if (form.art === "bild") return "Bild";
  if (form.art === "tabelle") return "Tabelle";
  if (form.art === "diagramm") return "Diagramm";
  return form.absaetze?.length ? "Text" : "Form";
}

function jonAuftrag(datei: JonDatei, offene: DateiKommentar[], frage = ""): string {
  const art = endung(datei.name);
  const werkzeuge = art === "pptx" ? "read_pptx und edit_pptx" : art === "docx" ? "read_docx und edit_docx" : "den passenden Werkzeugen";
  const zeilen = offene.map((k) => `- [${k.id}] ${stelleText(k.stelle)}${k.stelle.auszug ? ` („${kurz(k.stelle.auszug, 60)}“)` : ""}: ${k.text}`);
  const teile = [`Bitte arbeite an der Datei „${datei.name}“ (Pfad: ${datei.path}).`];
  if (frage) teile.push(frage);
  if (zeilen.length) teile.push("Setze diese Kommentare um:\n" + zeilen.join("\n"));
  teile.push(`Lies die Datei zuerst mit ${werkzeuge.split(" und ")[0]}, ändere die bestehende Datei direkt mit ${werkzeuge.split(" und ")[1] || werkzeuge} statt sie neu zu erstellen${zeilen.length ? " und hake die umgesetzten Kommentare danach mit datei_kommentare (aktion erledigt) ab" : ""}.`);
  return teile.join("\n\n");
}

function FolienForm({
  form,
  folie,
  pfad,
  version,
  hoehePt,
  nurRahmen,
}: {
  form: AnsichtForm;
  folie: number;
  pfad: string;
  version: string;
  hoehePt: number;
  nurRahmen: boolean;
}) {
  if (nurRahmen) return null;
  const stil: React.CSSProperties = {
    left: `${form.x}%`,
    top: `${form.y}%`,
    width: `${form.b}%`,
    height: `${form.h}%`,
    transform: form.drehung ? `rotate(${form.drehung}deg)` : undefined,
  };
  if (form.art === "bild") {
    return <img className="da-f-form" style={{ ...stil, objectFit: "cover" }} src={ansichtBildUrl(pfad, folie, form.index, version)} alt="" draggable={false} />;
  }
  if (form.art === "tabelle") {
    return (
      <div className="da-f-form da-f-tabelle" style={stil}>
        <table>
          <tbody>
            {(form.zeilen || []).map((zeile, r) => (
              <tr key={r}>{zeile.map((zelle, s) => (r === 0 ? <th key={s}>{zelle}</th> : <td key={s}>{zelle}</td>))}</tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  if (form.art === "diagramm") {
    const reihe = form.reihen?.[0];
    const maximum = Math.max(1, ...(reihe?.werte || [1]));
    return (
      <div className="da-f-form da-f-diagramm" style={stil}>
        {form.titel && <div className="da-f-diagramm-titel">{form.titel}</div>}
        <div className="da-f-balken">
          {(reihe?.werte || []).map((wert, i) => (
            <div key={i} className="da-f-balken-spalte">
              <div className="da-f-balken-wert" style={{ height: `${(wert / maximum) * 100}%` }} />
              <span>{reihe?.kategorien[i]}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return (
    <div
      className="da-f-form da-f-text"
      style={{
        ...stil,
        background: form.fuellung || undefined,
        borderRadius: form.rund ? "50%" : form.ecken ? "1.2cqh" : undefined,
      }}
    >
      {(form.absaetze || []).map((absatz, i) => (
        <p
          key={i}
          style={{
            fontSize: `${((absatz.groesse || 18) / hoehePt) * 100}cqh`,
            fontWeight: absatz.fett ? 700 : undefined,
            color: absatz.farbe || undefined,
            textAlign: (absatz.ausrichtung as "left" | "center" | "right") || "left",
            paddingLeft: absatz.ebene ? `${absatz.ebene * 2}cqh` : undefined,
          }}
        >
          {absatz.text || " "}
        </p>
      ))}
    </div>
  );
}

function Folien({
  inhalt,
  datei,
  render,
  aktiv,
  setAktiv,
  auswahl,
  waehlen,
  kommentare,
}: {
  inhalt: DateiInhalt;
  datei: JonDatei;
  render: RenderStand | undefined;
  aktiv: number;
  setAktiv: (n: number) => void;
  auswahl: Auswahl | null;
  waehlen: (a: Auswahl | null) => void;
  kommentare: DateiKommentar[];
}) {
  const folien = inhalt.folien || [];
  const folie: AnsichtFolie | undefined = folien[aktiv];
  const verhaeltnis = inhalt.verhaeltnis || 16 / 9;
  const gerendert = render?.status === "fertig";
  const version = render?.version || String(inhalt.geaendert);
  const hoehePt = inhalt.hoehe_pt || 540;
  const bildAnzahl = gerendert ? render?.seiten || folien.length : folien.length;
  const proFolie = useMemo(() => {
    const zahl: Record<number, number> = {};
    for (const k of kommentare) if (!k.erledigt && k.stelle.folie) zahl[k.stelle.folie] = (zahl[k.stelle.folie] || 0) + 1;
    return zahl;
  }, [kommentare]);

  if (!folie) return <div className="da-leer">Diese Präsentation hat keine Folien.</div>;

  const klickFlaeche = (e: MouseEvent<HTMLDivElement>) => {
    const rechteck = e.currentTarget.getBoundingClientRect();
    const x = Math.round(((e.clientX - rechteck.left) / rechteck.width) * 1000) / 10;
    const y = Math.round(((e.clientY - rechteck.top) / rechteck.height) * 1000) / 10;
    waehlen({ titel: `Folie ${folie.nummer} · Stelle ${Math.round(x)} % / ${Math.round(y)} %`, folie: folie.nummer, x, y, art: "stelle" });
  };

  return (
    <div className="da-folien">
      <div className="da-leiste">
        {Array.from({ length: Math.max(folien.length, bildAnzahl) }).map((_, i) => (
          <button key={i} className={"da-mini" + (i === aktiv ? " aktiv" : "")} onClick={() => setAktiv(i)} style={{ aspectRatio: String(verhaeltnis) }}>
            {gerendert ? <img src={ansichtSeiteUrl(datei.path, i + 1, version)} alt="" loading="lazy" draggable={false} /> : <span className="da-mini-zahl">{i + 1}</span>}
            <em>{i + 1}</em>
            {proFolie[i + 1] ? <b className="da-mini-punkt">{proFolie[i + 1]}</b> : null}
          </button>
        ))}
      </div>
      <div className="da-buehne-rahmen">
        <div className="da-buehne" style={{ aspectRatio: String(verhaeltnis), background: gerendert ? "#fff" : folie.hintergrund || "#fff", ["--da-v" as string]: verhaeltnis } as React.CSSProperties} onClick={klickFlaeche}>
          {gerendert && <img className="da-buehne-bild" src={ansichtSeiteUrl(datei.path, folie.nummer, version)} alt={`Folie ${folie.nummer}`} draggable={false} />}
          {folie.formen.map((form) => (
            <FolienForm key={form.index} form={form} folie={folie.nummer} pfad={datei.path} version={version} hoehePt={hoehePt} nurRahmen={gerendert} />
          ))}
          {folie.formen.map((form) => {
            const gewaehlt = auswahl?.folie === folie.nummer && auswahl?.form === form.index;
            const text = formText(form);
            return (
              <button
                key={"t" + form.index}
                className={"da-treffer" + (gewaehlt ? " gewaehlt" : "")}
                style={{ left: `${form.x}%`, top: `${form.y}%`, width: `${form.b}%`, height: `${form.h}%` }}
                title={`${formArt(form)}${text ? ": " + kurz(text, 60) : ""}`}
                onClick={(e) => {
                  e.stopPropagation();
                  waehlen({
                    titel: `Folie ${folie.nummer} · ${formArt(form)} ${form.index}${text ? " · „" + kurz(text, 40) + "“" : ""}`,
                    folie: folie.nummer,
                    form: form.index,
                    art: form.art,
                    auszug: kurz(text, 280),
                    bezeichnung: `${formArt(form)} ${form.index}`,
                  });
                }}
              />
            );
          })}
          {auswahl?.folie === folie.nummer && auswahl.x !== undefined && auswahl.form === undefined && (
            <span className="da-marke" style={{ left: `${auswahl.x}%`, top: `${auswahl.y}%` }} />
          )}
        </div>
        <div className="da-buehne-fuss">
          <button className="da-knopf-rund" onClick={() => setAktiv(Math.max(0, aktiv - 1))} disabled={aktiv === 0} aria-label="Vorherige Folie">
            <ChevronLeft size={16} />
          </button>
          <span>
            Folie {folie.nummer} von {inhalt.gesamt || folien.length}
          </span>
          <button className="da-knopf-rund" onClick={() => setAktiv(Math.min(folien.length - 1, aktiv + 1))} disabled={aktiv >= folien.length - 1} aria-label="Nächste Folie">
            <ChevronRight size={16} />
          </button>
          <button className="da-knopf-klein" onClick={() => waehlen({ titel: `Ganze Folie ${folie.nummer}`, folie: folie.nummer, art: "folie" })}>
            Ganze Folie kommentieren
          </button>
          {!gerendert && render?.status === "laeuft" && (
            <span className="da-hinweis">
              <Loader2 size={12} className="animate-spin" /> Originalansicht wird erzeugt …
            </span>
          )}
        </div>
        {folie.notizen && (
          <div className="da-notizen">
            <b>Sprechernotizen</b>
            <p>{folie.notizen}</p>
          </div>
        )}
      </div>
    </div>
  );
}

function Seiten({ datei, render, auswahl, waehlen }: { datei: JonDatei; render: RenderStand; auswahl: Auswahl | null; waehlen: (a: Auswahl | null) => void }) {
  const anzahl = render.seiten || 0;
  return (
    <div className="da-seiten">
      {Array.from({ length: anzahl }).map((_, i) => (
        <div
          key={i}
          className={"da-seite" + (auswahl?.seite === i + 1 ? " gewaehlt" : "")}
          onClick={(e) => {
            const r = e.currentTarget.getBoundingClientRect();
            const x = Math.round(((e.clientX - r.left) / r.width) * 1000) / 10;
            const y = Math.round(((e.clientY - r.top) / r.height) * 1000) / 10;
            waehlen({ titel: `Seite ${i + 1} · Stelle ${Math.round(x)} % / ${Math.round(y)} %`, seite: i + 1, x, y, art: "seite" });
          }}
        >
          <img src={ansichtSeiteUrl(datei.path, i + 1, render.version)} alt={`Seite ${i + 1}`} loading="lazy" draggable={false} />
          {auswahl?.seite === i + 1 && auswahl.x !== undefined && <span className="da-marke" style={{ left: `${auswahl.x}%`, top: `${auswahl.y}%` }} />}
          <em>Seite {i + 1}</em>
        </div>
      ))}
    </div>
  );
}

function Bloecke({ bloecke, datei, version, auswahl, waehlen }: { bloecke: AnsichtBlock[]; datei: JonDatei; version: string; auswahl: Auswahl | null; waehlen: (a: Auswahl | null) => void }) {
  return (
    <div className="da-papier">
      {bloecke.map((block) => {
        const gewaehlt = auswahl?.block === block.nr;
        const klick = () =>
          waehlen({
            titel: `Absatz ${block.nr}${block.text ? " · „" + kurz(block.text, 40) + "“" : block.art === "tabelle" ? " · Tabelle" : ""}`,
            block: block.nr,
            art: block.art,
            auszug: kurz(block.text || (block.zeilen || []).map((z) => z.join(" | ")).join(" / "), 280),
          });
        const klasse = "da-block da-block-" + block.art + (gewaehlt ? " gewaehlt" : "");
        const stil = block.ausrichtung && block.ausrichtung !== "left" ? { textAlign: block.ausrichtung as "center" | "right" } : undefined;
        if (block.art === "tabelle") {
          return (
            <div key={block.nr} className={klasse} onClick={klick}>
              <table>
                <tbody>
                  {(block.zeilen || []).map((zeile, r) => (
                    <tr key={r}>{zeile.map((zelle, s) => (r === 0 ? <th key={s}>{zelle}</th> : <td key={s}>{zelle}</td>))}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        const bilder = (block.bilder || []).map((rid) => <img key={rid} src={ansichtDocBildUrl(datei.path, rid, version)} alt="" draggable={false} />);
        if (!block.text && !bilder.length) return <div key={block.nr} className="da-block-leer" />;
        const Tag = block.art === "titel" ? "h1" : /^h[1-6]$/.test(block.art) ? (("h" + Math.min(6, Number(block.art[1]) + 1)) as "h2") : "p";
        return (
          <div key={block.nr} className={klasse} onClick={klick} style={stil}>
            {bilder.length > 0 && <div className="da-block-bilder">{bilder}</div>}
            {block.text && (
              <Tag>
                {block.art === "liste" && <span className="da-punkt">•</span>}
                {inline(block.text)}
              </Tag>
            )}
          </div>
        );
      })}
    </div>
  );
}

function Markdown({ text, auswahl, waehlen }: { text: string; auswahl: Auswahl | null; waehlen: (a: Auswahl | null) => void }) {
  const abschnitte = useMemo(() => text.split(/\n{2,}/).filter((t) => t.trim()), [text]);
  return (
    <div className="da-papier da-markdown">
      {abschnitte.map((abschnitt, i) => (
        <div
          key={i}
          className={"da-block" + (auswahl?.block === i ? " gewaehlt" : "")}
          onClick={() => waehlen({ titel: `Abschnitt ${i} · „${kurz(abschnitt, 40)}“`, block: i, art: "abschnitt", auszug: kurz(abschnitt, 280) })}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{abschnitt}</ReactMarkdown>
        </div>
      ))}
    </div>
  );
}

function Tabellen({ inhalt, auswahl, waehlen }: { inhalt: DateiInhalt; auswahl: Auswahl | null; waehlen: (a: Auswahl | null) => void }) {
  const [blatt, setBlatt] = useState(0);
  const blaetter = inhalt.blaetter || [];
  const aktuell = blaetter[blatt];
  if (!aktuell) return <div className="da-leer">Keine Tabellenblätter gefunden.</div>;
  return (
    <div className="da-tabellen">
      {blaetter.length > 1 && (
        <div className="da-reiter">
          {blaetter.map((b, i) => (
            <button key={i} className={i === blatt ? "aktiv" : ""} onClick={() => setBlatt(i)}>
              {b.name}
            </button>
          ))}
        </div>
      )}
      <div className="da-tabelle-rahmen">
        <table className="da-tabelle">
          <thead>
            <tr>
              <th />
              {(aktuell.zeilen[0] || []).map((_, s) => (
                <th key={s}>{spalte(s)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {aktuell.zeilen.map((zeile, r) => (
              <tr key={r}>
                <th>{r + 1}</th>
                {zeile.map((wert, s) => {
                  const zelle = `${spalte(s)}${r + 1}`;
                  return (
                    <td
                      key={s}
                      className={auswahl?.zelle === zelle && auswahl.blatt === aktuell.name ? "gewaehlt" : ""}
                      onClick={() => waehlen({ titel: `${aktuell.name} · ${zelle}${wert ? " · „" + kurz(wert, 30) + "“" : ""}`, blatt: aktuell.name, zelle, art: "zelle", auszug: kurz(wert, 200) })}
                    >
                      {wert}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {aktuell.gekuerzt && <div className="da-hinweis">Nur die ersten Zeilen werden angezeigt.</div>}
    </div>
  );
}

function Code({ text, auswahl, waehlen }: { text: string; auswahl: Auswahl | null; waehlen: (a: Auswahl | null) => void }) {
  const zeilen = useMemo(() => text.split("\n"), [text]);
  return (
    <div className="da-code">
      {zeilen.map((zeile, i) => (
        <div key={i} className={"da-code-zeile" + (auswahl?.zeile === i + 1 ? " gewaehlt" : "")} onClick={() => waehlen({ titel: `Zeile ${i + 1}`, zeile: i + 1, art: "zeile", auszug: kurz(zeile, 200) })}>
          <span className="da-code-nr">{i + 1}</span>
          <code>{zeile || " "}</code>
        </div>
      ))}
    </div>
  );
}

function Bild({ url, name, auswahl, waehlen }: { url: string; name: string; auswahl: Auswahl | null; waehlen: (a: Auswahl | null) => void }) {
  return (
    <div className="da-bild-rahmen">
      <div
        className="da-bild"
        onClick={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          const x = Math.round(((e.clientX - r.left) / r.width) * 1000) / 10;
          const y = Math.round(((e.clientY - r.top) / r.height) * 1000) / 10;
          waehlen({ titel: `Stelle ${Math.round(x)} % / ${Math.round(y)} %`, x, y, art: "stelle" });
        }}
      >
        <img src={url} alt={name} draggable={false} />
        {auswahl?.x !== undefined && <span className="da-marke" style={{ left: `${auswahl.x}%`, top: `${auswahl.y}%` }} />}
      </div>
    </div>
  );
}

export default function DateiAnsicht({ datei, onClose }: { datei: JonDatei; onClose: () => void }) {
  const [inhalt, setInhalt] = useState<DateiInhalt | null>(null);
  const [fehler, setFehler] = useState("");
  const [laedt, setLaedt] = useState(true);
  const [render, setRender] = useState<RenderStand | undefined>(undefined);
  const [kommentare, setKommentare] = useState<DateiKommentar[]>([]);
  const [auswahl, setAuswahl] = useState<Auswahl | null>(null);
  const [entwurf, setEntwurf] = useState("");
  const [aktiv, setAktiv] = useState(0);
  const [original, setOriginal] = useState(false);
  const [meldung, setMeldung] = useState("");
  const [nurOffen, setNurOffen] = useState(true);
  const [aktualisiert, setAktualisiert] = useState(false);
  const geaendert = useRef(0);
  const feld = useRef<HTMLTextAreaElement>(null);
  const art = endung(datei.name);
  const url = dateiInhaltUrl(datei.path);

  const laden = useCallback(
    async (still = false) => {
      if (!still) setLaedt(true);
      try {
        const [daten, liste] = await Promise.all([dateiAnsicht(datei.path), kommentareLaden(datei.path).catch(() => [] as DateiKommentar[])]);
        geaendert.current = daten.geaendert;
        setInhalt(daten);
        setRender(daten.render);
        setKommentare(liste);
        setFehler("");
        if (still) {
          setAktualisiert(true);
          setTimeout(() => setAktualisiert(false), 2600);
        }
      } catch (e) {
        if (!still) setFehler(e instanceof Error ? e.message : String(e));
      } finally {
        setLaedt(false);
      }
    },
    [datei.path]
  );

  useEffect(() => {
    void laden();
  }, [laden]);

  useEffect(() => {
    let aus = false;
    const takt = setInterval(async () => {
      if (document.hidden || aus) return;
      try {
        const stand = await dateiAnsichtStand(datei.path);
        if (aus) return;
        if (geaendert.current && stand.geaendert !== geaendert.current) {
          void laden(true);
          return;
        }
        setRender((alt) => (alt?.status === stand.render.status && alt?.version === stand.render.version ? alt : stand.render.status === "offen" ? alt : stand.render));
      } catch {
        return;
      }
    }, 2500);
    return () => {
      aus = true;
      clearInterval(takt);
    };
  }, [datei.path, laden]);

  useEffect(() => {
    const taste = (e: KeyboardEvent) => {
      const ziel = e.target as HTMLElement | null;
      const tippt = ziel && (ziel.tagName === "TEXTAREA" || ziel.tagName === "INPUT");
      if (e.key === "Escape") {
        if (auswahl) setAuswahl(null);
        else onClose();
        return;
      }
      if (tippt || !inhalt?.folien) return;
      if (e.key === "ArrowRight" || e.key === "PageDown") setAktiv((a) => Math.min((inhalt.folien?.length || 1) - 1, a + 1));
      if (e.key === "ArrowLeft" || e.key === "PageUp") setAktiv((a) => Math.max(0, a - 1));
    };
    window.addEventListener("keydown", taste);
    return () => window.removeEventListener("keydown", taste);
  }, [onClose, inhalt, auswahl]);

  const waehlen = (neu: Auswahl | null) => {
    setAuswahl(neu);
    if (neu) requestAnimationFrame(() => feld.current?.focus());
  };

  const offene = kommentare.filter((k) => !k.erledigt);
  const sichtbar = nurOffen ? offene : kommentare;

  const kommentieren = async () => {
    const text = entwurf.trim();
    if (!text) return;
    const { titel, ...stelle } = auswahl || { titel: "" };
    try {
      const neu = await kommentarAnlegen(datei.path, text, stelle);
      setKommentare((alt) => [...alt, neu]);
      setEntwurf("");
      setAuswahl(null);
      setMeldung("");
    } catch (e) {
      setMeldung(e instanceof Error ? e.message : String(e));
    }
  };

  const anJon = (frage = "") => {
    const ausgewaehlt = frage && auswahl ? `${frage}\n\nGemeint ist: ${auswahl.titel}${auswahl.auszug ? ` („${kurz(auswahl.auszug, 120)}“)` : ""}.` : frage;
    window.dispatchEvent(new CustomEvent("jon-senden", { detail: jonAuftrag(datei, frage ? [] : offene, ausgewaehlt) }));
    onClose();
  };

  const springen = (k: DateiKommentar) => {
    if (k.stelle.folie && inhalt?.folien) setAktiv(Math.max(0, k.stelle.folie - 1));
    setAuswahl({ ...k.stelle, titel: stelleText(k.stelle) });
  };

  const extern = async (ordner: boolean) => {
    setMeldung("");
    const ergebnis = await dateiOeffnen(datei.path, ordner);
    if (ergebnis?.error) setMeldung(ergebnis.error);
  };

  const dokumentOriginal = !!(inhalt && art !== "pptx" && render?.status === "fertig" && (render.seiten || 0) > 0);

  const ansicht = () => {
    if (laedt && !inhalt) {
      return (
        <div className="da-leer">
          <Loader2 size={22} className="animate-spin" /> Datei wird geöffnet …
        </div>
      );
    }
    if (fehler) return <div className="da-leer da-fehler">{fehler}</div>;
    if (datei.kind === "video") return <video src={url} controls className="da-medium" />;
    if (datei.kind === "audio") return <audio src={url} controls className="da-medium" />;
    if (!inhalt) return null;
    if (inhalt.art === "fehler") return <div className="da-leer da-fehler">{inhalt.fehler}</div>;
    if (inhalt.art === "folien") return <Folien inhalt={inhalt} datei={datei} render={render} aktiv={aktiv} setAktiv={setAktiv} auswahl={auswahl} waehlen={waehlen} kommentare={kommentare} />;
    if (inhalt.art === "pdf") {
      if (render?.status === "fertig") return <Seiten datei={datei} render={render} auswahl={auswahl} waehlen={waehlen} />;
      if (render?.status === "laeuft") {
        return (
          <div className="da-leer">
            <Loader2 size={22} className="animate-spin" /> Seiten werden vorbereitet …
          </div>
        );
      }
      return <Markdown text={(inhalt.texte || []).map((t, i) => `**Seite ${i + 1}**\n\n${t}`).join("\n\n")} auswahl={auswahl} waehlen={waehlen} />;
    }
    if (original && dokumentOriginal && render) return <Seiten datei={datei} render={render} auswahl={auswahl} waehlen={waehlen} />;
    if (inhalt.bloecke?.length) return <Bloecke bloecke={inhalt.bloecke} datei={datei} version={String(inhalt.geaendert)} auswahl={auswahl} waehlen={waehlen} />;
    if (inhalt.art === "markdown") return <Markdown text={inhalt.text || ""} auswahl={auswahl} waehlen={waehlen} />;
    if (inhalt.art === "html") return <iframe className="da-html" sandbox="allow-scripts" srcDoc={inhalt.text} title={datei.name} />;
    if (inhalt.art === "tabelle") return <Tabellen inhalt={inhalt} auswahl={auswahl} waehlen={waehlen} />;
    if (inhalt.art === "code") return <Code text={inhalt.text || ""} auswahl={auswahl} waehlen={waehlen} />;
    if (inhalt.art === "bild" || datei.kind === "bild") return <Bild url={url} name={datei.name} auswahl={auswahl} waehlen={waehlen} />;
    return <div className="da-leer">Diesen Dateityp zeigt Jon nicht selbst an. Öffne ihn im passenden Programm.</div>;
  };

  return (
    <div className="da-hintergrund" onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, scale: 0.975, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
        onClick={(e) => e.stopPropagation()}
        className="da-fenster"
        role="dialog"
        aria-modal="true"
        aria-label={`Datei ${datei.name}`}
      >
        <header className="da-kopf">
          <div className="da-kopf-text">
            <div className="da-name">{datei.name}</div>
            <div className="da-ort" title={datei.folder}>
              {datei.sizeText} · {datei.folder}
            </div>
          </div>
          {aktualisiert && (
            <span className="da-live">
              <RefreshCw size={12} /> Aktualisiert
            </span>
          )}
          {dokumentOriginal && (
            <div className="da-umschalter">
              <button className={!original ? "aktiv" : ""} onClick={() => setOriginal(false)}>
                Bearbeitbar
              </button>
              <button className={original ? "aktiv" : ""} onClick={() => setOriginal(true)}>
                Original
              </button>
            </div>
          )}
          <button className="da-knopf-rund" onClick={() => void laden(true)} title="Neu laden" aria-label="Neu laden">
            <RefreshCw size={15} />
          </button>
          <button className="da-knopf-rund" onClick={onClose} title="Schließen" aria-label="Schließen">
            <X size={16} />
          </button>
        </header>

        <div className="da-rumpf">
          <section className="da-inhalt">{ansicht()}</section>
          <aside className="da-seitenleiste">
            <div className="da-auswahl">
              {auswahl ? (
                <div className="da-auswahl-titel">
                  <MousePointerClick size={14} />
                  <span>{auswahl.titel}</span>
                  <button onClick={() => setAuswahl(null)} aria-label="Auswahl aufheben">
                    <X size={13} />
                  </button>
                </div>
              ) : (
                <div className="da-auswahl-tipp">
                  <MousePointerClick size={14} />
                  <span>Klick auf ein Element, einen Absatz, eine Zelle oder eine Stelle, um genau dort zu kommentieren.</span>
                </div>
              )}
              <textarea
                ref={feld}
                value={entwurf}
                onChange={(e) => setEntwurf(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    void kommentieren();
                  }
                }}
                rows={3}
                placeholder={auswahl ? "Was soll Jon hier ändern?" : "Kommentar zur ganzen Datei …"}
              />
              <div className="da-auswahl-knoepfe">
                <button className="da-knopf-gold" onClick={() => void kommentieren()} disabled={!entwurf.trim()}>
                  <MessageSquarePlus size={14} /> Kommentieren
                </button>
                <button className="da-knopf" onClick={() => entwurf.trim() && anJon(entwurf.trim())} disabled={!entwurf.trim()} title="Sofort an Jon schicken, ohne Kommentar zu speichern">
                  <Send size={14} /> Direkt an Jon
                </button>
              </div>
            </div>

            <div className="da-kommentare-kopf">
              <b>Kommentare</b>
              <span>{offene.length} offen</span>
              <button onClick={() => setNurOffen(!nurOffen)}>{nurOffen ? "Alle zeigen" : "Nur offene"}</button>
            </div>
            <div className="da-kommentare">
              {sichtbar.length === 0 && <div className="da-kommentare-leer">Noch keine {nurOffen ? "offenen " : ""}Kommentare.</div>}
              {sichtbar.map((k) => (
                <div key={k.id} className={"da-kommentar" + (k.erledigt ? " erledigt" : "")}>
                  <button className="da-kommentar-ort" onClick={() => springen(k)}>
                    {stelleText(k.stelle)}
                  </button>
                  {k.stelle.auszug && <div className="da-kommentar-auszug">„{kurz(k.stelle.auszug, 80)}“</div>}
                  <p>{k.text}</p>
                  {k.antwort && <div className="da-kommentar-antwort">Jon: {k.antwort}</div>}
                  <div className="da-kommentar-knoepfe">
                    <button
                      onClick={async () => {
                        const neu = await kommentarAendern(k.id, { erledigt: !k.erledigt }).catch(() => null);
                        if (neu) setKommentare((alt) => alt.map((x) => (x.id === k.id ? neu : x)));
                      }}
                      title={k.erledigt ? "Wieder öffnen" : "Als erledigt markieren"}
                    >
                      {k.erledigt ? <Undo2 size={13} /> : <Check size={13} />}
                    </button>
                    <button
                      onClick={async () => {
                        await kommentarLoeschen(k.id).catch(() => null);
                        setKommentare((alt) => alt.filter((x) => x.id !== k.id));
                      }}
                      title="Löschen"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <button className="da-jon" onClick={() => anJon()} disabled={!offene.length}>
              <Send size={15} /> {offene.length ? `Jon setzt ${offene.length} Kommentar${offene.length === 1 ? "" : "e"} um` : "Keine offenen Kommentare"}
            </button>
          </aside>
        </div>

        <footer className="da-fuss">
          <button className="da-knopf" onClick={() => void extern(false)}>
            <ExternalLink size={14} /> Im Programm öffnen
          </button>
          <button className="da-knopf" onClick={() => void extern(true)}>
            <FolderOpen size={14} /> Im Ordner zeigen
          </button>
          <a className="da-knopf" href={url} download={datei.name}>
            <Download size={14} /> Herunterladen
          </a>
          {meldung && <span className="da-meldung">{meldung}</span>}
        </footer>
      </motion.div>
    </div>
  );
}
