import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
export default function ModelPicker({ providers, provider, model, onChange, }) {
    const active = providers.find((p) => p.provider === provider);
    const models = active?.models ?? [];
    return (_jsxs("div", { className: "no-drag flex items-center gap-2", children: [_jsx("select", { value: provider, onChange: (e) => {
                    const next = providers.find((p) => p.provider === e.target.value);
                    onChange(e.target.value, next?.models[0] ?? "");
                }, className: "glass rounded-lg px-3 py-1.5 text-sm text-white/90 outline-none cursor-pointer", children: providers.map((p) => (_jsxs("option", { value: p.provider, disabled: !p.configured, className: "bg-ink-800", children: [p.provider, p.configured ? "" : " (kein Key)"] }, p.provider))) }), _jsx("select", { value: model, onChange: (e) => onChange(provider, e.target.value), className: "glass rounded-lg px-3 py-1.5 text-sm text-white/90 outline-none cursor-pointer max-w-[240px]", children: models.map((m) => (_jsx("option", { value: m, className: "bg-ink-800", children: m }, m))) })] }));
}
