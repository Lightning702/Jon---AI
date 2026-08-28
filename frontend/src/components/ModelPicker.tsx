import type { ProviderStatus } from "../lib/api";

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
  const groups = shared.reduce<Record<string, string[]>>((acc, entry) => {
    const rest = entry.slice("share:".length);
    const code = rest.slice(0, rest.indexOf("/"));
    (acc[code] ||= []).push(entry);
    return acc;
  }, {});

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
          <span className="text-gold/70">🔒</span>
          <span className="truncate">{model || models[0] || "—"}</span>
        </div>
      ) : (
        <select
          value={model}
          onChange={(e) => onChange(provider, e.target.value)}
          className="glass rounded-lg px-2 md:px-3 py-1.5 text-sm text-white/90 outline-none cursor-pointer min-w-0 max-w-[38vw] md:max-w-[240px]"
        >
          {shared.length === 0
            ? models.map((m) => (
                <option key={m} value={m} className="bg-ink-800">
                  {m}
                </option>
              ))
            : [
                <optgroup key="lokal" label="Auf diesem PC" className="bg-ink-800">
                  {own.map((m) => (
                    <option key={m} value={m} className="bg-ink-800">
                      {m}
                    </option>
                  ))}
                </optgroup>,
                ...Object.entries(groups).map(([code, entries]) => (
                  <optgroup
                    key={code}
                    label={`Freigabe ${code}`}
                    className="bg-ink-800"
                  >
                    {entries.map((m) => (
                      <option key={m} value={m} className="bg-ink-800">
                        {m.slice(m.indexOf("/") + 1)}
                      </option>
                    ))}
                  </optgroup>
                )),
              ]}
        </select>
      )}
    </div>
  );
}
