import { useEffect, useState } from "react";
import {
  VaultEntry,
  vaultAdd,
  vaultCreate,
  vaultDelete,
  vaultEntries,
  vaultGenerate,
  vaultLock,
  vaultReveal,
  vaultStatus,
  vaultUnlock,
} from "../lib/api";

export default function Vault({ onClose }: { onClose: () => void }) {
  const [mode, setMode] = useState<"loading" | "create" | "unlock" | "open">("loading");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [entries, setEntries] = useState<VaultEntry[]>([]);
  const [title, setTitle] = useState("");
  const [username, setUsername] = useState("");
  const [secret, setSecret] = useState("");
  const [revealed, setRevealed] = useState<Record<string, string>>({});
  const [adding, setAdding] = useState(false);

  const refresh = async () => {
    const data = await vaultEntries();
    if (data.locked) setMode("unlock");
    else {
      setEntries(data.entries);
      setMode("open");
    }
  };

  useEffect(() => {
    void vaultStatus().then((s) => {
      if (!s.exists) setMode("create");
      else if (s.unlocked) void refresh();
      else setMode("unlock");
    });
  }, []);

  const doCreate = async () => {
    setError("");
    try {
      await vaultCreate(password);
      setPassword("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const doUnlock = async () => {
    setError("");
    try {
      await vaultUnlock(password);
      setPassword("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const lock = async () => {
    await vaultLock();
    setEntries([]);
    setRevealed({});
    setMode("unlock");
  };

  const save = async () => {
    if (!title.trim() || !secret) return;
    try {
      await vaultAdd(title.trim(), username.trim(), secret);
      setTitle("");
      setUsername("");
      setSecret("");
      setAdding(false);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const reveal = async (id: string) => {
    if (revealed[id]) {
      setRevealed((r) => { const n = { ...r }; delete n[id]; return n; });
      return;
    }
    try {
      const r = await vaultReveal(id);
      setRevealed((prev) => ({ ...prev, [id]: r.secret }));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const gen = async () => setSecret(await vaultGenerate(20, true));

  const remove = async (id: string) => {
    await vaultDelete(id);
    await refresh();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[560px] max-w-[94vw] max-h-[90vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 h-14 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xl">🔒</span>
            <span className="text-[14px] text-white/90">Passwort-Tresor</span>
            <span className="text-[11px] text-white/35">verschlüsselt, nur auf deinem PC</span>
          </div>
          <div className="flex items-center gap-2">
            {mode === "open" && <button onClick={() => void lock()} className="text-[11.5px] text-white/50 hover:text-gold">🔒 Sperren</button>}
            <button onClick={onClose} className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition">✕</button>
          </div>
        </div>

        <div className="p-5 overflow-y-auto">
          {error && <div className="mb-3 px-3 py-2 rounded-xl border border-red-400/30 bg-red-400/10 text-[12.5px] text-red-200">{error}</div>}

          {(mode === "create" || mode === "unlock") && (
            <div className="flex flex-col items-center py-6">
              <div className="text-4xl mb-3">{mode === "create" ? "🆕" : "🔑"}</div>
              <div className="text-[13.5px] text-white/80 mb-4 text-center max-w-xs">
                {mode === "create"
                  ? "Lege ein Master-Passwort fest. Nur damit kommst du an den Tresor — Jon speichert es nirgends."
                  : "Gib dein Master-Passwort ein, um den Tresor zu öffnen."}
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void (mode === "create" ? doCreate() : doUnlock())}
                autoFocus
                placeholder="Master-Passwort"
                className="w-full max-w-xs bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-[13px] text-white/90 text-center placeholder-white/25 outline-none focus:border-gold/40"
              />
              <button
                onClick={() => void (mode === "create" ? doCreate() : doUnlock())}
                className="mt-3 px-5 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[12.5px] shadow-gold hover:brightness-110 transition"
              >
                {mode === "create" ? "Tresor anlegen" : "Öffnen"}
              </button>
            </div>
          )}

          {mode === "open" && (
            <>
              {!adding ? (
                <button onClick={() => setAdding(true)} className="w-full mb-3 py-2.5 rounded-xl border border-gold/30 bg-gold/10 text-gold/90 text-[13px] font-semibold hover:bg-gold/20 transition">+ Neuer Eintrag</button>
              ) : (
                <div className="mb-3 rounded-xl border border-white/10 bg-white/5 p-3 space-y-2">
                  <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Titel (z. B. GitHub)" className="w-full bg-white/5 border border-white/10 rounded-lg px-2.5 py-1.5 text-[12.5px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40" />
                  <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Benutzername / E-Mail (optional)" className="w-full bg-white/5 border border-white/10 rounded-lg px-2.5 py-1.5 text-[12.5px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40" />
                  <div className="flex gap-2">
                    <input value={secret} onChange={(e) => setSecret(e.target.value)} placeholder="Passwort / Geheimnis" className="flex-1 bg-white/5 border border-white/10 rounded-lg px-2.5 py-1.5 text-[12.5px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40" />
                    <button onClick={() => void gen()} title="Passwort generieren" className="px-2.5 py-1.5 rounded-lg border border-white/10 bg-white/5 text-white/60 text-[12px] hover:bg-white/10">🎲</button>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => void save()} disabled={!title.trim() || !secret} className="flex-1 py-1.5 rounded-lg bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[12px] disabled:opacity-40">Speichern</button>
                    <button onClick={() => setAdding(false)} className="px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 text-white/50 text-[12px]">Abbrechen</button>
                  </div>
                </div>
              )}
              <div className="space-y-2">
                {entries.length === 0 && <div className="text-center text-[12.5px] text-white/30 py-6">Noch keine Einträge im Tresor.</div>}
                {entries.map((e) => (
                  <div key={e.id} className="rounded-xl border border-white/10 bg-white/5 px-3.5 py-2.5">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="text-[13px] font-semibold text-white/90 truncate">{e.title}</div>
                        {e.username && <div className="text-[11.5px] text-white/45 truncate">{e.username}</div>}
                      </div>
                      <button onClick={() => void reveal(e.id)} className="px-2.5 py-1 rounded-lg border border-white/10 bg-white/5 text-white/60 text-[11.5px] hover:bg-white/10">{revealed[e.id] ? "Verbergen" : "Zeigen"}</button>
                      {revealed[e.id] && <button onClick={() => navigator.clipboard.writeText(revealed[e.id])} title="Kopieren" className="px-2 py-1 rounded-lg border border-white/10 bg-white/5 text-white/60 text-[11.5px] hover:bg-white/10">📋</button>}
                      <button onClick={() => void remove(e.id)} className="text-white/30 hover:text-red-300 text-[12px]">✕</button>
                    </div>
                    {revealed[e.id] && <div className="mt-1.5 font-mono text-[12.5px] text-gold/90 break-all bg-black/25 rounded-lg px-2 py-1.5">{revealed[e.id]}</div>}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
