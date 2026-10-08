import Symbol from "./Symbol";
import { useEffect, useState } from "react";
import {
  ProviderStatus,
  Stunde,
  UserSettings,
  getProviders,
  saveUserSettings,
  stundenplanLaden,
  stundenplanLoeschen,
  stundenplanSpeichern,
} from "../lib/api";

const WOCHE = ["montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag"];
import GeraetePanel from "./GeraetePanel";
import HandyModal from "./HandyModal";

interface Props {
  settings: UserSettings;
  onClose: () => void;
}

const field =
  "w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-[12px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50";

export default function ConnectionsModal({ settings, onClose }: Props) {
  const [form, setForm] = useState({
    mail_imap_host: settings.mail_imap_host ?? "",
    mail_imap_user: settings.mail_imap_user ?? "",
    mail_imap_password: settings.mail_imap_password ?? "",
    mail_smtp_host: settings.mail_smtp_host ?? "",
    mail_smtp_port: settings.mail_smtp_port ?? 587,
    calendar_ics_url: settings.calendar_ics_url ?? "",
    telegram_bot_token: settings.telegram_bot_token ?? "",
    mini_jon_bot_token: settings.mini_jon_bot_token ?? "",
    telegram_chat_id: settings.telegram_chat_id ?? "",
    telegram_provider: settings.telegram_provider ?? "",
    telegram_model: settings.telegram_model ?? "",
    telegram_morning: settings.telegram_morning ?? false,
    telegram_aktionsvideo: settings.telegram_aktionsvideo ?? true,
    telegram_morning_time: settings.telegram_morning_time ?? "07:30",
    telegram_morgen_stundenplan: settings.telegram_morgen_stundenplan ?? false,
    ha_url: settings.ha_url ?? "",
    ha_token: settings.ha_token ?? "",
    spotify_client_id: settings.spotify_client_id ?? "",
    spotify_client_secret: settings.spotify_client_secret ?? "",
    relay_enabled: settings.relay_enabled ?? false,
    relay_broker: settings.relay_broker ?? "broker.hivemq.com",
  });
  const [saved, setSaved] = useState(false);
  const [kopplung, setKopplung] = useState(false);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [plan, setPlan] = useState<Record<string, Stunde[]>>({});
  const [planText, setPlanText] = useState("");
  const [planMeldung, setPlanMeldung] = useState("");
  const [planLaeuft, setPlanLaeuft] = useState(false);
  const [zusaetze, setZusaetze] = useState<string[]>(settings.telegram_morgen_zusaetze ?? []);

  useEffect(() => {
    void stundenplanLaden()
      .then((d) => setPlan(d.tage))
      .catch(() => setPlan({}));
  }, []);

  const planSpeichern = async () => {
    if (!planText.trim()) return;
    setPlanLaeuft(true);
    setPlanMeldung("");
    try {
      const d = await stundenplanSpeichern(planText);
      setPlan(d.tage);
      setPlanText("");
      setPlanMeldung("Stundenplan gespeichert.");
    } catch (fehler) {
      setPlanMeldung(String((fehler as Error).message || fehler));
    } finally {
      setPlanLaeuft(false);
    }
  };

  const planEntfernen = async () => {
    await stundenplanLoeschen();
    setPlan({});
    setPlanMeldung("Stundenplan gelöscht.");
  };

  const zusatzEntfernen = (eintrag: string) => {
    const rest = zusaetze.filter((z) => z !== eintrag);
    setZusaetze(rest);
    void saveUserSettings({ telegram_morgen_zusaetze: rest });
  };

  const planTage = WOCHE.filter((tag) => (plan[tag] ?? []).length > 0);

  useEffect(() => {
    void getProviders()
      .then(setProviders)
      .catch(() => setProviders([]));
  }, []);

  const jonsAnbieter = settings.provider || "nvidia";
  const telegramAnbieter = form.telegram_provider || jonsAnbieter;
  const verfuegbar = providers.filter((p) => p.configured);
  const telegramModelle =
    providers.find((p) => p.provider === telegramAnbieter)?.models ?? [];
  const ollamaLeer =
    telegramAnbieter === "ollama" &&
    providers.length > 0 &&
    telegramModelle.length === 0;

  const set = (key: keyof typeof form, value: string | number | boolean) => {
    setForm((f) => ({ ...f, [key]: value }));
    setSaved(false);
  };

  const save = async () => {
    await saveUserSettings({
      ...form,
      mail_smtp_port: Number(form.mail_smtp_port) || 587,
    });
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[560px] max-w-[92vw] max-h-[86vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <div>
            <div className="text-white/90 font-semibold"><Symbol zeichen="🔌" /> Verbindungen</div>
            <div className="text-[11px] text-white/40">
              Alles kostenlos. Daten bleiben lokal auf deinem PC.
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
          <section className="space-y-2">
            <div className="text-[11px] uppercase tracking-wide text-gold/70">
              <Symbol zeichen="📱" /> Geräte
            </div>
            <GeraetePanel onPair={() => setKopplung(true)} />
          </section>

          <section className="space-y-2">
            <div className="text-[11px] uppercase tracking-wide text-gold/70">
              <Symbol zeichen="📧" /> E-Mail (IMAP/SMTP)
            </div>
            <p className="text-[11px] text-white/40 leading-relaxed">
              Gmail: Server <code>imap.gmail.com</code>, und statt deines
              Passworts ein{" "}
              <span className="text-gold/70">App-Passwort</span> (Google-Konto →
              Sicherheit → App-Passwörter). GMX/Web.de: IMAP erst in den
              Einstellungen freischalten.
            </p>
            <input
              className={field}
              placeholder="IMAP-Server (z. B. imap.gmail.com)"
              value={form.mail_imap_host}
              onChange={(e) => set("mail_imap_host", e.target.value)}
            />
            <input
              className={field}
              placeholder="E-Mail-Adresse"
              value={form.mail_imap_user}
              onChange={(e) => set("mail_imap_user", e.target.value)}
            />
            <input
              className={field}
              type="password"
              placeholder="App-Passwort"
              value={form.mail_imap_password}
              onChange={(e) => set("mail_imap_password", e.target.value)}
            />
            <div className="flex gap-2">
              <input
                className={field}
                placeholder="SMTP-Server (leer = automatisch)"
                value={form.mail_smtp_host}
                onChange={(e) => set("mail_smtp_host", e.target.value)}
              />
              <input
                className={`${field} w-24`}
                placeholder="587"
                value={form.mail_smtp_port}
                onChange={(e) => set("mail_smtp_port", e.target.value)}
              />
            </div>
          </section>

          <section className="space-y-2">
            <div className="text-[11px] uppercase tracking-wide text-gold/70">
              <Symbol zeichen="📅" /> Kalender (ICS)
            </div>
            <p className="text-[11px] text-white/40 leading-relaxed">
              Google Kalender → Einstellungen → Kalender → „Geheime Adresse im
              iCal-Format" kopieren. Funktioniert auch mit Outlook, Apple und
              Nextcloud.
            </p>
            <input
              className={field}
              placeholder="https://calendar.google.com/calendar/ical/.../basic.ics"
              value={form.calendar_ics_url}
              onChange={(e) => set("calendar_ics_url", e.target.value)}
            />
          </section>

          <section className="space-y-2">
            <div className="text-[11px] uppercase tracking-wide text-gold/70">
              <Symbol zeichen="📲" /> Telegram (Fernbedienung)
            </div>
            <p className="text-[11px] text-white/40 leading-relaxed">
              In Telegram <code>@BotFather</code> anschreiben → <code>/newbot</code>{" "}
              → Token hier einfügen. Danach deinem eigenen Bot{" "}
              <code>/start</code> schreiben — der erste Chat wird automatisch mit
              deinem PC verknüpft.
            </p>
            <input
              className={field}
              type="password"
              placeholder="Bot-Token von @BotFather"
              value={form.telegram_bot_token}
              onChange={(e) => set("telegram_bot_token", e.target.value)}
            />
            {form.telegram_chat_id && (
              <div className="text-[11px] text-emerald-300/80">
                ✓ Verknüpft mit Chat {form.telegram_chat_id}
                <button
                  onClick={() => set("telegram_chat_id", "")}
                  className="ml-2 text-white/40 hover:text-red-300"
                >
                  trennen
                </button>
              </div>
            )}
            <div className="text-[11px] text-white/40 pt-1">
              KI für Telegram — unabhängig von der App. Wähle zum Beispiel{" "}
              <code>ollama</code>, dann antwortet Jon in Telegram lokal über
              Ollama, auch wenn er in der App eine API wie NVIDIA benutzt.
              Antwortet ein Anbieter nicht, springt Jon auf ein Ersatzmodell und
              zuletzt auf Ollama. Unterwegs wechselst du mit{" "}
              <code>/anbieter</code> und <code>/modell</code> direkt im Chat.
            </div>
            <div className="flex gap-2">
              <select
                className={`${field} [&>option]:bg-zinc-900`}
                value={form.telegram_provider}
                onChange={(e) => {
                  set("telegram_provider", e.target.value);
                  set("telegram_model", "");
                }}
              >
                <option value="">Wie Jon ({jonsAnbieter})</option>
                {verfuegbar.map((p) => (
                  <option key={p.provider} value={p.provider}>
                    {p.label || p.provider}
                  </option>
                ))}
              </select>
              <select
                className={`${field} [&>option]:bg-zinc-900`}
                value={form.telegram_model}
                onChange={(e) => set("telegram_model", e.target.value)}
              >
                <option value="">Automatisch</option>
                {form.telegram_model &&
                  !telegramModelle.includes(form.telegram_model) && (
                    <option value={form.telegram_model}>
                      {form.telegram_model}
                    </option>
                  )}
                {telegramModelle.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
            {ollamaLeer && (
              <div className="text-[11px] text-amber-300/80">
                Ollama liefert gerade keine Modelle. Starte Ollama und lade ein
                Modell, z. B. <code>ollama pull gemma3</code>.
              </div>
            )}
            <div className="text-[11px] text-white/40">
              Der Bot merkt sich eure Gespräche dauerhaft und kennt Jons
              Gedächtnis (MEMORY.md).
            </div>
            <div className="flex items-center justify-between pt-2">
              <div className="text-[12px] text-white/70">
                <Symbol zeichen="🎬" /> Video nach Aktionen
              </div>
              <button
                onClick={() =>
                  set("telegram_aktionsvideo", !form.telegram_aktionsvideo)
                }
                className={`w-9 h-5 rounded-full flex items-center px-0.5 transition-colors ${
                  form.telegram_aktionsvideo ? "bg-gold/70" : "bg-white/15"
                }`}
              >
                <span
                  className={`w-4 h-4 rounded-full bg-white transition-transform ${
                    form.telegram_aktionsvideo ? "translate-x-4" : ""
                  }`}
                />
              </button>
            </div>
            <p className="text-[11px] text-white/40 leading-relaxed">
              Benutzt Jon auf deinen Wunsch Maus, Tastatur oder Programme, nimmt
              er den Bildschirm dabei auf und schickt dir das Video. Mit{" "}
              <code>/live</code> siehst du den Bildschirm laufend als Video,{" "}
              <code>/video</code> schickt sofort ein kurzes Stück. Braucht
              ffmpeg für die beste Qualität.
            </p>
            <div className="flex items-center justify-between pt-2">
              <div className="text-[12px] text-white/70">
                <Symbol zeichen="🌅" /> Guten-Morgen-Sprachnachricht
              </div>
              <button
                onClick={() => set("telegram_morning", !form.telegram_morning)}
                className={`w-9 h-5 rounded-full flex items-center px-0.5 transition-colors ${
                  form.telegram_morning ? "bg-gold/70" : "bg-white/15"
                }`}
              >
                <span
                  className={`w-4 h-4 rounded-full bg-white transition-transform ${
                    form.telegram_morning ? "translate-x-4" : ""
                  }`}
                />
              </button>
            </div>
            <p className="text-[11px] text-white/40 leading-relaxed">
              Jon schickt dir jeden Morgen zur Wunschzeit eine persönliche
              Sprachnachricht mit Wetter, Terminen und Erinnerungen. Schick ihm
              auch selbst Sprachnachrichten — er versteht sie. Mit{" "}
              <code>/stimme</code> antwortet er dir immer per Sprachnachricht.
            </p>
            {form.telegram_morning && (
              <input
                type="time"
                className={field}
                value={form.telegram_morning_time}
                onChange={(e) => set("telegram_morning_time", e.target.value)}
              />
            )}
            {form.telegram_morning && (
              <label className="flex items-center gap-2 text-[12px] text-white/80 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.telegram_morgen_stundenplan}
                  onChange={(e) => set("telegram_morgen_stundenplan", e.target.checked)}
                />
                Stundenplan des Tages mitschicken
              </label>
            )}
            {zusaetze.length > 0 && (
              <div className="space-y-1">
                <div className="text-[11px] text-white/50">Außerdem jeden Morgen:</div>
                {zusaetze.map((z) => (
                  <div key={z} className="flex items-center justify-between gap-2 px-2 py-1 rounded-lg bg-white/5 text-[11.5px] text-white/80">
                    <span className="truncate">{z}</span>
                    <button onClick={() => zusatzEntfernen(z)} className="text-white/40 hover:text-white text-[13px]" aria-label="Entfernen">
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
            <div className="text-[11px] uppercase tracking-wide text-gold/70 pt-3">
              <Symbol zeichen="📅" /> Stundenplan
            </div>
            <p className="text-[11px] text-white/40 leading-relaxed">
              Schreib Jon einfach im Chat oder auf Telegram: „Schick mir jeden Morgen meinen
              Stundenplan mit" - oder trag ihn hier ein, z. B. „Montag: 8:00 Mathe, 8:50 Deutsch".
              Ein Foto oder PDF vom Stundenplan kannst du Jon auch im Chat schicken.
            </p>
            {planTage.length > 0 && (
              <div className="grid grid-cols-2 gap-2">
                {planTage.map((tag) => (
                  <div key={tag} className="rounded-lg bg-white/5 px-2 py-1.5">
                    <div className="text-[11px] text-gold/80 capitalize">{tag}</div>
                    {(plan[tag] ?? []).map((s, i) => (
                      <div key={i} className="text-[11px] text-white/70 truncate">
                        {s.von ? `${s.von} ` : ""}
                        {s.fach}
                        {s.raum ? ` (${s.raum})` : ""}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
            <textarea
              className={`${field} min-h-[70px]`}
              placeholder={planTage.length ? "Neuen Stundenplan eintragen (ersetzt den alten)" : "Stundenplan eintragen"}
              value={planText}
              onChange={(e) => setPlanText(e.target.value)}
            />
            <div className="flex items-center gap-2">
              <button
                disabled={planLaeuft || !planText.trim()}
                onClick={() => void planSpeichern()}
                className="px-3 py-1.5 rounded-lg border border-gold/30 bg-gold/10 hover:bg-gold/20 text-[12px] text-gold/90 disabled:opacity-50"
              >
                {planLaeuft ? "Jon liest den Plan …" : "Stundenplan speichern"}
              </button>
              {planTage.length > 0 && (
                <button onClick={() => void planEntfernen()} className="px-3 py-1.5 rounded-lg text-[12px] text-white/50 hover:text-white">
                  Löschen
                </button>
              )}
              {planMeldung && <span className="text-[11px] text-white/60">{planMeldung}</span>}
            </div>
            <div className="text-[11px] uppercase tracking-wide text-gold/70 pt-3">
              <Symbol zeichen="👥" /> Gruppen & Mini Jon
            </div>
            <p className="text-[11px] text-white/40 leading-relaxed">
              Füge Jon (und Mini Jon) einfach zu einer Telegram-Gruppe hinzu:
              Sie lesen dort still mit, um den Kontext zu verstehen, und
              antworten nur, wenn jemand sie mit ihrem{" "}
              <code>@Benutzernamen</code> erwähnt — beide Bots können
              gleichzeitig in derselben Gruppe sein. Damit sie wirklich alles
              mitlesen können, bei <code>@BotFather</code> für jeden Bot{" "}
              <code>/setprivacy</code> → <code>Disable</code> setzen. Mini Jon
              braucht einen eigenen Bot (<code>/newbot</code>):
            </p>
            <input
              className={field}
              type="password"
              placeholder="Bot-Token für Mini Jon (optional)"
              value={form.mini_jon_bot_token}
              onChange={(e) => set("mini_jon_bot_token", e.target.value)}
            />
            <p className="text-[11px] text-white/40 leading-relaxed">
              Mini Jon kennt <code>/schlafen</code> und <code>/aufwachen</code>{" "}
              — schläft er, zeigt er statt einer Antwort seine
              Schlaf-Animation mit geschlossenen Augen (auch auf dem
              Bildschirm schläft er dann sichtbar).
            </p>
          </section>

          <section className="space-y-2">
            <div className="text-[11px] uppercase tracking-wide text-gold/70">
              <Symbol zeichen="🌍" /> Freunde-Chat übers Internet
            </div>
            <p className="text-[11px] text-white/40 leading-relaxed">
              Ohne Relay erreichst du nur Freunde im selben WLAN. Mit Relay
              kannst du auch Freunden in einer anderen Stadt schreiben — sie
              tragen deinen <span className="text-gold/70">Jon-Code</span> ein
              (steht im Chat oben links). Kostenlos, und weil alles Ende-zu-Ende
              verschlüsselt ist, sieht der Relay-Server nur unlesbaren Datensalat.
            </p>
            <button
              onClick={() => set("relay_enabled", !form.relay_enabled)}
              className="w-full flex items-center justify-between px-3 py-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 transition-colors"
            >
              <span className="text-[12px] text-white/90">Relay verwenden</span>
              <span
                className={`w-9 h-5 rounded-full flex items-center px-0.5 transition-colors ${
                  form.relay_enabled ? "bg-gold/70" : "bg-white/15"
                }`}
              >
                <span
                  className={`w-4 h-4 rounded-full bg-white transition-transform ${
                    form.relay_enabled ? "translate-x-4" : ""
                  }`}
                />
              </span>
            </button>
            <input
              className={field}
              placeholder="broker.hivemq.com"
              value={form.relay_broker}
              onChange={(e) => set("relay_broker", e.target.value)}
            />
          </section>

          <section className="space-y-2">
            <div className="text-[11px] uppercase tracking-wide text-gold/70">
              <Symbol zeichen="🎧" /> Spotify
            </div>
            <p className="text-[11px] text-white/40 leading-relaxed">
              Auf{" "}
              <code>developer.spotify.com/dashboard</code> einloggen → „Create
              app" → beliebiger Name, Redirect-URI{" "}
              <code>http://localhost</code> → Client-ID und Secret kopieren.
              Kostenlos, <span className="text-gold/70">auch ohne Premium</span>:
              Jon sucht den Song und startet ihn in deiner Spotify-App.
            </p>
            <input
              className={field}
              placeholder="Client ID"
              value={form.spotify_client_id}
              onChange={(e) => set("spotify_client_id", e.target.value)}
            />
            <input
              className={field}
              type="password"
              placeholder="Client Secret"
              value={form.spotify_client_secret}
              onChange={(e) => set("spotify_client_secret", e.target.value)}
            />
          </section>

          <section className="space-y-2">
            <div className="text-[11px] uppercase tracking-wide text-gold/70">
              <Symbol zeichen="🏠" /> Smart Home (Home Assistant)
            </div>
            <p className="text-[11px] text-white/40 leading-relaxed">
              In Home Assistant: Profil (unten links) → Sicherheit →
              „Langlebiges Zugriffstoken" erstellen.
            </p>
            <input
              className={field}
              placeholder="http://homeassistant.local:8123"
              value={form.ha_url}
              onChange={(e) => set("ha_url", e.target.value)}
            />
            <input
              className={field}
              type="password"
              placeholder="Langzeit-Token"
              value={form.ha_token}
              onChange={(e) => set("ha_token", e.target.value)}
            />
          </section>
        </div>

        <div className="flex items-center justify-between px-5 py-3 border-t border-white/10">
          <span className="text-[11px] text-emerald-300/80">
            {saved ? "Gespeichert ✓" : ""}
          </span>
          <button
            onClick={() => void save()}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[13px] shadow-gold hover:brightness-110 transition"
          >
            Speichern
          </button>
        </div>
      </div>
      {kopplung && <HandyModal onClose={() => setKopplung(false)} />}
    </div>
  );
}
