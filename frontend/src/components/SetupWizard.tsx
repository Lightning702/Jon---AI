import { useState } from "react";
import { connectAccount, getProviders, saveUserSettings } from "../lib/api";

const PROVIDERS = [
  {
    id: "nvidia",
    label: "NVIDIA",
    hint: "Kostenlos, empfohlen — Schlüssel auf build.nvidia.com",
    url: "https://build.nvidia.com",
    model: "openai/gpt-oss-20b",
  },
  {
    id: "openai",
    label: "OpenAI",
    hint: "Kostenpflichtig — platform.openai.com/api-keys",
    url: "https://platform.openai.com/api-keys",
    model: "gpt-4o-mini",
  },
  {
    id: "groq",
    label: "Groq",
    hint: "Kostenloses Kontingent — console.groq.com/keys",
    url: "https://console.groq.com/keys",
    model: "llama-3.3-70b-versatile",
  },
  {
    id: "ollama",
    label: "Ollama (lokal)",
    hint: "Gratis & offline — Ollama muss laufen, kein Schlüssel nötig",
    url: "https://ollama.com",
    model: "",
  },
];

export default function SetupWizard({ onDone }: { onDone: () => void }) {
  const [provider, setProvider] = useState(PROVIDERS[0]);
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const local = provider.id === "ollama";

  const finish = async () => {
    setError("");
    if (!local && !key.trim()) {
      setError("Bitte trage deinen API-Schlüssel ein.");
      return;
    }
    setBusy(true);
    try {
      if (!local) await connectAccount(provider.id, key.trim(), provider.model);
      const list = await getProviders();
      const found = list.find((p) => p.provider === provider.id);
      if (!found || (!found.configured && !local)) {
        setError("Der Schlüssel wurde nicht akzeptiert. Stimmt er?");
        setBusy(false);
        return;
      }
      const model =
        provider.model && found.models.includes(provider.model)
          ? provider.model
          : found.models[0] ?? provider.model;
      if (!model) {
        setError(
          local
            ? "Ollama antwortet nicht. Läuft es und ist ein Modell geladen?"
            : "Keine Modelle gefunden."
        );
        setBusy(false);
        return;
      }
      await saveUserSettings({ provider: provider.id, model });
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/80">
      <div className="glass rounded-2xl border border-gold/25 w-[520px] max-w-[93vw] p-6">
        <div className="text-center mb-5">
          <div className="text-4xl mb-2">🙂</div>
          <h2 className="text-xl font-semibold gold-text">Jon einrichten</h2>
          <p className="text-[12px] text-white/45 mt-1">
            Jon braucht ein Sprachmodell. Wähle einen Anbieter — der erste ist
            kostenlos.
          </p>
        </div>

        <div className="space-y-1.5">
          {PROVIDERS.map((p) => (
            <button
              key={p.id}
              onClick={() => {
                setProvider(p);
                setError("");
              }}
              className={`w-full text-left px-3 py-2 rounded-xl border transition ${
                provider.id === p.id
                  ? "border-gold/50 bg-gold/10"
                  : "border-white/10 bg-white/5 hover:bg-white/10"
              }`}
            >
              <div className="flex items-center gap-2 text-[13px] text-white/90">
                <span
                  className={`w-2 h-2 rounded-full ${
                    provider.id === p.id ? "bg-gold" : "bg-white/20"
                  }`}
                />
                {p.label}
              </div>
              <div className="text-[11px] text-white/45 mt-0.5 pl-4">{p.hint}</div>
            </button>
          ))}
        </div>

        {!local && (
          <>
            <input
              type="password"
              value={key}
              onChange={(e) => {
                setKey(e.target.value);
                setError("");
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") void finish();
              }}
              placeholder={`${provider.label}-API-Schlüssel`}
              className="w-full mt-4 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-[13px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50"
            />
            <a
              href={provider.url}
              target="_blank"
              rel="noreferrer"
              className="block text-[11px] text-gold/70 hover:text-gold mt-1.5 text-center"
            >
              Schlüssel hier holen ↗
            </a>
          </>
        )}

        {error && (
          <div className="text-[12px] text-red-300 mt-3 text-center">{error}</div>
        )}

        <button
          onClick={() => void finish()}
          disabled={busy}
          className="w-full mt-5 py-2.5 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold shadow-gold hover:brightness-110 disabled:opacity-50 transition"
        >
          {busy ? "Prüfe …" : "Fertig"}
        </button>
        <button
          onClick={onDone}
          className="w-full mt-2 text-[11px] text-white/35 hover:text-white/60 transition"
        >
          Später einrichten
        </button>
      </div>
    </div>
  );
}
