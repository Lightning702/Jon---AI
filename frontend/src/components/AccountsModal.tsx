import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Account,
  Reminder,
  SkillSummary,
  UserSettings,
  UsageEntry,
  addReminder,
  connectAccount,
  deleteReminder,
  deleteSkill,
  disconnectAccount,
  getAccounts,
  getReminders,
  getSkill,
  getSkills,
  getUsage,
  getUserSettings,
  resetUsage,
  saveSkill,
  saveUserSettings,
  setAccountModel,
} from "../lib/api";

type Tab =
  | "commands"
  | "accounts"
  | "usage"
  | "skills"
  | "prompt"
  | "reminders";

const TAB_LABELS: Record<Tab, string> = {
  commands: "Befehle",
  accounts: "Konten",
  usage: "Nutzung",
  skills: "Skills",
  prompt: "Prompt",
  reminders: "Erinnerungen",
};

const TAB_ORDER: Tab[] = [
  "commands",
  "accounts",
  "usage",
  "skills",
  "prompt",
  "reminders",
];

export default function AccountsModal({
  onClose,
  initialTab = "accounts",
}: {
  onClose: () => void;
  initialTab?: Tab;
}) {
  const [tab, setTab] = useState<Tab>(initialTab);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.18 }}
        className="glass rounded-2xl border border-white/15 w-[94%] max-w-2xl max-h-[85vh] overflow-hidden flex flex-col"
      >
        <div className="flex items-center justify-between px-5 h-14 border-b border-white/10">
          <div className="flex gap-1 flex-wrap">
            {TAB_ORDER.map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-3 py-1.5 rounded-lg text-[13px] transition ${
                  tab === t
                    ? "bg-gold/15 text-gold"
                    : "text-white/50 hover:text-white/80"
                }`}
              >
                {TAB_LABELS[t]}
              </button>
            ))}
          </div>
          <button
            onClick={onClose}
            className="text-white/40 hover:text-white/80 text-xl leading-none"
          >
            ×
          </button>
        </div>
        <div className="overflow-y-auto px-5 py-4">
          {tab === "commands" && <CommandsTab />}
          {tab === "accounts" && <AccountsTab />}
          {tab === "usage" && <UsageTab />}
          {tab === "skills" && <SkillsTab />}
          {tab === "prompt" && <PromptTab />}
          {tab === "reminders" && <RemindersTab />}
        </div>
      </motion.div>
    </div>
  );
}

const SLASH_COMMANDS: { cmd: string; desc: string }[] = [
  { cmd: "/briefing", desc: "Tagesbriefing: Datum, Wetter, Erinnerungen, Wecker." },
  { cmd: "/team <Thema>", desc: "Dein KI-Team (Entwickler, Design, Marketing, Jurist, CEO) diskutiert und gibt eine Empfehlung." },
  { cmd: "/simulate <Was wäre wenn …>", desc: "Jon spielt mehrere Szenarien mit Wahrscheinlichkeiten und Fazit durch." },
  { cmd: "/snapshot <Name>", desc: "Zeitreise: aktuellen Stand als Snapshot sichern." },
  { cmd: "/snapshots", desc: "Alle gespeicherten Zeitreise-Snapshots anzeigen." },
  { cmd: "/dream <Aufgabe>", desc: "Aufgabe anlegen, die Jon im Hintergrund ausarbeitet." },
  { cmd: "/dreams", desc: "Offene Dream-Aufgaben jetzt ausführen und Ergebnisse zeigen." },
  { cmd: "/export", desc: "Die aktuelle Unterhaltung als Markdown-Datei speichern." },
  { cmd: "/konten", desc: "Konten & API-Keys verwalten (auch /login, /accounts)." },
  { cmd: "/usage", desc: "Token-Nutzung pro Anbieter (auch /nutzung)." },
  { cmd: "/skills", desc: "Skills (Anleitungen) ansehen und bearbeiten." },
];

const SHORTCUTS: { keys: string; desc: string }[] = [
  { keys: "Strg + Alt + J", desc: "Jon-Fenster von überall öffnen oder verstecken." },
  { keys: "Strg + Alt + K", desc: "Kleiner Jon (Desktop-Begleiter) ein- oder ausblenden." },
  { keys: "Enter", desc: "Nachricht senden." },
];

const ABILITIES: { icon: string; title: string; example: string }[] = [
  { icon: "🖥️", title: "PC steuern", example: "„Öffne YouTube und suche nach Lofi.“" },
  { icon: "⏰", title: "Wecker & Timer", example: "„Stell einen Wecker für 7:00.“" },
  { icon: "🔔", title: "Erinnerungen", example: "„Erinnere mich täglich um 13 Uhr ans Trinken.“" },
  { icon: "🔍", title: "Web-Suche", example: "„Such die aktuellen Nachrichten zu …“" },
  { icon: "🌤️", title: "Wetter", example: "„Wie wird das Wetter morgen in Wien?“" },
  { icon: "📄", title: "PDF lesen", example: "„Fass mir diese PDF zusammen: C:\\…“" },
  { icon: "🖱️", title: "Maus & Tastatur", example: "„Schreib das in WhatsApp an Mama.“" },
  { icon: "📸", title: "Screenshot & Bildschirm", example: "„Mach einen Screenshot und schau, was falsch ist.“" },
  { icon: "🧠", title: "Gedächtnis", example: "„Merk dir, dass ich Rechtsanwalt bin.“" },
  { icon: "🗂️", title: "Dateien", example: "„Räum meinen Download-Ordner auf.“" },
  { icon: "💻", title: "Programmieren (Jon Code)", example: "Über den „Code“-Knopf oben." },
  { icon: "🙂", title: "Kleiner Jon", example: "Klick ihn an und rede direkt mit ihm." },
];

function CommandsTab() {
  return (
    <div className="space-y-5">
      <p className="text-[12px] text-white/45">
        Alles, was du mit Jon machen kannst. Slash-Befehle tippst du direkt ins
        Nachrichtenfeld. Für den Rest sag Jon einfach in normalen Worten, was du
        willst.
      </p>

      <div>
        <h3 className="text-[13px] font-semibold text-gold mb-2">Slash-Befehle</h3>
        <div className="space-y-1.5">
          {SLASH_COMMANDS.map((c) => (
            <div
              key={c.cmd}
              className="flex flex-col gap-0.5 px-3 py-2 rounded-lg bg-white/5 border border-white/10"
            >
              <code className="text-[12.5px] text-gold/90">{c.cmd}</code>
              <span className="text-[12px] text-white/60">{c.desc}</span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-[13px] font-semibold text-gold mb-2">Tastenkürzel</h3>
        <div className="space-y-1.5">
          {SHORTCUTS.map((s) => (
            <div
              key={s.keys}
              className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/5 border border-white/10"
            >
              <span className="text-[12px] font-semibold text-white/85 whitespace-nowrap">
                {s.keys}
              </span>
              <span className="text-[12px] text-white/60">{s.desc}</span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-[13px] font-semibold text-gold mb-2">
          Das kannst du Jon einfach sagen
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
          {ABILITIES.map((a) => (
            <div
              key={a.title}
              className="flex gap-2.5 px-3 py-2 rounded-lg bg-white/5 border border-white/10"
            >
              <span className="text-[16px] leading-none mt-0.5">{a.icon}</span>
              <div className="min-w-0">
                <div className="text-[12.5px] text-white/85">{a.title}</div>
                <div className="text-[11.5px] text-white/45 italic truncate">
                  {a.example}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-[13px] font-semibold text-gold mb-2">Sprachsteuerung</h3>
        <p className="text-[12px] text-white/60 px-3 py-2 rounded-lg bg-white/5 border border-white/10">
          Aktiviere das Mikrofon oben rechts und sag „Jon“, gefolgt von deinem
          Auftrag. Jon antwortet dir dann laut vorgelesen.
        </p>
      </div>
    </div>
  );
}

function AccountsTab() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [keys, setKeys] = useState<Record<string, string>>({});

  const refresh = async () => {
    setAccounts(await getAccounts());
    setLoading(false);
  };
  useEffect(() => {
    void refresh();
  }, []);

  if (loading) return <div className="text-white/40 text-sm">Lade …</div>;

  return (
    <div className="space-y-3">
      <p className="text-[12px] text-white/45">
        Verbinde dein Konto über den offiziellen API-Schlüssel des Anbieters. Jon nutzt
        dann deinen Zugang und erkennt automatisch alle verfügbaren Modelle. Tarif und
        Profil werden von den offiziellen APIs nicht bereitgestellt und daher nicht
        erfunden.
      </p>
      {accounts.map((a) => {
        const isLocal = a.auth === "local";
        return (
          <div
            key={a.provider}
            className="rounded-xl border border-white/10 bg-white/5 px-4 py-3"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full ${
                    a.connected ? "bg-emerald-400" : "bg-white/25"
                  }`}
                />
                <span className="text-[14px] text-white/90">{a.label}</span>
                {a.source && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-white/50">
                    {a.source === "account"
                      ? "Konto"
                      : a.source === "local"
                      ? "lokal"
                      : ".env"}
                  </span>
                )}
                {isLocal && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-400/10 text-emerald-300/80">
                    gratis
                  </span>
                )}
              </div>
              <a
                href={a.docs}
                target="_blank"
                rel="noreferrer"
                className="text-[11px] text-gold/70 hover:text-gold"
              >
                {isLocal ? "Installieren ↗" : "Schlüssel holen ↗"}
              </a>
            </div>

            {isLocal ? (
              <div className="mt-2 text-[12px]">
                {a.connected ? (
                  <span className="text-emerald-300/80">
                    Läuft lokal — {a.models.length} Modelle installiert
                  </span>
                ) : (
                  <span className="text-white/45">
                    Nicht erreichbar. Starte {a.label.split(" ")[0]} auf deinem PC — kein
                    API-Key, keine Kosten.
                  </span>
                )}
              </div>
            ) : (
              <div className="mt-2 flex gap-2">
                <input
                  type="password"
                  placeholder={
                    a.connected
                      ? "Neuen Schlüssel eingeben (optional)"
                      : "API-Schlüssel"
                  }
                  value={keys[a.provider] ?? ""}
                  onChange={(e) =>
                    setKeys((k) => ({ ...k, [a.provider]: e.target.value }))
                  }
                  className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-1.5 text-[12px] text-white/90 outline-none focus:border-gold/40"
                />
                <button
                  onClick={async () => {
                    const key = keys[a.provider];
                    if (!key) return;
                    await connectAccount(a.provider, key);
                    setKeys((k) => ({ ...k, [a.provider]: "" }));
                    await refresh();
                  }}
                  className="px-3 py-1.5 rounded-lg bg-gold/80 hover:bg-gold text-black text-[12px] font-medium"
                >
                  Verbinden
                </button>
                {a.source === "account" && (
                  <button
                    onClick={async () => {
                      await disconnectAccount(a.provider);
                      await refresh();
                    }}
                    className="px-3 py-1.5 rounded-lg border border-white/15 text-white/60 text-[12px] hover:bg-white/5"
                  >
                    Trennen
                  </button>
                )}
              </div>
            )}

            {a.connected && (
              <div className="mt-2 flex items-center gap-2">
                <span className="text-[11px] text-white/40">Standardmodell</span>
                <select
                  value={a.default_model ?? ""}
                  onChange={async (e) => {
                    await setAccountModel(a.provider, e.target.value);
                    await refresh();
                  }}
                  className="flex-1 bg-black/30 border border-white/10 rounded-lg px-2 py-1 text-[12px] text-white/85 outline-none"
                >
                  <option value="">automatisch</option>
                  {a.models.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {a.connected && (
              <div className="mt-1.5 text-[10.5px] text-white/35">
                {a.models.length} Modelle erkannt · Tarif: {a.plan}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function UsageTab() {
  const [usage, setUsage] = useState<Record<string, UsageEntry>>({});
  const [loaded, setLoaded] = useState(false);

  const refresh = async () => {
    setUsage(await getUsage());
    setLoaded(true);
  };
  useEffect(() => {
    void refresh();
  }, []);

  const entries = Object.entries(usage);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-[12px] text-white/45">
          Lokal gemessene Nutzung aus den offiziellen API-Antworten. Kosten und
          Rate-Limits liefern die meisten APIs nicht direkt.
        </p>
        <button
          onClick={async () => {
            await resetUsage();
            await refresh();
          }}
          className="text-[11px] text-white/40 hover:text-white/70 shrink-0 ml-3"
        >
          Zurücksetzen
        </button>
      </div>
      {loaded && entries.length === 0 && (
        <div className="text-white/40 text-sm">Noch keine Nutzung erfasst.</div>
      )}
      {entries.map(([provider, u]) => (
        <div
          key={provider}
          className="rounded-xl border border-white/10 bg-white/5 px-4 py-3"
        >
          <div className="text-[13px] text-gold mb-1.5">{provider}</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[12px]">
            <Stat label="Prompt-Tokens" value={u.prompt_tokens.toLocaleString()} />
            <Stat label="Completion-Tokens" value={u.completion_tokens.toLocaleString()} />
            <Stat label="Gesamt-Tokens" value={u.total_tokens.toLocaleString()} />
            <Stat label="Anfragen" value={String(u.requests)} />
            <Stat label="Ø Antwortzeit" value={`${u.avg_latency}s`} />
            <Stat label="Letztes Modell" value={u.last_model ?? "—"} />
          </div>
          {u.last_request && (
            <div className="mt-1.5 text-[10.5px] text-white/35">
              Letzte Anfrage: {new Date(u.last_request).toLocaleString()}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-white/45">{label}</span>
      <span className="text-white/85 truncate">{value}</span>
    </div>
  );
}

function SkillsTab() {
  const [skills, setSkills] = useState<SkillSummary[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [saved, setSaved] = useState(false);
  const [newName, setNewName] = useState("");

  const refresh = async () => setSkills(await getSkills());
  useEffect(() => {
    void refresh();
  }, []);

  const open = async (name: string) => {
    setActive(name);
    setSaved(false);
    const skill = await getSkill(name);
    setContent(skill.content);
  };

  const createNew = async () => {
    const slug = newName
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9_-]+/g, "-")
      .replace(/^-+|-+$/g, "");
    if (!slug) return;
    const template = `# ${slug}\n\nBeschreibe hier, wann Jon diesen Skill nutzen soll.\n\n## Vorgehen\n1. \n2. \n\n## Regeln\n- \n`;
    await saveSkill(slug, template);
    setNewName("");
    await refresh();
    await open(slug);
  };

  return (
    <div className="space-y-3">
      <p className="text-[12px] text-white/45">
        Skills sind bearbeitbare Anleitungen. Jon liest sie, bevor er passende Aufgaben
        startet. Du findest sie auch als Dateien im Ordner <code>skills/</code> der
        entpackten ZIP.
      </p>
      <div className="flex gap-2">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && createNew()}
          placeholder="Neuer Skill-Name (z. B. mein-workflow)"
          className="flex-1 bg-black/30 border border-white/10 rounded-lg px-3 py-1.5 text-[12px] text-white/90 outline-none focus:border-gold/40"
        />
        <button
          onClick={createNew}
          className="px-3 py-1.5 rounded-lg bg-gold/80 hover:bg-gold text-black text-[12px] font-medium"
        >
          + Neu
        </button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {skills.map((s) => (
          <button
            key={s.name}
            onClick={() => open(s.name)}
            className={`text-[12px] px-2.5 py-1 rounded-lg border transition ${
              active === s.name
                ? "bg-gold/15 border-gold/40 text-gold"
                : "border-white/10 bg-white/5 text-white/70 hover:bg-white/10"
            }`}
          >
            {s.name}
          </button>
        ))}
      </div>
      {active && (
        <div className="space-y-2">
          <textarea
            value={content}
            onChange={(e) => {
              setContent(e.target.value);
              setSaved(false);
            }}
            rows={14}
            className="w-full bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-[12px] font-mono text-white/85 outline-none focus:border-gold/40"
          />
          <div className="flex items-center gap-2">
            <button
              onClick={async () => {
                await saveSkill(active, content);
                setSaved(true);
                await refresh();
              }}
              className="px-3 py-1.5 rounded-lg bg-gold/80 hover:bg-gold text-black text-[12px] font-medium"
            >
              Speichern
            </button>
            <button
              onClick={async () => {
                await deleteSkill(active);
                setActive(null);
                setContent("");
                await refresh();
              }}
              className="px-3 py-1.5 rounded-lg border border-white/15 text-white/60 text-[12px] hover:bg-white/5"
            >
              Löschen
            </button>
            {saved && <span className="text-[11px] text-emerald-400">Gespeichert ✓</span>}
          </div>
        </div>
      )}
    </div>
  );
}

function PromptTab() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    void getUserSettings().then(setSettings);
  }, []);

  if (!settings) return <div className="text-white/40 text-sm">Lade …</div>;

  return (
    <div className="space-y-3">
      <p className="text-[12px] text-white/45">
        Gib Jon eine eigene Persönlichkeit oder feste Anweisungen. „Ergänzen" fügt dein
        Prompt zu Jons Standard hinzu, „Ersetzen" nutzt nur deins.
      </p>
      <div className="flex gap-1.5">
        {(["append", "replace"] as const).map((m) => (
          <button
            key={m}
            onClick={() => {
              setSettings({ ...settings, prompt_mode: m });
              setSaved(false);
            }}
            className={`text-[12px] px-3 py-1 rounded-lg border transition ${
              settings.prompt_mode === m
                ? "bg-gold/15 border-gold/40 text-gold"
                : "border-white/10 bg-white/5 text-white/70 hover:bg-white/10"
            }`}
          >
            {m === "append" ? "Ergänzen" : "Ersetzen"}
          </button>
        ))}
      </div>
      <textarea
        value={settings.custom_prompt}
        onChange={(e) => {
          setSettings({ ...settings, custom_prompt: e.target.value });
          setSaved(false);
        }}
        rows={12}
        placeholder="z. B. Antworte immer locker und mit Humor. Nenne mich beim Vornamen."
        className="w-full bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-[13px] text-white/85 outline-none focus:border-gold/40"
      />
      <div className="flex items-center gap-2">
        <button
          onClick={async () => {
            await saveUserSettings({
              custom_prompt: settings.custom_prompt,
              prompt_mode: settings.prompt_mode,
            });
            setSaved(true);
          }}
          className="px-3 py-1.5 rounded-lg bg-gold/80 hover:bg-gold text-black text-[12px] font-medium"
        >
          Speichern
        </button>
        {saved && <span className="text-[11px] text-emerald-400">Gespeichert ✓</span>}
      </div>
    </div>
  );
}

function RemindersTab() {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [text, setText] = useState("");
  const [time, setTime] = useState("13:00");
  const [repeat, setRepeat] = useState("daily");

  const refresh = async () => setReminders(await getReminders());
  useEffect(() => {
    void refresh();
  }, []);

  return (
    <div className="space-y-3">
      <p className="text-[12px] text-white/45">
        Jon erinnert dich, sobald die Zeit erreicht ist und die App offen ist (oder beim
        nächsten Öffnen danach). Du kannst Erinnerungen auch einfach im Chat anlegen: „Erinnere
        mich jeden Tag um 13 Uhr ans Wassertrinken."
      </p>
      <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 space-y-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Woran soll Jon dich erinnern?"
          className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-1.5 text-[12px] text-white/90 outline-none focus:border-gold/40"
        />
        <div className="flex gap-2">
          <input
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
            className="bg-black/30 border border-white/10 rounded-lg px-3 py-1.5 text-[12px] text-white/90 outline-none"
          />
          <select
            value={repeat}
            onChange={(e) => setRepeat(e.target.value)}
            className="bg-black/30 border border-white/10 rounded-lg px-2 py-1.5 text-[12px] text-white/85 outline-none"
          >
            <option value="daily">täglich</option>
            <option value="once">einmal</option>
          </select>
          <button
            onClick={async () => {
              if (!text.trim()) return;
              await addReminder(text.trim(), time, repeat);
              setText("");
              await refresh();
            }}
            className="flex-1 px-3 py-1.5 rounded-lg bg-gold/80 hover:bg-gold text-black text-[12px] font-medium"
          >
            Hinzufügen
          </button>
        </div>
      </div>
      {reminders.length === 0 && (
        <div className="text-white/40 text-sm">Keine Erinnerungen.</div>
      )}
      {reminders.map((r) => (
        <div
          key={r.id}
          className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-4 py-2.5"
        >
          <div>
            <div className="text-[13px] text-white/90">{r.text}</div>
            <div className="text-[11px] text-white/40">
              {r.time} · {r.repeat === "daily" ? "täglich" : "einmal"}
              {r.active ? "" : " · erledigt"}
            </div>
          </div>
          <button
            onClick={async () => {
              await deleteReminder(r.id);
              await refresh();
            }}
            className="text-white/40 hover:text-red-300 text-lg leading-none"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
