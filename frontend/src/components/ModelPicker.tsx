import Symbol from "./Symbol";
import ModellWahl from "./ModellWahl";
import type { ProviderStatus } from "../lib/api";

const NAMEN: Record<string, string> = { nvidia: "NVIDIA", ollama: "Ollama", openrouter: "OpenRouter", lmstudio: "LM Studio", xai: "xAI", anthropic: "Anthropic", gemini: "Google Gemini", openai: "OpenAI", felworks: "FelWorks", deepseek: "DeepSeek", mistral: "Mistral", groq: "Groq", together: "Together AI", lokalserver: "Lokaler Server" };

interface Props {
  providers: ProviderStatus[];
  provider: string;
  model: string;
  onChange: (provider: string, model: string) => void;
}

export default function ModelPicker({
  providers,
  provider,
  model,
  onChange,
}: Props) {
  const active = providers.find((p) => p.provider === provider);
  const models = active?.models ?? [];
  const locked = active?.locked === true;
  const own = models.filter((m) => !m.startsWith("share:"));
  const shared = models.filter((m) => m.startsWith("share:"));

  return (
    <div className="no-drag flex items-center gap-2 min-w-0">
      <select
        value={provider}
        onChange={(e) => {
          const next = providers.find((p) => p.provider === e.target.value);
          onChange(e.target.value, next?.models[0] ?? "");
        }}
        className="glass rounded-lg px-2 md:px-3 py-1.5 text-sm text-white/90 outline-none cursor-pointer min-w-0 max-w-[30vw] md:max-w-none"
      >
        {providers.map((p) => (
          <option
            key={p.provider}
            value={p.provider}
            disabled={!p.configured}
            className="bg-ink-800"
          >
            {p.label || p.provider}
            {p.configured ? "" : " (kein Key)"}
          </option>
        ))}
      </select>
      {locked ? (
        <div
          title={`${active?.label || "Freigegebener Server"} — der Besitzer gibt das Modell vor`}
          className="glass rounded-lg px-2 md:px-3 py-1.5 text-sm text-white/60 min-w-0 max-w-[38vw] md:max-w-[240px] truncate flex items-center gap-1.5"
        >
          <span className="text-gold/70"><Symbol zeichen="🔒" /></span>
          <span className="truncate">{model || models[0] || "—"}</span>
        </div>
      ) : (
        <ModellWahl
          provider={provider}
          providerLabel={active?.label || NAMEN[provider] || provider}
          models={[...own, ...shared]}
          model={model}
          onChange={(m) => onChange(provider, m)}
        />
      )}
    </div>
  );
}
