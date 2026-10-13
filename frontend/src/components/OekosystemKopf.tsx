import { Laptop, MapPin, Server, Smartphone, Tablet, Watch } from "lucide-react";
import { useEffect, useState } from "react";
import { OekosystemStand, oekosystem } from "../lib/api";

const SYMBOLE = { handy: Smartphone, tablet: Tablet, uhr: Watch, pc: Laptop };

export default function OekosystemKopf() {
  const [stand, setStand] = useState<OekosystemStand | null>(null);

  useEffect(() => {
    let lebt = true;
    const laden = (pruefen: boolean) =>
      oekosystem(pruefen)
        .then((s) => lebt && setStand(s))
        .catch(() => undefined);
    void laden(true);
    const takt = window.setInterval(() => void laden(false), 15000);
    return () => {
      lebt = false;
      window.clearInterval(takt);
    };
  }, []);

  if (!stand) return null;
  const online = stand.geraete.filter((g) => g.online).length + stand.verbund.filter((v) => v.online).length + 1;
  const gesamt = stand.geraete.length + stand.verbund.length + 1;
  const aktiv = stand.aktiv?.id !== "pc" ? stand.geraete.find((g) => g.id === stand.aktiv.id) : null;
  const eintraege = [
    { id: "ich", name: stand.ich.name, typ: "pc", zusatz: `${stand.ich.plattform} · dieser Jon`, online: true },
    ...stand.verbund.map((v) => ({ id: v.id, name: v.name, typ: v.plattform.toLowerCase().includes("pi") ? "pi" : "pc", zusatz: v.plattform, online: !!v.online })),
    ...stand.geraete.map((g) => ({ id: g.id, name: g.name, typ: g.typ || "handy", zusatz: g.besitzer ? `gehört ${g.besitzer}` : "Besitzer fehlt", online: g.online })),
  ];

  return (
    <div className="rounded-xl border border-gold/20 bg-gradient-to-br from-gold/[0.07] to-white/[0.02] p-3">
      <div className="flex items-center justify-between">
        <div className="text-[12px] font-medium text-white/85">Dein Jon-Ökosystem</div>
        <div className="text-[10.5px] text-white/45">
          {online} von {gesamt} online
        </div>
      </div>
      {aktiv ? (
        <div className="mt-1 flex items-center gap-1.5 text-[10.5px] text-gold/80">
          <MapPin size={11} />
          Du bist gerade am Gerät „{aktiv.name}“ – Erinnerungen kommen dort an.
        </div>
      ) : null}
      <div className="mt-2.5 grid grid-cols-2 gap-1.5">
        {eintraege.map((e) => {
          const Symbol = e.typ === "pi" ? Server : SYMBOLE[e.typ as keyof typeof SYMBOLE] ?? Smartphone;
          return (
            <div key={e.id} className="flex items-center gap-2 rounded-lg border border-white/10 bg-black/20 px-2 py-1.5">
              <span className={"relative flex h-7 w-7 flex-none items-center justify-center rounded-lg " + (e.online ? "bg-gold/15 text-gold" : "bg-white/5 text-white/35")}>
                <Symbol size={14} />
                <span className={"absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full border border-black " + (e.online ? "bg-emerald-400" : "bg-white/30")} />
              </span>
              <div className="min-w-0">
                <div className="truncate text-[11px] text-white/85">{e.name}</div>
                <div className="truncate text-[9.5px] text-white/40">{e.zusatz}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
