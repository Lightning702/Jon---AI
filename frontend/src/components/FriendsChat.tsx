import { useEffect, useRef, useState } from "react";
import {
  P2PIdentity,
  P2PMessage,
  P2PPeer,
  addPeer,
  deletePeer,
  getP2PMessages,
  getPeers,
  getTypingPeers,
  mediaUrl,
  sendP2PMessage,
  sendTyping,
} from "../lib/api";

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-gold/80 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s`, animationDuration: "0.9s" }}
        />
      ))}
    </span>
  );
}

interface Props {
  identity: P2PIdentity;
  onEditProfile: () => void;
  onClose: () => void;
}

export default function FriendsChat({
  identity,
  onEditProfile,
  onClose,
}: Props) {
  const [peers, setPeers] = useState<P2PPeer[]>([]);
  const [typing, setTyping] = useState<string[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<P2PMessage[]>([]);
  const [text, setText] = useState("");
  const [friendName, setFriendName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [adding, setAdding] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const activeRef = useRef<string | null>(null);
  const typingSentRef = useRef(0);

  useEffect(() => {
    activeRef.current = activeId;
  }, [activeId]);

  useEffect(() => {
    const tick = async () => {
      setPeers(await getPeers());
      const current = activeRef.current;
      if (current) setMessages(await getP2PMessages(current));
    };
    void tick();
    const timer = window.setInterval(() => void tick(), 2000);
    const typingTimer = window.setInterval(async () => {
      setTyping(await getTypingPeers());
    }, 400);
    return () => {
      window.clearInterval(timer);
      window.clearInterval(typingTimer);
    };
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, activeId, typing]);

  const openPeer = async (peerId: string) => {
    setActiveId(peerId);
    setError("");
    setMessages(await getP2PMessages(peerId));
  };

  const submit = async (media?: {
    name: string;
    mime: string;
    data: string;
  }) => {
    if (!activeId || busy) return;
    if (!text.trim() && !media) return;
    setBusy(true);
    setError("");
    try {
      await sendP2PMessage(activeId, text.trim(), media);
      setText("");
      setMessages(await getP2PMessages(activeId));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const attach = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result ?? "");
      void submit({
        name: file.name,
        mime: file.type || "application/octet-stream",
        data: result.slice(result.indexOf(",") + 1),
      });
    };
    reader.readAsDataURL(file);
  };

  const connect = async () => {
    if (!friendName.trim()) return;
    setAdding(true);
    setError("");
    try {
      await addPeer(friendName.trim());
      setFriendName("");
      setPeers(await getPeers());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setAdding(false);
    }
  };

  const remove = async (peerId: string) => {
    await deletePeer(peerId);
    if (peerId === activeId) {
      setActiveId(null);
      setMessages([]);
    }
    setPeers(await getPeers());
  };

  const isTyping = (peerId: string) => typing.includes(peerId);
  const found = peers.find((p) => p.id === activeId) ?? null;
  const active = found
    ? { ...found, typing: found.typing || isTyping(found.id) }
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[900px] max-w-[95vw] h-[640px] max-h-[90vh] flex overflow-hidden">
        <div className="w-64 border-r border-white/10 flex flex-col">
          <div className="px-4 py-3 border-b border-white/10">
            <button
              onClick={onEditProfile}
              className="w-full flex items-center gap-2 text-left hover:opacity-80 transition"
            >
              <span className="text-2xl">{identity.avatar}</span>
              <span className="min-w-0">
                <span className="block text-[13px] text-white/90 truncate">
                  {identity.name}
                </span>
                <span className="block text-[10px] text-white/35">
                  Dein Name · Profil ändern
                </span>
              </span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {peers.length === 0 && (
              <div className="text-[12px] text-white/35 px-2 py-6 text-center leading-relaxed">
                Noch keine Freunde. Wer Jon im selben Netzwerk offen hat,
                erscheint hier automatisch — oder gib unten seinen Namen ein.
              </div>
            )}
            {peers.map((p) => (
              <div
                key={p.id}
                className={`group flex items-center gap-2 px-2 py-2 rounded-xl cursor-pointer transition-colors ${
                  p.id === activeId
                    ? "bg-gold/15 border border-gold/30"
                    : "hover:bg-white/5 border border-transparent"
                }`}
                onClick={() => void openPeer(p.id)}
              >
                <span className="relative text-xl">
                  {p.avatar}
                  <span
                    className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-[#0c0c10] ${
                      p.online ? "bg-emerald-400" : "bg-white/25"
                    }`}
                  />
                </span>
                <span className="flex-1 min-w-0">
                  <span className="block text-[13px] text-white/85 truncate">
                    {p.name}
                  </span>
                  <span className="block text-[10px] text-white/35">
                    {p.typing || isTyping(p.id) ? (
                      <span className="text-gold/80">tippt …</span>
                    ) : p.online ? (
                      "online"
                    ) : (
                      "offline"
                    )}
                  </span>
                </span>
                {p.unread > 0 && (
                  <span className="text-[10px] font-semibold bg-gold text-black rounded-full px-1.5 py-0.5">
                    {p.unread}
                  </span>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    void remove(p.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 text-white/30 hover:text-red-300 text-[12px] transition"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          <div className="p-2 border-t border-white/10 space-y-1.5">
            <div className="flex gap-1.5">
              <input
                value={friendName}
                onChange={(e) => setFriendName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void connect();
                }}
                placeholder="Name des Freundes"
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-[12px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50"
              />
              <button
                onClick={() => void connect()}
                disabled={adding}
                title="Freund per Name suchen"
                className="px-2.5 rounded-lg bg-gold/20 border border-gold/40 text-gold text-[12px] hover:bg-gold/30 disabled:opacity-50 transition"
              >
                {adding ? "…" : "+"}
              </button>
            </div>
            <div className="text-[10px] text-white/30 leading-snug">
              Einfach den Namen eintippen — Jon findet ihn im Netzwerk.
            </div>
          </div>
        </div>

        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex items-center justify-between px-5 h-14 border-b border-white/10">
            <div className="text-[14px] text-white/90">
              {active ? (
                <span className="flex items-center gap-2">
                  <span className="text-xl">{active.avatar}</span>
                  {active.name}
                  {active.typing ? (
                    <span className="text-[11px] text-gold/90 flex items-center gap-1.5">
                      <TypingDots /> tippt …
                    </span>
                  ) : (
                    <span
                      className={`text-[11px] ${
                        active.online ? "text-emerald-400" : "text-white/30"
                      }`}
                    >
                      {active.online ? "online" : "offline"}
                    </span>
                  )}
                </span>
              ) : (
                <span className="text-white/40">💬 Freunde-Chat</span>
              )}
            </div>
            <button
              onClick={onClose}
              className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition"
            >
              ✕
            </button>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
            {!active && (
              <div className="h-full flex flex-col items-center justify-center text-center text-white/35 text-[13px] leading-relaxed px-10">
                <div className="text-4xl mb-3">💬</div>
                Wähle links einen Freund aus.
                <br />
                Nachrichten, Bilder und Videos werden{" "}
                <span className="text-gold/70">direkt</span> zwischen euren PCs
                verschickt — ohne Server, ohne Cloud.
              </div>
            )}
            {active &&
              messages.length === 0 && (
                <div className="text-center text-white/30 text-[12px] py-10">
                  Noch keine Nachrichten. Schreib {active.name} etwas!
                </div>
              )}
            {messages.map((m) => {
              const mine = m.direction === "out";
              return (
                <div
                  key={m.id}
                  className={`flex ${mine ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[70%] px-3 py-2 rounded-2xl ${
                      mine
                        ? "bg-gradient-to-br from-gold-light/90 to-gold-dark/90 text-black rounded-br-md"
                        : "bg-white/8 border border-white/10 text-white/90 rounded-bl-md"
                    }`}
                  >
                    {m.media_kind === "image" && (
                      <img
                        src={mediaUrl(m.id)}
                        alt={m.media_name ?? ""}
                        className="rounded-lg mb-1 max-h-72 w-auto"
                      />
                    )}
                    {m.media_kind === "video" && (
                      <video
                        src={mediaUrl(m.id)}
                        controls
                        className="rounded-lg mb-1 max-h-72"
                      />
                    )}
                    {m.media_kind === "file" && (
                      <a
                        href={mediaUrl(m.id)}
                        download={m.media_name ?? "datei"}
                        className={`flex items-center gap-1.5 text-[12px] underline mb-1 ${
                          mine ? "text-black/80" : "text-gold/80"
                        }`}
                      >
                        📎 {m.media_name}
                      </a>
                    )}
                    {m.text && (
                      <div className="whitespace-pre-wrap break-words text-[13.5px]">
                        {m.text}
                      </div>
                    )}
                    <div
                      className={`text-[10px] mt-0.5 ${
                        mine ? "text-black/45" : "text-white/30"
                      }`}
                    >
                      {new Date(m.created_at).toLocaleTimeString("de-DE", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </div>
                  </div>
                </div>
              );
            })}
            {active?.typing && (
              <div className="flex justify-start">
                <div className="bg-white/8 border border-white/10 rounded-2xl rounded-bl-md px-4 py-3">
                  <TypingDots />
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="px-5 py-1.5 text-[12px] text-red-300 border-t border-red-400/20 bg-red-400/5">
              {error}
            </div>
          )}

          {active && (
            <div className="p-3 border-t border-white/10">
              <div className="flex items-end gap-2">
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/*,video/*,.pdf,.txt,.zip"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) attach(file);
                    e.target.value = "";
                  }}
                />
                <button
                  onClick={() => fileRef.current?.click()}
                  disabled={busy}
                  title="Bild, Video oder Datei senden"
                  className="w-9 h-9 rounded-xl border border-white/10 bg-white/5 text-white/40 hover:text-gold hover:border-gold/40 disabled:opacity-40 transition"
                >
                  📎
                </button>
                <textarea
                  value={text}
                  onChange={(e) => {
                    setText(e.target.value);
                    const now = Date.now();
                    if (e.target.value && now - typingSentRef.current > 1200) {
                      typingSentRef.current = now;
                      void sendTyping(active.id);
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void submit();
                    }
                  }}
                  rows={1}
                  placeholder={`Nachricht an ${active.name} …`}
                  className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-[13.5px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50 resize-none max-h-32"
                />
                <button
                  onClick={() => void submit()}
                  disabled={busy || !text.trim()}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[13px] shadow-gold disabled:opacity-40 hover:brightness-110 transition"
                >
                  {busy ? "…" : "Senden"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
