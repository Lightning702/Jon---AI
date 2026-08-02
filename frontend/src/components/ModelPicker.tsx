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
  const own = models.filter((m) => !m.startsWith("share:"));
  const shared = models.filter((m) => m.startsWith("share:"));
  const groups = shared.reduce<Record<string, string[]>>((acc, entry) => {
    const rest = entry.slice("share:".length);
    const code = rest.slice(0, rest.indexOf("/"));
    (acc[code] ||= []).push(entry);
    return acc;
  }, {});

  return (
    <div className="no-drag flex items-center gap-2">
      <select
        value={provider}
        onChange={(e) => {
          const next = providers.find((p) => p.provider === e.target.value);
          onChange(e.target.value, next?.models[0] ?? "");
        }}
        className="glass rounded-lg px-3 py-1.5 text-sm text-white/90 outline-none cursor-pointer"
      >
        {providers.map((p) => (
          <option
            key={p.provider}
            value={p.provider}
            disabled={!p.configured}
            className="bg-ink-800"
          >
            {p.provider}
            {p.configured ? "" : " (kein Key)"}
          </option>
        ))}
      </select>
      <select
        value={model}
        onChange={(e) => onChange(provider, e.target.value)}
        className="glass rounded-lg px-3 py-1.5 text-sm text-white/90 outline-none cursor-pointer max-w-[240px]"
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
    </div>
  );
}
