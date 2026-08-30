import { useEffect, useMemo, useRef, useState } from "react";
import {
  StudioConfig,
  StudioProvider,
  StudioWork,
  connectStudio,
  deleteStudioWork,
  disconnectStudio,
  generateStudioWork,
  getStudioConfig,
  saveStudioWork,
  studioFileUrl,
} from "../lib/api";

const AUTH_LABEL: Record<string, string> = {
  api_key: "API-Schlüssel",
  lokal: "Läuft bei dir",
  frei: "Ohne Schlüssel",
};

function bytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function when(stamp: number): string {
  return new Date(stamp * 1000).toLocaleString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function Studio({ onClose }: { onClose: () => void }) {
  const [config, setConfig] = useState<StudioConfig | null>(null);
  const [setup, setSetup] = useState(false);
  const [choice, setChoice] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [prompt, setPrompt] = useState("");
  const [negative, setNegative] = useState("");
  const [kind, setKind] = useState<"bild" | "video">("bild");
  const [model, setModel] = useState("");
  const [size, setSize] = useState("");
  const [works, setWorks] = useState<StudioWork[]>([]);
  const [preview, setPreview] = useState<StudioWork | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [hinweis, setHinweis] = useState("");
  const [vorlage, setVorlage] = useState<{
    url: string;
    name: string;
    id?: string;
  } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const provider = useMemo<StudioProvider | null>(
    () => config?.liste.find((p) => p.id === config.anbieter) ?? null,
    [config]
  );
  const picked = useMemo<StudioProvider | null>(
    () => config?.liste.find((p) => p.id === choice) ?? null,
    [config, choice]
  );

  const apply = (data: StudioConfig) => {
    setConfig(data);
    setWorks(data.galerie);
    setSize((current) => current || data.groesse);
    setSetup(!data.bereit);
    const active = data.liste.find((p) => p.id === data.anbieter);
    if (active) {
      setModel((current) => current || active.modell_bild);
      if (!active.video) setKind("bild");
    }
  };

  useEffect(() => {
    let alive = true;
    getStudioConfig()
      .then((data) => {
        if (!alive) return;
        apply(data);
        setChoice(data.anbieter || "pollinations");
      })
      .catch((e) => alive && setError(e instanceof Error ? e.message : String(e)))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!picked) return;
    setApiKey("");
    setBaseUrl(picked.basis);
  }, [picked]);

  const connect = async () => {
    if (!picked || busy) return;
    setBusy(true);
    setError("");
    try {
      const data = await connectStudio({
        provider: picked.id,
        api_key: apiKey,
        base_url: baseUrl,
        size,
      });
      apply(data);
      setModel(
        data.liste.find((p) => p.id === data.anbieter)?.modell_bild ?? ""
      );
      setSetup(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const forget = async (id: string) => {
    setBusy(true);
    try {
      apply(await disconnectStudio(id));
      setSetup(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const addVorlage = (file: File) => {
    const reader = new FileReader();
    reader.onload = () =>
      setVorlage({ url: String(reader.result ?? ""), name: file.name });
    reader.onerror = () => setError("Die Vorlage ließ sich nicht lesen.");
    reader.readAsDataURL(file);
  };

  const create = async () => {
    if (!prompt.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      setHinweis("");
      const work = await generateStudioWork({
        prompt: prompt.trim(),
        kind,
        model: model.trim(),
        size,
        negative: negative.trim(),
        image: kind === "bild" ? (vorlage?.id ?? vorlage?.url ?? "") : "",
      });
      setWorks((prev) => [work, ...prev]);
      setPreview(work);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const speichern = async (work: StudioWork) => {
    setError("");
    try {
      const r = await saveStudioWork(work.id);
      setHinweis(`Gespeichert: ${r.gespeichert}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const remove = async (work: StudioWork) => {
    try {
      await deleteStudioWork(work.id);
      setWorks((prev) => prev.filter((w) => w.id !== work.id));
      setPreview((current) => (current?.id === work.id ? null : current));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const models =
    kind === "video" ? picked?.video_modelle : picked?.bild_modelle;
  const activeModels =
    kind === "video" ? provider?.video_modelle ?? [] : provider?.bild_modelle ?? [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[900px] max-w-[96vw] h-[700px] max-h-[94vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 h-14 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-xl">🎨</span>
            <span className="text-[14px] text-white/90">Video / Foto</span>
            <span className="hidden md:inline text-[11px] text-white/35 truncate">
              {provider && !setup
                ? `${provider.label} · ${provider.verbunden ? "verbunden" : "nicht verbunden"}`
                : "Bilder und Videos von einer KI erstellen"}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {provider && !setup && (
              <button
                onClick={() => {
                  setChoice(provider.id);
                  setSetup(true);
                }}
                className="px-2.5 h-7 rounded-full border border-white/10 bg-white/5 text-[11px] text-white/60 hover:text-white/90 transition"
              >
                Anbieter wechseln
              </button>
            )}
            <button
              onClick={onClose}
              className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition"
            >
              ✕
            </button>
          </div>
        </div>

        {error && (
          <div className="mx-4 mt-3 px-3 py-2 rounded-xl border border-red-400/30 bg-red-400/10 text-[12.5px] text-red-200 shrink-0">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex-1 grid place-items-center text-[13px] text-white/40">
            Lade …
          </div>
        ) : setup ? (
          <div className="flex-1 overflow-y-auto p-4">
            <div className="text-[13px] text-white/70 mb-1">
              Womit soll Jon deine Bilder erstellen?
            </div>
            <div className="text-[11.5px] text-white/40 mb-3">
              Such dir eine Bild- oder Video-KI aus. Entweder mit deinem eigenen
              API-Schlüssel, komplett kostenlos ohne Anmeldung oder lokal auf
              deinem eigenen Rechner.
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {config?.liste.map((entry) => (
                <button
                  key={entry.id}
                  onClick={() => setChoice(entry.id)}
                  className={`text-left rounded-xl border px-3.5 py-3 transition ${
                    choice === entry.id
                      ? "border-gold/50 bg-gold/10"
                      : "border-white/10 bg-white/5 hover:bg-white/10"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-[13.5px] font-semibold text-white/90 flex-1">
                      {entry.label}
                    </span>
                    {entry.verbunden && (
                      <span className="text-[10px] text-emerald-300/80">bereit</span>
                    )}
                    <span className="text-[10px] text-white/35">
                      {AUTH_LABEL[entry.auth]}
                    </span>
                  </div>
                  <div className="text-[11.5px] text-white/45 mt-1 leading-snug">
                    {entry.hinweis}
                  </div>
                  <div className="text-[10.5px] text-white/30 mt-1">
                    {entry.video ? "Bilder und Videos" : "nur Bilder"}
                    {entry.bearbeiten ? " · bearbeitet auch vorhandene Bilder" : ""}
                    {entry.geerbt ? " · Schlüssel aus Jon" : ""}
                  </div>
                </button>
              ))}
            </div>

            {picked && (
              <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3.5">
                <div className="text-[12.5px] text-white/80 mb-2">
                  {picked.label} einrichten
                </div>
                {picked.auth === "api_key" && (
                  <>
                    <input
                      type="password"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder={
                        picked.geerbt
                          ? "Schlüssel kommt schon aus Jon — leer lassen"
                          : picked.verbunden
                            ? "Schlüssel ist gespeichert — leer lassen zum Behalten"
                            : "API-Schlüssel einfügen"
                      }
                      className="w-full bg-black/30 border border-white/10 rounded-xl px-3 py-2.5 text-[13px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40"
                    />
                    <a
                      href={picked.docs}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-block mt-2 text-[11.5px] text-gold/80 hover:text-gold"
                    >
                      Schlüssel holen: {picked.docs}
                    </a>
                  </>
                )}
                {picked.auth === "lokal" && (
                  <input
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    placeholder="http://127.0.0.1:7860"
                    className="w-full bg-black/30 border border-white/10 rounded-xl px-3 py-2.5 text-[13px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40"
                  />
                )}
                {picked.auth === "frei" && (
                  <div className="text-[12px] text-white/50">
                    Hier brauchst du gar nichts — einfach loslegen.
                  </div>
                )}
                <div className="flex items-center gap-2 mt-3">
                  <button
                    onClick={() => void connect()}
                    disabled={busy}
                    className="px-4 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[12.5px] shadow-gold disabled:opacity-40 hover:brightness-110 transition"
                  >
                    {busy ? "…" : "Nehmen"}
                  </button>
                  {picked.auth === "api_key" && picked.verbunden && !picked.geerbt && (
                    <button
                      onClick={() => void forget(picked.id)}
                      disabled={busy}
                      className="px-3 py-2 rounded-xl border border-white/10 bg-white/5 text-[12px] text-white/55 hover:text-white/90 transition"
                    >
                      Schlüssel löschen
                    </button>
                  )}
                  {config?.bereit && (
                    <button
                      onClick={() => setSetup(false)}
                      className="px-3 py-2 rounded-xl border border-white/10 bg-white/5 text-[12px] text-white/55 hover:text-white/90 transition"
                    >
                      Zurück
                    </button>
                  )}
                </div>
                {models && models.length > 0 && (
                  <div className="text-[11px] text-white/35 mt-3">
                    Modelle: {models.join(" · ")}
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 min-h-0 flex flex-col md:flex-row">
            <div className="md:w-[340px] shrink-0 border-b md:border-b-0 md:border-r border-white/10 p-4 overflow-y-auto">
              <div className="flex gap-1.5 mb-3">
                {(["bild", "video"] as const).map((option) => (
                  <button
                    key={option}
                    onClick={() => {
                      setKind(option);
                      const list =
                        option === "video"
                          ? provider?.video_modelle ?? []
                          : provider?.bild_modelle ?? [];
                      setModel(list[0] ?? "");
                    }}
                    disabled={option === "video" && !provider?.video}
                    className={`flex-1 py-1.5 rounded-lg text-[12px] border transition disabled:opacity-30 ${
                      kind === option
                        ? "border-gold/50 bg-gold/15 text-gold"
                        : "border-white/10 bg-white/5 text-white/55 hover:text-white/85"
                    }`}
                  >
                    {option === "bild" ? "🖼️ Bild" : "🎬 Video"}
                  </button>
                ))}
              </div>

              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    void create();
                  }
                }}
                rows={5}
                placeholder="Beschreibe, was zu sehen sein soll — z. B. „ein goldener Fuchs im Nebelwald, Morgenlicht, Weitwinkel“"
                className="w-full bg-black/30 border border-white/10 rounded-xl px-3 py-2.5 text-[13px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40 resize-none"
              />

              {provider?.bearbeiten && kind === "bild" && (
                <div className="mt-2 rounded-xl border border-white/10 bg-white/5 p-2">
                  <div className="flex items-center gap-2">
                    {vorlage ? (
                      <img
                        src={vorlage.url}
                        alt=""
                        className="w-10 h-10 rounded-lg object-cover shrink-0"
                      />
                    ) : (
                      <span className="w-10 h-10 rounded-lg grid place-items-center bg-black/30 text-[15px] shrink-0">
                        🖼️
                      </span>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="text-[11.5px] text-white/70 truncate">
                        {vorlage ? vorlage.name : "Vorlage zum Bearbeiten"}
                      </div>
                      <div className="text-[10px] text-white/30">
                        {vorlage
                          ? "Jon ändert dieses Bild nach deinem Text"
                          : "Optional — Bild auswählen und beschreiben, was sich ändern soll"}
                      </div>
                    </div>
                    {vorlage ? (
                      <button
                        onClick={() => setVorlage(null)}
                        className="px-2 py-1 rounded-lg border border-white/10 bg-white/5 text-[11px] text-white/50 hover:text-white/90 transition shrink-0"
                      >
                        ✕
                      </button>
                    ) : (
                      <div className="flex gap-1 shrink-0">
                        <button
                          onClick={() => fileRef.current?.click()}
                          className="px-2 py-1 rounded-lg border border-white/10 bg-white/5 text-[11px] text-white/55 hover:text-white/90 transition"
                        >
                          Datei
                        </button>
                        {preview && preview.art === "bild" && (
                          <button
                            onClick={() =>
                              setVorlage({
                                url: studioFileUrl(preview),
                                name: "Aus der Galerie",
                                id: preview.id,
                              })
                            }
                            className="px-2 py-1 rounded-lg border border-white/10 bg-white/5 text-[11px] text-white/55 hover:text-white/90 transition"
                          >
                            Galerie
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                  <input
                    ref={fileRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) addVorlage(file);
                      e.target.value = "";
                    }}
                  />
                </div>
              )}

              <input
                value={negative}
                onChange={(e) => setNegative(e.target.value)}
                placeholder="Was NICHT drauf soll (optional)"
                className="w-full mt-2 bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-[12.5px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40"
              />

              <div className="mt-2 grid grid-cols-2 gap-2">
                <select
                  value={size}
                  onChange={(e) => setSize(e.target.value)}
                  className="bg-black/30 border border-white/10 rounded-xl px-2.5 py-2 text-[12px] text-white/80 outline-none focus:border-gold/40"
                >
                  {(config?.groessen ?? []).map((option) => (
                    <option key={option} value={option} className="bg-neutral-900">
                      {option}
                    </option>
                  ))}
                </select>
                <input
                  list="studio-modelle"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="Modell"
                  className="bg-black/30 border border-white/10 rounded-xl px-2.5 py-2 text-[12px] text-white/80 placeholder-white/25 outline-none focus:border-gold/40"
                />
                <datalist id="studio-modelle">
                  {activeModels.map((option) => (
                    <option key={option} value={option} />
                  ))}
                </datalist>
              </div>

              <button
                onClick={() => void create()}
                disabled={busy || !prompt.trim()}
                className="w-full mt-3 px-4 py-2.5 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[13px] shadow-gold disabled:opacity-40 hover:brightness-110 transition"
              >
                {busy
                  ? kind === "video"
                    ? "Video entsteht …"
                    : vorlage
                      ? "Bild wird bearbeitet …"
                      : "Bild entsteht …"
                  : kind === "video"
                    ? "Video erstellen"
                    : vorlage
                      ? "Bild bearbeiten"
                      : "Bild erstellen"}
              </button>
              <div className="text-[10.5px] text-white/30 mt-2">
                Strg+Enter erstellt sofort. Videos brauchen je nach Modell ein
                paar Minuten.
              </div>
            </div>

            <div className="flex-1 min-w-0 flex flex-col">
              <div className="flex-1 min-h-0 overflow-y-auto p-4">
                {preview ? (
                  <div>
                    <div className="rounded-2xl border border-white/10 bg-black/30 overflow-hidden">
                      {preview.art === "video" ? (
                        <video
                          key={preview.id}
                          src={studioFileUrl(preview)}
                          controls
                          autoPlay
                          loop
                          className="w-full max-h-[46vh] bg-black"
                        />
                      ) : (
                        <img
                          key={preview.id}
                          src={studioFileUrl(preview)}
                          alt={preview.prompt}
                          className="w-full max-h-[46vh] object-contain bg-black"
                        />
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                      <span className="text-[11.5px] text-white/45 flex-1 min-w-[160px] truncate">
                        {preview.modell || preview.anbieter_label} ·{" "}
                        {bytes(preview.groesse_bytes)} · {preview.dauer_s}s
                      </span>
                      <button
                        onClick={() => void speichern(preview)}
                        className="px-2.5 py-1 rounded-lg border border-gold/30 bg-gold/10 text-[11.5px] text-gold/90 hover:bg-gold/20 transition"
                      >
                        ⬇ Herunterladen
                      </button>
                      <a
                        href={studioFileUrl(preview)}
                        target="_blank"
                        rel="noreferrer"
                        className="px-2.5 py-1 rounded-lg border border-white/10 bg-white/5 text-[11.5px] text-white/60 hover:text-white/90 transition"
                      >
                        Groß ansehen
                      </a>
                      <button
                        onClick={() => setPrompt(preview.prompt)}
                        className="px-2.5 py-1 rounded-lg border border-white/10 bg-white/5 text-[11.5px] text-white/60 hover:text-white/90 transition"
                      >
                        Prompt übernehmen
                      </button>
                      <button
                        onClick={() => void remove(preview)}
                        className="px-2.5 py-1 rounded-lg border border-red-400/25 bg-red-400/10 text-[11.5px] text-red-200/80 hover:text-red-100 transition"
                      >
                        Löschen
                      </button>
                    </div>
                    {hinweis && (
                      <div className="text-[11.5px] text-emerald-300/70 mt-1.5 break-all">
                        {hinweis}
                      </div>
                    )}
                    <div className="text-[12px] text-white/55 mt-2 leading-snug">
                      {preview.prompt}
                    </div>
                  </div>
                ) : (
                  <div className="h-full grid place-items-center text-center px-6">
                    <div>
                      <div className="text-3xl mb-2">🎨</div>
                      <div className="text-[13px] text-white/60">
                        {busy
                          ? "Jon malt …"
                          : "Schreib links, was du sehen willst."}
                      </div>
                      <div className="text-[11.5px] text-white/30 mt-1">
                        Alles landet in deiner Galerie unten und bleibt lokal auf
                        deinem PC.
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {works.length > 0 && (
                <div className="border-t border-white/10 p-3 shrink-0">
                  <div className="text-[10px] uppercase tracking-wider text-white/30 mb-2">
                    Galerie · {works.length}
                  </div>
                  <div className="flex gap-2 overflow-x-auto pb-1">
                    {works.map((work) => (
                      <button
                        key={work.id}
                        onClick={() => setPreview(work)}
                        title={`${work.prompt}\n${when(work.erstellt)}`}
                        className={`relative w-[74px] h-[74px] shrink-0 rounded-xl overflow-hidden border transition ${
                          preview?.id === work.id
                            ? "border-gold/60"
                            : "border-white/10 hover:border-white/30"
                        }`}
                      >
                        {work.art === "video" ? (
                          <div className="w-full h-full grid place-items-center bg-black/50 text-[18px]">
                            🎬
                          </div>
                        ) : (
                          <img
                            src={studioFileUrl(work)}
                            alt=""
                            className="w-full h-full object-cover"
                          />
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
