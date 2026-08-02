import { useEffect, useRef, useState } from "react";
import {
  OllamaConfig,
  OllamaHost,
  OllamaStatus,
  getOllamaConfig,
  getOllamaHosts,
  getOllamaModels,
  getOllamaStatus,
  resetOllamaConfig,
  saveOllamaConfig,
  testOllama,
} from "../lib/api";
import OllamaSharePanel from "./OllamaSharePanel";

interface Props {
  onClose: () => void;
}

interface Form {
  enabled: boolean;
  scheme: string;
  host: string;
  port: string;
  model: string;
  temperature: string;
  top_p: string;
  top_k: string;
  max_tokens: string;
  context_length: string;
  keep_alive: string;
  seed: string;
  system_prompt: string;
  stream: boolean;
  timeout: string;
  auto_reconnect: boolean;
  auto_load_models: boolean;
}

const field =
  "w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-[12px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50";
const label = "text-[11px] text-white/45 px-0.5";
const section = "text-[11px] uppercase tracking-wide text-gold/70";

function toForm(config: OllamaConfig): Form {
  return {
    enabled: config.enabled,
    scheme: config.scheme,
    host: config.host,
    port: String(config.port),
    model: config.model,
    temperature: String(config.temperature),
    top_p: String(config.top_p),
    top_k: String(config.top_k),
    max_tokens: String(config.max_tokens),
    context_length: String(config.context_length),
    keep_alive: config.keep_alive,
    seed: String(config.seed),
    system_prompt: config.system_prompt,
    stream: config.stream,
    timeout: String(config.timeout),
    auto_reconnect: config.auto_reconnect,
    auto_load_models: config.auto_load_models,
  };
}

function toPayload(form: Form): Partial<OllamaConfig> {
  return {
    enabled: form.enabled,
    scheme: form.scheme,
    host: form.host.trim(),
    port: Number(form.port),
    model: form.model,
    temperature: Number(form.temperature),
    top_p: Number(form.top_p),
    top_k: Number(form.top_k),
    max_tokens: Number(form.max_tokens),
    context_length: Number(form.context_length),
    keep_alive: form.keep_alive.trim(),
    seed: Number(form.seed),
    system_prompt: form.system_prompt,
    stream: form.stream,
    timeout: Number(form.timeout),
    auto_reconnect: form.auto_reconnect,
    auto_load_models: form.auto_load_models,
  };
}

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

function Dot({ state }: { state: string }) {
  const color =
    state === "online"
      ? "bg-emerald-400"
      : state === "connecting"
      ? "bg-amber-400 animate-pulse"
      : state === "disabled"
      ? "bg-white/30"
      : "bg-red-400";
  return <span className={`w-2 h-2 rounded-full ${color}`} />;
}

function moment(value: string): string {
  if (!value) return "noch keine";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function stateText(state: string): string {
  if (state === "online") return "Online";
  if (state === "connecting") return "Verbinde …";
  if (state === "disabled") return "Ausgeschaltet";
  return "Offline";
}

export default function OllamaModal({ onClose }: Props) {
  const [form, setForm] = useState<Form | null>(null);
  const [status, setStatus] = useState<OllamaStatus | null>(null);
  const [models, setModels] = useState<string[]>([]);
  const [hosts, setHosts] = useState<OllamaHost[]>([]);
  const [urlText, setUrlText] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    void (async () => {
      try {
        const config = await getOllamaConfig();
        if (!alive.current) return;
        setForm(toForm(config));
        setUrlText(config.url);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        return;
      }
      void getOllamaHosts().then((list) => alive.current && setHosts(list));
      await refresh(false);
    })();
    const timer = window.setInterval(() => void refresh(false), 15000);
    return () => {
      alive.current = false;
      window.clearInterval(timer);
    };
  }, []);

  const refresh = async (force: boolean) => {
    try {
      const next = await getOllamaStatus(force);
      if (!alive.current) return;
      setStatus(next);
      if (next.models.length) setModels(next.models);
    } catch {
      if (alive.current) setStatus(null);
    }
  };

  const set = <K extends keyof Form>(key: K, value: Form[K]) => {
    setForm((current) => {
      if (!current) return current;
      const next = { ...current, [key]: value };
      if (key === "host" || key === "port" || key === "scheme") {
        setUrlText(`${next.scheme}://${next.host}:${next.port}`);
      }
      return next;
    });
    setNote("");
    setError("");
  };

  const setUrl = (raw: string) => {
    setUrlText(raw);
    setNote("");
    setError("");
    const match = raw
      .trim()
      .match(/^(?:(https?):\/\/)?(\[[^\]]+\]|[^:/\s]+)(?::(\d+))?\/?$/i);
    if (!match) return;
    setForm((current) =>
      current
        ? {
            ...current,
            scheme: (match[1] || current.scheme).toLowerCase(),
            host: match[2].replace(/^\[|\]$/g, ""),
            port: match[3] || current.port,
          }
        : current
    );
  };

  const save = async (): Promise<boolean> => {
    if (!form) return false;
    setBusy(true);
    setError("");
    try {
      const config = await saveOllamaConfig(toPayload(form));
      setForm(toForm(config));
      setUrlText(config.url);
      setNote("Gespeichert ✓");
      window.setTimeout(() => alive.current && setNote(""), 2500);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const test = async () => {
    if (!(await save())) return;
    setConnecting(true);
    setStatus((current) => (current ? { ...current, state: "connecting" } : current));
    try {
      const result = await testOllama();
      if (!alive.current) return;
      setStatus(result);
      if (result.models.length) setModels(result.models);
      setNote(
        result.state === "online"
          ? `Verbunden mit ${result.url} in ${result.response_ms} ms`
          : ""
      );
      if (result.state !== "online") setError(result.error);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      if (alive.current) setConnecting(false);
    }
  };

  const reloadModels = async () => {
    setBusy(true);
    try {
      const result = await getOllamaModels(true);
      if (!alive.current) return;
      setModels(result.models);
      setNote(
        result.models.length
          ? `${result.models.length} Modelle geladen`
          : "Keine Modelle gefunden — auf dem Server: ollama pull <modell>"
      );
    } finally {
      if (alive.current) setBusy(false);
    }
  };

  const reset = async () => {
    setBusy(true);
    try {
      const config = await resetOllamaConfig();
      setForm(toForm(config));
      setUrlText(config.url);
      setNote("Auf Standard zurückgesetzt");
      await refresh(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      if (alive.current) setBusy(false);
    }
  };

  const pickHost = (host: string) => {
    set("host", host);
  };

  const state = connecting ? "connecting" : status?.state ?? "offline";
  const url = form ? `${form.scheme}://${form.host}:${form.port}` : "";

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[620px] max-w-[94vw] max-h-[88vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <div>
            <div className="text-white/90 font-semibold">🦙 Ollama</div>
            <div className="text-[11px] text-white/40">
              Modelle laufen auf deinem eigenen Rechner oder auf einem Server im
              Netzwerk. Kostenlos, ohne Schlüssel, ohne Cloud.
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition-colors"
          >
            ✕
          </button>
        </div>

        {!form ? (
          <div className="px-5 py-8 text-[12px] text-white/50">
            {error || "Lade Einstellungen …"}
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
              <section className="space-y-2">
                <div className="flex items-center gap-2">
                  <Dot state={state} />
                  <span className="text-[13px] text-white/90">
                    {stateText(state)}
                  </span>
                  <span className="text-[11px] text-white/40">{status?.url || url}</span>
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] text-white/50">
                  <div>
                    Antwortzeit:{" "}
                    <span className="text-white/80">
                      {status && status.response_ms ? `${status.response_ms} ms` : "—"}
                    </span>
                  </div>
                  <div>
                    Ollama-Version:{" "}
                    <span className="text-white/80">{status?.version || "—"}</span>
                  </div>
                  <div>
                    Gewähltes Modell:{" "}
                    <span className="text-white/80">{form.model || "—"}</span>
                  </div>
                  <div>
                    Installierte Modelle:{" "}
                    <span className="text-white/80">{status?.model_count ?? 0}</span>
                  </div>
                  <div className="col-span-2">
                    Letzte erfolgreiche Verbindung:{" "}
                    <span className="text-white/80">
                      {moment(status?.last_success ?? "")}
                    </span>
                  </div>
                </div>
                {status?.error && state !== "online" && (
                  <div className="text-[11px] text-amber-300/90 leading-relaxed">
                    {status.error}
                  </div>
                )}
                <div className="flex gap-2 pt-1">
                  <button
                    onClick={() => void test()}
                    disabled={busy || connecting}
                    className="flex-1 text-[12px] py-2 rounded-xl border border-gold/30 bg-gold/10 text-gold/90 hover:bg-gold/20 transition disabled:opacity-50"
                  >
                    Verbindung testen
                  </button>
                  <button
                    onClick={() => void refresh(true)}
                    disabled={busy || connecting}
                    className="flex-1 text-[12px] py-2 rounded-xl border border-white/10 bg-white/5 text-white/70 hover:bg-white/10 transition disabled:opacity-50"
                  >
                    Status aktualisieren
                  </button>
                </div>
              </section>

              <section className="space-y-2">
                <div className={section}>Server</div>
                <Switch
                  text="Ollama verwenden"
                  hint="Schaltet Ollama als Anbieter in Jon an oder aus."
                  on={form.enabled}
                  onClick={() => set("enabled", !form.enabled)}
                />
                <div className={label}>Server-URL</div>
                <input
                  className={field}
                  placeholder="http://127.0.0.1:11434"
                  value={urlText}
                  onChange={(e) => setUrl(e.target.value)}
                />
                <div className="flex gap-2">
                  <div className="flex-1">
                    <div className={label}>Host / IP</div>
                    <input
                      className={field}
                      placeholder="127.0.0.1"
                      value={form.host}
                      onChange={(e) => set("host", e.target.value)}
                    />
                  </div>
                  <div className="w-28">
                    <div className={label}>Port</div>
                    <input
                      className={field}
                      placeholder="11434"
                      value={form.port}
                      onChange={(e) => set("port", e.target.value)}
                    />
                  </div>
                  <div className="w-28">
                    <div className={label}>Protokoll</div>
                    <select
                      value={form.scheme}
                      onChange={(e) => set("scheme", e.target.value)}
                      className={`${field} [&>option]:bg-zinc-900`}
                    >
                      <option value="http">http</option>
                      <option value="https">https</option>
                    </select>
                  </div>
                </div>
                {hosts.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {hosts.map((item) => (
                      <button
                        key={item.host}
                        title={item.hint}
                        onClick={() => pickHost(item.host)}
                        className="text-[11px] px-2 py-1 rounded-lg border border-white/10 bg-white/5 text-white/60 hover:bg-white/10 transition"
                      >
                        {item.label}: {item.host}
                      </button>
                    ))}
                  </div>
                )}
                <p className="text-[11px] text-white/40 leading-relaxed">
                  Läuft Ollama auf einem anderen PC, im Heimnetz oder über
                  Tailscale, trägst du hier einfach dessen Adresse und Port ein.
                  Auf dem Server muss dafür{" "}
                  <code>OLLAMA_HOST=0.0.0.0</code> gesetzt und Port {form.port} in
                  der Firewall offen sein.
                </p>
              </section>

              <section className="space-y-2">
                <div className={section}>Modell</div>
                <div className="flex gap-2">
                  <select
                    value={form.model}
                    onChange={(e) => set("model", e.target.value)}
                    className={`${field} [&>option]:bg-zinc-900`}
                  >
                    <option value="">Kein Modell gewählt</option>
                    {(models.includes(form.model) || !form.model
                      ? models
                      : [form.model, ...models]
                    ).map((name) => (
                      <option key={name} value={name}>
                        {name}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => void reloadModels()}
                    disabled={busy}
                    className="px-3 text-[12px] rounded-xl border border-white/10 bg-white/5 text-white/70 hover:bg-white/10 transition disabled:opacity-50"
                  >
                    Neu laden
                  </button>
                </div>
                <Switch
                  text="Modelle automatisch laden"
                  hint="Jon holt die Modell-Liste beim Start und beim Öffnen dieses Fensters selbst vom Server."
                  on={form.auto_load_models}
                  onClick={() => set("auto_load_models", !form.auto_load_models)}
                />
                <p className="text-[11px] text-white/40 leading-relaxed">
                  Neue Modelle installierst du auf dem Server mit{" "}
                  <code>ollama pull llama3.2</code>. Danach hier auf „Neu laden“.
                </p>
              </section>

              <section className="space-y-2">
                <div className={section}>Antwortverhalten</div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <div className={label}>Temperatur (0 – 2)</div>
                    <input
                      className={field}
                      value={form.temperature}
                      onChange={(e) => set("temperature", e.target.value)}
                    />
                  </div>
                  <div>
                    <div className={label}>Top P (0 – 1)</div>
                    <input
                      className={field}
                      value={form.top_p}
                      onChange={(e) => set("top_p", e.target.value)}
                    />
                  </div>
                  <div>
                    <div className={label}>Top K</div>
                    <input
                      className={field}
                      value={form.top_k}
                      onChange={(e) => set("top_k", e.target.value)}
                    />
                  </div>
                  <div>
                    <div className={label}>Max Tokens (-1 = ohne Limit)</div>
                    <input
                      className={field}
                      value={form.max_tokens}
                      onChange={(e) => set("max_tokens", e.target.value)}
                    />
                  </div>
                  <div>
                    <div className={label}>Context Length</div>
                    <input
                      className={field}
                      value={form.context_length}
                      onChange={(e) => set("context_length", e.target.value)}
                    />
                  </div>
                  <div>
                    <div className={label}>Seed (-1 = zufällig)</div>
                    <input
                      className={field}
                      value={form.seed}
                      onChange={(e) => set("seed", e.target.value)}
                    />
                  </div>
                  <div>
                    <div className={label}>Keep Alive</div>
                    <input
                      className={field}
                      placeholder="5m"
                      value={form.keep_alive}
                      onChange={(e) => set("keep_alive", e.target.value)}
                    />
                  </div>
                  <div>
                    <div className={label}>Timeout (Sekunden)</div>
                    <input
                      className={field}
                      value={form.timeout}
                      onChange={(e) => set("timeout", e.target.value)}
                    />
                  </div>
                </div>
                <p className="text-[11px] text-white/40 leading-relaxed">
                  Keep Alive sagt, wie lange das Modell nach der Antwort im
                  Speicher bleibt: <code>5m</code>, <code>1h</code>,{" "}
                  <code>0</code> (sofort entladen) oder <code>-1</code> (dauerhaft
                  geladen). Eine größere Context Length braucht mehr Arbeits- und
                  Grafikspeicher.
                </p>
              </section>

              <section className="space-y-2">
                <div className={section}>System Prompt</div>
                <textarea
                  className={`${field} h-24 resize-none`}
                  placeholder="Zusätzliche Anweisung, die bei jedem Ollama-Gespräch gilt (optional)."
                  value={form.system_prompt}
                  onChange={(e) => set("system_prompt", e.target.value)}
                />
              </section>

              <section className="space-y-2">
                <div className={section}>Verbindung</div>
                <Switch
                  text="Antwort live mitschreiben (Streaming)"
                  hint="Aus: Jon zeigt die Antwort erst, wenn sie komplett fertig ist."
                  on={form.stream}
                  onClick={() => set("stream", !form.stream)}
                />
                <Switch
                  text="Automatisch neu verbinden"
                  hint="Bricht die Verbindung weg, versucht Jon es von allein noch einmal."
                  on={form.auto_reconnect}
                  onClick={() => set("auto_reconnect", !form.auto_reconnect)}
                />
              </section>

              <OllamaSharePanel onModelsChanged={() => void refresh(true)} />
            </div>

            <div className="flex items-center justify-between gap-3 px-5 py-3 border-t border-white/10">
              <div className="text-[11px] min-w-0 truncate">
                {error ? (
                  <span className="text-red-300/90">{error}</span>
                ) : (
                  <span className="text-emerald-300/80">{note}</span>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => void reset()}
                  disabled={busy}
                  className="px-3 py-2 rounded-xl border border-white/10 bg-white/5 text-white/60 text-[12px] hover:bg-white/10 transition disabled:opacity-50"
                >
                  Zurücksetzen
                </button>
                <button
                  onClick={() => void save()}
                  disabled={busy}
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[13px] shadow-gold hover:brightness-110 transition disabled:opacity-50"
                >
                  Speichern
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
