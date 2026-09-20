import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  zeitAnpassen,
  zeitNeustart,
  zeitPause,
  zeitRuhe,
  zeitStand,
  zeitStarten,
  zeitStoppen,
  zeitWeiter,
} from "../lib/api";
import type { JonUhr, JonUhrArt, JonWecker } from "../lib/api";

interface Props {
  uhren: JonUhr[];
  wecker?: JonWecker[];
}

const ARTEN: { art: JonUhrArt; titel: string; farbe: string }[] = [
  { art: "timer", titel: "Timer", farbe: "#e8b64c" },
  { art: "wecker", titel: "Wecker", farbe: "#a9a2ff" },
  { art: "stoppuhr", titel: "Stoppuhr", farbe: "#7fd4a8" },
];

const VORGABEN: Record<JonUhrArt, number> = {
  timer: 300,
  wecker: 1800,
  stoppuhr: 0,
};

function zwei(wert: number): string {
  return String(Math.floor(Math.max(0, wert))).padStart(2, "0");
}

function ziffern(sekunden: number, zehntel = false): string {
  const ganz = Math.max(0, sekunden);
  const stunden = Math.floor(ganz / 3600);
  const minuten = Math.floor((ganz % 3600) / 60);
  const rest = Math.floor(ganz % 60);
  if (stunden > 0) return `${stunden}:${zwei(minuten)}:${zwei(rest)}`;
  if (zehntel) return `${zwei(minuten)}:${zwei(rest)},${Math.floor((ganz % 1) * 10)}`;
  return `${zwei(minuten)}:${zwei(rest)}`;
}

function uhrzeit(zeitpunkt: number): string {
  const ziel = new Date(zeitpunkt * 1000);
  return `${zwei(ziel.getHours())}:${zwei(ziel.getMinutes())}`;
}

function dauerText(sekunden: number): string {
  const minuten = Math.round(Math.max(0, sekunden) / 60);
  if (minuten < 1) return "in weniger als einer Minute";
  if (minuten < 60) return `in ${minuten} Minuten`;
  const stunden = Math.floor(minuten / 60);
  const rest = minuten % 60;
  if (!rest) return `in ${stunden} Stunden`;
  return `in ${stunden} Std. ${rest} Min.`;
}

let raum: AudioContext | null = null;

function tonRaum(): AudioContext | null {
  try {
    if (!raum) raum = new AudioContext();
    if (raum.state === "suspended") void raum.resume();
    return raum;
  } catch {
    return null;
  }
}

function klingeln(): () => void {
  const halle = tonRaum();
  if (!halle) return () => {};
  let aus = false;
  let takt: number | null = null;

  const schlag = (start: number, hoehe: number) => {
    const ton = halle.createOscillator();
    const laut = halle.createGain();
    ton.type = "triangle";
    ton.frequency.value = hoehe;
    ton.connect(laut);
    laut.connect(halle.destination);
    laut.gain.setValueAtTime(0.0001, start);
    laut.gain.exponentialRampToValueAtTime(0.18, start + 0.012);
    laut.gain.exponentialRampToValueAtTime(0.0001, start + 0.26);
    ton.start(start);
    ton.stop(start + 0.28);
  };

  const runde = () => {
    if (aus) return;
    const jetzt = halle.currentTime;
    for (let i = 0; i < 4; i++) schlag(jetzt + i * 0.18, i % 2 === 0 ? 1120 : 840);
  };

  runde();
  takt = window.setInterval(runde, 2000);
  window.setTimeout(() => {
    aus = true;
    if (takt) window.clearInterval(takt);
  }, 45000);

  return () => {
    aus = true;
    if (takt) window.clearInterval(takt);
  };
}

function Ring({
  anteil,
  farbe,
  matt,
  kind,
}: {
  anteil: number;
  farbe: string;
  matt: boolean;
  kind: React.ReactNode;
}) {
  const r = 68;
  const umfang = 2 * Math.PI * r;
  const striche = Array.from({ length: 12 }, (_, i) => i);
  return (
    <div className="relative h-[168px] w-[168px]">
      <svg viewBox="0 0 168 168" className="absolute inset-0 h-full w-full">
        {striche.map((i) => {
          const bogen = ((i * 30 - 90) * Math.PI) / 180;
          const aussen = 78;
          const innen = aussen - (i % 3 === 0 ? 8 : 4);
          return (
            <line
              key={i}
              x1={84 + Math.cos(bogen) * innen}
              y1={84 + Math.sin(bogen) * innen}
              x2={84 + Math.cos(bogen) * aussen}
              y2={84 + Math.sin(bogen) * aussen}
              stroke="rgba(255,255,255,0.22)"
              strokeWidth={i % 3 === 0 ? 2 : 1}
              strokeLinecap="round"
            />
          );
        })}
      </svg>
      <svg viewBox="0 0 168 168" className="absolute inset-0 h-full w-full -rotate-90">
        <circle
          cx="84"
          cy="84"
          r={r}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="5"
        />
        <circle
          cx="84"
          cy="84"
          r={r}
          fill="none"
          stroke={farbe}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={umfang}
          strokeDashoffset={umfang * (1 - Math.min(1, Math.max(0, anteil)))}
          opacity={matt ? 0.45 : 1}
          style={{ transition: "stroke-dashoffset 0.3s linear" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {kind}
      </div>
    </div>
  );
}

function Knopf({
  kind,
  onClick,
  ton = "still",
  weit = false,
}: {
  kind: React.ReactNode;
  onClick: () => void;
  ton?: "still" | "gold" | "rot";
  weit?: boolean;
}) {
  const farben =
    ton === "gold"
      ? "border-amber-300/30 bg-amber-300/15 text-amber-100 hover:bg-amber-300/25"
      : ton === "rot"
        ? "border-red-300/25 bg-red-400/15 text-red-100 hover:bg-red-400/25"
        : "border-white/15 bg-white/[0.06] text-white/75 hover:bg-white/[0.12]";
  return (
    <button
      onClick={onClick}
      className={
        "h-8 rounded-full border text-[11.5px] font-medium transition active:scale-95 " +
        (weit ? "px-5 " : "px-3.5 ") +
        farben
      }
    >
      {kind}
    </button>
  );
}

function RundKnopf({ kind, onClick }: { kind: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex h-9 w-9 items-center justify-center rounded-full border border-white/15 bg-white/[0.06] text-[15px] text-white/75 transition hover:bg-white/[0.12] active:scale-95"
    >
      {kind}
    </button>
  );
}

export default function ZeitCard({ uhren, wecker }: Props) {
  const altlast = useMemo<JonUhr[]>(
    () =>
      (wecker ?? [])
        .map((eintrag) => {
          const ziel = new Date(eintrag.klingelt).getTime() / 1000;
          return {
            id: eintrag.name || eintrag.klingelt,
            art: "wecker" as JonUhrArt,
            titel: eintrag.titel,
            gestartet: ziel - 3600,
            gemessen: Date.now() / 1000,
            laeuft: true,
            verstrichen: 0,
            klingelt: false,
            ziel,
            klingelt_um: eintrag.klingelt,
            dauer: 3600,
          };
        })
        .filter((eintrag) => (eintrag.ziel ?? 0) > Date.now() / 1000),
    [wecker]
  );

  const [liste, setListe] = useState<JonUhr[]>([...uhren, ...altlast]);
  const [tab, setTab] = useState<JonUhrArt>(uhren[0]?.art ?? altlast[0]?.art ?? "timer");
  const [gewaehlt, setGewaehlt] = useState("");
  const [entwurf, setEntwurf] = useState<Record<JonUhrArt, number>>(VORGABEN);
  const [jetzt, setJetzt] = useState(() => Date.now() / 1000);
  const stopper = useRef<Map<string, () => void>>(new Map());

  useEffect(() => {
    setListe([...uhren, ...altlast]);
  }, [uhren, altlast]);

  const laden = useCallback(async () => {
    try {
      const stand = await zeitStand();
      setListe([...stand.uhren, ...altlast]);
    } catch {
      /* die Karte laeuft lokal weiter */
    }
  }, [altlast]);

  const laufend = liste.some((u) => u.laeuft || u.klingelt);

  useEffect(() => {
    const takt = window.setInterval(
      () => setJetzt(Date.now() / 1000),
      laufend ? 100 : 1000
    );
    return () => window.clearInterval(takt);
  }, [laufend]);

  useEffect(() => {
    const takt = window.setInterval(() => void laden(), liste.length ? 6000 : 30000);
    return () => window.clearInterval(takt);
  }, [laden, liste.length]);

  useEffect(() => {
    const laufende = stopper.current;
    return () => {
      for (const aus of laufende.values()) aus();
      laufende.clear();
    };
  }, []);

  const berechnet = useMemo(
    () =>
      liste.map((uhr) => {
        const versatz = uhr.laeuft ? Math.max(0, jetzt - (uhr.gemessen ?? jetzt)) : 0;
        const verstrichen = uhr.verstrichen + versatz;
        const dauer = uhr.dauer ?? 0;
        const rest =
          uhr.art === "wecker"
            ? Math.max(0, (uhr.ziel ?? 0) - jetzt)
            : Math.max(0, dauer - verstrichen);
        const fertig = uhr.art === "stoppuhr" ? false : rest <= 0;
        return {
          ...uhr,
          verstrichenJetzt: verstrichen,
          restJetzt: rest,
          fertigJetzt: fertig,
          anteil:
            uhr.art === "stoppuhr"
              ? (verstrichen % 60) / 60
              : dauer > 0
                ? rest / dauer
                : 0,
        };
      }),
    [liste, jetzt]
  );

  useEffect(() => {
    for (const uhr of berechnet) {
      const laeutet = uhr.fertigJetzt && uhr.klingelt === true;
      if (laeutet && !uhr.ton_pc && !stopper.current.has(uhr.id)) {
        stopper.current.set(uhr.id, klingeln());
      }
      if (!laeutet && stopper.current.has(uhr.id)) {
        stopper.current.get(uhr.id)?.();
        stopper.current.delete(uhr.id);
      }
    }
  }, [berechnet]);

  const beruhigen = (kennung: string) => {
    stopper.current.get(kennung)?.();
    stopper.current.delete(kennung);
  };

  const handeln = async (kennung: string, arbeit: () => Promise<unknown>) => {
    beruhigen(kennung);
    try {
      await arbeit();
    } catch {
      /* der letzte Stand bleibt stehen */
    }
    await laden();
  };

  const dieser = ARTEN.find((e) => e.art === tab) ?? ARTEN[0];
  const passende = berechnet.filter((u) => u.art === tab);
  const aktiv = passende.find((u) => u.id === gewaehlt) ?? passende[passende.length - 1];
  const entwurfWert = entwurf[tab];

  const schieben = (sekunden: number) => {
    if (aktiv) {
      void handeln(aktiv.id, () => zeitAnpassen(aktiv.id, sekunden));
      return;
    }
    setEntwurf((alt) => ({
      ...alt,
      [tab]: Math.max(60, Math.min(24 * 3600, alt[tab] + sekunden)),
    }));
  };

  const starten = () =>
    handeln("neu", () => zeitStarten(tab, tab === "stoppuhr" ? 0 : entwurfWert));

  const kopf = (
    <div className="flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.04] p-1">
      {ARTEN.map((eintrag) => {
        const an = eintrag.art === tab;
        const zahl = berechnet.filter((u) => u.art === eintrag.art).length;
        return (
          <button
            key={eintrag.art}
            onClick={() => {
              setTab(eintrag.art);
              setGewaehlt("");
            }}
            className={
              "flex-1 rounded-full px-2 py-1.5 text-[11.5px] font-medium transition " +
              (an
                ? "bg-white/[0.13] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.16)]"
                : "text-white/45 hover:text-white/75")
            }
          >
            {eintrag.titel}
            {zahl > 1 && <span className="ml-1 text-[9.5px] opacity-60">{zahl}</span>}
          </button>
        );
      })}
    </div>
  );

  const anzeige = aktiv ? (
    <>
      <div
        className={
          "text-[30px] font-light leading-none tabular-nums tracking-tight " +
          (aktiv.fertigJetzt ? "text-amber-200" : "text-white/95")
        }
      >
        {aktiv.art === "wecker"
          ? uhrzeit(aktiv.ziel ?? 0)
          : aktiv.art === "stoppuhr"
            ? ziffern(aktiv.verstrichenJetzt, true)
            : ziffern(aktiv.restJetzt)}
      </div>
      <div className="mt-1.5 max-w-[120px] truncate text-center text-[10px] text-white/45">
        {aktiv.fertigJetzt
          ? aktiv.art === "wecker"
            ? "Aufstehen"
            : "Zeit ist um"
          : aktiv.art === "wecker"
            ? dauerText(aktiv.restJetzt)
            : aktiv.art === "stoppuhr"
              ? aktiv.laeuft
                ? "läuft"
                : "pausiert"
              : aktiv.laeuft
                ? `bis ${uhrzeit(jetzt + aktiv.restJetzt)}`
                : "pausiert"}
      </div>
    </>
  ) : (
    <>
      <div className="text-[30px] font-light leading-none tabular-nums tracking-tight text-white/95">
        {tab === "wecker" ? uhrzeit(jetzt + entwurfWert) : ziffern(entwurfWert)}
      </div>
      <div className="mt-1.5 text-[10px] text-white/45">
        {tab === "stoppuhr"
          ? "bereit"
          : tab === "wecker"
            ? dauerText(entwurfWert)
            : "eingestellt"}
      </div>
    </>
  );

  const knoepfe = aktiv ? (
    <div className="flex flex-wrap items-center justify-center gap-1.5">
      {aktiv.fertigJetzt ? (
        <>
          <Knopf
            kind="Ton aus"
            ton="gold"
            weit
            onClick={() => handeln(aktiv.id, () => zeitRuhe(aktiv.id))}
          />
          {aktiv.art !== "wecker" && (
            <Knopf
              kind="Nochmal"
              onClick={() => handeln(aktiv.id, () => zeitNeustart(aktiv.id))}
            />
          )}
          <Knopf
            kind="Fertig"
            ton="rot"
            onClick={() => handeln(aktiv.id, () => zeitStoppen(aktiv.id))}
          />
        </>
      ) : (
        <>
          {aktiv.art !== "wecker" &&
            (aktiv.laeuft ? (
              <Knopf
                kind="Pause"
                weit
                onClick={() => handeln(aktiv.id, () => zeitPause(aktiv.id))}
              />
            ) : (
              <Knopf
                kind="Weiter"
                ton="gold"
                weit
                onClick={() => handeln(aktiv.id, () => zeitWeiter(aktiv.id))}
              />
            ))}
          <Knopf
            kind="Neustart"
            onClick={() => handeln(aktiv.id, () => zeitNeustart(aktiv.id))}
          />
          <Knopf
            kind="Stopp"
            ton="rot"
            onClick={() => handeln(aktiv.id, () => zeitStoppen(aktiv.id))}
          />
        </>
      )}
    </div>
  ) : (
    <div className="flex items-center justify-center gap-1.5">
      {tab !== "stoppuhr" &&
        [1, 5, 15].map((minuten) => (
          <Knopf
            key={minuten}
            kind={`+${minuten}`}
            onClick={() => schieben(minuten * 60)}
          />
        ))}
      <Knopf kind="Starten" ton="gold" weit onClick={starten} />
    </div>
  );

  if (!berechnet.length && !uhren.length) return null;

  return (
    <div className="mt-3 w-full max-w-[340px]">
      <div className="rounded-[26px] border border-white/10 bg-white/[0.045] px-4 pb-4 pt-3 backdrop-blur-xl shadow-[0_18px_40px_-24px_rgba(0,0,0,0.8)]">
        {kopf}

        {passende.length > 1 && (
          <div className="mt-2.5 flex flex-wrap justify-center gap-1">
            {passende.map((uhr) => (
              <button
                key={uhr.id}
                onClick={() => setGewaehlt(uhr.id)}
                className={
                  "max-w-[110px] truncate rounded-full px-2.5 py-1 text-[10px] transition " +
                  (uhr.id === aktiv?.id
                    ? "bg-white/[0.14] text-white/90"
                    : "bg-white/[0.05] text-white/45 hover:text-white/70")
                }
              >
                {uhr.titel ||
                  (uhr.art === "wecker" ? uhrzeit(uhr.ziel ?? 0) : ziffern(uhr.restJetzt))}
              </button>
            ))}
          </div>
        )}

        <div className="mt-3 flex items-center justify-center gap-2">
          {tab === "stoppuhr" ? (
            <div className="w-9" />
          ) : (
            <RundKnopf kind="−" onClick={() => schieben(-60)} />
          )}
          <div className={aktiv?.fertigJetzt ? "animate-pulse" : ""}>
            <Ring
              anteil={aktiv ? aktiv.anteil : 1}
              farbe={dieser.farbe}
              matt={!!aktiv && !aktiv.laeuft && !aktiv.fertigJetzt}
              kind={anzeige}
            />
          </div>
          {tab === "stoppuhr" ? (
            <div className="w-9" />
          ) : (
            <RundKnopf kind="+" onClick={() => schieben(60)} />
          )}
        </div>

        {aktiv?.titel && (
          <div className="mt-2 truncate text-center text-[10.5px] text-white/40">
            {aktiv.titel}
          </div>
        )}

        <div className="mt-3">{knoepfe}</div>
      </div>
    </div>
  );
}
