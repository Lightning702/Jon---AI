import { useEffect, useRef, useState } from "react";
import {
  OllamaInvite,
  OllamaRemote,
  OllamaShare,
  OllamaShareUser,
  OllamaStatus,
  ShareVisibility,
  connectOllamaRemote,
  createOllamaInvite,
  deleteOllamaInvite,
  forgetOllamaRemote,
  getOllamaRemotes,
  getOllamaShare,
  getOllamaStatus,
  newOllamaShareCode,
  refreshOllamaRemote,
  removeOllamaShareUser,
  revokeOllamaShare,
  saveOllamaShare,
} from "../lib/api";

const field =
  "w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-[12px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50";
const chip =
  "text-[11px] px-2.5 py-1.5 rounded-lg border border-white/10 bg-white/5 text-white/70 hover:bg-white/10 transition disabled:opacity-40";
const gold =
  "text-[12px] px-3 py-1.5 rounded-lg border border-gold/35 bg-gold/12 text-gold/90 hover:bg-gold/20 transition disabled:opacity-40";

const WER_DARF: { value: ShareVisibility; text: string; hint: string }[] = [
  {
    value: "public",
    text: "Jeder mit meinem Code",
    hint: "Wer deinen Code kennt, darf mitschreiben. Am einfachsten für Freunde.",
  },
  {
    value: "invited",
    text: "Nur wen ich einlade",
    hint: "Du erstellst pro Person eine Einladung. Sie gilt genau einmal.",
  },
  {
    value: "private",
    text: "Gerade niemand",
    hint: "Pause: Es kommt niemand Neues dazu. Wer schon verbunden ist, bleibt es, bis du ihn entfernst.",
  },
];

function Step({
  n,
  title,
  children,
}: {
  n: number;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex gap-3">
      <div className="w-6 h-6 shrink-0 rounded-full bg-gold/15 border border-gold/35 text-gold text-[11px] flex items-center justify-center">
        {n}
      </div>
      <div className="min-w-0 flex-1 space-y-2">
        <div className="text-[12.5px] text-white/90">{title}</div>
        {children}
      </div>
    </div>
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
  const [mode, setMode] = useState<"geben" | "nutzen">("geben");
  const [share, setShare] = useState<OllamaShare | null>(null);
  const [users, setUsers] = useState<OllamaShareUser[]>([]);
  const [remotes, setRemotes] = useState<OllamaRemote[]>([]);
  const [status, setStatus] = useState<OllamaStatus | null>(null);
  const [inviteLabel, setInviteLabel] = useState("");
  const [freshInvite, setFreshInvite] = useState<OllamaInvite | null>(null);
  const [joinCode, setJoinCode] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [details, setDetails] = useState(false);
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
    if (alive.current) {
      setRemotes(list);
      if (list.length > 0) setMode((m) => m);
    }
    try {
      const next = await getOllamaStatus();
      if (alive.current) setStatus(next);
    } catch {
      if (alive.current) setStatus(null);
    }
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
      say(`${what} kopiert — jetzt deinem Freund schicken`);
    } catch {
      say(text);
    }
  };

  const rollCode = async () => {
    setBusy(true);
    try {
      setShare(await newOllamaShareCode());
      say("Neuer Code — der alte funktioniert nicht mehr");
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
      say("Einladung fertig");
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
      say(`${name} kann jetzt nicht mehr mitschreiben`);
    } finally {
      if (alive.current) setBusy(false);
    }
  };

  const revokeAll = async () => {
    setBusy(true);
    try {
      const count = await revokeOllamaShare();
      await load();
      say(count > 0 ? `${count} Person(en) entfernt` : "Es war niemand verbunden");
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
      say(`${entry.name} ist erreichbar`);
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

  const bereit = status?.state === "online";
  const modell = share.shared_model || status?.model || "";

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5">
        <div className="text-[12px] text-white/80 leading-relaxed">
          <b className="text-gold/90">Was ist das?</b> Ollama ist die KI, die auf
          deinem eigenen Computer rechnet. Teilen heißt: Ein Freund darf seine Fragen
          an <b>deine</b> KI schicken. Er braucht dann selbst keine KI und keinen
          Schlüssel — und sieht von deinem PC nichts außer den Antworten.
        </div>
      </div>

      <div className="flex gap-1">
        <button
          onClick={() => setMode("geben")}
          className={`flex-1 px-3 py-2 rounded-xl border text-left transition ${
            mode === "geben"
              ? "border-gold/40 bg-gold/12"
              : "border-white/10 bg-white/5 hover:bg-white/10"
          }`}
        >
          <div
            className={`text-[12.5px] ${
              mode === "geben" ? "text-gold" : "text-white/85"
            }`}
          >
            📤 Ich gebe meine KI frei
          </div>
          <div className="text-[10.5px] text-white/45 mt-0.5">
            Freunde dürfen über meinen PC schreiben
          </div>
        </button>
        <button
          onClick={() => setMode("nutzen")}
          className={`flex-1 px-3 py-2 rounded-xl border text-left transition ${
            mode === "nutzen"
              ? "border-gold/40 bg-gold/12"
              : "border-white/10 bg-white/5 hover:bg-white/10"
          }`}
        >
          <div
            className={`text-[12.5px] ${
              mode === "nutzen" ? "text-gold" : "text-white/85"
            }`}
          >
            📥 Ich nutze die KI von jemandem
          </div>
          <div className="text-[10.5px] text-white/45 mt-0.5">
            Ich habe einen Code bekommen
          </div>
        </button>
      </div>

      {mode === "geben" ? (
        <div className="space-y-4">
          {!bereit && (
            <div className="rounded-xl border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-[11.5px] text-amber-200/90 leading-relaxed">
              Dafür muss Ollama auf deinem PC laufen. Öffne im Zahnrad-Menü den
              Bereich <b>Ollama</b> und drücke dort <b>Verbindung testen</b> — steht
              da <b>Online</b>, kann es losgehen.
            </div>
          )}

          <Step n={1} title="Freigabe einschalten">
            <button
              onClick={() => void patch({ enabled: !share.enabled })}
              disabled={busy}
              className={`w-full flex items-center justify-between gap-3 px-3 py-2 rounded-xl border transition ${
                share.enabled
                  ? "border-emerald-400/35 bg-emerald-400/10"
                  : "border-white/10 bg-white/5 hover:bg-white/10"
              }`}
            >
              <span className="text-[12px] text-white/90">
                {share.enabled ? "Ist eingeschaltet" : "Ist aus"}
              </span>
              <span
                className={`w-9 h-5 shrink-0 rounded-full flex items-center px-0.5 transition-colors ${
                  share.enabled ? "bg-emerald-400/70" : "bg-white/15"
                }`}
              >
                <span
                  className={`w-4 h-4 rounded-full bg-white transition-transform ${
                    share.enabled ? "translate-x-4" : ""
                  }`}
                />
              </span>
            </button>
          </Step>

          {share.enabled && (
            <>
              <Step n={2} title="Wer darf mitschreiben?">
                <div className="space-y-1">
                  {WER_DARF.map((item) => (
                    <button
                      key={item.value}
                      onClick={() => void patch({ visibility: item.value })}
                      disabled={busy}
                      className={`w-full text-left px-3 py-2 rounded-xl border transition ${
                        share.visibility === item.value
                          ? "border-gold/40 bg-gold/12"
                          : "border-white/10 bg-white/5 hover:bg-white/10"
                      }`}
                    >
                      <div
                        className={`text-[12px] ${
                          share.visibility === item.value
                            ? "text-gold"
                            : "text-white/85"
                        }`}
                      >
                        {item.text}
                      </div>
                      <div className="text-[10.5px] text-white/45 mt-0.5 leading-snug">
                        {item.hint}
                      </div>
                    </button>
                  ))}
                </div>
              </Step>

              {share.visibility === "public" && (
                <Step n={3} title="Diesen Code deinem Freund schicken">
                  <div className="rounded-xl border border-gold/25 bg-gold/5 px-3 py-3 text-center">
                    <div className="text-[24px] tracking-[6px] text-gold/90 break-all">
                      {share.code}
                    </div>
                    <div className="flex gap-2 justify-center mt-2">
                      <button
                        className={gold}
                        onClick={() => void copy(share.code, "Code")}
                      >
                        Code kopieren
                      </button>
                      <button
                        className={chip}
                        onClick={() => void copy(share.link, "Link")}
                      >
                        Link kopieren
                      </button>
                    </div>
                    <div className="text-[10.5px] text-white/40 mt-2 leading-snug">
                      Im selben WLAN reicht der Code. Ist dein Freund woanders,
                      schick ihm den Link — da steht deine Adresse mit drin.
                    </div>
                  </div>
                </Step>
              )}

              {share.visibility === "invited" && (
                <Step n={3} title="Für jede Person eine Einladung erstellen">
                  <div className="flex gap-2">
                    <input
                      className={field}
                      placeholder="Für wen? z. B. Anna"
                      value={inviteLabel}
                      onChange={(e) => setInviteLabel(e.target.value)}
                    />
                    <button className={gold} disabled={busy} onClick={() => void invite()}>
                      Erstellen
                    </button>
                  </div>
                  {freshInvite && (
                    <div className="rounded-xl border border-gold/25 bg-gold/5 px-3 py-2">
                      <div className="text-[11px] text-white/70">
                        Einladung für {freshInvite.label || "deinen Freund"}
                      </div>
                      <div className="text-[16px] tracking-[3px] text-gold/90 break-all">
                        {freshInvite.code}
                      </div>
                      <button
                        className={`${gold} mt-1`}
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
                      className="flex items-center justify-between gap-2 text-[11px] text-white/55 px-1"
                    >
                      <span className="truncate">
                        Offen: {item.label || "ohne Namen"} · {item.code}
                      </span>
                      <button
                        className="text-white/35 hover:text-red-300"
                        onClick={() => void dropInvite(item.code)}
                      >
                        löschen
                      </button>
                    </div>
                  ))}
                </Step>
              )}

              {share.visibility === "private" && (
                <div className="text-[11.5px] text-white/50 px-1 leading-relaxed">
                  Gerade kommt niemand Neues dazu. Wähle oben „Jeder mit meinem Code"
                  oder „Nur wen ich einlade", wenn du wieder jemanden hereinlassen
                  willst.
                </div>
              )}

              <Step
                n={share.visibility === "private" ? 3 : 4}
                title={`Wer gerade verbunden ist (${users.length})`}
              >
                {users.length === 0 ? (
                  <div className="text-[11.5px] text-white/45 leading-relaxed">
                    Noch niemand. Sobald dein Freund den Code eingetragen hat, taucht
                    er hier auf — mit dem, was er gerade macht.
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    {users.map((user) => (
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
                          </div>
                          <button
                            className="text-[11px] text-white/40 hover:text-red-300 shrink-0"
                            disabled={busy}
                            onClick={() => void kick(user.id, user.user)}
                          >
                            rauswerfen
                          </button>
                        </div>
                        <div className="text-[10.5px] text-white/45 mt-1">
                          {user.state === "aktiv"
                            ? "schreibt gerade"
                            : user.state === "verbunden"
                            ? "verbunden"
                            : "gerade offline"}
                          {user.requests > 0 ? ` · ${user.requests} Fragen` : ""}
                          {` · zuletzt ${moment(user.last_activity)}`}
                        </div>
                      </div>
                    ))}
                    <button
                      className="text-[11px] text-red-300/80 hover:text-red-300 px-1"
                      disabled={busy}
                      onClick={() => void revokeAll()}
                    >
                      Alle rauswerfen
                    </button>
                  </div>
                )}
              </Step>

              <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-[11.5px] text-white/55 leading-relaxed">
                <b className="text-white/80">Was dein Freund darf:</b> Fragen an dein
                Modell {modell ? <>(<span className="text-gold/80">{modell}</span>)</> : null}{" "}
                stellen und die Antworten lesen.{" "}
                <b className="text-white/80">Was er nicht darf:</b> deine Chats lesen,
                deine Dateien sehen oder deinen PC steuern. Das geht technisch nicht —
                freigegeben ist nur das Antworten. Und du kannst jeden jederzeit mit
                einem Klick rauswerfen.
              </div>

              <button
                onClick={() => setDetails((v) => !v)}
                className="text-[11px] text-white/40 hover:text-white/70"
              >
                {details ? "Weniger anzeigen" : "Name, Beschreibung & neuer Code …"}
              </button>
              {details && (
                <div className="space-y-2">
                  <input
                    className={field}
                    placeholder={`Name der Freigabe (optional), z. B. „PC von ${share.owner}"`}
                    value={share.name}
                    onChange={(e) => setShare({ ...share, name: e.target.value })}
                    onBlur={() => void patch({ name: share.name })}
                  />
                  <input
                    className={field}
                    placeholder="Kurze Beschreibung (optional), z. B. große Grafikkarte"
                    value={share.description}
                    onChange={(e) =>
                      setShare({ ...share, description: e.target.value })
                    }
                    onBlur={() => void patch({ description: share.description })}
                  />
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10.5px] text-white/40 leading-snug">
                      Adresse: {share.host}:{share.port}
                    </span>
                    <button className={chip} disabled={busy} onClick={() => void rollCode()}>
                      Neuen Code erzeugen
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          <Step n={1} title="Code oder Link von deinem Freund einfügen">
            <div className="flex gap-2">
              <input
                className={field}
                placeholder="z. B. AB39KD12"
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void join();
                }}
              />
              <button className={gold} disabled={busy} onClick={() => void join()}>
                Verbinden
              </button>
            </div>
            <div className="text-[10.5px] text-white/40 leading-snug">
              Seid ihr im selben WLAN, reicht der Code. Ist dein Freund woanders,
              brauchst du seinen Link (der sieht so aus:
              <code className="text-white/60"> AB39KD12@192.168.1.50:8758</code>).
            </div>
          </Step>

          <Step n={2} title="Oben im Chat auswählen">
            <div className="text-[11.5px] text-white/55 leading-relaxed">
              Nach dem Verbinden steht oben links im Chat bei den Anbietern zusätzlich{" "}
              <b className="text-gold/80">„Ollama von …"</b>. Wähle das aus — das
              Modell stellt dein Freund ein, du musst nichts weiter tun. Dann schreibt
              Jon über seinen Computer.
            </div>
          </Step>

          {remotes.length === 0 ? (
            <div className="text-[11.5px] text-white/45 px-1">
              Noch nichts verbunden.
            </div>
          ) : (
            <div className="space-y-1.5">
              <div className="text-[11px] text-white/45 px-1">
                Verbunden mit ({remotes.length})
              </div>
              {remotes.map((entry) => (
                <div
                  key={entry.code}
                  className="rounded-xl border border-white/10 bg-white/5 px-3 py-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-[12px] text-white/90 truncate">
                        {entry.owner ? `Ollama von ${entry.owner}` : entry.name}
                      </div>
                      <div className="text-[10.5px] text-white/40 truncate">
                        Modell: {entry.model || entry.models[0] || "—"}
                      </div>
                    </div>
                    <div className="flex gap-1 shrink-0">
                      <button
                        className={chip}
                        disabled={busy}
                        onClick={() => void refreshRemote(entry.code)}
                      >
                        Prüfen
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
                  {entry.error && (
                    <div className="text-[10.5px] text-amber-300/90 mt-1">
                      {entry.error}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {(note || error) && (
        <div
          className={`text-[11.5px] ${
            error ? "text-red-300/90" : "text-emerald-300/80"
          }`}
        >
          {error || note}
        </div>
      )}
    </div>
  );
}
