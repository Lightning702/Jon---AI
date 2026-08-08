import { useCallback, useEffect, useMemo, useState } from "react";
import {
  clearPhoneHistory,
  deletePhoneCall,
  getPhoneCalls,
  getPhoneDiagnostics,
  getPhoneHistory,
  getPhoneSetup,
  getPhoneStatus,
  hangupPhoneCall,
  newPhoneCredentials,
  restartPhone,
  schedulePhoneCall,
  setPhoneAddress,
  testPhoneCall,
  updatePhoneCall,
  saveUserSettings,
  type PhoneCall,
  type PhoneCheck,
  type PhoneLogEntry,
  type PhoneSetup,
  type PhoneStatus,
} from "../lib/api";

const STATUS_LABEL: Record<string, string> = {
  scheduled: "geplant",
  calling: "📞 wird angerufen",
  ringing: "📞 klingelt",
  active: "🟢 verbunden",
  completed: "✓ erledigt",
  missed: "⚪ nicht abgenommen",
  rejected: "🔴 abgelehnt",
  failed: "🔴 fehlgeschlagen",
  cancelled: "abgesagt",
};

function whenText(iso: string): string {
  const moment = new Date(iso);
  if (Number.isNaN(moment.getTime())) return iso;
  const today = new Date();
  const sameDay = moment.toDateString() === today.toDateString();
  const tomorrow = new Date(today.getTime() + 86400000);
  const clock = moment.toLocaleTimeString("de-AT", {
    hour: "2-digit",
    minute: "2-digit",
  });
  if (sameDay) return `Heute ${clock}`;
  if (moment.toDateString() === tomorrow.toDateString()) return `Morgen ${clock}`;
  return `${moment.toLocaleDateString("de-AT", {
    day: "2-digit",
    month: "2-digit",
  })} ${clock}`;
}

function Dot({ ok }: { ok: boolean }) {
  return <span className={ok ? "text-emerald-400" : "text-red-400"}>{ok ? "🟢" : "🔴"}</span>;
}

export default function PhoneCalls({ onClose }: { onClose: () => void }) {
  const [status, setStatus] = useState<PhoneStatus | null>(null);
  const [calls, setCalls] = useState<PhoneCall[]>([]);
  const [checks, setChecks] = useState<PhoneCheck[]>([]);
  const [setup, setSetup] = useState<PhoneSetup | null>(null);
  const [history, setHistory] = useState<PhoneLogEntry[]>([]);
  const [tab, setTab] = useState<"calls" | "setup" | "log">("calls");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [when, setWhen] = useState("");
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [recurrence, setRecurrence] = useState("");
  const [editing, setEditing] = useState<string>("");
  const [editWhen, setEditWhen] = useState("");
  const [newUser, setNewUser] = useState("");

  const load = useCallback(async () => {
    try {
      const [nextStatus, nextCalls, diag] = await Promise.all([
        getPhoneStatus(),
        getPhoneCalls(),
        getPhoneDiagnostics(),
      ]);
      setStatus(nextStatus);
      setCalls(nextCalls);
      setChecks(diag.checks);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Telefonfunktion nicht erreichbar.");
    }
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 5000);
    return () => window.clearInterval(timer);
  }, [load]);

  useEffect(() => {
    if (tab === "setup" && !setup) getPhoneSetup().then(setSetup).catch(() => {});
    if (tab === "log") getPhoneHistory().then(setHistory).catch(() => {});
  }, [tab, setup]);

  const ready = useMemo(
    () => checks.length > 0 && checks.every((c) => c.ok),
    [checks]
  );

  async function guard(label: string, action: () => Promise<void>) {
    setBusy(label);
    setError("");
    setNote("");
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Das hat nicht geklappt.");
    } finally {
      setBusy("");
    }
  }

  async function toggleEnabled(next: boolean) {
    await guard("toggle", async () => {
      await saveUserSettings({ phone_enabled: next });
      await restartPhone();
      await load();
    });
  }

  async function addCall() {
    if (!when.trim()) {
      setError("Sag mir, wann ich anrufen soll — zum Beispiel „morgen um 9 Uhr“.");
      return;
    }
    await guard("add", async () => {
      await schedulePhoneCall({
        when: when.trim(),
        reason: reason.trim(),
        message: message.trim(),
        recurrence: recurrence.trim(),
      });
      setWhen("");
      setReason("");
      setMessage("");
      setRecurrence("");
      await load();
    });
  }

  async function saveEdit(id: string) {
    await guard("edit", async () => {
      await updatePhoneCall(id, { when: editWhen.trim() });
      setEditing("");
      setEditWhen("");
      await load();
    });
  }

  async function runTest() {
    await guard("test", async () => {
      const result = await testPhoneCall();
      const label = STATUS_LABEL[result.status] ?? result.status;
      setNote(
        `Testanruf: ${label}${result.reason ? ` — ${result.reason}` : ""}` +
          (result.duration ? ` (${result.duration}s)` : "")
      );
      await load();
    });
  }

  const device = status?.device;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[640px] max-w-[94vw] max-h-[88vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <div>
            <div className="text-white/90 font-semibold">📞 Telefonanrufe</div>
            <div className="text-[11px] text-white/40">
              Jon ruft dich auf dem Handy an — über dein eigenes Netz, ohne Anbieter.
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="px-5 py-3 border-b border-white/10 flex items-center gap-3 flex-wrap">
          <label className="flex items-center gap-2 text-sm text-white/80">
            <input
              type="checkbox"
              checked={status?.enabled ?? false}
              disabled={busy === "toggle"}
              onChange={(e) => toggleEnabled(e.target.checked)}
            />
            Eingeschaltet
          </label>
          <div className="text-[12px] text-white/60 flex items-center gap-1">
            SIP <Dot ok={Boolean(status?.running)} />
          </div>
          <div className="text-[12px] text-white/60 flex items-center gap-1">
            Handy <Dot ok={Boolean(device?.registered)} />
          </div>
          <div className="text-[12px] text-white/60 flex items-center gap-1">
            Bereit <Dot ok={ready} />
          </div>
          <div className="ml-auto flex gap-2">
            {status?.active_call ? (
              <button
                onClick={() => guard("hangup", async () => { await hangupPhoneCall(); await load(); })}
                className="px-3 py-1.5 rounded-lg text-[12px] bg-red-500/20 border border-red-400/30 text-red-200"
              >
                Auflegen
              </button>
            ) : null}
            <button
              onClick={runTest}
              disabled={busy === "test" || !status?.enabled}
              className="px-3 py-1.5 rounded-lg text-[12px] bg-white/10 border border-white/15 text-white/80 disabled:opacity-40"
            >
              {busy === "test" ? "ruft an…" : "Testanruf"}
            </button>
          </div>
        </div>

        <div className="px-5 pt-3 flex gap-2 text-[12px]">
          {(["calls", "setup", "log"] as const).map((key) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`px-3 py-1.5 rounded-lg border ${
                tab === key
                  ? "bg-white/15 border-white/25 text-white/90"
                  : "bg-white/5 border-white/10 text-white/50"
              }`}
            >
              {key === "calls" ? "Geplante Anrufe" : key === "setup" ? "Einrichtung" : "Verlauf"}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {error ? (
            <div className="text-[12px] text-red-300 bg-red-500/10 border border-red-400/20 rounded-lg px-3 py-2">
              {error}
            </div>
          ) : null}
          {note ? (
            <div className="text-[12px] text-emerald-200 bg-emerald-500/10 border border-emerald-400/20 rounded-lg px-3 py-2">
              {note}
            </div>
          ) : null}
          {status?.error ? (
            <div className="text-[12px] text-amber-200 bg-amber-500/10 border border-amber-400/20 rounded-lg px-3 py-2">
              {status.error}
            </div>
          ) : null}

          {tab === "calls" ? (
            <>
              <div className="space-y-2">
                <div className="text-[12px] text-white/50">Neuen Anruf planen</div>
                <input
                  value={when}
                  onChange={(e) => setWhen(e.target.value)}
                  placeholder="Wann? z. B. „in 20 Minuten“, „heute um 18 Uhr“, „morgen um 9“"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/90 outline-none focus:border-white/25"
                />
                <div className="flex gap-2">
                  <input
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Grund (Projekt-Erinnerung)"
                    className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/90 outline-none focus:border-white/25"
                  />
                  <input
                    value={recurrence}
                    onChange={(e) => setRecurrence(e.target.value)}
                    placeholder="Wiederholung"
                    className="w-40 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/90 outline-none focus:border-white/25"
                  />
                </div>
                <input
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Was Jon zuerst sagt (leer = Jon denkt sich etwas aus)"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/90 outline-none focus:border-white/25"
                />
                <button
                  onClick={addCall}
                  disabled={busy === "add"}
                  className="px-4 py-2 rounded-lg text-[13px] bg-[#d4af37]/20 border border-[#d4af37]/40 text-[#f7e4a8] disabled:opacity-40"
                >
                  Anruf planen
                </button>
              </div>

              <div className="space-y-2">
                <div className="text-[12px] text-white/50">
                  {calls.length ? "Geplant" : "Es ist noch kein Anruf geplant."}
                </div>
                {calls.map((call) => (
                  <div
                    key={call.id}
                    className="rounded-lg border border-white/10 bg-white/5 px-3 py-2"
                  >
                    <div className="flex items-center gap-2">
                      <div className="text-sm text-white/90 font-medium">
                        {whenText(call.scheduled_at)}
                      </div>
                      {call.recurrence ? (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/10 text-white/60">
                          {call.recurrence}
                        </span>
                      ) : null}
                      <div className="ml-auto flex gap-2">
                        <button
                          onClick={() => {
                            setEditing(call.id);
                            setEditWhen("");
                          }}
                          className="text-[11px] text-white/50 hover:text-white/90"
                        >
                          Ändern
                        </button>
                        <button
                          onClick={() =>
                            guard("del", async () => {
                              await deletePhoneCall(call.id);
                              await load();
                            })
                          }
                          className="text-[11px] text-red-300/70 hover:text-red-200"
                        >
                          Löschen
                        </button>
                      </div>
                    </div>
                    <div className="text-[12px] text-white/50">
                      {call.reason || call.message || "ohne Grund"}
                    </div>
                    {editing === call.id ? (
                      <div className="flex gap-2 mt-2">
                        <input
                          value={editWhen}
                          onChange={(e) => setEditWhen(e.target.value)}
                          placeholder="Neuer Zeitpunkt"
                          className="flex-1 bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-[12px] text-white/90 outline-none"
                        />
                        <button
                          onClick={() => saveEdit(call.id)}
                          className="px-3 py-1 rounded-lg text-[11px] bg-white/10 border border-white/15 text-white/80"
                        >
                          Speichern
                        </button>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            </>
          ) : null}

          {tab === "setup" ? (
            <div className="space-y-4">
              <div className="space-y-1">
                {checks.map((check) => (
                  <div key={check.name} className="flex items-start gap-2 text-[12px]">
                    <Dot ok={check.ok} />
                    <div className="flex-1">
                      <span className="text-white/80">{check.name}</span>
                      <span className="text-white/40"> — {check.detail}</span>
                      {check.fix ? (
                        <div className="mt-1">
                          <div className="font-mono text-[10.5px] text-amber-200/80 bg-black/40 rounded px-2 py-1 break-all">
                            {check.fix}
                          </div>
                          <button
                            onClick={() => {
                              navigator.clipboard?.writeText(check.fix ?? "");
                              setNote(
                                "Befehl kopiert. In PowerShell einfügen, Enter — dann fragt " +
                                  "Windows einmal nach Administratorrechten. Auf „Ja“ klicken."
                              );
                            }}
                            className="mt-1 text-[10px] text-white/50 hover:text-white/90"
                          >
                            Befehl kopieren
                          </button>
                          {check.fix_hint ? (
                            <div className="text-[10px] text-white/35 mt-0.5">
                              {check.fix_hint}
                            </div>
                          ) : null}
                        </div>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>

              {setup?.addresses?.length ? (
                <div className="space-y-1">
                  <div className="text-[12px] text-white/50">
                    Welche Adresse soll Jon deinem Handy nennen?
                  </div>
                  {setup.addresses.map((address) => (
                    <label
                      key={address.ip}
                      className={`flex items-center gap-2 text-[12px] rounded-lg border px-2 py-1.5 cursor-pointer ${
                        address.selected
                          ? "border-[#d4af37]/40 bg-[#d4af37]/10"
                          : "border-white/10 bg-white/5"
                      }`}
                    >
                      <input
                        type="radio"
                        name="phone-address"
                        checked={address.selected}
                        onChange={() =>
                          guard("addr", async () => {
                            setSetup(await setPhoneAddress(address.ip));
                            await load();
                          })
                        }
                      />
                      <span className="font-mono text-white/90">
                        {address.ip || "auto"}
                      </span>
                      <span className="text-white/40">{address.label}</span>
                      {address.kind === "vpn" || address.kind === "virtual" ? (
                        <span className="ml-auto text-[10px] text-amber-300/80">
                          vom Handy nicht erreichbar
                        </span>
                      ) : null}
                      {address.kind === "mesh" ? (
                        <span className="ml-auto text-[10px] text-emerald-300/80">
                          auch mit mobilen Daten
                        </span>
                      ) : null}
                    </label>
                  ))}
                </div>
              ) : null}

              <ol className="space-y-3 text-[13px] text-white/70">
                <li>
                  <b className="text-white/90">1. SIP-App installieren</b>
                  <div className="text-white/50">
                    Kostenlos und quelloffen:{" "}
                    <a
                      className="text-[#f7e4a8]"
                      href={setup?.app_url ?? "https://f-droid.org/packages/org.linphone/"}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Linphone
                    </a>{" "}
                    (F-Droid oder Play Store).
                  </div>
                </li>
                <li>
                  <b className="text-white/90">2. Zugangsdaten eintragen</b>
                  {setup ? (
                    <div className="mt-1 rounded-lg border border-white/10 bg-black/30 px-3 py-2 font-mono text-[12px] space-y-1">
                      <div>Benutzername: {setup.username}</div>
                      <div>Passwort: {setup.password}</div>
                      <div>Domain / Server: {setup.server}:{setup.port}</div>
                      <div>Transport: {setup.transport}</div>
                    </div>
                  ) : (
                    <div className="text-white/40">wird geladen…</div>
                  )}
                  <div className="mt-2 flex gap-2 items-center flex-wrap">
                    <input
                      value={newUser}
                      onChange={(e) => setNewUser(e.target.value)}
                      placeholder="neuer Benutzername"
                      className="w-44 bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-[12px] text-white/90 outline-none focus:border-white/25"
                    />
                    <button
                      onClick={() =>
                        guard("pw", async () => {
                          setSetup(await newPhoneCredentials(newUser.trim()));
                          setNewUser("");
                          setNote(
                            "Neue Zugangsdaten erzeugt — im Handy beide Felder neu eintragen."
                          );
                        })
                      }
                      className="px-3 py-1.5 rounded-lg text-[11px] bg-white/10 border border-white/15 text-white/70"
                    >
                      Neu erzeugen
                    </button>
                    <span className="text-[10px] text-white/35">
                      leer lassen = Jon würfelt einen Namen aus
                    </span>
                  </div>
                </li>
                <li>
                  <b className="text-white/90">3. In Linphone eintragen</b>
                  <div className="text-white/50 mb-1">
                    Beim ersten Start <b className="text-white/70">„SIP-Konto verwenden“</b> —
                    nicht „Konto erstellen“. Später über Menü ☰ → Einstellungen → Konten →
                    Konto hinzufügen.
                  </div>
                  <table className="w-full text-[12px] border border-white/10 rounded-lg overflow-hidden">
                    <tbody>
                      {[
                        ["Benutzername", setup?.username ?? "…"],
                        ["Passwort", setup?.password ?? "…"],
                        [
                          "Domain",
                          setup ? `${setup.server}:${setup.port}` : "…",
                        ],
                        ["Transport", "UDP"],
                      ].map(([label, value]) => (
                        <tr key={label} className="border-b border-white/5 last:border-0">
                          <td className="px-2 py-1 text-white/50 w-32">{label}</td>
                          <td className="px-2 py-1 font-mono text-white/90 break-all">
                            {value}
                          </td>
                          <td className="px-2 py-1 w-8">
                            <button
                              onClick={() => {
                                navigator.clipboard?.writeText(String(value));
                                setNote(`${label} kopiert.`);
                              }}
                              className="text-white/40 hover:text-white/90"
                              title="kopieren"
                            >
                              ⧉
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="text-[11px] text-amber-200/70 mt-1">
                    Achtung bei der Autokorrektur des Handys — sie macht aus dem ersten
                    Zeichen gern einen Großbuchstaben. Lieber kopieren und einfügen.
                  </div>
                </li>
                <li>
                  <b className="text-white/90">4. Android am Einschlafen hindern</b>
                  <div className="text-white/50">
                    Einstellungen → Apps → Linphone → <b className="text-white/70">Akku</b> →
                    „Uneingeschränkt“. Sonst schläft der SIP-Dienst ein und es klingelt
                    nicht. In Linphone zusätzlich Einstellungen → Netzwerk →
                    „Dienst im Vordergrund“ einschalten.
                  </div>
                </li>
                <li>
                  <b className="text-white/90">5. Verbindung prüfen</b>
                  <div className="text-white/50">
                    {device?.registered
                      ? `🟢 Angemeldet: ${device.user_agent || "Gerät"} über ${device.source} (${(device.transport ?? "").toUpperCase()})`
                      : "Linphone zeigt oben „Verbunden“ in Grün — dann erscheint dein Gerät hier."}
                  </div>
                  {status?.attempts?.length ? (
                    <div className="mt-1 rounded-lg border border-white/10 bg-black/30 px-2 py-1.5">
                      <div className="text-[11px] text-white/50 mb-0.5">
                        Was bei Jon ankommt:
                      </div>
                      {status.attempts.slice(0, 4).map((attempt, index) => (
                        <div key={index} className="text-[11px] text-white/60">
                          <span className="font-mono text-white/45">{attempt.source}</span>{" "}
                          <span className="text-white/35">{attempt.transport.toUpperCase()}</span>{" "}
                          {attempt.detail}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="mt-1 text-[11px] text-amber-200/70">
                      Bei Jon ist bisher kein einziger Versuch angekommen — dein Handy
                      erreicht ihn also gar nicht. Das ist Netzwerk oder Firewall, nicht
                      Linphone.
                    </div>
                  )}
                </li>
                <li>
                  <b className="text-white/90">6. Testanruf</b>
                  <div className="text-white/50">
                    Oben auf „Testanruf“ — dein Handy muss klingeln.
                  </div>
                </li>
              </ol>

              <details className="text-[12px] text-white/60">
                <summary className="cursor-pointer text-white/70">
                  Linphone hängt auf „Verbindung wird hergestellt“?
                </summary>
                <ol className="mt-2 space-y-1.5 pl-4 list-decimal text-white/50">
                  <li>
                    <b className="text-white/70">Erreicht das Handy den PC?</b> Im
                    Handy-Browser{" "}
                    <span className="font-mono text-white/70">
                      http://{setup?.server ?? "…"}:8756/api/health
                    </span>{" "}
                    aufrufen. Kommt nichts, liegt es am Netzwerk — gleiches WLAN? Gast-WLAN?
                    Manche Router trennen Geräte voneinander („AP-Isolation“).
                  </li>
                  <li>
                    <b className="text-white/70">Stimmt die Adresse?</b> Oben die
                    WLAN-Adresse wählen, keine VPN- oder virtuelle.
                  </li>
                  <li>
                    <b className="text-white/70">Firewall?</b> Den Befehl aus der Ampel
                    ausführen.
                  </li>
                  <li>
                    <b className="text-white/70">Passwort exakt?</b> Kopieren statt tippen.
                  </li>
                </ol>
              </details>

              <div className="border-t border-white/10 pt-3 space-y-2">
                <div className="text-[12px] text-white/70">
                  <b className="text-white/90">📱 Von unterwegs, mit mobilen Daten</b>
                  <div className="text-white/50">
                    Installiere <a className="text-[#f7e4a8]" href="https://tailscale.com/download/windows" target="_blank" rel="noreferrer">Tailscale</a>{" "}
                    auf dem PC und auf dem Handy, beide mit demselben Konto. Dann trägst
                    du in Linphone die Tailscale-Adresse als Domain ein — die gilt zu
                    Hause genauso wie unterwegs. Steht die Adresse oben auf
                    „Automatisch“, musst du beim Verlassen des Hauses nichts umstellen.
                    Gib den SIP-Port <b>niemals</b> im Router frei.
                  </div>
                </div>
                <div className="text-[12px] text-white/70">
                  <b className="text-white/90">☎️ Jon anrufen</b>
                  <div className="text-white/50">
                    Ruf in Linphone einfach{" "}
                    <span className="font-mono text-white/80">
                      {setup?.username ?? "…"}
                    </span>{" "}
                    an — Jon hebt ab und begrüßt dich. Ohne gültiges SIP-Passwort nimmt
                    er nichts an.
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {tab === "log" ? (
            <div className="space-y-2">
              {history.length === 0 ? (
                <div className="text-[12px] text-white/40">Noch keine Anrufe.</div>
              ) : null}
              {history.map((entry) => (
                <div
                  key={`${entry.id}-${entry.started_at}`}
                  className="rounded-lg border border-white/10 bg-white/5 px-3 py-2"
                >
                  <div className="flex items-center gap-2 text-[12px]">
                    <span className="text-white/80">
                      {STATUS_LABEL[entry.status] ?? entry.status}
                    </span>
                    <span className="text-white/40">{entry.started_at?.replace("T", " ")}</span>
                    <span className="ml-auto text-white/40">{entry.duration}s</span>
                  </div>
                  {entry.reason ? (
                    <div className="text-[11px] text-white/40">{entry.reason}</div>
                  ) : null}
                  {entry.transcript?.length ? (
                    <div className="mt-2 space-y-0.5 text-[11px]">
                      {entry.transcript.map((line, index) => (
                        <div key={index}>
                          <span className={line.who === "jon" ? "text-[#f7e4a8]" : "text-white/60"}>
                            {line.who === "jon" ? "Jon" : "Du"}:
                          </span>{" "}
                          <span className="text-white/70">{line.text}</span>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
              {history.length ? (
                <button
                  onClick={() =>
                    guard("clear", async () => {
                      await clearPhoneHistory();
                      setHistory([]);
                    })
                  }
                  className="px-3 py-1.5 rounded-lg text-[11px] bg-white/10 border border-white/15 text-white/60"
                >
                  Verlauf löschen
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
