import { useState } from "react";
import { P2PIdentity, saveIdentity } from "../lib/api";

const AVATARS = ["🙂", "😎", "🦊", "🐼", "🐧", "🦉", "🐨", "🐯", "👾", "🚀", "⚡", "🌸"];

interface Props {
  identity: P2PIdentity;
  firstRun: boolean;
  onSaved: (identity: P2PIdentity) => void;
  onClose: () => void;
}

export default function ProfileModal({
  identity,
  firstRun,
  onSaved,
  onClose,
}: Props) {
  const [name, setName] = useState(identity.name);
  const [avatar, setAvatar] = useState(identity.avatar || "🙂");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!name.trim()) {
      setError("Bitte gib einen Namen ein.");
      return;
    }
    setSaving(true);
    try {
      onSaved(await saveIdentity(name.trim(), avatar));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/75">
      <div className="glass rounded-2xl border border-gold/25 w-[440px] max-w-[92vw] p-6">
        <div className="text-center mb-5">
          <div className="text-5xl mb-2">{avatar}</div>
          <h2 className="text-xl font-semibold gold-text">
            {firstRun ? "Willkommen bei Jon" : "Dein Profil"}
          </h2>
          <p className="text-[12px] text-white/45 mt-1">
            {firstRun
              ? "Wie soll Jon dich nennen? Unter diesem Namen sehen dich auch deine Freunde im Chat."
              : "Name und Bild kannst du jederzeit ändern."}
          </p>
        </div>

        <input
          autoFocus
          value={name}
          maxLength={32}
          onChange={(e) => {
            setName(e.target.value);
            setError("");
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") void save();
          }}
          placeholder="Dein Name"
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white/90 placeholder-white/30 outline-none focus:border-gold/50"
        />

        <div className="grid grid-cols-6 gap-2 mt-4">
          {AVATARS.map((a) => (
            <button
              key={a}
              onClick={() => setAvatar(a)}
              className={`h-10 rounded-xl text-xl border transition-colors ${
                avatar === a
                  ? "border-gold/60 bg-gold/15"
                  : "border-white/10 bg-white/5 hover:bg-white/10"
              }`}
            >
              {a}
            </button>
          ))}
        </div>

        {error && (
          <div className="text-[12px] text-red-300 mt-3 text-center">{error}</div>
        )}

        <div className="flex gap-2 mt-5">
          {!firstRun && (
            <button
              onClick={onClose}
              className="flex-1 py-2.5 rounded-xl border border-white/10 bg-white/5 text-white/60 hover:bg-white/10 transition"
            >
              Abbrechen
            </button>
          )}
          <button
            onClick={() => void save()}
            disabled={saving}
            className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold shadow-gold hover:brightness-110 disabled:opacity-50 transition"
          >
            {saving ? "Speichert …" : firstRun ? "Los geht's" : "Speichern"}
          </button>
        </div>
      </div>
    </div>
  );
}
