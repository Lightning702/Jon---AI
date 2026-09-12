import { useEffect, useRef, useState } from "react";
import {
  OllamaStatus,
  ToolMode,
  UserSettings,
  backupUrl,
  getAutostart,
  getOllamaConfig,
  getOllamaStatus,
  getUserSettings,
  importBackup,
  saveOllamaConfig,
  saveUserSettings,
  setAutostart,
} from "../lib/api";
import { setNaturalVoice } from "../lib/tts";
import { Theme, applyTheme, readTheme } from "../lib/theme";
import { useT } from "../hooks/useT";
import ConnectionsModal from "./ConnectionsModal";
import DiagnosticsModal from "./DiagnosticsModal";
import HandyModal from "./HandyModal";
import UninstallModal from "./UninstallModal";
import OllamaModal from "./OllamaModal";

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
  const { lang, setLang } = useT();
  const [open, setOpen] = useState(false);
  const [uninstallOpen, setUninstallOpen] = useState(false);
  const [diagnoseOpen, setDiagnoseOpen] = useState(false);
  const [handyOpen, setHandyOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>(readTheme);
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
  const [autofile, setAutofile] = useState(false);
  const [appUsage, setAppUsage] = useState(false);
  const [browserAgent, setBrowserAgent] = useState(true);
  const [browserSichtbar, setBrowserSichtbar] = useState(true);
  const [browserDryRun, setBrowserDryRun] = useState(false);
  const [browserPlan, setBrowserPlan] = useState("auto");
  const [browserSchritte, setBrowserSchritte] = useState(25);
  const [initiative, setInitiative] = useState(false);
  const [wahrnehmung, setWahrnehmung] = useState(false);
  const [konsolidierung, setKonsolidierung] = useState(true);
  const [kritiker, setKritiker] = useState(false);
  const [erwartung, setErwartung] = useState(true);
  const [metakognition, setMetakognition] = useState(true);
  const [neugier, setNeugier] = useState(true);
  const [neugierAuto, setNeugierAuto] = useState(false);
  const [fertigkeitAuto, setFertigkeitAuto] = useState(false);
  const [datenschutz, setDatenschutz] = useState("warnen");
  const [budgetTokens, setBudgetTokens] = useState(0);
  const [budgetEuro, setBudgetEuro] = useState(0);
  const [suchmaschine, setSuchmaschine] = useState("brave");
  const [browserSpeicher, setBrowserSpeicher] = useState("festplatte");
  const [webBrowser, setWebBrowser] = useState("system");
  const [routine, setRoutine] = useState(true);
  const [petRoam, setPetRoam] = useState(false);
  const [petWellness, setPetWellness] = useState(true);
  const [connections, setConnections] = useState<UserSettings | null>(null);
  const [wakeSensitivity, setWakeSensitivity] = useState("mittel");
  const [micList, setMicList] = useState<{ id: string; name: string }[]>([]);
  const [selectedMic, setSelectedMic] = useState("default");
  const [ollamaOpen, setOllamaOpen] = useState(false);
  const [ollamaOn, setOllamaOn] = useState(false);
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus | null>(null);

  const loadOllama = async () => {
    try {
      const config = await getOllamaConfig();
      setOllamaOn(config.enabled);
      setOllamaStatus(await getOllamaStatus());
    } catch {
      setOllamaStatus(null);
    }
  };

  const toggleOllama = () => {
    const next = !ollamaOn;
    setOllamaOn(next);
    void saveOllamaConfig({ enabled: next }).then(() => loadOllama());
  };

  const loadMics = async () => {
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true }).catch(() => {});
      const devices = await navigator.mediaDevices.enumerateDevices();
      const inputs = devices
        .filter((d) => d.kind === "audioinput")
        .map((d) => ({
          id: d.deviceId,
          name: d.label || `Mikrofon (${d.deviceId.slice(0, 5)})`,
        }));
      setMicList(inputs);
    } catch {}
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
      setAutofile(s.autofile_enabled === true);
      setAppUsage(s.app_usage_enabled === true);
      setBrowserAgent(s.browser_agent !== false);
      setBrowserSichtbar(s.browser_sichtbar !== false);
      setBrowserDryRun(s.browser_dry_run === true);
      setBrowserPlan(s.browser_plan_modus || "auto");
      setBrowserSchritte(s.browser_max_schritte || 25);
      setInitiative(s.initiative_enabled === true);
      setWahrnehmung(s.wahrnehmung_enabled === true);
      setKonsolidierung(s.konsolidierung_auto !== false);
      setKritiker(s.kritiker_enabled === true);
      setErwartung(s.erwartung_enabled !== false);
      setMetakognition(s.metakognition_enabled !== false);
      setNeugier(s.neugier_enabled !== false);
      setNeugierAuto(s.neugier_auto === true);
      setFertigkeitAuto(s.fertigkeit_auto === true);
      setDatenschutz(s.datenschutz_regel || "warnen");
      setBudgetTokens(s.budget_tokens_tag || 0);
      setBudgetEuro(s.budget_euro_monat || 0);
      setSuchmaschine(s.browser_suchmaschine || "brave");
      setBrowserSpeicher(s.browser_speicher || "festplatte");
      setWebBrowser(s.web_browser || "system");
      setRoutine(s.routine_enabled !== false);
      setPetRoam(s.pet_roam === true);
      setPetWellness(s.pet_wellness !== false);
      setWakeSensitivity(s.wake_sensitivity || "mittel");
      setSelectedMic(s.microphone_device || "default");
    });
    void loadMics();
    void loadOllama();
    navigator.mediaDevices.addEventListener("devicechange", loadMics);
    void (async () => {
      const backend = await getAutostart();
      if (backend) {
        setStartup(true);
        return;
      }
      if (jonBridge?.getStartup) setStartup(await jonBridge.getStartup());
    })();
    return () => {
      navigator.mediaDevices.removeEventListener("devicechange", loadMics);
    };
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

  const toggleInitiative = () => {
    const next = !initiative;
    setInitiative(next);
    void saveUserSettings({ initiative_enabled: next });
  };

  const toggleWahrnehmung = () => {
    const next = !wahrnehmung;
    setWahrnehmung(next);
    void saveUserSettings({ wahrnehmung_enabled: next });
  };

  const toggleKonsolidierung = () => {
    const next = !konsolidierung;
    setKonsolidierung(next);
    void saveUserSettings({ konsolidierung_auto: next });
  };

  const toggleKritiker = () => {
    const next = !kritiker;
    setKritiker(next);
    void saveUserSettings({ kritiker_enabled: next });
  };

  const toggleErwartung = () => {
    const next = !erwartung;
    setErwartung(next);
    void saveUserSettings({ erwartung_enabled: next });
  };

  const toggleMetakognition = () => {
    const next = !metakognition;
    setMetakognition(next);
    void saveUserSettings({ metakognition_enabled: next });
  };

  const toggleNeugier = () => {
    const next = !neugier;
    setNeugier(next);
    void saveUserSettings({ neugier_enabled: next });
  };

  const toggleNeugierAuto = () => {
    const next = !neugierAuto;
    setNeugierAuto(next);
    void saveUserSettings({ neugier_auto: next });
  };

  const toggleFertigkeitAuto = () => {
    const next = !fertigkeitAuto;
    setFertigkeitAuto(next);
    void saveUserSettings({ fertigkeit_auto: next });
  };

  const pickDatenschutz = (value: string) => {
    setDatenschutz(value);
    void saveUserSettings({ datenschutz_regel: value });
  };

  const pickBrowserSpeicher = (value: string) => {
    setBrowserSpeicher(value);
    void saveUserSettings({
      browser_speicher: value,
      browser_persistent: value === "festplatte",
    });
  };

  const pickWebBrowser = (value: string) => {
    setWebBrowser(value);
    void saveUserSettings({ web_browser: value });
  };

  const pickSuchmaschine = (value: string) => {
    setSuchmaschine(value);
    void saveUserSettings({ browser_suchmaschine: value });
  };

  const toggleBrowserAgent = () => {
    const next = !browserAgent;
    setBrowserAgent(next);
    void saveUserSettings({ browser_agent: next });
  };

  const toggleBrowserSichtbar = () => {
    const next = !browserSichtbar;
    setBrowserSichtbar(next);
    void saveUserSettings({ browser_sichtbar: next });
  };

  const toggleBrowserDryRun = () => {
    const next = !browserDryRun;
    setBrowserDryRun(next);
    void saveUserSettings({ browser_dry_run: next });
  };

  const pickBrowserPlan = (value: string) => {
    setBrowserPlan(value);
    void saveUserSettings({ browser_plan_modus: value });
  };

  const pickBrowserSchritte = (value: number) => {
    const sicher = Math.max(3, Math.min(60, value || 25));
    setBrowserSchritte(sicher);
    void saveUserSettings({ browser_max_schritte: sicher });
  };

  const toggleTimeline = () => {
    const next = !timeline;
    setTimeline(next);
    void saveUserSettings({ timeline_enabled: next });
  };

  const toggleAutofile = () => {
    const next = !autofile;
    setAutofile(next);
    void saveUserSettings({ autofile_enabled: next });
  };

  const toggleAppUsage = () => {
    const next = !appUsage;
    setAppUsage(next);
    void saveUserSettings({ app_usage_enabled: next });
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

  const togglePetWellness = () => {
    const next = !petWellness;
    setPetWellness(next);
    void saveUserSettings({ pet_wellness: next });
  };

  const pickWakeSensitivity = (value: string) => {
    setWakeSensitivity(value);
    void saveUserSettings({ wake_sensitivity: value });
  };

  const pickMicrophone = (deviceId: string) => {
    setSelectedMic(deviceId);
    const mic = micList.find((m) => m.id === deviceId);
    const name = mic ? mic.name : "";
    localStorage.setItem("jon_mic_device", deviceId);
    localStorage.setItem("jon_mic_name", name);
    void saveUserSettings({ microphone_device: deviceId, microphone_name: name });
    window.dispatchEvent(new Event("jon_mic_changed"));
  };

  const openConnections = async () => {
    setOpen(false);
    try {
      setConnections(await getUserSettings());
    } catch {
      setConnections(null);
    }
  };

  const saveCity = (value: string) => {
    setCity(value);
    void saveUserSettings({ briefing_city: value.trim() });
  };

  const changeTheme = (next: Theme) => {
    setTheme(next);
    localStorage.setItem("jon_theme", next);
    applyTheme(next);
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
    { value: "cozy", label: "Cozy", hint: "Weiß mit zartem Rosa — weich und warm." },
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
            <Section title="Ollama" />
            <div className="space-y-1">
              <Toggle
                label="Ollama verwenden"
                hint="Modelle laufen lokal auf deinem PC oder auf einem Server im Netzwerk — kostenlos und ohne Cloud."
                on={ollamaOn}
                onClick={toggleOllama}
              />
              <div className="flex items-center gap-1.5 px-1 py-0.5">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    !ollamaOn || ollamaStatus?.state === "disabled"
                      ? "bg-white/25"
                      : ollamaStatus?.state === "online"
                      ? "bg-emerald-400"
                      : "bg-red-400"
                  }`}
                />
                <span className="text-[10px] text-white/45 truncate">
                  {!ollamaOn || ollamaStatus?.state === "disabled"
                    ? "Ausgeschaltet"
                    : ollamaStatus?.state === "online"
                    ? `Online · ${ollamaStatus.response_ms} ms · ${ollamaStatus.model_count} Modelle`
                    : "Offline"}
                </span>
              </div>
              <button
                onClick={() => {
                  setOllamaOpen(true);
                  setOpen(false);
                }}
                className="w-full flex items-center justify-between gap-2 px-2 py-1 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 transition-colors"
              >
                <span className="text-[11px] text-white/85">
                  Server & Modelle …
                </span>
                <span className="text-white/40 text-[12px]">›</span>
              </button>
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
              <Toggle
                label="Downloads automatisch einsortieren"
                hint="Neue Downloads wandern in Unterordner nach Typ (Bilder, Dokumente, Musik, Rechnungen, Screenshots …). Alles per Papierkorb wiederherstellbar."
                on={autofile}
                onClick={toggleAutofile}
              />
              <Toggle
                label="App-Nutzung erfassen (/fokus)"
                hint="Jon merkt sich lokal, in welchen Apps du wie lange bist, und zeigt es dir mit /fokus. Nichts verlaesst deinen PC."
                on={appUsage}
                onClick={toggleAppUsage}
              />
            </div>
            <Section title="Browser-Agent" />
            <div className="space-y-1">
              <Toggle
                label="Browser-Agent"
                hint="Jon darf einen echten Chromium-Browser selbst bedienen: Seiten öffnen, lesen, klicken, Formulare ausfüllen."
                on={browserAgent}
                onClick={toggleBrowserAgent}
              />
              <Toggle
                label="Browserfenster zeigen"
                hint="Aus = Jon arbeitet unsichtbar im Hintergrund (headless). An = du siehst live zu."
                on={browserSichtbar}
                onClick={toggleBrowserSichtbar}
              />
              <Toggle
                label="Nur Probelauf (Dry Run)"
                hint="Jon plant und schaut nach, verändert aber nichts: keine Bestellung, kein Absenden."
                on={browserDryRun}
                onClick={toggleBrowserDryRun}
              />
              <div className="text-[10px] text-white/40 px-0.5 pt-1">Planmodus</div>
              <Segmented
                value={browserPlan}
                items={[
                  {
                    value: "auto",
                    label: "Auto",
                    hint: "Nur bei riskanten oder mehrstufigen Aufgaben wird geplant.",
                  },
                  {
                    value: "immer",
                    label: "Immer",
                    hint: "Jon plant jede Browser-Aufgabe vorher.",
                  },
                  {
                    value: "aus",
                    label: "Aus",
                    hint: "Jon legt direkt los. Kritische Aktionen bleiben trotzdem gesperrt.",
                  },
                ]}
                onPick={pickBrowserPlan}
              />
              <div className="flex items-center justify-between gap-2 px-2 py-1 rounded-lg border border-white/10 bg-white/5">
                <span className="text-[11px] text-white/85">Schritte je Auftrag</span>
                <input
                  type="number"
                  min={3}
                  max={60}
                  value={browserSchritte}
                  onChange={(e) => pickBrowserSchritte(Number(e.target.value))}
                  className="w-16 bg-black/30 border border-white/10 rounded-md px-2 py-0.5 text-[11px] text-white/85 text-right"
                />
              </div>
              <div className="text-[10px] text-white/40 px-0.5 leading-relaxed">
                Käufe, Bestellungen, Nachrichten und Löschungen fragen immer nach –
                das lässt sich nicht abschalten.
              </div>
              <div className="text-[10px] text-white/40 px-0.5 pt-1">
                Womit öffnet Jon Webseiten?
              </div>
              <select
                value={webBrowser}
                onChange={(e) => pickWebBrowser(e.target.value)}
                className="w-full bg-black/30 border border-white/10 rounded-lg px-2 py-1 text-[11px] text-white/85"
              >
                <option value="system">Normaler Browser des PCs (Standard)</option>
                <option value="jon">Jon-Browser (Jon kann mitlesen)</option>
                <option value="chrome">Google Chrome</option>
                <option value="edge">Microsoft Edge</option>
                <option value="firefox">Firefox</option>
                <option value="brave">Brave</option>
                <option value="opera">Opera</option>
                <option value="vivaldi">Vivaldi</option>
              </select>
              <div className="text-[10px] text-white/40 px-0.5 leading-relaxed">
                Seiten für dich öffnet Jon normal in deinem gewohnten Browser. Zum
                Suchen und Lesen nimmt er immer seinen eigenen — nur dort sieht
                er, was auf der Seite steht.
              </div>
              <div className="text-[10px] text-white/40 px-0.5 pt-1">
                Wo liegen die Browserdaten?
              </div>
              <Segmented
                value={browserSpeicher}
                items={[
                  {
                    value: "festplatte",
                    label: "Festplatte",
                    hint: "Cookies, Logins und Cache bleiben in Jons Browserprofil erhalten.",
                  },
                  {
                    value: "ram",
                    label: "Nur RAM",
                    hint: "Alles nur im Arbeitsspeicher: nichts landet auf der Platte, beim Schließen ist alles weg — auch Screenshots.",
                  },
                ]}
                onPick={pickBrowserSpeicher}
              />
              <div className="text-[10px] text-white/40 px-0.5 pt-1">Suchmaschine</div>
              <select
                value={suchmaschine}
                onChange={(e) => pickSuchmaschine(e.target.value)}
                className="w-full bg-black/30 border border-white/10 rounded-lg px-2 py-1 text-[11px] text-white/85"
              >
                <option value="brave">Brave (liest sich am besten)</option>
                <option value="duckduckgo">DuckDuckGo</option>
                <option value="startpage">Startpage</option>
                <option value="ecosia">Ecosia</option>
                <option value="google">Google</option>
                <option value="bing">Bing</option>
              </select>
            </div>
            <Section title="Jons Denken" />
            <div className="space-y-1">
              <Toggle
                label="Eigeninitiative"
                hint="Jon schaut regelmäßig, was gestern war und was morgen ansteht, und schlägt von selbst etwas vor. Ausführen darf er nur Harmloses."
                on={initiative}
                onClick={toggleInitiative}
              />
              <Toggle
                label="Nachts nacharbeiten"
                hint="Jon fasst den vergangenen Tag zusammen, merkt sich dauerhafte Fakten, klärt Widersprüche und vergisst Unwichtiges."
                on={konsolidierung}
                onClick={toggleKonsolidierung}
              />
              <Toggle
                label="Dauerhaft wahrnehmen"
                hint="Jon merkt sich im Hintergrund, welches Fenster vorne ist und ob neue Mails oder Geräte dazukommen. Alles bleibt lokal."
                on={wahrnehmung}
                onClick={toggleWahrnehmung}
              />
              <Toggle
                label="Selbstprüfung vor der Antwort"
                hint="Bei unsicheren Antworten prüft Jon sich selbst und sagt dir, woran er zweifelt. Kostet einen zusätzlichen Modellaufruf."
                on={kritiker}
                onClick={toggleKritiker}
              />
              <Toggle
                label="Vorher sagen, was er erwartet"
                hint="Vor jedem Werkzeug schätzt Jon, wie sicher es klappt, und vergleicht es danach mit dem Ergebnis. Aus den Überraschungen lernt er. Läuft lokal und kostet nichts."
                on={erwartung}
                onClick={toggleErwartung}
              />
              <Toggle
                label="Aufwand selbst einteilen"
                hint="Jon schätzt vor der Antwort ein, wie schwer die Sache ist, und holt bei schweren Fragen mehr Hintergrund heran als bei einem kurzen Zuruf."
                on={metakognition}
                onClick={toggleMetakognition}
              />
              <Toggle
                label="Offene Fragen sammeln"
                hint="Wenn Jon etwas nicht weiß, merkt er sich die Frage, statt zu raten. Du siehst sie unter Denken → Offen."
                on={neugier}
                onClick={toggleNeugier}
              />
              <Toggle
                label="Offene Fragen nachts klären"
                hint="Jon sucht selbst nach Antworten auf seine offenen Fragen und legt sie ins Gedächtnis. Braucht Internet und kostet Modellaufrufe."
                on={neugierAuto}
                onClick={toggleNeugierAuto}
              />
              <Toggle
                label="Abläufe selbst zu Fertigkeiten machen"
                hint="Wiederholst du denselben Ablauf oft, merkt Jon ihn sich als einen Handgriff und macht ihn künftig in einem Rutsch."
                on={fertigkeitAuto}
                onClick={toggleFertigkeitAuto}
              />
              <div className="text-[10px] text-white/40 px-0.5 pt-1">
                Persönliche Daten nach außen
              </div>
              <Segmented
                value={datenschutz}
                items={[
                  {
                    value: "warnen",
                    label: "Warnen",
                    hint: "Zugangsdaten werden blockiert, bei persönlichen Angaben sagt Jon Bescheid.",
                  },
                  {
                    value: "streng",
                    label: "Streng",
                    hint: "Auch persönliche Angaben (Mail, Telefon, Adresse) verlassen den PC nicht.",
                  },
                  {
                    value: "erlauben",
                    label: "Locker",
                    hint: "Nur ein Hinweis, keine Sperre. Zugangsdaten bleiben trotzdem heikel.",
                  },
                ]}
                onPick={pickDatenschutz}
              />
              <div className="flex items-center justify-between gap-2 px-2 py-1 rounded-lg border border-white/10 bg-white/5">
                <span className="text-[11px] text-white/85">Tokens je Tag (0 = frei)</span>
                <input
                  type="number"
                  min={0}
                  step={1000}
                  value={budgetTokens}
                  onChange={(e) => {
                    const wert = Math.max(0, Number(e.target.value) || 0);
                    setBudgetTokens(wert);
                    void saveUserSettings({ budget_tokens_tag: wert });
                  }}
                  className="w-24 bg-black/30 border border-white/10 rounded-md px-2 py-0.5 text-[11px] text-white/85 text-right"
                />
              </div>
              <div className="flex items-center justify-between gap-2 px-2 py-1 rounded-lg border border-white/10 bg-white/5">
                <span className="text-[11px] text-white/85">Euro je Monat (0 = frei)</span>
                <input
                  type="number"
                  min={0}
                  step={1}
                  value={budgetEuro}
                  onChange={(e) => {
                    const wert = Math.max(0, Number(e.target.value) || 0);
                    setBudgetEuro(wert);
                    void saveUserSettings({ budget_euro_monat: wert });
                  }}
                  className="w-24 bg-black/30 border border-white/10 rounded-md px-2 py-0.5 text-[11px] text-white/85 text-right"
                />
              </div>
              <div className="text-[10px] text-white/40 px-0.5 leading-relaxed">
                Ziele, Rückblick, Vorschläge und Jons Selbstbild siehst du mit /denken.
              </div>
            </div>
            <Section title="Sprache / Language" />
            <div className="pt-1">
              <div className="text-[10px] text-white/40 px-0.5 mb-1">
                UI & Chat Sprache
              </div>
              <select
                value={lang}
                onChange={(e) => {
                  const next = e.target.value;
                  setLang(next);
                  void saveUserSettings({ language: next });
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
                Mikrofon
              </div>
              <select
                value={selectedMic}
                onChange={(e) => pickMicrophone(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-[11px] text-white/90 outline-none focus:border-gold/50 [&>option]:bg-zinc-900 mb-2"
              >
                <option value="default">Standard (PC-Auswahl)</option>
                {micList.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
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
            <Section title="Mini Jon" />
            <div className="space-y-1">
              <Toggle
                label="Frei über den Bildschirm"
                hint="Mini Jon wandert am unteren Rand herum statt fest in der Ecke zu stehen. Schläft, wenn du weg bist."
                on={petRoam}
                onClick={togglePetRoam}
              />
              <Toggle
                label="Trink- & Steh-Erinnerungen"
                hint="Mini Jon erinnert dich alle 90 Minuten sanft ans Trinken, Aufstehen und Durchatmen."
                on={petWellness}
                onClick={togglePetWellness}
              />
              <div className="text-[9.5px] text-white/35 px-0.5 pt-1 leading-snug">
                Aussehen und Haustier stellst du in „Mini Jon anpassen“ ein — Klick auf
                Mini Jon, dann auf das Pinsel-Symbol.
              </div>
            </div>
            <Section title="Tagesbriefing" />
            <input
              value={city}
              onChange={(e) => saveCity(e.target.value)}
              placeholder="Stadt (für das Wetter)"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-[11px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50"
            />
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
              onClick={() => {
                setOpen(false);
                setDiagnoseOpen(true);
              }}
              title="Zeigt Version, laufende Hintergrunddienste, Fehler und die Adresse zum Koppeln des Handys."
              className="w-full flex items-center justify-between gap-2 px-2 py-1.5 mt-2 rounded-lg border border-white/15 bg-white/[0.04] hover:bg-white/10 transition-colors"
            >
              <span className="text-[11px] text-white/80">Diagnose & Handy koppeln …</span>
              <span className="text-white/50 text-[12px]">›</span>
            </button>
            <button
              onClick={() => {
                setOpen(false);
                setHandyOpen(true);
              }}
              title="Zeigt einen QR-Code. Die Jon-App am Handy scannt ihn und verbindet sich - auch von unterwegs."
              className="w-full flex items-center justify-between gap-2 px-2 py-1.5 mt-2 rounded-lg border border-white/15 bg-white/[0.04] hover:bg-white/10 transition-colors"
            >
              <span className="text-[11px] text-white/80">Handy verbinden …</span>
              <span className="text-white/50 text-[12px]">›</span>
            </button>
            <button
              onClick={() => void openConnections()}
              className="w-full flex items-center justify-between gap-2 px-2 py-1.5 mt-2 rounded-lg border border-gold/30 bg-gold/10 hover:bg-gold/20 transition-colors"
            >
              <span className="text-[11px] text-gold/90">
                🔌 Verbindungen …
              </span>
              <span className="text-gold/70 text-[12px]">›</span>
            </button>
            <button
              onClick={() => {
                setOpen(false);
                setUninstallOpen(true);
              }}
              title="Löscht alle Daten von Jon und entfernt das Programm."
              className="w-full flex items-center justify-between gap-2 px-2 py-1.5 mt-2 rounded-lg border border-red-500/30 bg-red-500/5 hover:bg-red-500/15 transition-colors"
            >
              <span className="text-[11px] text-red-300/90">
                🗑️ Jon deinstallieren …
              </span>
              <span className="text-red-300/60 text-[12px]">›</span>
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
      {uninstallOpen && (
        <UninstallModal onClose={() => setUninstallOpen(false)} />
      )}
      {diagnoseOpen && (
        <DiagnosticsModal onClose={() => setDiagnoseOpen(false)} />
      )}
      {handyOpen && <HandyModal onClose={() => setHandyOpen(false)} />}
      {ollamaOpen && (
        <OllamaModal
          onClose={() => {
            setOllamaOpen(false);
            void loadOllama();
          }}
        />
      )}
    </div>
  );
}
