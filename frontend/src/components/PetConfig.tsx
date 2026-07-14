import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  ProviderStatus,
  getProviders,
  getUserSettings,
  saveUserSettings,
} from "../lib/api";

type Eyes = "round" | "happy" | "sleepy";

interface Cfg {
  pet_accent: string;
  pet_face: string;
  pet_cheeks: boolean;
  pet_scale: number;
  pet_eyes: Eyes;
  pet_provider: string;
  pet_model: string;
}

const DEFAULT: Cfg = {
  pet_accent: "#d4af37",
  pet_face: "#0a0a0e",
  pet_cheeks: false,
  pet_scale: 1,
  pet_eyes: "round",
  pet_provider: "",
  pet_model: "openai/gpt-oss-20b",
};

function Eyes({ style, color }: { style: Eyes; color: string }) {
  if (style === "happy")
    return (
      <>
        <path d="M35 55 Q43 46 51 55" fill="none" stroke={color} strokeWidth={5} strokeLinecap="round" />
        <path d="M69 55 Q77 46 85 55" fill="none" stroke={color} strokeWidth={5} strokeLinecap="round" />
      </>
    );
  if (style === "sleepy")
    return (
      <>
        <path d="M36 53 h13" stroke={color} strokeWidth={5} strokeLinecap="round" />
        <path d="M71 53 h13" stroke={color} strokeWidth={5} strokeLinecap="round" />
      </>
    );
  return (
    <>
      <circle cx={43} cy={53} r={8} fill={color} />
      <circle cx={77} cy={53} r={8} fill={color} />
      <circle cx={45.5} cy={50.5} r={2.5} fill="#fff" />
      <circle cx={79.5} cy={50.5} r={2.5} fill="#fff" />
    </>
  );
}

export default function PetConfig({ onClose }: { onClose: () => void }) {
  const [cfg, setCfg] = useState<Cfg>(DEFAULT);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [mainProvider, setMainProvider] = useState("");

  useEffect(() => {
    void getUserSettings().then((s) => {
      setCfg({
        pet_accent: s.pet_accent || DEFAULT.pet_accent,
        pet_face: s.pet_face || DEFAULT.pet_face,
        pet_cheeks: s.pet_cheeks !== false,
        pet_scale: s.pet_scale || 1,
        pet_eyes: (s.pet_eyes as Eyes) || "round",
        pet_provider: s.pet_provider || "",
        pet_model: s.pet_model || DEFAULT.pet_model,
      });
      setMainProvider(s.provider || "");
    });
    void getProviders()
      .then(setProviders)
      .catch(() => setProviders([]));
  }, []);

  const update = (patch: Partial<Cfg>) => {
    const next = { ...cfg, ...patch };
    setCfg(next);
    void saveUserSettings(patch);
  };

  const reset = () => {
    setCfg(DEFAULT);
    void saveUserSettings(DEFAULT);
  };

  const eyeOptions: { value: Eyes; label: string }[] = [
    { value: "round", label: "Rund" },
    { value: "happy", label: "Fröhlich" },
    { value: "sleepy", label: "Verschlafen" },
  ];

  const configured = providers.filter((p) => p.configured);
  const activeProvider = cfg.pet_provider || mainProvider || "nvidia";
  const models =
    providers.find((p) => p.provider === activeProvider)?.models ?? [];
  const followsJon = Boolean(mainProvider) && mainProvider !== "nvidia";
  const selectField =
    "w-full bg-white/5 border border-white/10 rounded-lg px-2.5 py-1.5 text-[12px] text-white/90 outline-none focus:border-gold/50 [&>option]:bg-zinc-900";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.18 }}
        className="glass rounded-2xl border border-white/15 w-[94%] max-w-lg max-h-[85vh] overflow-hidden flex flex-col"
      >
        <div className="flex items-center justify-between px-5 h-14 border-b border-white/10">
          <div className="text-[15px] font-semibold gold-text">Mini Jon anpassen</div>
          <button
            onClick={onClose}
            className="text-white/40 hover:text-white/80 text-xl leading-none"
          >
            ×
          </button>
        </div>
        <div className="overflow-y-auto px-5 py-5 flex flex-col items-center gap-5">
          <svg width={140} height={140} viewBox="0 0 120 120">
            <circle cx={60} cy={60} r={52} fill={cfg.pet_face} />
            <circle
              cx={60}
              cy={60}
              r={52}
              fill="none"
              stroke={cfg.pet_accent}
              strokeWidth={4}
            />
            {cfg.pet_cheeks && (
              <>
                <ellipse cx={38} cy={70} rx={8} ry={5} fill="#ff9bb0" opacity={0.5} />
                <ellipse cx={82} cy={70} rx={8} ry={5} fill="#ff9bb0" opacity={0.5} />
              </>
            )}
            <Eyes style={cfg.pet_eyes} color={cfg.pet_accent} />
            <path
              d="M44 76 Q60 90 76 76"
              fill="none"
              stroke={cfg.pet_accent}
              strokeWidth={5}
              strokeLinecap="round"
            />
          </svg>

          <div className="w-full space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-[13px] text-white/80">Farbe</span>
              <input
                type="color"
                value={cfg.pet_accent}
                onChange={(e) => update({ pet_accent: e.target.value })}
                className="w-10 h-8 rounded cursor-pointer bg-transparent"
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[13px] text-white/80">Hintergrund (dunkel)</span>
              <input
                type="color"
                value={cfg.pet_face}
                onChange={(e) => update({ pet_face: e.target.value })}
                className="w-10 h-8 rounded cursor-pointer bg-transparent"
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[13px] text-white/80">Augen</span>
              <div className="flex gap-1">
                {eyeOptions.map((o) => (
                  <button
                    key={o.value}
                    onClick={() => update({ pet_eyes: o.value })}
                    className={`px-2.5 py-1 rounded-lg text-[12px] border transition ${
                      cfg.pet_eyes === o.value
                        ? "border-gold/50 bg-gold/15 text-gold"
                        : "border-white/10 bg-white/5 text-white/60 hover:bg-white/10"
                    }`}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[13px] text-white/80">Wangenrot (rosa)</span>
              <button
                onClick={() => update({ pet_cheeks: !cfg.pet_cheeks })}
                className={`w-9 h-5 rounded-full flex items-center px-0.5 transition-colors ${
                  cfg.pet_cheeks ? "bg-gold/70" : "bg-white/15"
                }`}
              >
                <span
                  className={`w-4 h-4 rounded-full bg-white transition-transform ${
                    cfg.pet_cheeks ? "translate-x-4" : ""
                  }`}
                />
              </button>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="text-[13px] text-white/80 whitespace-nowrap">
                Größe
              </span>
              <input
                type="range"
                min={0.7}
                max={1.4}
                step={0.05}
                value={cfg.pet_scale}
                onChange={(e) => update({ pet_scale: parseFloat(e.target.value) })}
                className="flex-1 accent-gold"
              />
              <span className="text-[12px] text-white/50 w-10 text-right">
                {Math.round(cfg.pet_scale * 100)}%
              </span>
            </div>
            <div className="space-y-1 pt-1">
              <span className="text-[13px] text-white/80">Anbieter</span>
              <select
                value={cfg.pet_provider}
                onChange={(e) =>
                  update({ pet_provider: e.target.value, pet_model: "" })
                }
                className={selectField}
              >
                <option value="">Wie Jon ({mainProvider || "nvidia"})</option>
                {configured.map((p) => (
                  <option key={p.provider} value={p.provider}>
                    {p.provider}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <span className="text-[13px] text-white/80">Modell</span>
              <select
                value={cfg.pet_model}
                onChange={(e) => update({ pet_model: e.target.value })}
                className={selectField}
              >
                <option value="">Automatisch (openai/gpt-oss-20b)</option>
                {cfg.pet_model && !models.includes(cfg.pet_model) && (
                  <option value={cfg.pet_model}>{cfg.pet_model}</option>
                )}
                {models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
              <div className="text-[11px] text-white/40 leading-snug">
                {followsJon
                  ? `Jon nutzt gerade ${mainProvider} — Mini Jon übernimmt Anbieter und Modell automatisch von Jon. Deine Auswahl hier gilt wieder, sobald Jon auf NVIDIA läuft.`
                  : "Mini Jon plaudert — ein schnelles Modell antwortet in ~2 s. Wechselt Jon oben zu einem anderen Anbieter als NVIDIA, übernimmt Mini Jon automatisch Jons Anbieter und Modell."}
              </div>
            </div>
          </div>

          <div className="w-full flex items-center justify-between pt-1">
            <button
              onClick={reset}
              className="text-[12px] text-white/45 hover:text-white/80"
            >
              Zurücksetzen
            </button>
            <p className="text-[11px] text-white/35">
              Der weiße Modus färbt Mini Jon automatisch hell.
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
