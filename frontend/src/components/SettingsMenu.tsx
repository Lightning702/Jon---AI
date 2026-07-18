import { useEffect, useRef, useState } from "react";
import {
  PairedDevice,
  ToolMode,
  UserSettings,
  backupUrl,
  getAutostart,
  getPairedDevices,
  getUserSettings,
  importBackup,
  removePairedDevice,
  saveUserSettings,
  setAutostart,
} from "../lib/api";
import { setNaturalVoice } from "../lib/tts";
import ConnectionsModal from "./ConnectionsModal";

type Theme = "dark" | "light";

interface Choice {
  value: string;
  label: string;
  hint: string;
}

const jonBridge = (window as unknown as {
  jon?: {
    getStartup?: () => Promise<boolean>;
    setStartup?: (enabled: boolean) => Promise<boolean>;
  };
}).jon;

function Section({ title }: { title: string }) {
  return (
    <div className="text-[9px] uppercase tracking-wider text-white/35 mt-2 mb-1 px-0.5">
      {title}
    </div>
  );
}

function Segmented({
  value,
  items,
  onPick,
}: {
  value: string;
  items: Choice[];
  onPick: (value: string) => void;
}) {
  return (
    <div className="flex gap-1">
      {items.map((item) => (
        <button
          key={item.value}
          title={item.hint}
          onClick={() => onPick(item.value)}
          className={`flex-1 text-[11px] py-1 rounded-lg border transition-colors ${
            value === item.value
              ? "border-gold/40 bg-gold/15 text-gold"
              : "border-white/10 bg-white/5 text-white/50 hover:bg-white/10"
          }`}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

function Toggle({
  label,
  hint,
  on,
  onClick,
}: {
  label: string;
  hint: string;
  on: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      title={hint}
      className="w-full flex items-center justify-between gap-2 px-2 py-1 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 transition-colors"
    >
      <span className="text-[11px] text-white/85 truncate">{label}</span>
      <span
        className={`w-7 h-4 shrink-0 rounded-full flex items-center px-0.5 transition-colors ${
          on ? "bg-gold/70" : "bg-white/15"
        }`}
      >
        <span
          className={`w-3 h-3 rounded-full bg-white transition-transform ${
            on ? "translate-x-3" : ""
          }`}
        />
      </span>
    </button>
  );
}

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
  const [failover, setFailover] = useState(true);
  const [startup, setStartup] = useState(false);
  const [city, setCity] = useState("");
  const [clipboard, setClipboard] = useState(true);
  const [webcam, setWebcam] = useState(false);
  const [backupInfo, setBackupInfo] = useState("");
  const backupRef = useRef<HTMLInputElement>(null);
  const [voice, setVoice] = useState(true);
  const [cowork, setCowork] = useState(false);
  const [coworkApp, setCoworkApp] = useState("auto");
  const [quickwrite, setQuickwrite] = useState(true);
  const [timeline, setTimeline] = useState(false);
  const [routine, setRoutine] = useState(true);
  const [petRoam, setPetRoam] = useState(false);
  const [petCompanion, setPetCompanion] = useState("none");
  const [connections, setConnections] = useState<UserSettings | null>(null);
  const [devices, setDevices] = useState<PairedDevice[]>([]);
  const [wakeSensitivity, setWakeSensitivity] = useState("mittel");

  useEffect(() => {
    if (!open) return;
    void getPairedDevices()
      .then(setDevices)
      .catch(() => setDevices([]));
  }, [open]);

  const dropDevice = async (id: string) => {
    await removePairedDevice(id);
    setDevices((prev) => prev.filter((d) => d.id !== id));
  };

  useEffect(() => {
    void getUserSettings().then((s) => {
      setPersonality(s.personality !== false);
      setFailover(s.auto_failover !== false);
      setCity(s.briefing_city ?? "");
      setClipboard(s.clipboard_history !== false);
      setWebcam(s.webcam_enabled === true);
      setVoice(s.natural_voice !== false);
      setCowork(s.cowork_enabled === true);
      setCoworkApp(s.cowork_app || "auto");
      setQuickwrite(s.quickwrite_enabled !== false);
      setTimeline(s.timeline_enabled === true);
      setRoutine(s.routine_enabled !== false);
      setPetRoam(s.pet_roam === true);
      setPetCompanion(s.pet_companion || "none");
      setWakeSensitivity(s.wake_sensitivity || "mittel");
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

  const toggleFailover = () => {
    const next = !failover;
    setFailover(next);
    void saveUserSettings({ auto_failover: next });
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

  const toggleCowork = () => {
    const next = !cowork;
    setCowork(next);
    void saveUserSettings({ cowork_enabled: next });
  };

  const pickCoworkApp = (value: string) => {
    setCoworkApp(value);
    void saveUserSettings({ cowork_app: value });
  };

  const toggleQuickwrite = () => {
    const next = !quickwrite;
    setQuickwrite(next);
    void saveUserSettings({ quickwrite_enabled: next });
  };

  const toggleTimeline = () => {
    const next = !timeline;
    setTimeline(next);
    void saveUserSettings({ timeline_enabled: next });
  };

  const toggleRoutine = () => {
    const next = !routine;
    setRoutine(next);
    void saveUserSettings({ routine_enabled: next });
  };

  const togglePetRoam = () => {
    const next = !petRoam;
    setPetRoam(next);
    void saveUserSettings({ pet_roam: next });
  };

  const pickCompanion = (value: string) => {
    setPetCompanion(value);
    void saveUserSettings({ pet_companion: value });
  };

  const pickWakeSensitivity = (value: string) => {
    setWakeSensitivity(value);
    void saveUserSettings({ wake_sensitivity: value });
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

  const options: Choice[] = [
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

  const themes: Choice[] = [
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
          <div className="absolute right-0 top-9 z-50 w-56 glass rounded-xl border border-white/15 px-2 py-2 text-left max-h-[calc(100vh-7rem)] overflow-y-auto overscroll-contain">
            <Section title="PC-Steuerung durch Jon" />
            <Segmented
              value={toolMode}
              items={options}
              onPick={(v) => {
                onToolModeChange(v as ToolMode);
                setOpen(false);
              }}
            />
            <Section title="Design" />
            <Segmented
              value={theme}
              items={themes}
              onPick={(v) => changeTheme(v as Theme)}
            />
            <Section title="Jon" />
            <div className="space-y-1">
              <Toggle
                label="Persönlichkeit"
                hint="Jon mit Charakter, Gefühlen und Gedächtnis."
                on={personality}
                onClick={togglePersonality}
              />
              <Toggle
                label="Anbieter wechseln"
                hint="Ist dein Anbieter überlastet, nimmt Jon dasselbe Modell bei einem anderen. Kann dort Guthaben kosten."
                on={failover}
                onClick={toggleFailover}
              />
              <Toggle
                label="Mit Windows starten"
                hint="Backend und App starten beim Hochfahren automatisch."
                on={startup}
                onClick={() => void toggleStartup()}
              />
              <Toggle
                label="Clipboard-Historie"
                hint="Jon merkt sich lokal, was du kopierst (📋-Knopf)."
                on={clipboard}
                onClick={toggleClipboard}
              />
              <Toggle
                label="Webcam erlauben"
                hint="Jon darf auf Nachfrage durch die Webcam schauen."
                on={webcam}
                onClick={toggleWebcam}
              />
              <Toggle
                label="Natürliche Stimme"
                hint="Echte Neural-Stimme statt Roboterstimme (gratis)."
                on={voice}
                onClick={toggleVoice}
              />
            </div>
            <Section title="Mitarbeiten & Fokus" />
            <div className="space-y-1">
              <Toggle
                label="Mini Jon arbeitet mit"
                hint="Er prüft alle 5 Minuten, ob deine gewählte App offen ist, fragt dann per Sprache und Knopf, ob er mithelfen soll, und gibt Tipps."
                on={cowork}
                onClick={toggleCowork}
              />
              {cowork && (
                <div className="pt-1">
                  <div className="text-[10px] text-white/40 px-0.5 mb-1">
                    Bei welcher App soll er fragen?
                  </div>
                  <select
                    value={coworkApp}
                    onChange={(e) => pickCoworkApp(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-[11px] text-white/90 outline-none focus:border-gold/50 [&>option]:bg-zinc-900"
                  >
                    <option value="auto">Egal welche Arbeits-App</option>
                    <option value="vscode">VS Code</option>
                    <option value="word">Word</option>
                    <option value="docs">Google Docs</option>
                    <option value="libreoffice">LibreOffice Writer</option>
                    <option value="obsidian">Obsidian</option>
                    <option value="onenote">OneNote</option>
                    <option value="excel">Excel</option>
                    <option value="powerpoint">PowerPoint</option>
                    <option value="notion">Notion</option>
                    <option value="notepadpp">Notepad++</option>
                    <option value="notepad">Editor</option>
                    <option value="pycharm">PyCharm</option>
                    <option value="intellij">IntelliJ</option>
                  </select>
                  <div className="text-[9.5px] text-white/35 px-0.5 mt-1 leading-snug">
                    Sobald die App offen ist, fragt Mini Jon (spricht + zeigt Ja/Nein). Bei
                    „Ja" schaut er ab und zu über die Schulter, bei „Nein" fragt er später.
                  </div>
                </div>
              )}
              <Toggle
                label="Gewohnheiten erkennen"
                hint="Jon bemerkt wiederkehrende Abläufe und bietet an, sie zu automatisieren."
                on={routine}
                onClick={toggleRoutine}
              />
              <Toggle
                label="Schreib-Hotkey (Strg+Alt+H)"
                hint="Text irgendwo markieren und mit Strg+Alt+H oder Strg+Alt+Rechtsklick von Jon verbessern lassen."
                on={quickwrite}
                onClick={toggleQuickwrite}
              />
              <Toggle
                label="Bildschirm-Zeitreise"
                hint="Jon merkt sich lokal, was du offen hattest, und findet es auf Nachfrage wieder. Alles bleibt auf deinem PC."
                on={timeline}
                onClick={toggleTimeline}
              />
            </div>
            <Section title="Sprache / Language" />
            <div className="pt-1">
              <div className="text-[10px] text-white/40 px-0.5 mb-1">
                UI & Chat Sprache
              </div>
              <select
                value={localStorage.getItem("jon_lang") || "de"}
                onChange={(e) => {
                  const lang = e.target.value;
                  localStorage.setItem("jon_lang", lang);
                  window.dispatchEvent(new Event("jon_lang_change"));
                  void saveUserSettings({ language: lang });
                }}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-[11px] text-white/90 outline-none focus:border-gold/50 [&>option]:bg-zinc-900"
              >
                <option value="de">Deutsch</option>
                <option value="en">English</option>
              </select>
            </div>
            <Section title="Sprachsteuerung" />
            <div className="pt-1">
              <div className="text-[10px] text-white/40 px-0.5 mb-1">
                Wake-Word-Empfindlichkeit („Jon“)
              </div>
              <Segmented
                value={wakeSensitivity}
                items={[
                  {
                    value: "niedrig",
                    label: "Niedrig",
                    hint: "Reagiert nur bei sehr deutlichem „Jon“ — kaum Fehlauslöser.",
                  },
                  {
                    value: "mittel",
                    label: "Mittel",
                    hint: "Ausgewogen (Standard).",
                  },
                  {
                    value: "hoch",
                    label: "Hoch",
                    hint: "Reagiert schnell, kann öfter versehentlich anspringen.",
                  },
                ]}
                onPick={pickWakeSensitivity}
              />
              <div className="text-[9.5px] text-white/35 px-0.5 mt-1 leading-snug">
                Mit openWakeWord läuft die Erkennung offline im Backend. Fehlt es,
                nutzt Jon automatisch die bisherige Erkennung im Fenster.
              </div>
            </div>
            <Section title="Mini Jon & Haustier" />
            <div className="space-y-1">
              <Toggle
                label="Frei über den Bildschirm"
                hint="Mini Jon wandert am unteren Rand herum statt fest in der Ecke zu stehen. Schläft, wenn du weg bist."
                on={petRoam}
                onClick={togglePetRoam}
              />
              <div className="pt-1">
                <div className="text-[10px] text-white/40 px-0.5 mb-1">
                  Haustier für Mini Jon
                </div>
                <Segmented
                  value={petCompanion}
                  items={[
                    { value: "none", label: "Keins", hint: "Mini Jon ist allein." },
                    { value: "cat", label: "🐱 Katze", hint: "Minka lebt bei Mini Jon." },
                    { value: "dog", label: "🐶 Hund", hint: "Rocky lebt bei Mini Jon." },
                  ]}
                  onPick={pickCompanion}
                />
                <div className="text-[9.5px] text-white/35 px-0.5 mt-1 leading-snug">
                  Mini Jon spielt mit dem Tier, wenn er frei ist — schläft mit ihm,
                  wenn du weg bist.
                </div>
              </div>
            </div>
            <Section title="Tagesbriefing" />
            <input
              value={city}
              onChange={(e) => saveCity(e.target.value)}
              placeholder="Stadt (für das Wetter)"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-[11px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50"
            />
            {devices.length > 0 && (
              <>
                <Section title="Gekoppelte Geräte" />
                <div className="space-y-1">
                  {devices.map((d) => (
                    <div
                      key={d.id}
                      className="flex items-center justify-between gap-2 px-2 py-1 rounded-lg border border-white/10 bg-white/5"
                    >
                      <div className="min-w-0">
                        <div className="text-[11px] text-white/85 truncate">
                          📱 {d.name}
                        </div>
                        <div className="text-[9.5px] text-white/35">
                          seit {d.paired_at.slice(0, 10)}
                        </div>
                      </div>
                      <button
                        onClick={() => void dropDevice(d.id)}
                        title="Gerät entkoppeln — es muss sich danach neu koppeln."
                        className="text-white/35 hover:text-red-300 text-[12px] shrink-0"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              </>
            )}
            <Section title="Backup" />
            <div className="flex gap-1">
              <a
                href={backupUrl()}
                download
                title="Gedächtnis, Wissensbasis, Skills und Einstellungen sichern — ohne API-Schlüssel."
                className="flex-1 text-center text-[11px] py-1 rounded-lg border border-white/10 bg-white/5 text-white/60 hover:bg-white/10 transition"
              >
                Export
              </a>
              <input
                ref={backupRef}
                type="file"
                accept=".zip"
                className="hidden"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  e.target.value = "";
                  if (!file) return;
                  setBackupInfo("Stelle wieder her …");
                  try {
                    setBackupInfo(await importBackup(file));
                  } catch (err) {
                    setBackupInfo(
                      err instanceof Error ? err.message : String(err)
                    );
                  }
                }}
              />
              <button
                onClick={() => backupRef.current?.click()}
                title="Ein zuvor exportiertes Backup wieder einspielen."
                className="flex-1 text-[11px] py-1 rounded-lg border border-white/10 bg-white/5 text-white/60 hover:bg-white/10 transition"
              >
                Import
              </button>
            </div>
            {backupInfo && (
              <div className="text-[10px] text-gold/70 mt-1 leading-snug">
                {backupInfo}
              </div>
            )}
            <button
              onClick={() => void openConnections()}
              className="w-full flex items-center justify-between gap-2 px-2 py-1.5 mt-2 rounded-lg border border-gold/30 bg-gold/10 hover:bg-gold/20 transition-colors"
            >
              <span className="text-[11px] text-gold/90">
                🔌 Verbindungen …
              </span>
              <span className="text-gold/70 text-[12px]">›</span>
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
