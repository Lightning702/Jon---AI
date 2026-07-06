import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { motion } from "framer-motion";
import { useState } from "react";
const TOOL_LABELS = {
    run_powershell: "PowerShell",
    run_cmd: "CMD",
    open_url: "URL öffnen",
    start_program: "Programm starten",
    kill_program: "Programm beenden",
    open_explorer: "Explorer",
    list_dir: "Ordner lesen",
    read_file: "Datei lesen",
    write_file: "Datei schreiben",
    move_path: "Verschieben",
    delete_path: "Löschen",
    open_in_vscode: "VS Code",
};
export default function MessageBubble({ entry }) {
    const isUser = entry.role === "user";
    const [showReasoning, setShowReasoning] = useState(false);
    return (_jsx(motion.div, { initial: { opacity: 0, y: 12 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25 }, className: `flex ${isUser ? "justify-end" : "justify-start"}`, children: _jsx("div", { className: `max-w-[76%] ${isUser ? "items-end" : "items-start"}`, children: _jsxs("div", { className: `px-4 py-3 rounded-2xl leading-relaxed whitespace-pre-wrap ${isUser
                    ? "bg-gradient-to-br from-gold-light/90 to-gold-dark/90 text-black rounded-br-md"
                    : "glass text-white/90 rounded-bl-md"}`, children: [entry.tools && entry.tools.length > 0 && !isUser && (_jsx("div", { className: "mb-2 flex flex-wrap gap-1.5", children: entry.tools.map((t, i) => (_jsxs("span", { className: "inline-flex items-center gap-1.5 text-[11px] px-2 py-1 rounded-lg bg-gold/10 border border-gold/25 text-gold/90", children: [!t.done ? (_jsx("span", { className: "w-2 h-2 rounded-full bg-gold animate-pulse" })) : (_jsx("span", { children: t.ok ? "✓" : "✕" })), TOOL_LABELS[t.name] ?? t.name] }, i))) })), entry.reasoning && !isUser && (_jsxs("div", { className: "mb-2", children: [_jsx("button", { onClick: () => setShowReasoning((v) => !v), className: "text-[11px] text-gold/70 hover:text-gold transition", children: showReasoning ? "Denkprozess verbergen" : "Denkprozess anzeigen" }), showReasoning && (_jsx("pre", { className: "mt-2 text-[12px] text-white/50 whitespace-pre-wrap border-l-2 border-gold/30 pl-3", children: entry.reasoning }))] })), _jsx("span", { children: entry.content }), entry.streaming && (_jsx("span", { className: "inline-block w-2 h-4 ml-0.5 align-middle bg-gold animate-pulse rounded-sm" }))] }) }) }));
}
