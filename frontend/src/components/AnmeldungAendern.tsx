import { useState } from "react";
import { SUPPORT_URL, angemeldeterName, zugangAendern } from "../lib/anmeldung";

const feld =
  "w-full h-9 rounded-xl border border-white/10 bg-white/[0.04] px-3 text-[12.5px] text-white/90 placeholder-white/35 outline-none transition focus:border-gold/60";

export default function AnmeldungAendern({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState(angemeldeterName());
  const [passwort, setPasswort] = useState("");
  const [neuerName, setNeuerName] = useState("");
  const [neuesPasswort, setNeuesPasswort] = useState("");
  const [wiederholung, setWiederholung] = useState("");
  const [fehler, setFehler] = useState("");
  const [fertig, setFertig] = useState(false);
  const [arbeitet, setArbeitet] = useState(false);

  const speichern = async () => {
    setFehler("");
    if (!name.trim() || !passwort) {
      setFehler("Gib zuerst deinen jetzigen Benutzernamen und dein Passwort ein.");
      return;
    }
    if (!neuerName.trim() && !neuesPasswort) {
      setFehler("Trag einen neuen Benutzernamen oder ein neues Passwort ein.");
      return;
    }
    if (neuesPasswort && neuesPasswort !== wiederholung) {
      setFehler("Die beiden neuen Passwörter sind nicht gleich.");
      return;
    }
    setArbeitet(true);
    const antwort = await zugangAendern({
      benutzername: name.trim(),
      passwort,
      neuer_benutzername: neuerName.trim(),
      neues_passwort: neuesPasswort,
    });
    setArbeitet(false);
    if (antwort.ok) {
      setFertig(true);
      setPasswort("");
      setNeuesPasswort("");
      setWiederholung("");
      return;
    }
    setFehler(antwort.text);
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-2xl border border-gold/20 bg-[#0b0b10]/95 shadow-[0_30px_100px_rgba(0,0,0,0.7)]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <div>
            <div className="text-[14px] font-semibold gold-text">Anmeldung ändern</div>
            <div className="text-[11px] text-white/40">
              Benutzername und Passwort für Jon in der App und im Web.
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition"
          >
            ✕
          </button>
        </div>
        {fertig ? (
          <div className="px-5 py-6 space-y-4">
            <div className="text-[13px] text-emerald-300/90">
              ✓ Gespeichert. Ab dem nächsten Start gelten die neuen Zugangsdaten.
            </div>
            <button
              onClick={onClose}
              className="w-full h-9 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black text-[13px] font-semibold hover:brightness-110 transition"
            >
              Fertig
            </button>
          </div>
        ) : (
          <div className="px-5 py-4 space-y-4">
            <div className="space-y-2">
              <div className="text-[11px] uppercase tracking-wide text-gold/70">Jetzt</div>
              <input
                className={feld}
                placeholder="Jetziger Benutzername"
                value={name}
                autoComplete="username"
                onChange={(e) => setName(e.target.value)}
              />
              <input
                className={feld}
                type="password"
                placeholder="Jetziges Passwort"
                value={passwort}
                autoComplete="current-password"
                onChange={(e) => setPasswort(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <div className="text-[11px] uppercase tracking-wide text-gold/70">Neu</div>
              <input
                className={feld}
                placeholder="Neuer Benutzername (leer = bleibt)"
                value={neuerName}
                autoComplete="off"
                onChange={(e) => setNeuerName(e.target.value)}
              />
              <input
                className={feld}
                type="password"
                placeholder="Neues Passwort (leer = bleibt)"
                value={neuesPasswort}
                autoComplete="new-password"
                onChange={(e) => setNeuesPasswort(e.target.value)}
              />
              {neuesPasswort && (
                <input
                  className={feld}
                  type="password"
                  placeholder="Neues Passwort wiederholen"
                  value={wiederholung}
                  autoComplete="new-password"
                  onChange={(e) => setWiederholung(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void speichern();
                  }}
                />
              )}
            </div>
            {fehler && <div className="text-[11.5px] text-red-300">{fehler}</div>}
            <div className="flex items-center justify-between gap-3 pt-1">
              <a
                href={SUPPORT_URL}
                target="_blank"
                rel="noreferrer"
                className="text-[11px] text-gold/70 hover:text-gold hover:underline underline-offset-2"
              >
                Zugangsdaten vergessen?
              </a>
              <button
                onClick={() => void speichern()}
                disabled={arbeitet}
                className="px-5 h-9 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black text-[13px] font-semibold shadow-gold hover:brightness-110 transition disabled:opacity-40"
              >
                {arbeitet ? "Prüfe …" : "Speichern"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
