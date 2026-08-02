import { useEffect, useRef, useState } from "react";
import {
  OllamaInvite,
  OllamaRemote,
  OllamaShare,
  OllamaShareUser,
  ShareVisibility,
  connectOllamaRemote,
  createOllamaInvite,
  deleteOllamaInvite,
  forgetOllamaRemote,
  getOllamaRemotes,
  getOllamaShare,
  newOllamaShareCode,
  refreshOllamaRemote,
  removeOllamaShareUser,
  revokeOllamaShare,
  saveOllamaShare,
} from "../lib/api";

const field =
  "w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-[12px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50";
const label = "text-[11px] text-white/45 px-0.5";
const section = "text-[11px] uppercase tracking-wide text-gold/70";
const chip =
  "text-[11px] px-2 py-1 rounded-lg border border-white/10 bg-white/5 text-white/65 hover:bg-white/10 transition disabled:opacity-40";

const VISIBILITIES: { value: ShareVisibility; text: string; hint: string }[] = [
  {
    value: "private",
    text: "Privat",
    hint: "Niemand kann sich verbinden. Bestehende Zugänge bleiben, bis du sie widerrufst.",
  },
  {
    value: "invited",
    text: "Nur Eingeladene",
    hint: "Nur wer eine persönliche Einladung von dir hat, kommt herein.",
  },
  {
    value: "public",
    text: "Öffentlich",
    hint: "Jeder mit deinem Freigabecode darf sich verbinden.",
  },
];

function Switch({
  text,
  hint,
  on,
  onClick,
}: {
  text: string;
  hint: string;
  on: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      title={hint}
      className="w-full flex items-center justify-between gap-3 px-3 py-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 transition-colors text-left"
    >
      <span className="text-[12px] text-white/90">{text}</span>
      <span
        className={`w-9 h-5 shrink-0 rounded-full flex items-center px-0.5 transition-colors ${
          on ? "bg-gold/70" : "bg-white/15"
        }`}
      >
        <span
          className={`w-4 h-4 rounded-full bg-white transition-transform ${
            on ? "translate-x-4" : ""
          }`}
        />
      </span>
    </button>
  );
}

function moment(value: string): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function OllamaSharePanel({
  onModelsChanged,
}: {
  onModelsChanged?: () => void;
}) {
  const [share, setShare] = useState<OllamaShare | null>(null);
  const [users, setUsers] = useState<OllamaShareUser[]>([]);
  const [remotes, setRemotes] = useState<OllamaRemote[]>([]);
  const [inviteLabel, setInviteLabel] = useState("");
  const [freshInvite, setFreshInvite] = useState<OllamaInvite | null>(null);
  const [joinCode, setJoinCode] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const alive = useRef(true);

  const load = async () => {
    try {
      const data = await getOllamaShare();
      if (!alive.current) return;
      setShare(data.share);
      setUsers(data.users);
    } catch (err) {
      if (alive.current) setError(err instanceof Error ? err.message : String(err));
    }
    const list = await getOllamaRemotes();
    if (alive.current) setRemotes(list);
  };

  useEffect(() => {
    alive.current = true;
    void load();
    const timer = window.setInterval(() => void load(), 15000);
    return () => {
      alive.current = false;
      window.clearInterval(timer);
    };
  }, []);

  const say = (text: string) => {
    setError("");
    setNote(text);
    window.setTimeout(() => alive.current && setNote(""), 3000);
  };

  const fail = (err: unknown) => {
    setNote("");
    setError(err instanceof Error ? err.message : String(err));
  };

  const patch = async (values: Partial<OllamaShare>) => {
    setBusy(true);
    try {
      const next = await saveOllamaShare(values);
      if (!alive.current) return;
      setShare(next);
      say("Gespeichert ✓");
    } catch (err) {
      fail(err);
    } finally {
      if (alive.current) setBusy(false);
    }
  };

  const copy = async (text: string, what: string) => {
    try {
      await navigator.clipboard.writeText(text);
      say(`${what} kopiert ✓`);
    } catch {
      say(text);
    }
  };

  const rollCode = async () => {
    setBusy(true);
    try {
      setShare(await newOllamaShareCode());
      say("Neuer Freigabecode erzeugt — der alte gilt nicht mehr");
    } catch (err) {
      fail(err);
    } finally {
      if (alive.current) setBusy(false);
    }
  };

  const invite = async () => {
    setBusy(true);
    try {
      const created = await createOllamaInvite(inviteLabel);
      if (!alive.current) return;
      setFreshInvite(created);
      setInviteLabel("");
      await load();
      say("Einladung erstellt");
    } catch (err) {
      fail(err);
    } finally {
      if (alive.current) setBusy(false);
    }
  };

  const dropInvite = async (code: string) => {
    await deleteOllamaInvite(code);
    if (freshInvite?.code === code) setFreshInvite(null);
    await load();
  };

  const kick = async (id: string, name: string) => {
    setBusy(true);
    try {
      await removeOllamaShareUser(id);
      await load();
      say(`${name} hat keinen Zugriff mehr`);
    } finally {
      if (alive.current) setBusy(false);
    }
  };

  const revokeAll = async () => {
    setBusy(true);
    try {
      const count = await revokeOllamaShare();
      await load();
      say(
        count > 0
          ? `Zugriff für ${count} Benutzer widerrufen`
          : "Es war niemand verbunden"
      );
    } finally {
      if (alive.current) setBusy(false);
    }
  };

  const join = async () => {
    const code = joinCode.trim();
    if (!code) return;
    setBusy(true);
    try {
      const entry = await connectOllamaRemote(code);
      if (!alive.current) return;
      setJoinCode("");
      await load();
      onModelsChanged?.();
      say(`Verbunden mit ${entry.name}`);
    } catch (err) {
      fail(err);
    } finally {
      if (alive.current) setBusy(false);
    }
  };

  const refreshRemote = async (code: string) => {
    setBusy(true);
    try {
      const entry = await refreshOllamaRemote(code);
      await load();
      onModelsChanged?.();
      say(`${entry.models.length} Modelle von ${entry.name}`);
    } catch (err) {
      fail(err);
    } finally {
      if (alive.current) setBusy(false);
    }
  };

  const forget = async (code: string) => {
    setBusy(true);
    try {
      await forgetOllamaRemote(code);
      await load();
      onModelsChanged?.();
      say("Verbindung getrennt");
    } finally {
      if (alive.current) setBusy(false);
    }
  };

  if (!share) return null;

  return (
    <>
      <section className="space-y-2">
        <div className={section}>Serverfreigabe</div>
        <Switch
          text="Meinen Ollama-Server freigeben"
          hint="Andere Jon-Benutzer dürfen dann über deinen Server antworten lassen. Sie bekommen keinen Zugriff auf deinen PC."
          on={share.enabled}
          onClick={() => void patch({ enabled: !share.enabled })}
        />
        {share.enabled && (
          <>
            <div>
              <div className={label}>Freigabename</div>
              <input
                className={field}
                placeholder={`Ollama von ${share.owner || "mir"}`}
                value={share.name}
                onChange={(e) => setShare({ ...share, name: e.target.value })}
                onBlur={() => void patch({ name: share.name })}
              />
            </div>
            <div>
              <div className={label}>Beschreibung</div>
              <input
                className={field}
                placeholder="z. B. RTX 4090, llama3.3 und qwen2.5-coder"
                value={share.description}
                onChange={(e) =>
                  setShare({ ...share, description: e.target.value })
                }
                onBlur={() => void patch({ description: share.description })}
              />
            </div>
            <div>
              <div className={label}>Sichtbarkeit</div>
              <div className="flex gap-1">
                {VISIBILITIES.map((item) => (
                  <button
                    key={item.value}
                    title={item.hint}
                    onClick={() => void patch({ visibility: item.value })}
                    className={`flex-1 text-[11px] py-1.5 rounded-lg border transition-colors ${
                      share.visibility === item.value
                        ? "border-gold/40 bg-gold/15 text-gold"
                        : "border-white/10 bg-white/5 text-white/50 hover:bg-white/10"
                    }`}
                  >
                    {item.text}
                  </button>
                ))}
              </div>
              <div className="text-[10.5px] text-white/40 px-0.5 mt-1 leading-snug">
                {VISIBILITIES.find((v) => v.value === share.visibility)?.hint}
              </div>
            </div>

            <div className="rounded-xl border border-gold/25 bg-gold/5 px-3 py-2 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-[10px] uppercase tracking-wider text-white/40">
                    Freigabecode
                  </div>
                  <div className="text-[18px] tracking-[4px] text-gold/90 truncate">
                    {share.code}
                  </div>
                </div>
                <div className="flex gap-1 shrink-0">
                  <button
                    className={chip}
                    onClick={() => void copy(share.code, "Code")}
                  >
                    Code kopieren
                  </button>
                  <button
                    className={chip}
                    onClick={() => void copy(share.link, "Einladungslink")}
                  >
                    Link kopieren
                  </button>
                </div>
              </div>
              <div className="text-[10.5px] text-white/40 break-all">
                {share.link}
              </div>
              <button className={chip} disabled={busy} onClick={() => void rollCode()}>
                Neuen Code erzeugen
              </button>
            </div>

            {share.visibility === "invited" && (
              <div className="space-y-2">
                <div className={label}>Einladungen</div>
                <div className="flex gap-2">
                  <input
                    className={field}
                    placeholder="Für wen? (z. B. Anna)"
                    value={inviteLabel}
                    onChange={(e) => setInviteLabel(e.target.value)}
                  />
                  <button
                    className={chip}
                    disabled={busy}
                    onClick={() => void invite()}
                  >
                    Erstellen
                  </button>
                </div>
                {freshInvite && (
                  <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">
                    <div className="text-[11px] text-white/80">
                      {freshInvite.label || "Einladung"}: {freshInvite.code}
                    </div>
                    <div className="text-[10.5px] text-white/40 break-all">
                      {freshInvite.link}
                    </div>
                    <button
                      className={`${chip} mt-1`}
                      onClick={() =>
                        void copy(freshInvite.link ?? freshInvite.code, "Einladung")
                      }
                    >
                      Einladung kopieren
                    </button>
                  </div>
                )}
                {share.open_invites.map((item) => (
                  <div
                    key={item.code}
                    className="flex items-center justify-between gap-2 text-[11px] text-white/60 px-1"
                  >
                    <span className="truncate">
                      {item.label || "Ohne Namen"} · {item.code}
                    </span>
                    <button
                      className="text-white/35 hover:text-red-300"
                      onClick={() => void dropInvite(item.code)}
                    >
                      löschen
                    </button>
                  </div>
                ))}
                {share.open_invites.length === 0 && !freshInvite && (
                  <div className="text-[10.5px] text-white/35 px-0.5">
                    Noch keine offenen Einladungen. Jede Einladung gilt für genau
                    einen Benutzer und verfällt nach der ersten Nutzung.
                  </div>
                )}
              </div>
            )}

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <div className={label}>Verbundene Benutzer ({users.length})</div>
                {users.length > 0 && (
                  <button
                    className="text-[11px] text-red-300/80 hover:text-red-300"
                    disabled={busy}
                    onClick={() => void revokeAll()}
                  >
                    Allen Zugriff entziehen
                  </button>
                )}
              </div>
              {users.length === 0 ? (
                <div className="text-[10.5px] text-white/35 px-0.5">
                  Noch niemand verbunden. Gib deinen Freigabecode weiter.
                </div>
              ) : (
                users.map((user) => (
                  <div
                    key={user.id}
                    className="rounded-xl border border-white/10 bg-white/5 px-3 py-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className={`w-2 h-2 rounded-full shrink-0 ${
                            user.state === "aktiv"
                              ? "bg-emerald-400 animate-pulse"
                              : user.state === "verbunden"
                              ? "bg-emerald-400/60"
                              : "bg-white/25"
                          }`}
                        />
                        <span className="text-[12px] text-white/90 truncate">
                          {user.user}
                        </span>
                        <span className="text-[10.5px] text-white/35 truncate">
                          {user.address}
                        </span>
                      </div>
                      <button
                        className="text-[11px] text-white/40 hover:text-red-300 shrink-0"
                        disabled={busy}
                        onClick={() => void kick(user.id, user.user)}
                      >
                        entfernen
                      </button>
                    </div>
                    <div className="text-[10.5px] text-white/45 mt-1">
                      {user.state}
                      {user.model ? ` · ${user.model}` : ""}
                      {user.sessions > 0 ? ` · ${user.sessions} Sitzung(en)` : ""}
                      {` · ${user.requests} Anfragen · zuletzt ${moment(
                        user.last_activity
                      )}`}
                    </div>
                  </div>
                ))
              )}
            </div>
            <p className="text-[11px] text-white/40 leading-relaxed">
              Andere erreichen dich unter <code>{share.host}:{share.port}</code>.
              Freigegeben wird ausschließlich das Antworten deines Ollama-Servers —
              deine Chats, Dateien und die PC-Steuerung bleiben unerreichbar. Jede
              Anfrage muss ein gültiges Zugriffstoken haben; entziehst du den
              Zugriff, gilt das sofort.
            </p>
          </>
        )}
      </section>

      <section className="space-y-2">
        <div className={section}>Freigegebene Server nutzen</div>
        <div className="flex gap-2">
          <input
            className={field}
            placeholder="Freigabecode oder Einladungslink"
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void join();
            }}
          />
          <button className={chip} disabled={busy} onClick={() => void join()}>
            Verbinden
          </button>
        </div>
        {remotes.length === 0 ? (
          <div className="text-[10.5px] text-white/35 px-0.5">
            Noch kein fremder Server verbunden. Nach dem Verbinden erscheinen seine
            Modelle oben in deiner KI-Auswahl.
          </div>
        ) : (
          remotes.map((entry) => (
            <div
              key={entry.code}
              className="rounded-xl border border-white/10 bg-white/5 px-3 py-2"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-[12px] text-white/90 truncate">
                    {entry.name}
                  </div>
                  <div className="text-[10.5px] text-white/40 truncate">
                    {entry.owner ? `${entry.owner} · ` : ""}
                    {entry.base} · {entry.models.length} Modelle
                  </div>
                </div>
                <div className="flex gap-1 shrink-0">
                  <button
                    className={chip}
                    disabled={busy}
                    onClick={() => void refreshRemote(entry.code)}
                  >
                    Aktualisieren
                  </button>
                  <button
                    className="text-[11px] text-white/40 hover:text-red-300 px-1"
                    disabled={busy}
                    onClick={() => void forget(entry.code)}
                  >
                    trennen
                  </button>
                </div>
              </div>
              {entry.description && (
                <div className="text-[10.5px] text-white/45 mt-1">
                  {entry.description}
                </div>
              )}
              {entry.error && (
                <div className="text-[10.5px] text-amber-300/90 mt-1">
                  {entry.error}
                </div>
              )}
            </div>
          ))
        )}
        <p className="text-[11px] text-white/40 leading-relaxed">
          Im Chat wählst du oben den Anbieter <b>ollama</b> und dann das Modell des
          freigegebenen Servers. Verlauf, Streaming und deine Ollama-Einstellungen
          gelten dabei ganz normal weiter.
        </p>
      </section>

      {(note || error) && (
        <div
          className={`text-[11px] ${
            error ? "text-red-300/90" : "text-emerald-300/80"
          }`}
        >
          {error || note}
        </div>
      )}
    </>
  );
}
