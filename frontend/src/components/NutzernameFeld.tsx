import { useEffect, useState } from "react";
import { getIdentity, saveIdentity, type P2PIdentity } from "../lib/api";

export default function NutzernameFeld() {
  const [ich, setIch] = useState<P2PIdentity | null>(null);
  const [name, setName] = useState("");
  const [stand, setStand] = useState<"" | "speichert" | "gespeichert" | "fehler">("");

  useEffect(() => {
    void getIdentity()
      .then((daten) => {
        setIch(daten);
        setName(daten.name);
      })
      .catch(() => setIch(null));
  }, []);

  const speichern = async () => {
    const neu = name.trim().slice(0, 32);
    if (!ich || neu === ich.name) return;
    setStand("speichert");
    try {
      const daten = await saveIdentity(neu, ich.avatar);
      setIch(daten);
      setName(daten.name);
      setStand("gespeichert");
      window.dispatchEvent(new CustomEvent("jon-identitaet", { detail: daten }));
      window.setTimeout(() => setStand(""), 1800);
    } catch {
      setStand("fehler");
    }
  };

  return (
    <div className="px-2 py-1.5 rounded-lg border border-white/10 bg-white/5">
      <div className="flex items-center justify-between">
        <label htmlFor="jon-nutzername" className="text-[11px] text-white/85">
          Dein Name
        </label>
        <span className="text-[10px] text-white/40">
          {stand === "speichert" ? "Speichert …" : stand === "gespeichert" ? "Gespeichert" : stand === "fehler" ? "Nicht gespeichert" : ""}
        </span>
      </div>
      <input
        id="jon-nutzername"
        value={name}
        maxLength={32}
        disabled={!ich}
        onChange={(e) => setName(e.target.value)}
        onBlur={() => void speichern()}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            void speichern();
          }
        }}
        placeholder="Wie soll Jon dich nennen?"
        className="w-full mt-1 px-2 py-1 rounded-md bg-black/30 border border-white/10 text-[12px] text-white/90 placeholder-white/30 outline-none focus:border-gold/40"
      />
      <div className="text-[10px] text-white/40 mt-1">So spricht Jon dich an, und so sehen dich Freunde im Chat.</div>
    </div>
  );
}
