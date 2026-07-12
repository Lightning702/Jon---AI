import { useEffect, useState } from "react";
import {
  ToolMode,
  UserSettings,
  getAutostart,
  getUserSettings,
  saveUserSettings,
  setAutostart,
} from "../lib/api";
import { setNaturalVoice } from "../lib/tts";
import ConnectionsModal from "./ConnectionsModal";

type Theme = "dark" | "light";

const jonBridge = (window as unknown as {
  jon?: {
    getStartup?: () => Promise<boolean>;
    setStartup?: (enabled: boolean) => Promise<boolean>;
  };
}).jon;

export default function SettingsMenu({
  toolMode,
  onToolModeChange,
}: {
  toolMode: ToolMode;
  onToolModeChange: (mode: ToolMode) => void;
}) {
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>(() =>
    localStorage.getItem("jon_theme") === "light" ? "light" : "dark"
  );
  const [personality, setPersonality] = useState(true);
  const [startup, setStartup] = useState(false);
  const [city, setCity] = useState("");
  const [clipboard, setClipboard] = useState(true);
  const [webcam, setWebcam] = useState(false);
  const [voice, setVoice] = useState(true);
  const [connections, setConnections] = useState<UserSettings | null>(null);

  useEffect(() => {
    void getUserSettings().then((s) => {
      setPersonality(s.personality !== false);
      setCity(s.briefing_city ?? "");
      setClipboard(s.clipboard_history !== false);
      setWebcam(s.webcam_enabled === true);
      setVoice(s.natural_voice !== false);
    });
    void (async () => {
      const backend = await getAutostart();
      if (backend) {
        setStartup(true);
        return;
      }
      if (jonBridge?.getStartup) setStartup(await jonBridge.getStartup());
    })();
  }, []);

  const togglePersonality = () => {
    const next = !personality;
    setPersonality(next);
    void saveUserSettings({ personality: next });
  };

  const toggleStartup = async () => {
    const next = !startup;
    setStartup(next);
    const ok = await setAutostart(next);
    if (!ok && jonBridge?.setStartup) await jonBridge.setStartup(next);
  };

  const toggleClipboard = () => {
    const next = !clipboard;
    setClipboard(next);
    void saveUserSettings({ clipboard_history: next });
  };

  const toggleWebcam = () => {
    const next = !webcam;
    setWebcam(next);
    void saveUserSettings({ webcam_enabled: next });
  };

  const toggleVoice = () => {
    const next = !voice;
    setVoice(next);
    setNaturalVoice(next);
    void saveUserSettings({ natural_voice: next });
  };

  const openConnections = async () => {
    setConnections(await getUserSettings());
    setOpen(false);
  };

  const saveCity = (value: string) => {
    setCity(value);
    void saveUserSettings({ briefing_city: value.trim() });
  };

  const changeTheme = (next: Theme) => {
    setTheme(next);
    localStorage.setItem("jon_theme", next);
    document.documentElement.classList.toggle("light", next === "light");
    void saveUserSettings({ theme: next });
  };

  const options: { value: ToolMode; label: string; hint: string }[] = [
    {
      value: "ask",
      label: "Zuerst fragen",
      hint: "Jon fragt vor jeder PC-Aktion um Erlaubnis (Standard).",
    },
    {
      value: "allow",
      label: "Alles erlauben",
      hint: "Jon führt PC-Aktionen sofort ohne Nachfrage aus.",
    },
  ];

  const themes: { value: Theme; label: string; hint: string }[] = [
    { value: "dark", label: "Dunkel", hint: "Schwarz-Gold (Standard)." },
    { value: "light", label: "Hell", hint: "Weißer Modus mit Gold-Akzenten." },
  ];

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        title="Einstellungen"
        className={`flex items-center justify-center w-7 h-7 rounded-full border transition-colors ${
          open
            ? "border-amber-400/40 bg-amber-400/10 text-amber-300"
            : "border-white/10 bg-white/5 text-white/40 hover:text-white/70"
        }`}
      >
        <svg
          width="13"
          height="13"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.09a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.09a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.09a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-9 z-50 w-72 glass rounded-2xl border border-white/15 px-4 py-3 text-left">
            <div className="text-[11px] uppercase tracking-wide text-white/40 mb-2">
              PC-Steuerung durch Jon
            </div>
            <div className="space-y-1.5">
              {options.map((o) => (
                <button
                  key={o.value}
                  onClick={() => {
                    onToolModeChange(o.value);
                    setOpen(false);
                  }}
                  className={`w-full text-left px-3 py-2 rounded-xl border transition-colors ${
                    toolMode === o.value
                      ? "border-gold/40 bg-gold/10"
                      : "border-white/10 bg-white/5 hover:bg-white/10"
                  }`}
                >
                  <div className="flex items-center gap-2 text-[12px] text-white/90">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        toolMode === o.value ? "bg-gold" : "bg-white/20"
                      }`}
                    />
                    {o.label}
                  </div>
                  <div className="text-[11px] text-white/45 mt-0.5 pl-4">
                    {o.hint}
                  </div>
                </button>
              ))}
            </div>
            <div className="text-[11px] uppercase tracking-wide text-white/40 mt-3 mb-2">
              Design
            </div>
            <div className="space-y-1.5">
              {themes.map((t) => (
                <button
                  key={t.value}
                  onClick={() => changeTheme(t.value)}
                  className={`w-full text-left px-3 py-2 rounded-xl border transition-colors ${
                    theme === t.value
                      ? "border-gold/40 bg-gold/10"
                      : "border-white/10 bg-white/5 hover:bg-white/10"
                  }`}
                >
                  <div className="flex items-center gap-2 text-[12px] text-white/90">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        theme === t.value ? "bg-gold" : "bg-white/20"
                      }`}
                    />
                    {t.label}
                  </div>
                  <div className="text-[11px] text-white/45 mt-0.5 pl-4">
                    {t.hint}
                  </div>
                </button>
              ))}
            </div>
            <div className="text-[11px] uppercase tracking-wide text-white/40 mt-3 mb-2">
              Jon als Person
            </div>
            <button
              onClick={togglePersonality}
              className="w-full flex items-center justify-between px-3 py-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 transition-colors"
            >
              <div className="text-left">
                <div className="text-[12px] text-white/90">Persönlichkeit</div>
                <div className="text-[11px] text-white/45">
                  Jon mit Charakter, Gefühlen & Gedächtnis.
                </div>
              </div>
              <span
                className={`w-9 h-5 rounded-full flex items-center px-0.5 transition-colors ${
                  personality ? "bg-gold/70" : "bg-white/15"
                }`}
              >
                <span
                  className={`w-4 h-4 rounded-full bg-white transition-transform ${
                    personality ? "translate-x-4" : ""
                  }`}
                />
              </span>
            </button>
            <button
              onClick={() => void toggleStartup()}
              className="w-full flex items-center justify-between px-3 py-2 mt-1.5 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 transition-colors"
            >
              <div className="text-left">
                <div className="text-[12px] text-white/90">Mit Windows starten</div>
                <div className="text-[11px] text-white/45">
                  Backend & App starten beim Hochfahren automatisch.
                </div>
              </div>
              <span
                className={`w-9 h-5 rounded-full flex items-center px-0.5 transition-colors ${
                  startup ? "bg-gold/70" : "bg-white/15"
                }`}
              >
                <span
                  className={`w-4 h-4 rounded-full bg-white transition-transform ${
                    startup ? "translate-x-4" : ""
                  }`}
                />
              </span>
            </button>
            <button
              onClick={toggleClipboard}
              className="w-full flex items-center justify-between px-3 py-2 mt-1.5 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 transition-colors"
            >
              <div className="text-left">
                <div className="text-[12px] text-white/90">Clipboard-Historie</div>
                <div className="text-[11px] text-white/45">
                  Jon merkt sich lokal, was du kopierst (📋-Knopf).
                </div>
              </div>
              <span
                className={`w-9 h-5 rounded-full flex items-center px-0.5 transition-colors ${
                  clipboard ? "bg-gold/70" : "bg-white/15"
                }`}
              >
                <span
                  className={`w-4 h-4 rounded-full bg-white transition-transform ${
                    clipboard ? "translate-x-4" : ""
                  }`}
                />
              </span>
            </button>
            <button
              onClick={toggleWebcam}
              className="w-full flex items-center justify-between px-3 py-2 mt-1.5 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 transition-colors"
            >
              <div className="text-left">
                <div className="text-[12px] text-white/90">Webcam erlauben</div>
                <div className="text-[11px] text-white/45">
                  Jon darf auf Nachfrage durch die Webcam schauen.
                </div>
              </div>
              <span
                className={`w-9 h-5 rounded-full flex items-center px-0.5 transition-colors ${
                  webcam ? "bg-gold/70" : "bg-white/15"
                }`}
              >
                <span
                  className={`w-4 h-4 rounded-full bg-white transition-transform ${
                    webcam ? "translate-x-4" : ""
                  }`}
                />
              </span>
            </button>
            <button
              onClick={toggleVoice}
              className="w-full flex items-center justify-between px-3 py-2 mt-1.5 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 transition-colors"
            >
              <div className="text-left">
                <div className="text-[12px] text-white/90">Natürliche Stimme</div>
                <div className="text-[11px] text-white/45">
                  Echte Neural-Stimme statt Roboterstimme (gratis).
                </div>
              </div>
              <span
                className={`w-9 h-5 rounded-full flex items-center px-0.5 transition-colors ${
                  voice ? "bg-gold/70" : "bg-white/15"
                }`}
              >
                <span
                  className={`w-4 h-4 rounded-full bg-white transition-transform ${
                    voice ? "translate-x-4" : ""
                  }`}
                />
              </span>
            </button>
            <div className="text-[11px] uppercase tracking-wide text-white/40 mt-3 mb-2">
              Tagesbriefing
            </div>
            <input
              value={city}
              onChange={(e) => saveCity(e.target.value)}
              placeholder="Deine Stadt (für das Wetter)"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-[12px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50"
            />
            <button
              onClick={() => void openConnections()}
              className="w-full flex items-center justify-between px-3 py-2 mt-3 rounded-xl border border-gold/30 bg-gold/10 hover:bg-gold/20 transition-colors"
            >
              <div className="text-left">
                <div className="text-[12px] text-gold/90">🔌 Verbindungen …</div>
                <div className="text-[11px] text-white/45">
                  E-Mail, Kalender, Telegram, Smart Home
                </div>
              </div>
              <span className="text-gold/70 text-[13px]">›</span>
            </button>
          </div>
        </>
      )}
      {connections && (
        <ConnectionsModal
          settings={connections}
          onClose={() => setConnections(null)}
        />
      )}
    </div>
  );
}
