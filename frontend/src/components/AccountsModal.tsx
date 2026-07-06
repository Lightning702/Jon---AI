import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Account,
  SkillSummary,
  UsageEntry,
  connectAccount,
  disconnectAccount,
  getAccounts,
  getSkill,
  getSkills,
  getUsage,
  resetUsage,
  saveSkill,
  setAccountModel,
} from "../lib/api";

type Tab = "accounts" | "usage" | "skills";

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
          <div className="flex gap-1">
            {(["accounts", "usage", "skills"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-3 py-1.5 rounded-lg text-[13px] transition ${
                  tab === t
                    ? "bg-gold/15 text-gold"
                    : "text-white/50 hover:text-white/80"
                }`}
              >
                {t === "accounts" ? "Konten" : t === "usage" ? "Nutzung" : "Skills"}
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
          {tab === "accounts" && <AccountsTab />}
          {tab === "usage" && <UsageTab />}
          {tab === "skills" && <SkillsTab />}
        </div>
      </motion.div>
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
      {accounts.map((a) => (
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
                  {a.source === "account" ? "Konto" : ".env"}
                </span>
              )}
            </div>
            <a
              href={a.docs}
              target="_blank"
              rel="noreferrer"
              className="text-[11px] text-gold/70 hover:text-gold"
            >
              Schlüssel holen ↗
            </a>
          </div>

          <div className="mt-2 flex gap-2">
            <input
              type="password"
              placeholder={
                a.connected ? "Neuen Schlüssel eingeben (optional)" : "API-Schlüssel"
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
      ))}
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

  useEffect(() => {
    void getSkills().then(setSkills);
  }, []);

  const open = async (name: string) => {
    setActive(name);
    setSaved(false);
    const skill = await getSkill(name);
    setContent(skill.content);
  };

  return (
    <div className="space-y-3">
      <p className="text-[12px] text-white/45">
        Skills sind bearbeitbare Anleitungen. Jon liest sie, bevor er passende Aufgaben
        startet. Du findest sie auch als Dateien im Ordner <code>skills/</code> der
        entpackten ZIP.
      </p>
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
                setSkills(await getSkills());
              }}
              className="px-3 py-1.5 rounded-lg bg-gold/80 hover:bg-gold text-black text-[12px] font-medium"
            >
              Speichern
            </button>
            {saved && <span className="text-[11px] text-emerald-400">Gespeichert ✓</span>}
          </div>
        </div>
      )}
    </div>
  );
}
