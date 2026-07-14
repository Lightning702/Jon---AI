import { useState } from "react";
import { UserSettings, saveUserSettings } from "../lib/api";

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
    telegram_chat_id: settings.telegram_chat_id ?? "",
    telegram_model: settings.telegram_model ?? "openai/gpt-oss-20b",
    telegram_morning: settings.telegram_morning ?? false,
    telegram_morning_time: settings.telegram_morning_time ?? "07:30",
    ha_url: settings.ha_url ?? "",
    ha_token: settings.ha_token ?? "",
    spotify_client_id: settings.spotify_client_id ?? "",
    spotify_client_secret: settings.spotify_client_secret ?? "",
    relay_enabled: settings.relay_enabled ?? false,
    relay_broker: settings.relay_broker ?? "broker.hivemq.com",
  });
  const [saved, setSaved] = useState(false);

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
            <div className="text-white/90 font-semibold">🔌 Verbindungen</div>
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
              📧 E-Mail (IMAP/SMTP)
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
              📅 Kalender (ICS)
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
              📲 Telegram (Fernbedienung)
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
              Modell für Telegram (unterwegs zählt Tempo — in der App gilt weiter
              dein normal gewähltes Modell). Wechselt Jon in der App zu einem
              anderen Anbieter als NVIDIA, übernimmt Telegram automatisch Jons
              Anbieter und Modell. Der Bot merkt sich eure Gespräche dauerhaft
              und kennt Jons Gedächtnis (MEMORY.md):
            </div>
            <input
              className={field}
              placeholder="openai/gpt-oss-20b"
              value={form.telegram_model}
              onChange={(e) => set("telegram_model", e.target.value)}
            />
            <div className="flex items-center justify-between pt-2">
              <div className="text-[12px] text-white/70">
                🌅 Guten-Morgen-Sprachnachricht
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
          </section>

          <section className="space-y-2">
            <div className="text-[11px] uppercase tracking-wide text-gold/70">
              🌍 Freunde-Chat übers Internet
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
              🎧 Spotify
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
              🏠 Smart Home (Home Assistant)
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
    </div>
  );
}
