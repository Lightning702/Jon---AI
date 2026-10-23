import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Box, Cpu, FileCode2, FilePlus2, Folder, Loader2, Monitor, Play, Plus, Power, RotateCcw, RotateCw, Save, TerminalSquare, Trash2, X } from "lucide-react";
import { DockerStand, Lauf, testumgebung, Umgebung, vorschauAdresse } from "../lib/testumgebung";
import "./testumgebung.css";

interface Zeile {
  id: number;
  befehl: string;
  lauf?: Lauf;
  fehler?: string;
}

const LAUF_BEFEHL: Record<string, (datei: string, maschine: boolean) => string> = {
  py: (d, m) => `${m ? "python3" : "python"} "${d}"`,
  js: (d) => `node "${d}"`,
  mjs: (d) => `node "${d}"`,
  php: (d, m) => `${m ? "php83" : "php"} "${d}"`,
  sh: (d) => `sh "${d}"`,
  ps1: (d) => `powershell -NoProfile -ExecutionPolicy Bypass -File "${d}"`,
};

let zaehler = 0;

function endung(pfad: string): string {
  return (pfad.split(".").pop() || "").toLowerCase();
}

function groesse(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function Testumgebung({ onClose, start }: { onClose: () => void; start?: { id: string; datei: string } }) {
  const [umgebungen, setUmgebungen] = useState<Umgebung[]>([]);
  const [docker, setDocker] = useState<DockerStand>({ installiert: false, laeuft: false });
  const [aktiv, setAktiv] = useState(start?.id || "standard");
  const [dateien, setDateien] = useState<{ pfad: string; groesse: number }[]>([]);
  const [datei, setDatei] = useState(start?.datei || "");
  const [inhalt, setInhalt] = useState("");
  const [gespeichert, setGespeichert] = useState("");
  const [zeilen, setZeilen] = useState<Zeile[]>([]);
  const [befehl, setBefehl] = useState("");
  const [busy, setBusy] = useState("");
  const [meldung, setMeldung] = useState("");
  const [ansicht, setAnsicht] = useState<"terminal" | "vorschau">("terminal");
  const [takt, setTakt] = useState(0);
  const [neuName, setNeuName] = useState("");
  const [neuDatei, setNeuDatei] = useState("");
  const terminal = useRef<HTMLDivElement>(null);

  const umgebung = umgebungen.find((u) => u.id === aktiv);
  const maschine = umgebung?.modus === "maschine";
  const geaendert = inhalt !== gespeichert;
  const html = ["html", "htm", "svg"].includes(endung(datei));

  const laden = useCallback(async () => {
    try {
      const daten = await testumgebung.liste();
      setDocker(daten.docker);
      if (!daten.umgebungen.length) {
        const neu = await testumgebung.beschreiben("standard");
        setUmgebungen([neu]);
        setAktiv(neu.id);
      } else {
        setUmgebungen(daten.umgebungen);
        setAktiv((alt) => (daten.umgebungen.some((u) => u.id === alt) ? alt : daten.umgebungen[0].id));
      }
    } catch (e) {
      setMeldung(e instanceof Error ? e.message : String(e));
    }
  }, []);

  const dateienLaden = useCallback(async (id: string) => {
    try {
      setDateien((await testumgebung.dateien(id)).dateien);
    } catch (e) {
      setDateien([]);
      setMeldung(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void laden();
  }, [laden]);

  useEffect(() => {
    if (!aktiv) return;
    void dateienLaden(aktiv);
  }, [aktiv, dateienLaden]);

  useEffect(() => {
    if (!datei || !aktiv) {
      setInhalt("");
      setGespeichert("");
      return;
    }
    let weg = false;
    testumgebung
      .lesen(aktiv, datei)
      .then((d) => {
        if (weg) return;
        setInhalt(d.inhalt);
        setGespeichert(d.inhalt);
        if (["html", "htm", "svg"].includes(endung(datei))) setAnsicht("vorschau");
      })
      .catch(() => {
        if (!weg) {
          setInhalt("");
          setGespeichert("");
        }
      });
    return () => {
      weg = true;
    };
  }, [aktiv, datei]);

  useEffect(() => {
    if (umgebung?.zustand !== "richtet_ein") return;
    const zeit = window.setTimeout(() => void laden(), 4000);
    return () => window.clearTimeout(zeit);
  }, [umgebung?.zustand, laden]);

  useEffect(() => {
    const el = terminal.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [zeilen]);

  useEffect(() => {
    const taste = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", taste);
    return () => window.removeEventListener("keydown", taste);
  }, [onClose]);

  const handeln = async (name: string, aufgabe: () => Promise<void>) => {
    setBusy(name);
    setMeldung("");
    try {
      await aufgabe();
    } catch (e) {
      setMeldung(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy("");
    }
  };

  const speichern = () =>
    handeln("speichern", async () => {
      if (!datei) return;
      await testumgebung.schreiben(aktiv, datei, inhalt);
      setGespeichert(inhalt);
      setTakt((t) => t + 1);
      await dateienLaden(aktiv);
    });

  const ausfuehren = async (text: string) => {
    const befehlText = text.trim();
    if (!befehlText) return;
    const id = ++zaehler;
    setAnsicht("terminal");
    setZeilen((alt) => [...alt.slice(-60), { id, befehl: befehlText }]);
    try {
      const lauf = await testumgebung.ausfuehren(aktiv, befehlText);
      setZeilen((alt) => alt.map((z) => (z.id === id ? { ...z, lauf } : z)));
    } catch (e) {
      setZeilen((alt) => alt.map((z) => (z.id === id ? { ...z, fehler: e instanceof Error ? e.message : String(e) } : z)));
    }
    void dateienLaden(aktiv);
  };

  const dateiStarten = async () => {
    if (geaendert) await speichern();
    if (html) {
      setAnsicht("vorschau");
      setTakt((t) => t + 1);
      return;
    }
    const bauer = LAUF_BEFEHL[endung(datei)];
    if (!bauer) {
      setMeldung("Diese Datei kann ich nicht direkt starten. Gib im Terminal einen Befehl ein.");
      return;
    }
    await ausfuehren(bauer(datei, maschine));
  };

  const neueUmgebung = (alsMaschine: boolean) =>
    handeln("neu", async () => {
      const neu = await testumgebung.neu(neuName.trim() || (alsMaschine ? "Maschine" : "Test"), alsMaschine);
      setNeuName("");
      await laden();
      setAktiv(neu.id);
      setDatei("");
      setZeilen([]);
    });

  const zuruecksetzen = () =>
    handeln("zuruecksetzen", async () => {
      if (!window.confirm(`„${umgebung?.name || aktiv}“ zurücksetzen? Alle Dateien darin werden gelöscht.`)) return;
      await testumgebung.zuruecksetzen(aktiv);
      setDatei("");
      setZeilen([]);
      await laden();
      await dateienLaden(aktiv);
    });

  const loeschen = () =>
    handeln("loeschen", async () => {
      if (!window.confirm(`„${umgebung?.name || aktiv}“ endgültig löschen?`)) return;
      await testumgebung.loeschen(aktiv);
      setDatei("");
      setZeilen([]);
      setAktiv("standard");
      await laden();
    });

  const dateiAnlegen = () =>
    handeln("datei", async () => {
      const name = neuDatei.trim();
      if (!name) return;
      await testumgebung.schreiben(aktiv, name, "");
      setNeuDatei("");
      await dateienLaden(aktiv);
      setDatei(name);
    });

  const vorschauDatei = useMemo(() => (html ? datei : dateien.find((d) => /\.(html?|svg)$/i.test(d.pfad))?.pfad || ""), [html, datei, dateien]);

  return (
    <div className="tu-huelle" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <section className="tu" role="dialog" aria-label="Jon Testumgebung">
        <header className="tu-kopf">
          <Box size={18} />
          <div className="tu-titel">
            <strong>Jon Testumgebung</strong>
            <span>{maschine ? "Linux-Maschine (Docker) · abgeschottet" : "Abgeschotteter Ordner auf diesem PC"}</span>
          </div>
          <select value={aktiv} onChange={(e) => { setAktiv(e.target.value); setDatei(""); setZeilen([]); }} aria-label="Testumgebung wählen">
            {umgebungen.map((u) => (
              <option key={u.id} value={u.id}>{u.name}{u.modus === "maschine" ? " · Maschine" : ""}</option>
            ))}
          </select>
          <button type="button" className="tu-knopf" disabled={!!busy} onClick={() => void zuruecksetzen()} title="Alles darin löschen und neu anfangen"><RotateCcw size={14} />Zurücksetzen</button>
          <button type="button" className="tu-knopf gefahr" disabled={!!busy || aktiv === "standard"} onClick={() => void loeschen()} title={aktiv === "standard" ? "Die Standard-Umgebung kannst du zurücksetzen" : "Diese Testumgebung löschen"}><Trash2 size={14} />Löschen</button>
          <button type="button" className="tu-zu" onClick={onClose} aria-label="Schließen"><X size={18} /></button>
        </header>
        <div className="tu-leiste">
          <input value={neuName} onChange={(e) => setNeuName(e.target.value)} placeholder="Name für eine neue Umgebung" maxLength={60} onKeyDown={(e) => e.key === "Enter" && void neueUmgebung(docker.laeuft)} />
          <button type="button" className="tu-knopf" disabled={!!busy} onClick={() => void neueUmgebung(false)} title="Neuer abgeschotteter Ordner"><Folder size={14} />Neu (Ordner)</button>
          <button type="button" className="tu-knopf gold" disabled={!!busy || !docker.laeuft} onClick={() => void neueUmgebung(true)} title={docker.laeuft ? "Neue Linux-Maschine mit Python, Node und PHP" : "Dafür muss Docker laufen"}><Cpu size={14} />Neu (Maschine)</button>
          <span className={"tu-docker " + (docker.laeuft ? "an" : "")}>
            <Power size={12} />
            {docker.laeuft ? "Docker läuft" : docker.installiert ? "Docker ist aus" : "Kein Docker – Ordner-Modus"}
          </span>
          {docker.installiert && !docker.laeuft && (
            <button type="button" className="tu-knopf" onClick={() => void handeln("docker", async () => { setMeldung((await testumgebung.dockerStarten()).text); window.setTimeout(() => void laden(), 30000); })}>Docker starten</button>
          )}
          {umgebung?.zustand === "richtet_ein" && <span className="tu-hinweis"><Loader2 size={12} className="tu-dreh" />Maschine installiert Python, Node und PHP …</span>}
        </div>
        {meldung && <div className="tu-meldung" role="alert"><span>{meldung}</span><button type="button" onClick={() => setMeldung("")} aria-label="Meldung schließen"><X size={13} /></button></div>}
        <div className="tu-inhalt">
          <aside className="tu-dateien">
            <div className="tu-abschnitt">Dateien {umgebung ? `· ${groesse(umgebung.groesse)}` : ""}</div>
            <div className="tu-liste">
              {dateien.map((d) => (
                <button key={d.pfad} type="button" className={d.pfad === datei ? "an" : ""} onClick={() => setDatei(d.pfad)} title={d.pfad}>
                  <FileCode2 size={13} />
                  <span>{d.pfad}</span>
                </button>
              ))}
              {!dateien.length && <p className="tu-leer">Noch leer. Lass Jon Code schreiben oder leg eine Datei an.</p>}
            </div>
            <div className="tu-neu-datei">
              <input value={neuDatei} onChange={(e) => setNeuDatei(e.target.value)} placeholder="z. B. index.html" onKeyDown={(e) => e.key === "Enter" && void dateiAnlegen()} />
              <button type="button" onClick={() => void dateiAnlegen()} aria-label="Datei anlegen" title="Datei anlegen"><FilePlus2 size={14} /></button>
            </div>
          </aside>
          <div className="tu-editor">
            <div className="tu-editor-kopf">
              <span>{datei || "Keine Datei gewählt"}{geaendert && datei ? " ●" : ""}</span>
              <button type="button" className="tu-knopf" disabled={!datei || !geaendert || !!busy} onClick={() => void speichern()} title="Speichern (Strg+S)"><Save size={13} />Speichern</button>
              <button type="button" className="tu-knopf gold" disabled={!datei || !!busy} onClick={() => void dateiStarten()} title={html ? "In der Vorschau zeigen" : "Datei ausführen"}><Play size={13} />{html ? "Ansehen" : "Starten"}</button>
            </div>
            <textarea
              value={inhalt}
              disabled={!datei}
              spellCheck={false}
              onChange={(e) => setInhalt(e.target.value)}
              onKeyDown={(e) => {
                if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
                  e.preventDefault();
                  void speichern();
                }
                if (e.key === "Tab") {
                  e.preventDefault();
                  const feld = e.currentTarget;
                  const a = feld.selectionStart;
                  const b = feld.selectionEnd;
                  setInhalt(inhalt.slice(0, a) + "  " + inhalt.slice(b));
                  requestAnimationFrame(() => feld.setSelectionRange(a + 2, a + 2));
                }
              }}
              placeholder={datei ? "" : "Wähle links eine Datei."}
            />
          </div>
          <div className="tu-rechts">
            <div className="tu-tabs">
              <button type="button" className={ansicht === "terminal" ? "an" : ""} onClick={() => setAnsicht("terminal")}><TerminalSquare size={13} />Terminal</button>
              <button type="button" className={ansicht === "vorschau" ? "an" : ""} onClick={() => setAnsicht("vorschau")}><Monitor size={13} />Vorschau</button>
              {ansicht === "vorschau" && vorschauDatei && <button type="button" className="tu-neu-laden" onClick={() => setTakt((t) => t + 1)} title="Neu laden"><RotateCw size={13} /></button>}
            </div>
            {ansicht === "terminal" ? (
              <div className="tu-terminal">
                <div className="tu-ausgabe" ref={terminal}>
                  {!zeilen.length && <p className="tu-leer">{maschine ? "Linux-Shell in der Maschine. Probier: python3 --version, node -v, apk add htop" : "PowerShell im Testordner. Probier: python --version, node -v, dir"}</p>}
                  {zeilen.map((z) => (
                    <div key={z.id} className="tu-lauf">
                      <div className="tu-befehl"><span>{maschine ? "$" : "PS>"}</span>{z.befehl}</div>
                      {!z.lauf && !z.fehler && <div className="tu-wartet"><Loader2 size={12} className="tu-dreh" />läuft …</div>}
                      {z.fehler && <pre className="tu-fehler">{z.fehler}</pre>}
                      {z.lauf && (
                        <>
                          <pre>{z.lauf.ausgabe?.trimEnd() || ""}</pre>
                          <div className={"tu-exit " + (z.lauf.exit === 0 ? "ok" : "nok")}>{z.lauf.abgebrochen ? "abgebrochen (Zeitlimit)" : `exit ${z.lauf.exit}`} · {z.lauf.dauer?.toFixed(1)} s</div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
                <form className="tu-eingabe" onSubmit={(e) => { e.preventDefault(); const text = befehl; setBefehl(""); void ausfuehren(text); }}>
                  <span>{maschine ? "$" : "PS>"}</span>
                  <input value={befehl} onChange={(e) => setBefehl(e.target.value)} placeholder="Befehl eingeben und Enter drücken" aria-label="Befehl" />
                  <button type="submit" disabled={!befehl.trim()} aria-label="Ausführen"><Plus size={14} /></button>
                </form>
              </div>
            ) : vorschauDatei ? (
              <iframe key={`${vorschauDatei}-${takt}`} className="tu-vorschau" title="Vorschau" src={vorschauAdresse(`/testumgebung-vorschau/${aktiv}/${vorschauDatei}`)} sandbox="allow-scripts allow-forms allow-modals allow-pointer-lock allow-popups" />
            ) : (
              <p className="tu-leer tu-mitte">Leg eine .html-Datei an oder lass Jon eine Website bauen, dann siehst du sie hier.</p>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
