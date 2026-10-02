import { ReactNode, useEffect, useState } from "react";
import {
  AnmeldeAntwort,
  SUPPORT_URL,
  StandFehler,
  anmeldeStand,
  anmelden,
  zugangEinrichten,
} from "../lib/anmeldung";
import TokenGate from "./TokenGate";

type Phase = "laden" | "schluessel" | "einrichten" | "anmelden" | "offen";

const imDesktop = () => typeof window !== "undefined" && Boolean(window.jon);

function JonGesicht({ klein = false }: { klein?: boolean }) {
  return (
    <svg viewBox="0 0 120 120" className={klein ? "w-12 h-12" : "w-full h-full"} aria-hidden>
      <defs>
        <linearGradient id="anmeldung-ring" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="rgb(var(--gold-light-rgb))" />
          <stop offset="55%" stopColor="rgb(var(--gold-rgb))" />
          <stop offset="100%" stopColor="rgb(var(--gold-dark-rgb))" />
        </linearGradient>
      </defs>
      <circle cx="60" cy="60" r="46" fill="#0a0a0e" stroke="url(#anmeldung-ring)" strokeWidth="6" />
      <ellipse cx="45" cy="54" rx="7" ry="9" fill="url(#anmeldung-ring)" />
      <ellipse cx="75" cy="54" rx="7" ry="9" fill="url(#anmeldung-ring)" />
      <path
        d="M44 76 Q60 88 76 76"
        fill="none"
        stroke="url(#anmeldung-ring)"
        strokeWidth="5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function Hintergrund() {
  return (
    <div className="absolute inset-0 overflow-hidden bg-black" aria-hidden>
      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice">
        <defs>
          <linearGradient id="anmeldung-band-a" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="rgb(var(--gold-rgb))" stopOpacity="0" />
            <stop offset="45%" stopColor="rgb(var(--gold-light-rgb))" stopOpacity="0.55" />
            <stop offset="100%" stopColor="rgb(var(--gold-rgb))" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="anmeldung-band-b" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0" />
            <stop offset="50%" stopColor="#ffffff" stopOpacity="0.28" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
          </linearGradient>
          <filter id="anmeldung-weich">
            <feGaussianBlur stdDeviation="14" />
          </filter>
          <filter id="anmeldung-fein">
            <feGaussianBlur stdDeviation="2" />
          </filter>
          <radialGradient id="anmeldung-glanz" cx="0.5" cy="0.45" r="0.6">
            <stop offset="0%" stopColor="rgb(var(--gold-rgb))" stopOpacity="0.12" />
            <stop offset="100%" stopColor="#000" stopOpacity="0" />
          </radialGradient>
        </defs>
        <rect width="1600" height="900" fill="url(#anmeldung-glanz)" />
        <g className="anmeldung-band anmeldung-band-1">
          <path d="M-100 520 C 300 300, 700 180, 1700 -40" stroke="url(#anmeldung-band-a)" strokeWidth="60" fill="none" filter="url(#anmeldung-weich)" />
          <path d="M-100 520 C 300 300, 700 180, 1700 -40" stroke="url(#anmeldung-band-a)" strokeWidth="2" fill="none" filter="url(#anmeldung-fein)" />
        </g>
        <g className="anmeldung-band anmeldung-band-2">
          <path d="M-200 980 C 300 700, 900 620, 1800 180" stroke="url(#anmeldung-band-b)" strokeWidth="90" fill="none" filter="url(#anmeldung-weich)" />
          <path d="M-200 980 C 300 700, 900 620, 1800 180" stroke="url(#anmeldung-band-b)" strokeWidth="1.5" fill="none" />
        </g>
        <g className="anmeldung-band anmeldung-band-3">
          <path d="M600 -80 C 800 200, 1100 420, 1750 560" stroke="url(#anmeldung-band-a)" strokeWidth="40" fill="none" filter="url(#anmeldung-weich)" opacity="0.7" />
          <path d="M-150 160 C 200 120, 420 60, 700 -60" stroke="url(#anmeldung-band-b)" strokeWidth="28" fill="none" filter="url(#anmeldung-weich)" opacity="0.6" />
        </g>
      </svg>
    </div>
  );
}

function Auge({ offen }: { offen: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
      <circle cx="12" cy="12" r="3" />
      {offen && <path d="M4 4l16 16" />}
    </svg>
  );
}

function Feld({
  wert,
  setzen,
  platzhalter,
  geheim = false,
  autoFocus = false,
  autoComplete,
  onEnter,
}: {
  wert: string;
  setzen: (wert: string) => void;
  platzhalter: string;
  geheim?: boolean;
  autoFocus?: boolean;
  autoComplete?: string;
  onEnter: () => void;
}) {
  const [sichtbar, setSichtbar] = useState(false);
  return (
    <div className="relative">
      <input
        value={wert}
        onChange={(e) => setzen(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") onEnter();
        }}
        type={geheim && !sichtbar ? "password" : "text"}
        placeholder={platzhalter}
        autoFocus={autoFocus}
        autoComplete={autoComplete}
        spellCheck={false}
        className="w-full h-10 rounded-xl border border-white/10 bg-white/[0.04] px-3 pr-10 text-[13px] text-white/90 placeholder-white/35 outline-none transition focus:border-gold/60 focus:bg-white/[0.07] focus:shadow-[0_0_0_3px_rgb(var(--gold-rgb)/0.12)]"
      />
      {geheim && (
        <button
          type="button"
          tabIndex={-1}
          onClick={() => setSichtbar((v) => !v)}
          title={sichtbar ? "Passwort verbergen" : "Passwort anzeigen"}
          className="absolute right-2 top-1/2 -translate-y-1/2 w-7 h-7 flex items-center justify-center rounded-lg text-white/40 hover:text-gold transition"
        >
          <Auge offen={sichtbar} />
        </button>
      )}
    </div>
  );
}

function Fensterleiste() {
  const api = window.jon;
  if (!api) return null;
  return (
    <div
      className="absolute top-0 inset-x-0 h-10 flex items-center justify-end px-2 z-10"
      style={{ WebkitAppRegion: "drag" } as React.CSSProperties}
    >
      <div className="flex gap-1" style={{ WebkitAppRegion: "no-drag" } as React.CSSProperties}>
        <button
          onClick={() => api.minimize()}
          title="Minimieren"
          className="w-8 h-8 rounded-lg text-white/50 hover:text-white hover:bg-white/10 transition"
        >
          &#8211;
        </button>
        <button
          onClick={() => api.close()}
          title="Jon beenden"
          className="w-8 h-8 rounded-lg text-white/50 hover:text-white hover:bg-red-500/70 transition"
        >
          &#10005;
        </button>
      </div>
    </div>
  );
}

export default function Anmeldung({ children }: { children: ReactNode }) {
  const [phase, setPhase] = useState<Phase>("laden");
  const [name, setName] = useState("");
  const [passwort, setPasswort] = useState("");
  const [wiederholung, setWiederholung] = useState("");
  const [fehler, setFehler] = useState("");
  const [hinweis, setHinweis] = useState("");
  const [arbeitet, setArbeitet] = useState(false);
  const [sperre, setSperre] = useState(0);
  const [wackeln, setWackeln] = useState(0);
  const [mindestens, setMindestens] = useState({ benutzername: 2, passwort: 6 });
  const [startet, setStartet] = useState(false);

  useEffect(() => {
    let aus = false;
    const laden = async () => {
      while (!aus) {
        try {
          const stand = await anmeldeStand();
          if (aus) return;
          setMindestens(stand.mindestens);
          setSperre(stand.gesperrt_sekunden);
          setPhase(stand.eingerichtet ? "anmelden" : "einrichten");
          return;
        } catch (err) {
          if (aus) return;
          if (err instanceof StandFehler && err.status === 401) {
            setPhase("schluessel");
            return;
          }
          if (err instanceof StandFehler && err.status === 404) {
            setPhase("offen");
            return;
          }
          setStartet(true);
          await new Promise((r) => setTimeout(r, 1200));
        }
      }
    };
    void laden();
    return () => {
      aus = true;
    };
  }, []);

  useEffect(() => {
    if (sperre <= 0) return;
    const takt = window.setInterval(() => setSperre((s) => Math.max(0, s - 1)), 1000);
    return () => window.clearInterval(takt);
  }, [sperre > 0]);

  useEffect(() => {
    if (phase === "offen") window.jon?.angemeldet?.();
  }, [phase]);

  if (phase === "offen") return <>{children}</>;
  if (phase === "schluessel") return <TokenGate open />;

  const einrichten = phase === "einrichten";

  const fertig = () => {
    setPasswort("");
    setWiederholung("");
    setPhase("offen");
  };

  const scheitern = (text: string) => {
    setFehler(text);
    setWackeln((w) => w + 1);
  };

  const auswerten = (antwort: AnmeldeAntwort) => {
    if (antwort.ok) {
      fertig();
      return;
    }
    if (antwort.status === 429) {
      setSperre(antwort.sekunden ?? 60);
      if (imDesktop() && antwort.versucheUebrig === 0) {
        scheitern("Zu viele Fehlversuche – Jon schließt sich jetzt.");
        window.setTimeout(() => window.jon?.close(), 2200);
        return;
      }
      scheitern(antwort.text);
      return;
    }
    if (typeof antwort.versucheUebrig === "number") {
      setHinweis(
        antwort.versucheUebrig === 1
          ? "Noch ein Versuch."
          : `Noch ${antwort.versucheUebrig} Versuche.`
      );
    }
    scheitern(antwort.text);
  };

  const absenden = async () => {
    if (arbeitet || sperre > 0) return;
    setFehler("");
    const sauber = name.trim();
    if (sauber.length < mindestens.benutzername) {
      scheitern(`Der Benutzername braucht mindestens ${mindestens.benutzername} Zeichen.`);
      return;
    }
    if (einrichten) {
      if (passwort.length < mindestens.passwort) {
        scheitern(`Das Passwort braucht mindestens ${mindestens.passwort} Zeichen.`);
        return;
      }
      if (passwort !== wiederholung) {
        scheitern("Die beiden Passwörter sind nicht gleich.");
        return;
      }
    } else if (!passwort) {
      scheitern("Bitte gib dein Passwort ein.");
      return;
    }
    setArbeitet(true);
    const antwort = einrichten
      ? await zugangEinrichten(sauber, passwort)
      : await anmelden(sauber, passwort);
    setArbeitet(false);
    auswerten(antwort);
  };

  const bereit =
    !arbeitet &&
    sperre === 0 &&
    name.trim().length > 0 &&
    passwort.length > 0 &&
    (!einrichten || wiederholung.length > 0);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 select-none">
      <Hintergrund />
      <Fensterleiste />
      {phase === "laden" ? (
        <div className="relative flex flex-col items-center gap-4">
          <div className="w-20 h-20 anmeldung-puls">
            <JonGesicht />
          </div>
          <div className="text-[12px] text-white/50">
            {startet ? "Jon startet …" : "Einen Moment …"}
          </div>
        </div>
      ) : (
        <div className="relative w-full max-w-[800px]">
          <div
            key={wackeln}
            className={`relative rounded-[22px] border border-gold/20 bg-[#0b0b10]/85 backdrop-blur-2xl shadow-[0_30px_120px_rgba(0,0,0,0.75),0_0_60px_rgb(var(--gold-rgb)/0.08)] p-6 sm:p-10 ${
              wackeln ? "anmeldung-wackeln" : ""
            }`}
          >
            <div className="pointer-events-none absolute inset-0 rounded-[22px] bg-gradient-to-br from-gold/[0.07] via-transparent to-transparent" />
            <div className="relative flex items-start justify-between gap-6">
              <div className="min-w-0">
                <div className="text-[20px] sm:text-[26px] font-light text-white/90 leading-tight">
                  {einrichten ? "Willkommen bei" : "Willkommen zurück bei"}
                </div>
                <div className="text-[40px] sm:text-[56px] font-semibold leading-none mt-1 gold-text tracking-tight">
                  Jon
                </div>
                <div className="text-[11.5px] text-white/40 mt-3 max-w-[300px] leading-relaxed">
                  {einrichten
                    ? "Lege deinen Zugang fest. Ab jetzt fragt Jon bei jedem Start nach Benutzername und Passwort."
                    : "Melde dich an, um Jon zu öffnen."}
                </div>
              </div>
              <div className="shrink-0 w-24 h-24 sm:w-[200px] sm:h-[200px] rounded-[26px] border border-gold/20 bg-gradient-to-br from-[#1b1b24] to-[#07070a] p-4 sm:p-8 shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_0_40px_rgb(var(--gold-rgb)/0.12)]">
                <JonGesicht />
              </div>
            </div>
            <div className="relative mt-8 sm:mt-14 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-5">
              <div className="w-full sm:w-[280px] space-y-2.5">
                <Feld
                  wert={name}
                  setzen={setName}
                  platzhalter="Benutzername"
                  autoFocus
                  autoComplete="username"
                  onEnter={() => void absenden()}
                />
                <Feld
                  wert={passwort}
                  setzen={setPasswort}
                  platzhalter="Passwort"
                  geheim
                  autoComplete={einrichten ? "new-password" : "current-password"}
                  onEnter={() => void absenden()}
                />
                {einrichten && (
                  <Feld
                    wert={wiederholung}
                    setzen={setWiederholung}
                    platzhalter="Passwort wiederholen"
                    geheim
                    autoComplete="new-password"
                    onEnter={() => void absenden()}
                  />
                )}
                <div className="min-h-[18px] text-[11.5px] leading-snug">
                  {sperre > 0 ? (
                    <span className="text-red-300">
                      Gesperrt – noch {sperre} {sperre === 1 ? "Sekunde" : "Sekunden"}.
                    </span>
                  ) : fehler ? (
                    <span className="text-red-300">
                      {fehler} {hinweis && <span className="text-white/45">{hinweis}</span>}
                    </span>
                  ) : null}
                </div>
                {!einrichten && (
                  <a
                    href={SUPPORT_URL}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-block text-[11.5px] text-gold/75 hover:text-gold hover:underline underline-offset-2"
                  >
                    Benutzername oder Passwort vergessen?
                  </a>
                )}
              </div>
              <div className="flex items-center justify-end">
                <button
                  onClick={() => void absenden()}
                  disabled={!bereit}
                  title={einrichten ? "Zugang anlegen" : "Anmelden"}
                  className="w-14 h-14 rounded-full flex items-center justify-center bg-gradient-to-br from-gold-light via-gold to-gold-dark text-black shadow-[0_8px_30px_rgb(var(--gold-rgb)/0.35)] transition hover:brightness-110 active:scale-95 disabled:opacity-35 disabled:shadow-none"
                >
                  {arbeitet ? (
                    <span className="w-5 h-5 rounded-full border-2 border-black/30 border-t-black animate-spin" />
                  ) : (
                    <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                      <path d="M9 5l7 7-7 7" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
          </div>
          <div className="mt-4 text-center text-[11px] text-white/30">
            Jon von FelWorks · Zugangsdaten liegen nur verschlüsselt auf diesem Gerät
          </div>
        </div>
      )}
    </div>
  );
}
