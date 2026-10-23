import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Symbol from "./Symbol";
import { uploadAttachment } from "../lib/api";
import { Aufgabe, Bewertung, Kurs, KursKurz, Lektion, lehrer } from "../lib/lehrer";
import { speak, stopSpeaking } from "../lib/tts";

type Datei = { name: string; pfad?: string; fehler?: string; laedt: boolean };
type Reiter = "lernen" | "ueben" | "test" | "fragen";

function Fliesstext({ text }: { text: string }) {
  const bloecke = text.split(/\n{2,}/).map((b) => b.trim()).filter(Boolean);
  const inline = (zeile: string, schluessel: string) =>
    zeile.split(/(\*\*[^*]+\*\*)/g).map((teil, i) =>
      teil.startsWith("**") && teil.endsWith("**") ? (
        <strong key={`${schluessel}-${i}`} className="text-gold-light font-semibold">{teil.slice(2, -2).replace(/\*([^*]+)\*/g, "$1")}</strong>
      ) : (
        <span key={`${schluessel}-${i}`}>{teil.replace(/\*([^*]+)\*/g, "$1")}</span>
      )
    );
  const punkt = /^\s*([-*•]|\d+[.)])\s+/;
  return (
    <div className="space-y-3 text-[14px] leading-[1.7] text-white/85">
      {bloecke.map((block, i) => {
        const zeilen = block.split("\n");
        const gruppen: { art: "liste" | "zitat" | "text" | "titel" | "linie"; zeilen: string[] }[] = [];
        for (const zeile of zeilen) {
          const art = /^\s*-{3,}\s*$/.test(zeile) ? "linie" : /^#{1,4}\s/.test(zeile) ? "titel" : zeile.trimStart().startsWith(">") ? "zitat" : punkt.test(zeile) ? "liste" : "text";
          const letzte = gruppen[gruppen.length - 1];
          if (letzte && letzte.art === art && art !== "titel" && art !== "linie") letzte.zeilen.push(zeile);
          else gruppen.push({ art, zeilen: [zeile] });
        }
        return (
          <div key={i} className="space-y-2">
            {gruppen.map((gruppe, g) => {
              const schluessel = `${i}-${g}`;
              if (gruppe.art === "linie") return <hr key={schluessel} className="border-white/10" />;
              if (gruppe.art === "titel") return <h4 key={schluessel} className="text-[15px] font-semibold text-white">{inline(gruppe.zeilen[0].replace(/^#{1,4}\s/, ""), schluessel)}</h4>;
              if (gruppe.art === "zitat") {
                return (
                  <blockquote key={schluessel} className="border-l-2 border-gold/60 pl-3 text-white/80">
                    {gruppe.zeilen.map((z, j) => <div key={j}>{inline(z.replace(/^\s*>\s?/, ""), `${schluessel}-${j}`)}</div>)}
                  </blockquote>
                );
              }
              if (gruppe.art === "liste") {
                return (
                  <ul key={schluessel} className="space-y-1.5 pl-1">
                    {gruppe.zeilen.map((z, j) => (
                      <li key={j} className="flex gap-2">
                        <span className="mt-[9px] w-1.5 h-1.5 rounded-full bg-gold/70 shrink-0" />
                        <span>{inline(z.replace(punkt, ""), `${schluessel}-${j}`)}</span>
                      </li>
                    ))}
                  </ul>
                );
              }
              return <p key={schluessel}>{gruppe.zeilen.map((z, j) => <span key={j}>{inline(z, `${schluessel}-${j}`)}{j < gruppe.zeilen.length - 1 && <br />}</span>)}</p>;
            })}
          </div>
        );
      })}
    </div>
  );
}

function Ring({ wert, groesse = 44 }: { wert: number; groesse?: number }) {
  const prozent = Math.round(Math.max(0, Math.min(1, wert)) * 100);
  return (
    <div className="relative shrink-0 rounded-full grid place-items-center" style={{ width: groesse, height: groesse, background: `conic-gradient(rgb(var(--gold-rgb)) ${prozent * 3.6}deg, rgba(255,255,255,0.08) 0deg)` }}>
      <div className="absolute inset-[4px] rounded-full bg-[#0d0d12]" />
      <span className="relative text-[11px] font-semibold text-white/85">{prozent}%</span>
    </div>
  );
}

function Balken({ wert }: { wert: number }) {
  return (
    <div className="h-1.5 rounded-full bg-white/8 overflow-hidden">
      <div className="h-full rounded-full bg-gradient-to-r from-gold-dark to-gold-light transition-all duration-500" style={{ width: `${Math.round(Math.max(0, Math.min(1, wert)) * 100)}%` }} />
    </div>
  );
}

function tageBis(termin: string): number | null {
  if (!termin) return null;
  const ziel = new Date(`${termin}T00:00:00`).getTime();
  if (Number.isNaN(ziel)) return null;
  const heute = new Date();
  heute.setHours(0, 0, 0, 0);
  return Math.round((ziel - heute.getTime()) / 86400000);
}

function Uebung({ kursId, aufgabe, nachher, kompakt }: { kursId: string; aufgabe: Aufgabe; nachher: (b: Bewertung) => void; kompakt?: boolean }) {
  const [antwort, setAntwort] = useState("");
  const [bewertung, setBewertung] = useState<Bewertung | null>(null);
  const [busy, setBusy] = useState(false);
  const [fehler, setFehler] = useState("");
  const eingabe = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    setAntwort("");
    setBewertung(null);
    setFehler("");
    window.setTimeout(() => eingabe.current?.focus(), 60);
  }, [aufgabe.id]);

  const pruefen = async (wert?: string) => {
    if (busy || bewertung) return;
    const gegeben = wert ?? antwort;
    setBusy(true);
    setFehler("");
    try {
      const ergebnis = await lehrer.antworten(kursId, aufgabe.id, gegeben);
      setAntwort(gegeben);
      setBewertung(ergebnis);
      nachher(ergebnis);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const optionen = aufgabe.art === "wahr_falsch" ? ["wahr", "falsch"] : aufgabe.optionen;
  const schwer = ["leicht", "mittel", "knifflig"][Math.max(0, Math.min(2, aufgabe.schwierigkeit - 1))];

  return (
    <div className={`rounded-2xl border border-white/10 bg-white/[0.03] ${kompakt ? "p-4" : "p-5"}`}>
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-white/40 mb-2">
        <span>{{ auswahl: "Auswahl", frei: "Freie Antwort", lueckentext: "Lückentext", wahr_falsch: "Wahr oder falsch" }[aufgabe.art]}</span>
        <span className="w-1 h-1 rounded-full bg-white/25" />
        <span>{schwer}</span>
        {aufgabe.stufe > 0 && (
          <>
            <span className="w-1 h-1 rounded-full bg-white/25" />
            <span className="text-gold/70">Wiederholung</span>
          </>
        )}
      </div>
      <div className="text-[16px] leading-relaxed text-white/95 font-medium whitespace-pre-wrap">{aufgabe.frage}</div>
      {optionen.length > 0 ? (
        <div className={`mt-4 grid gap-2 ${aufgabe.art === "wahr_falsch" ? "grid-cols-2" : ""}`}>
          {optionen.map((option) => {
            const gewaehlt = bewertung && antwort === option;
            const richtig = bewertung && option.trim().toLowerCase() === bewertung.loesung.trim().toLowerCase();
            return (
              <button
                key={option}
                disabled={busy || !!bewertung}
                onClick={() => void pruefen(option)}
                className={`text-left px-4 py-3 rounded-xl border text-[14px] transition ${
                  richtig
                    ? "border-emerald-400/60 bg-emerald-400/10 text-emerald-100"
                    : gewaehlt
                      ? "border-red-400/60 bg-red-400/10 text-red-100"
                      : "border-white/10 bg-white/[0.04] text-white/85 hover:border-gold/40 hover:bg-gold/[0.06]"
                }`}
              >
                {aufgabe.art === "wahr_falsch" ? (option === "wahr" ? "Wahr" : "Falsch") : option}
              </button>
            );
          })}
        </div>
      ) : (
        <div className="mt-4">
          <textarea
            ref={eingabe}
            value={antwort}
            disabled={busy || !!bewertung}
            onChange={(e) => setAntwort(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void pruefen();
              }
            }}
            rows={aufgabe.art === "lueckentext" ? 1 : 3}
            placeholder={aufgabe.art === "lueckentext" ? "Was gehört in die Lücke?" : "Deine Antwort …"}
            className="w-full resize-none bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-[14px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50"
          />
          {!bewertung && (
            <button onClick={() => void pruefen()} disabled={busy} className="mt-2 px-4 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black text-[13px] font-semibold disabled:opacity-50">
              {busy ? "Jon prüft …" : "Prüfen"}
            </button>
          )}
        </div>
      )}
      {busy && optionen.length > 0 && <div className="mt-3 text-[12px] text-white/45">Jon prüft …</div>}
      {fehler && <div className="mt-3 text-[12px] text-red-300">{fehler}</div>}
      {bewertung && (
        <div className={`mt-4 rounded-xl border p-4 ${bewertung.richtig ? "border-emerald-400/30 bg-emerald-400/[0.07]" : bewertung.teilweise ? "border-amber-400/30 bg-amber-400/[0.07]" : "border-red-400/30 bg-red-400/[0.07]"}`}>
          <div className="flex items-center gap-2 text-[14px] font-semibold text-white">
            <Symbol zeichen={bewertung.richtig ? "✅" : "❌"} />
            {bewertung.richtig ? "Richtig!" : bewertung.teilweise ? "Fast!" : "Noch nicht ganz"}
          </div>
          {bewertung.feedback && bewertung.feedback !== "Richtig!" && bewertung.feedback !== "Leider falsch." && <div className="mt-1.5 text-[13px] text-white/80">{bewertung.feedback}</div>}
          {!bewertung.richtig && <div className="mt-2 text-[13px] text-white/85"><span className="text-white/50">Lösung: </span>{bewertung.loesung}</div>}
          {bewertung.erklaerung && <div className="mt-1.5 text-[12.5px] text-white/60"><Fliesstext text={bewertung.erklaerung} /></div>}
        </div>
      )}
    </div>
  );
}

export default function Lehrer({ onClose }: { onClose: () => void }) {
  const [kurse, setKurse] = useState<KursKurz[]>([]);
  const [kurs, setKurs] = useState<Kurs | null>(null);
  const [lektionNr, setLektionNr] = useState(1);
  const [reiter, setReiter] = useState<Reiter>("lernen");
  const [fach, setFach] = useState("");
  const [ziel, setZiel] = useState("");
  const [niveau, setNiveau] = useState("");
  const [termin, setTermin] = useState("");
  const [dateien, setDateien] = useState<Datei[]>([]);
  const [ziehen, setZiehen] = useState(false);
  const [fehler, setFehler] = useState("");
  const [busy, setBusy] = useState(false);
  const [aufgabe, setAufgabe] = useState<Aufgabe | null>(null);
  const [beantwortet, setBeantwortet] = useState(false);
  const [zusatz, setZusatz] = useState<{ art: string; text: string } | null>(null);
  const [zusatzBusy, setZusatzBusy] = useState("");
  const [frage, setFrage] = useState("");
  const [fragenBusy, setFragenBusy] = useState(false);
  const [test, setTest] = useState<{ aufgaben: Aufgabe[]; index: number; richtig: number; fertig: boolean } | null>(null);
  const [testBeantwortet, setTestBeantwortet] = useState(false);
  const [liest, setLiest] = useState(false);
  const dateiFeld = useRef<HTMLInputElement | null>(null);
  const chatEnde = useRef<HTMLDivElement | null>(null);

  const laden = useCallback(() => void lehrer.kurse().then(setKurse).catch(() => setKurse([])), []);
  useEffect(laden, [laden]);

  const kursLaden = useCallback(async (id: string) => {
    const daten = await lehrer.kurs(id);
    setKurs(daten);
    return daten;
  }, []);

  useEffect(() => {
    const bauend = kurse.some((k) => k.status === "baut") || kurs?.status === "baut" || kurs?.lektionsliste.some((l) => !l.bereit);
    if (!bauend) return;
    const takt = window.setInterval(() => {
      laden();
      if (kurs) void kursLaden(kurs.id);
    }, 2500);
    return () => window.clearInterval(takt);
  }, [kurse, kurs, laden, kursLaden]);

  useEffect(() => {
    if (reiter === "fragen") chatEnde.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [kurs?.chat.length, fragenBusy, reiter]);

  useEffect(() => () => stopSpeaking(), []);

  const hochladen = async (liste: FileList | File[]) => {
    const neue = Array.from(liste).slice(0, 30);
    if (!neue.length) return;
    setDateien((alt) => [...alt, ...neue.map((d) => ({ name: d.name, laedt: true }))]);
    for (const datei of neue) {
      try {
        const ergebnis = await uploadAttachment(datei, datei.type || "application/octet-stream");
        setDateien((alt) => alt.map((d) => (d.name === datei.name && d.laedt ? { ...d, laedt: false, pfad: ergebnis.pfad } : d)));
      } catch (e) {
        setDateien((alt) => alt.map((d) => (d.name === datei.name && d.laedt ? { ...d, laedt: false, fehler: e instanceof Error ? e.message : String(e) } : d)));
      }
    }
  };

  const bauen = async () => {
    if (!fach.trim() || busy) {
      setFehler("Schreib kurz, was du lernst – zum Beispiel „Deutsch: Kommasetzung“.");
      return;
    }
    if (dateien.some((d) => d.laedt)) {
      setFehler("Einen Moment, die Dateien werden noch hochgeladen.");
      return;
    }
    setBusy(true);
    setFehler("");
    try {
      const neu = await lehrer.neu({ fach: fach.trim(), ziel: ziel.trim(), niveau: niveau.trim(), termin, dateien: dateien.filter((d) => d.pfad).map((d) => d.pfad as string) });
      setFach("");
      setZiel("");
      setNiveau("");
      setTermin("");
      setDateien([]);
      laden();
      await oeffnen(neu.id);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const oeffnen = async (id: string) => {
    const daten = await kursLaden(id);
    const schwach = [...daten.lektionsliste].filter((l) => l.bereit).sort((a, b) => a.beherrschung - b.beherrschung)[0];
    setLektionNr(schwach?.nr ?? 1);
    setReiter("lernen");
    setAufgabe(null);
    setZusatz(null);
    setTest(null);
  };

  const lektion: Lektion | undefined = useMemo(() => kurs?.lektionsliste.find((l) => l.nr === lektionNr), [kurs, lektionNr]);

  const naechsteAufgabe = async (nur?: number) => {
    if (!kurs) return;
    setBusy(true);
    setFehler("");
    setBeantwortet(false);
    try {
      const daten = await lehrer.aufgabe(kurs.id, nur);
      setAufgabe(daten.aufgabe);
      if (daten.aufgabe.lektion !== lektionNr) setLektionNr(daten.aufgabe.lektion);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const zusatzHolen = async (art: string) => {
    if (!kurs || !lektion) return;
    setZusatzBusy(art);
    try {
      const daten = await lehrer.erklaeren(kurs.id, lektion.nr, art);
      setZusatz({ art, text: daten.text });
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    } finally {
      setZusatzBusy("");
    }
  };

  const fragen = async () => {
    if (!kurs || !frage.trim() || fragenBusy) return;
    const text = frage.trim();
    setFrage("");
    setFragenBusy(true);
    setKurs({ ...kurs, chat: [...kurs.chat, { rolle: "du", text, zeit: Date.now() / 1000 }] });
    try {
      await lehrer.fragen(kurs.id, text, lektionNr);
      await kursLaden(kurs.id);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    } finally {
      setFragenBusy(false);
    }
  };

  const testStarten = async () => {
    if (!kurs) return;
    setBusy(true);
    try {
      const daten = await lehrer.probetest(kurs.id, 10);
      setTest({ aufgaben: daten.aufgaben, index: 0, richtig: 0, fertig: false });
      setTestBeantwortet(false);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const vorlesen = () => {
    if (!lektion) return;
    if (liest) {
      stopSpeaking();
      setLiest(false);
      return;
    }
    setLiest(true);
    void speak(`${lektion.titel}. ${lektion.inhalt.replace(/\*\*/g, "")}`).finally(() => setLiest(false));
  };

  const kopf = (
    <div className="flex items-center justify-between px-5 h-14 border-b border-white/10 shrink-0">
      <div className="flex items-center gap-3 min-w-0">
        <span className="w-8 h-8 rounded-xl grid place-items-center bg-gold/15 text-gold"><Symbol zeichen="🎓" /></span>
        <div className="min-w-0">
          <div className="text-[14px] text-white/95 font-semibold leading-tight">Jon Lehrer</div>
          <div className="text-[11px] text-white/45 truncate">{kurs ? kurs.titel : "Dein persönlicher Lernkurs aus deinen Unterlagen"}</div>
        </div>
        {kurs && (
          <button onClick={() => { setKurs(null); setTest(null); laden(); }} className="ml-2 text-[11px] text-gold/80 hover:text-gold px-2 py-1 rounded-lg hover:bg-gold/10">Alle Kurse</button>
        )}
      </div>
      <button onClick={onClose} className="w-8 h-8 rounded-lg grid place-items-center text-white/50 hover:text-white hover:bg-white/10" aria-label="Schließen"><Symbol zeichen="✖" /></button>
    </div>
  );

  if (!kurs) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75" onClick={(e) => e.target === e.currentTarget && onClose()}>
        <div className="glass rounded-2xl border border-white/12 w-[1040px] max-w-[96vw] h-[720px] max-h-[94vh] flex flex-col overflow-hidden">
          {kopf}
          <div className="flex-1 overflow-y-auto grid md:grid-cols-[1.05fr_1fr] gap-5 p-5">
            <div className="rounded-2xl border border-gold/20 bg-gradient-to-b from-gold/[0.07] to-transparent p-5 flex flex-col">
              <div className="text-[18px] font-semibold text-white">Was lernst du gerade?</div>
              <div className="text-[12.5px] text-white/55 mt-1 leading-relaxed">Sag es mir einmal und gib mir alle Lernunterlagen – Mitschriften, Arbeitsblätter, PDFs, Fotos vom Heft, Folien. Ich mache daraus deinen Kurs mit Erklärungen, Übungen und Probetest.</div>
              <label className="mt-4 text-[11px] uppercase tracking-wider text-white/40">Fach oder Thema</label>
              <input value={fach} onChange={(e) => setFach(e.target.value)} placeholder="z. B. Deutsch: Kommasetzung · Englisch Unit 4 · Bio: Zelle" className="mt-1 bg-black/30 border border-white/10 rounded-xl px-4 py-2.5 text-[14px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50" />
              <div className="grid grid-cols-3 gap-2 mt-3">
                <div className="col-span-1">
                  <label className="text-[11px] uppercase tracking-wider text-white/40">Ziel</label>
                  <input value={ziel} onChange={(e) => setZiel(e.target.value)} placeholder="Schularbeit" className="mt-1 w-full bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-[13px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50" />
                </div>
                <div className="col-span-1">
                  <label className="text-[11px] uppercase tracking-wider text-white/40">Niveau</label>
                  <input value={niveau} onChange={(e) => setNiveau(e.target.value)} placeholder="8. Klasse" className="mt-1 w-full bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-[13px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50" />
                </div>
                <div className="col-span-1">
                  <label className="text-[11px] uppercase tracking-wider text-white/40">Termin</label>
                  <input type="date" value={termin} onChange={(e) => setTermin(e.target.value)} className="mt-1 w-full bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-[13px] text-white/90 outline-none focus:border-gold/50 [color-scheme:dark]" />
                </div>
              </div>
              <div
                onDragOver={(e) => { e.preventDefault(); setZiehen(true); }}
                onDragLeave={() => setZiehen(false)}
                onDrop={(e) => { e.preventDefault(); setZiehen(false); void hochladen(e.dataTransfer.files); }}
                onClick={() => dateiFeld.current?.click()}
                className={`mt-4 flex-1 min-h-[150px] rounded-2xl border-2 border-dashed cursor-pointer grid place-items-center text-center px-4 transition ${ziehen ? "border-gold/70 bg-gold/[0.08]" : "border-white/12 hover:border-gold/40 hover:bg-white/[0.03]"}`}
              >
                <div>
                  <div className="mx-auto w-11 h-11 rounded-2xl grid place-items-center bg-white/[0.06] text-gold"><Symbol zeichen="📤" /></div>
                  <div className="mt-2 text-[13.5px] text-white/85">Lerndateien hierher ziehen oder klicken</div>
                  <div className="text-[11.5px] text-white/40 mt-0.5">PDF, Word, PowerPoint, Bilder, Text – so viele du willst</div>
                </div>
                <input ref={dateiFeld} type="file" multiple className="hidden" onChange={(e) => e.target.files && void hochladen(e.target.files)} accept=".pdf,.doc,.docx,.ppt,.pptx,.odt,.odp,.txt,.md,.rtf,.png,.jpg,.jpeg,.webp,.heic,.csv,.xlsx" />
              </div>
              {dateien.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
                  {dateien.map((d, i) => (
                    <span key={`${d.name}-${i}`} className={`inline-flex items-center gap-1.5 text-[11.5px] px-2.5 py-1 rounded-full border ${d.fehler ? "border-red-400/40 text-red-200" : d.laedt ? "border-white/10 text-white/50" : "border-emerald-400/30 text-emerald-100"}`} title={d.fehler || d.name}>
                      <Symbol zeichen={d.fehler ? "⚠" : d.laedt ? "⏳" : "✅"} />
                      <span className="max-w-[180px] truncate">{d.name}</span>
                      <button onClick={(e) => { e.stopPropagation(); setDateien((alt) => alt.filter((_, j) => j !== i)); }} className="text-white/40 hover:text-white">×</button>
                    </span>
                  ))}
                </div>
              )}
              {fehler && <div className="mt-3 text-[12px] text-red-300">{fehler}</div>}
              <button onClick={() => void bauen()} disabled={busy} className="mt-4 py-3 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[14px] shadow-gold hover:brightness-110 disabled:opacity-50 transition">
                {busy ? "Starte …" : "Kurs bauen"}
              </button>
              <div className="text-[11px] text-white/35 mt-2 text-center">Ohne Dateien baut Jon den Kurs aus seinem Fachwissen.</div>
            </div>
            <div className="flex flex-col min-h-0">
              <div className="text-[12px] uppercase tracking-wider text-white/40 mb-2">Deine Kurse</div>
              {kurse.length === 0 ? (
                <div className="flex-1 rounded-2xl border border-white/8 bg-white/[0.02] grid place-items-center text-center p-6">
                  <div>
                    <div className="mx-auto w-12 h-12 rounded-2xl grid place-items-center bg-white/[0.05] text-white/50"><Symbol zeichen="📚" /></div>
                    <div className="mt-3 text-[13.5px] text-white/70">Noch kein Kurs</div>
                    <div className="text-[12px] text-white/40 mt-1 max-w-[280px]">Links eintragen, Dateien dazu – nach etwa einer Minute kannst du mit der ersten Lektion loslegen.</div>
                  </div>
                </div>
              ) : (
                <div className="space-y-2 overflow-y-auto pr-1">
                  {kurse.map((k) => {
                    const tage = tageBis(k.termin);
                    return (
                      <div key={k.id} className="group rounded-2xl border border-white/10 bg-white/[0.03] hover:border-gold/35 hover:bg-white/[0.05] transition p-3.5 flex items-center gap-3 cursor-pointer" onClick={() => void oeffnen(k.id)}>
                        {k.status === "baut" ? (
                          <div className="w-11 h-11 rounded-full border-2 border-gold/30 border-t-gold animate-spin shrink-0" />
                        ) : (
                          <Ring wert={k.beherrschung} />
                        )}
                        <div className="min-w-0 flex-1">
                          <div className="text-[14px] text-white/95 truncate font-medium">{k.titel}</div>
                          <div className="text-[11.5px] text-white/45 truncate">
                            {k.status === "baut" ? `${k.schritt || "Wird gebaut"} · ${k.fortschritt}%` : k.status === "fehler" ? `Fehler: ${k.fehler}` : `${k.lektionen} Lektionen${k.faellig ? ` · ${k.faellig} zum Wiederholen` : ""}${tage !== null && tage >= 0 ? ` · noch ${tage} Tage` : ""}${k.serie > 1 ? ` · ${k.serie} Tage in Folge` : ""}`}
                          </div>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (window.confirm(`Kurs „${k.titel}“ löschen?`)) void lehrer.entfernen(k.id).then(laden);
                          }}
                          className="opacity-0 group-hover:opacity-100 w-8 h-8 rounded-lg grid place-items-center text-white/40 hover:text-red-300 hover:bg-red-400/10 transition"
                          aria-label="Kurs löschen"
                        >
                          <Symbol zeichen="🗑" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const tage = tageBis(kurs.termin);
  const gesamt = kurs.lektionsliste.length ? kurs.lektionsliste.reduce((s, l) => s + l.beherrschung, 0) / kurs.lektionsliste.length : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="glass rounded-2xl border border-white/12 w-[1180px] max-w-[97vw] h-[780px] max-h-[95vh] flex flex-col overflow-hidden">
        {kopf}
        {kurs.status === "fehler" ? (
          <div className="flex-1 grid place-items-center p-8 text-center">
            <div>
              <div className="text-[15px] text-white/85">Der Kurs ließ sich nicht bauen.</div>
              <div className="text-[12.5px] text-red-300 mt-1">{kurs.fehler}</div>
              <button onClick={() => void lehrer.neuBauen(kurs.id).then(() => kursLaden(kurs.id))} className="mt-4 px-4 py-2 rounded-xl bg-gold/15 text-gold hover:bg-gold/25 text-[13px]">Neu bauen</button>
            </div>
          </div>
        ) : kurs.status === "baut" ? (
          <div className="flex-1 grid place-items-center p-8 text-center">
            <div className="w-full max-w-md">
              <div className="mx-auto w-14 h-14 rounded-full border-2 border-gold/25 border-t-gold animate-spin" />
              <div className="mt-4 text-[16px] text-white/90 font-medium">Jon bereitet deinen Kurs vor</div>
              <div className="text-[12.5px] text-white/50 mt-1">{kurs.schritt}</div>
              <div className="mt-4"><Balken wert={kurs.fortschritt / 100} /></div>
              <div className="text-[11.5px] text-white/35 mt-3">Sobald die erste Lektion fertig ist, kannst du anfangen – der Rest kommt im Hintergrund dazu.</div>
            </div>
          </div>
        ) : (
          <div className="flex-1 min-h-0 grid grid-cols-[290px_1fr]">
            <aside className="border-r border-white/10 flex flex-col min-h-0">
              <div className="p-4 border-b border-white/8 flex items-center gap-3">
                <Ring wert={gesamt} groesse={52} />
                <div className="min-w-0">
                  <div className="text-[13px] text-white/90 font-medium">Dein Stand</div>
                  <div className="text-[11.5px] text-white/50 leading-snug">{tage !== null && tage >= 0 ? `Noch ${tage} Tage · ` : ""}{kurs.faellig ? `${kurs.faellig} fällig` : "nichts fällig"}{kurs.serie > 1 ? ` · ${kurs.serie} Tage in Folge` : ""}</div>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {kurs.lektionsliste.map((l) => (
                  <button
                    key={l.nr}
                    disabled={!l.bereit}
                    onClick={() => { setLektionNr(l.nr); setZusatz(null); if (reiter === "test") setReiter("lernen"); }}
                    className={`w-full text-left rounded-xl px-3 py-2.5 transition ${l.nr === lektionNr ? "bg-gold/[0.1] border border-gold/30" : "border border-transparent hover:bg-white/[0.04]"} ${l.bereit ? "" : "opacity-50"}`}
                  >
                    <div className="flex items-center gap-2">
                      <span className={`w-6 h-6 rounded-lg grid place-items-center text-[11px] font-semibold shrink-0 ${l.beherrschung >= 0.8 ? "bg-emerald-400/15 text-emerald-200" : "bg-white/[0.06] text-white/60"}`}>{l.beherrschung >= 0.8 ? <Symbol zeichen="✅" /> : l.nr}</span>
                      <span className="text-[12.5px] text-white/85 leading-snug line-clamp-2">{l.titel.replace(/^Lektion\s+\d+:\s*/i, "")}</span>
                    </div>
                    <div className="mt-2 pl-8">{l.bereit ? <Balken wert={l.beherrschung} /> : <div className="text-[10.5px] text-white/40">wird vorbereitet …</div>}</div>
                  </button>
                ))}
              </div>
              {kurs.empfehlung && <div className="m-3 rounded-xl bg-white/[0.04] border border-white/8 p-3 text-[11.5px] text-white/60 leading-relaxed">{kurs.empfehlung}</div>}
            </aside>
            <section className="flex flex-col min-h-0">
              <div className="flex items-center gap-1 px-4 pt-3 border-b border-white/8">
                {([
                  ["lernen", "Lernen", "📖"],
                  ["ueben", "Üben", "✍"],
                  ["test", "Probetest", "🏆"],
                  ["fragen", "Frag deinen Lehrer", "💬"],
                ] as [Reiter, string, string][]).map(([key, label, icon]) => (
                  <button
                    key={key}
                    onClick={() => {
                      setReiter(key);
                      if (key === "ueben" && !aufgabe) void naechsteAufgabe();
                    }}
                    className={`flex items-center gap-1.5 px-3.5 py-2 text-[13px] rounded-t-xl border-b-2 transition ${reiter === key ? "text-gold border-gold" : "text-white/55 border-transparent hover:text-white/85"}`}
                  >
                    <Symbol zeichen={icon} />
                    {label}
                  </button>
                ))}
              </div>
              <div className="flex-1 overflow-y-auto p-6">
                {fehler && <div className="mb-3 text-[12px] text-red-300">{fehler}</div>}
                {reiter === "lernen" && lektion && (
                  <div className="max-w-[760px]">
                    <div className="text-[11px] uppercase tracking-wider text-gold/70">Lektion {lektion.nr} von {kurs.lektionsliste.length}</div>
                    <h2 className="text-[22px] font-semibold text-white mt-1 leading-tight">{lektion.titel.replace(/^Lektion\s+\d+:\s*/i, "")}</h2>
                    {lektion.ziele.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {lektion.ziele.map((z) => <span key={z} className="text-[11.5px] px-2.5 py-1 rounded-full bg-white/[0.05] border border-white/10 text-white/70">{z}</span>)}
                      </div>
                    )}
                    <div className="mt-5"><Fliesstext text={lektion.inhalt} /></div>
                    {lektion.beispiele.length > 0 && (
                      <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                        <div className="text-[12px] uppercase tracking-wider text-white/45 mb-2">Beispiele</div>
                        <ul className="space-y-2">{lektion.beispiele.map((b) => <li key={b} className="text-[13.5px] text-white/85 flex gap-2"><span className="text-gold">›</span><span>{b}</span></li>)}</ul>
                      </div>
                    )}
                    {lektion.begriffe.length > 0 && (
                      <div className="mt-4 grid sm:grid-cols-2 gap-2">
                        {lektion.begriffe.map((b) => {
                          const [wort, ...rest] = b.split(":");
                          return <div key={b} className="rounded-xl bg-white/[0.03] border border-white/8 px-3 py-2"><div className="text-[12.5px] text-gold-light font-medium">{wort}</div>{rest.length > 0 && <div className="text-[12px] text-white/60">{rest.join(":").trim()}</div>}</div>;
                        })}
                      </div>
                    )}
                    <div className="mt-6 flex flex-wrap gap-2">
                      <button onClick={() => { setReiter("ueben"); void naechsteAufgabe(lektion.nr); }} className="px-4 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black text-[13px] font-semibold">Jetzt üben</button>
                      {[["einfacher", "Einfacher erklären"], ["beispiele", "Mehr Beispiele"], ["merkzettel", "Spickzettel"]].map(([art, label]) => (
                        <button key={art} onClick={() => void zusatzHolen(art)} disabled={!!zusatzBusy} className="px-3.5 py-2 rounded-xl border border-white/12 text-white/75 hover:border-gold/40 hover:text-white text-[13px] disabled:opacity-50">{zusatzBusy === art ? "Jon schreibt …" : label}</button>
                      ))}
                      <button onClick={vorlesen} className="px-3.5 py-2 rounded-xl border border-white/12 text-white/75 hover:border-gold/40 hover:text-white text-[13px] inline-flex items-center gap-1.5"><Symbol zeichen="🔊" />{liest ? "Stopp" : "Vorlesen"}</button>
                    </div>
                    {zusatz && (
                      <div className="mt-5 rounded-2xl border border-gold/25 bg-gold/[0.05] p-5">
                        <div className="text-[12px] uppercase tracking-wider text-gold/80 mb-2">{{ einfacher: "Noch einmal einfach", beispiele: "Mehr Beispiele", merkzettel: "Spickzettel" }[zusatz.art] ?? "Zusatz"}</div>
                        <Fliesstext text={zusatz.text} />
                      </div>
                    )}
                  </div>
                )}
                {reiter === "ueben" && (
                  <div className="max-w-[720px]">
                    {aufgabe ? (
                      <>
                        <div className="text-[12px] text-white/45 mb-2">Lektion {aufgabe.lektion}: {kurs.lektionsliste.find((l) => l.nr === aufgabe.lektion)?.titel.replace(/^Lektion\s+\d+:\s*/i, "")}</div>
                        <Uebung kursId={kurs.id} aufgabe={aufgabe} nachher={() => { setBeantwortet(true); void kursLaden(kurs.id); laden(); }} />
                        <div className="mt-4 flex gap-2">
                          <button onClick={() => void naechsteAufgabe()} disabled={busy} className={`px-4 py-2 rounded-xl text-[13px] font-semibold ${beantwortet ? "bg-gradient-to-r from-gold-light to-gold-dark text-black" : "border border-white/12 text-white/70"}`}>{busy ? "Lade …" : beantwortet ? "Nächste Aufgabe" : "Überspringen"}</button>
                          <button onClick={() => void naechsteAufgabe(lektionNr)} disabled={busy} className="px-3.5 py-2 rounded-xl border border-white/12 text-white/70 text-[13px]">Nur diese Lektion</button>
                        </div>
                      </>
                    ) : (
                      <div className="text-[13px] text-white/55">{busy ? "Jon sucht die passende Aufgabe …" : "Tippe auf „Üben“, um zu starten."}</div>
                    )}
                  </div>
                )}
                {reiter === "test" && (
                  <div className="max-w-[720px]">
                    {!test ? (
                      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
                        <div className="text-[18px] text-white font-semibold">Probetest</div>
                        <div className="text-[13px] text-white/60 mt-1">10 Aufgaben quer durch den Kurs – mit Schwerpunkt auf dem, was noch nicht sitzt. Danach weißt du, wo du stehst.</div>
                        <button onClick={() => void testStarten()} disabled={busy} className="mt-4 px-5 py-2.5 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black text-[13px] font-semibold">{busy ? "Stelle zusammen …" : "Test starten"}</button>
                      </div>
                    ) : test.fertig ? (
                      <div className="rounded-2xl border border-gold/25 bg-gold/[0.05] p-6 text-center">
                        <Ring wert={test.aufgaben.length ? test.richtig / test.aufgaben.length : 0} groesse={84} />
                        <div className="text-[20px] text-white font-semibold mt-3">{test.richtig} von {test.aufgaben.length} richtig</div>
                        <div className="text-[13px] text-white/60 mt-1">{test.richtig / Math.max(1, test.aufgaben.length) >= 0.85 ? "Ausgezeichnet – du bist bereit!" : test.richtig / Math.max(1, test.aufgaben.length) >= 0.6 ? "Gut! Übe noch die markierten Lektionen." : "Da geht noch was – Jon hat die schwachen Stellen für die Wiederholung vorgemerkt."}</div>
                        <button onClick={() => setTest(null)} className="mt-4 px-4 py-2 rounded-xl border border-white/15 text-white/80 text-[13px]">Neuer Test</button>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center justify-between mb-3">
                          <div className="text-[12px] text-white/50">Aufgabe {test.index + 1} von {test.aufgaben.length}</div>
                          <div className="w-48"><Balken wert={test.index / test.aufgaben.length} /></div>
                        </div>
                        <Uebung kursId={kurs.id} aufgabe={test.aufgaben[test.index]} kompakt nachher={(b) => { setTestBeantwortet(true); setTest((t) => (t ? { ...t, richtig: t.richtig + (b.richtig ? 1 : 0) } : t)); }} />
                        <button
                          onClick={() => {
                            setTestBeantwortet(false);
                            setTest((t) => (t ? (t.index + 1 >= t.aufgaben.length ? { ...t, fertig: true } : { ...t, index: t.index + 1 }) : t));
                            void kursLaden(kurs.id);
                          }}
                          disabled={!testBeantwortet}
                          className="mt-4 px-4 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black text-[13px] font-semibold disabled:opacity-40"
                        >
                          {test.index + 1 >= test.aufgaben.length ? "Auswertung" : "Weiter"}
                        </button>
                      </>
                    )}
                  </div>
                )}
                {reiter === "fragen" && (
                  <div className="max-w-[760px] flex flex-col min-h-full">
                    <div className="flex-1 space-y-3">
                      {kurs.chat.length === 0 && <div className="text-[13px] text-white/50">Frag alles zum Stoff – Jon antwortet mit Blick auf deine Unterlagen. Zum Beispiel: „Warum steht vor ‚dass‘ ein Komma?“</div>}
                      {kurs.chat.map((n, i) => (
                        <div key={i} className={`flex ${n.rolle === "du" ? "justify-end" : "justify-start"}`}>
                          <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-[13.5px] ${n.rolle === "du" ? "bg-gold/15 text-white/90 rounded-br-md" : "bg-white/[0.05] border border-white/8 rounded-bl-md"}`}>
                            {n.rolle === "du" ? n.text : <Fliesstext text={n.text} />}
                          </div>
                        </div>
                      ))}
                      {fragenBusy && <div className="text-[12px] text-white/45">Jon denkt nach …</div>}
                      <div ref={chatEnde} className="h-20" />
                    </div>
                    <div className="sticky bottom-0 -mx-6 -mb-6 px-6 py-4 bg-[#0c0c11]/95 backdrop-blur border-t border-white/8">
                      <div className="flex gap-2">
                        <input value={frage} onChange={(e) => setFrage(e.target.value)} onKeyDown={(e) => e.key === "Enter" && void fragen()} placeholder="Deine Frage an Jon …" className="flex-1 bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-[13.5px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50" />
                        <button onClick={() => void fragen()} disabled={fragenBusy || !frage.trim()} className="px-4 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black text-[13px] font-semibold disabled:opacity-40">Fragen</button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
