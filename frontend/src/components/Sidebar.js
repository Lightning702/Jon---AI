import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { motion } from "framer-motion";
export default function Sidebar({ conversations, activeId, onSelect, onNew, onDelete, }) {
    return (_jsxs("aside", { className: "glass-strong w-72 flex flex-col h-full border-r border-white/10", children: [_jsx("div", { className: "p-4", children: _jsx("button", { onClick: onNew, className: "no-drag w-full py-3 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold shadow-gold hover:brightness-110 transition", children: "+ Neue Unterhaltung" }) }), _jsxs("div", { className: "flex-1 overflow-y-auto px-2 space-y-1", children: [conversations.map((c) => (_jsxs(motion.div, { initial: { opacity: 0, x: -8 }, animate: { opacity: 1, x: 0 }, className: `group flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer transition ${activeId === c.id
                            ? "bg-gold/15 border border-gold/30"
                            : "hover:bg-white/5 border border-transparent"}`, onClick: () => onSelect(c.id), children: [_jsxs("div", { className: "min-w-0", children: [_jsx("p", { className: "text-sm truncate", children: c.title }), _jsxs("p", { className: "text-[11px] text-white/40 truncate", children: [c.provider, " \u00B7 ", c.model] })] }), _jsx("button", { onClick: (e) => {
                                    e.stopPropagation();
                                    onDelete(c.id);
                                }, className: "opacity-0 group-hover:opacity-100 text-white/40 hover:text-red-400 px-1 transition", children: "\u2715" })] }, c.id))), conversations.length === 0 && (_jsx("p", { className: "text-center text-white/30 text-sm mt-8", children: "Noch keine Unterhaltungen" }))] }), _jsx("div", { className: "p-4 text-[11px] text-white/30 border-t border-white/10", children: "Jon Desktop v1.0.0" })] }));
}
