import { useEffect, useRef, useState } from "react";
import {
  P2PGroup,
  P2PGroupInvite,
  P2PIdentity,
  P2PMessage,
  P2PPeer,
  P2PRequest,
  addPeer,
  answerGroupInvite,
  answerRequest,
  clearChat,
  createGroup,
  deleteGroup,
  deleteMessage,
  deletePeer,
  getGroupInvites,
  getGroups,
  getP2PMessages,
  getPeers,
  getRequests,
  getTypingPeers,
  leaveGroup,
  mediaUrl,
  reactToMessage,
  searchChats,
  sendP2PMessage,
  sendTyping,
  transcribeMessage,
} from "../lib/api";
import { VoiceRecorder } from "../lib/recorder";

const EMOJIS = ["❤️", "👍", "😂", "😮", "😢", "🔥"];

interface Props {
  identity: P2PIdentity;
  onEditProfile: () => void;
  onClose: () => void;
}

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

export default function FriendsChat({
  identity,
  onEditProfile,
  onClose,
}: Props) {
  const [peers, setPeers] = useState<P2PPeer[]>([]);
  const [groups, setGroups] = useState<P2PGroup[]>([]);
  const [requests, setRequests] = useState<P2PRequest[]>([]);
  const [typing, setTyping] = useState<string[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<P2PMessage[]>([]);
  const [text, setText] = useState("");
  const [friendInput, setFriendInput] = useState("");
  const [addMode, setAddMode] = useState<"name" | "code">("name");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [adding, setAdding] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcripts, setTranscripts] = useState<Record<string, string>>({});
  const [groupMode, setGroupMode] = useState(false);
  const [groupName, setGroupName] = useState("");
  const [groupMembers, setGroupMembers] = useState<string[]>([]);
  const [copied, setCopied] = useState(false);
  const [invites, setInvites] = useState<P2PGroupInvite[]>([]);
  const [replyTo, setReplyTo] = useState<P2PMessage | null>(null);
  const [menuFor, setMenuFor] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<P2PMessage[]>([]);
  const [mentionOpen, setMentionOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const activeRef = useRef<string | null>(null);
  const typingSentRef = useRef(0);
  const recorderRef = useRef<VoiceRecorder | null>(null);

  useEffect(() => {
    activeRef.current = activeId;
  }, [activeId]);

  useEffect(() => {
    const tick = async () => {
      setPeers(await getPeers());
      setGroups(await getGroups());
      setRequests(await getRequests());
      setInvites(await getGroupInvites());
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

  const isTyping = (peerId: string) => typing.includes(peerId);
  const group = groups.find((g) => g.id === activeId) ?? null;
  const peer = peers.find((p) => p.id === activeId) ?? null;
  const activeName = group?.name ?? peer?.name ?? "";

  const openChat = async (id: string) => {
    setActiveId(id);
    setError("");
    setMessages(await getP2PMessages(id));
  };

  const submit = async (media?: { name: string; mime: string; data: string }) => {
    if (!activeId || busy) return;
    if (!text.trim() && !media) return;
    setBusy(true);
    setError("");
    try {
      await sendP2PMessage(
        group ? "" : activeId,
        text.trim(),
        media,
        group ? activeId : "",
        replyTo?.id ?? ""
      );
      setText("");
      setReplyTo(null);
      setMessages(await getP2PMessages(activeId));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const react = async (messageId: string, emoji: string) => {
    setMenuFor(null);
    await reactToMessage(messageId, emoji);
    if (activeId) setMessages(await getP2PMessages(activeId));
  };

  const removeMessage = async (messageId: string, forAll: boolean) => {
    setMenuFor(null);
    await deleteMessage(messageId, forAll);
    if (activeId) setMessages(await getP2PMessages(activeId));
  };

  const clearHistory = async () => {
    if (!activeId) return;
    await clearChat(activeId);
    setMessages(await getP2PMessages(activeId));
  };

  const leave = async () => {
    if (!group) return;
    await leaveGroup(group.id);
    setActiveId(null);
    setMessages([]);
    setGroups(await getGroups());
  };

  const decideGroup = async (groupId: string, action: "accept" | "reject") => {
    setError("");
    try {
      await answerGroupInvite(groupId, action);
      setInvites(await getGroupInvites());
      setGroups(await getGroups());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const runSearch = async (value: string) => {
    setQuery(value);
    setHits(value.trim().length >= 2 ? await searchChats(value) : []);
  };

  const insertMention = (name: string) => {
    setText((prev) => prev.replace(/@[\wÀ-ſ]*$/, `@${name} `));
    setMentionOpen(false);
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

  const toggleRecording = async () => {
    if (recording) {
      const blob = await recorderRef.current?.stop();
      recorderRef.current = null;
      setRecording(false);
      if (!blob) return;
      const reader = new FileReader();
      reader.onload = () => {
        const result = String(reader.result ?? "");
        void submit({
          name: `sprachnachricht-${Date.now()}.wav`,
          mime: "audio/wav",
          data: result.slice(result.indexOf(",") + 1),
        });
      };
      reader.readAsDataURL(blob);
      return;
    }
    try {
      const rec = new VoiceRecorder();
      await rec.start();
      recorderRef.current = rec;
      setRecording(true);
    } catch {
      setError("Kein Mikrofon-Zugriff.");
    }
  };

  const transcribe = async (messageId: string) => {
    setTranscripts((prev) => ({ ...prev, [messageId]: "…" }));
    try {
      const result = await transcribeMessage(messageId);
      setTranscripts((prev) => ({ ...prev, [messageId]: result }));
    } catch (e) {
      setTranscripts((prev) => ({
        ...prev,
        [messageId]: e instanceof Error ? e.message : String(e),
      }));
    }
  };

  const connect = async () => {
    if (!friendInput.trim()) return;
    setAdding(true);
    setError("");
    try {
      await addPeer(friendInput.trim(), addMode);
      setFriendInput("");
      setPeers(await getPeers());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setAdding(false);
    }
  };

  const decide = async (peerId: string, action: "accept" | "reject" | "block") => {
    await answerRequest(peerId, action);
    setRequests(await getRequests());
    setPeers(await getPeers());
  };

  const saveGroup = async () => {
    setError("");
    try {
      await createGroup(groupName.trim(), groupMembers);
      setGroupMode(false);
      setGroupName("");
      setGroupMembers([]);
      setGroups(await getGroups());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const remove = async (id: string, isGroup: boolean) => {
    if (isGroup) await deleteGroup(id);
    else await deletePeer(id);
    if (id === activeId) {
      setActiveId(null);
      setMessages([]);
    }
    setPeers(await getPeers());
    setGroups(await getGroups());
  };

  const copyCode = () => {
    void navigator.clipboard.writeText(identity.code);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[940px] max-w-[95vw] h-[660px] max-h-[92vh] flex overflow-hidden">
        <div className="w-72 border-r border-white/10 flex flex-col">
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
                  Profil ändern
                </span>
              </span>
            </button>
            <button
              onClick={copyCode}
              title="Dein Jon-Code — den kann dir ein Freund aus dem Internet eintragen"
              className="mt-2 w-full text-left text-[10px] text-white/40 hover:text-gold transition font-mono border border-white/10 rounded-lg px-2 py-1"
            >
              {copied ? "✓ kopiert" : `Jon-Code: ${identity.code}`}
            </button>
          </div>

          <div className="px-2 pt-2">
            <input
              value={query}
              onChange={(e) => void runSearch(e.target.value)}
              placeholder="🔍 In allen Chats suchen …"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-[12px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50"
            />
          </div>

          {invites.length > 0 && (
            <div className="p-2 border-b border-white/10 space-y-1.5">
              <div className="text-[10px] uppercase tracking-wide text-gold/70 px-1">
                Gruppen-Einladungen
              </div>
              {invites.map((g) => (
                <div
                  key={g.id}
                  className="rounded-xl border border-gold/30 bg-gold/10 px-2.5 py-2"
                >
                  <div className="text-[12px] text-white/90">👥 {g.name}</div>
                  <div className="text-[10px] text-white/40">
                    von {g.from_name} · {g.members.join(", ")}
                  </div>
                  <div className="flex gap-1 mt-1.5">
                    <button
                      onClick={() => void decideGroup(g.id, "accept")}
                      className="flex-1 text-[11px] py-1 rounded-lg bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold"
                    >
                      Beitreten
                    </button>
                    <button
                      onClick={() => void decideGroup(g.id, "reject")}
                      className="flex-1 text-[11px] py-1 rounded-lg border border-white/15 text-white/60 hover:bg-white/10"
                    >
                      Ablehnen
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {requests.length > 0 && (
            <div className="p-2 border-b border-white/10 space-y-1.5">
              <div className="text-[10px] uppercase tracking-wide text-gold/70 px-1">
                Freundschaftsanfragen
              </div>
              {requests.map((r) => (
                <div
                  key={r.id}
                  className="rounded-xl border border-gold/30 bg-gold/10 px-2.5 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{r.avatar}</span>
                    <span className="flex-1 min-w-0">
                      <span className="block text-[12px] text-white/90 truncate">
                        {r.name}
                      </span>
                      <span className="block text-[10px] text-white/40">
                        möchte mit dir schreiben
                      </span>
                    </span>
                  </div>
                  <div className="flex gap-1 mt-1.5">
                    <button
                      onClick={() => void decide(r.id, "accept")}
                      className="flex-1 text-[11px] py-1 rounded-lg bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold"
                    >
                      Annehmen
                    </button>
                    <button
                      onClick={() => void decide(r.id, "reject")}
                      className="flex-1 text-[11px] py-1 rounded-lg border border-white/15 text-white/60 hover:bg-white/10"
                    >
                      Ablehnen
                    </button>
                    <button
                      onClick={() => void decide(r.id, "block")}
                      title="Blockieren"
                      className="px-2 text-[11px] py-1 rounded-lg border border-red-400/30 text-red-300/80 hover:bg-red-400/10"
                    >
                      🚫
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {hits.length > 0 && (
              <div className="space-y-1 pb-2 mb-1 border-b border-white/10">
                <div className="text-[10px] uppercase tracking-wide text-gold/70 px-1">
                  {hits.length} Treffer
                </div>
                {hits.map((h) => (
                  <button
                    key={h.id}
                    onClick={() => {
                      void openChat(h.chat_id ?? h.peer_id);
                      setQuery("");
                      setHits([]);
                    }}
                    className="w-full text-left px-2 py-1.5 rounded-lg hover:bg-white/5 transition"
                  >
                    <div className="text-[11px] text-gold/80">{h.chat_name}</div>
                    <div className="text-[12px] text-white/70 truncate">
                      {h.text || h.transcript}
                    </div>
                  </button>
                ))}
              </div>
            )}
            {peers.length === 0 && groups.length === 0 && (
              <div className="text-[12px] text-white/35 px-2 py-6 text-center leading-relaxed">
                Noch keine Freunde. Wer Jon im selben Netzwerk offen hat,
                erscheint hier automatisch — sonst gib unten seinen Namen ein.
              </div>
            )}
            {groups.map((g) => (
              <div
                key={g.id}
                onClick={() => void openChat(g.id)}
                className={`group flex items-center gap-2 px-2 py-2 rounded-xl cursor-pointer transition-colors ${
                  g.id === activeId
                    ? "bg-gold/15 border border-gold/30"
                    : "hover:bg-white/5 border border-transparent"
                }`}
              >
                <span className="text-xl">👥</span>
                <span className="flex-1 min-w-0">
                  <span className="block text-[13px] text-white/85 truncate">
                    {g.name}
                  </span>
                  <span className="block text-[10px] text-white/35 truncate">
                    {g.member_names.join(", ") || "keine Mitglieder"}
                  </span>
                </span>
                {g.unread > 0 && (
                  <span className="text-[10px] font-semibold bg-gold text-black rounded-full px-1.5 py-0.5">
                    {g.unread}
                  </span>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    void remove(g.id, true);
                  }}
                  className="opacity-0 group-hover:opacity-100 text-white/30 hover:text-red-300 text-[12px] transition"
                >
                  ✕
                </button>
              </div>
            ))}
            {peers.map((p) => (
              <div
                key={p.id}
                onClick={() => void openChat(p.id)}
                className={`group flex items-center gap-2 px-2 py-2 rounded-xl cursor-pointer transition-colors ${
                  p.id === activeId
                    ? "bg-gold/15 border border-gold/30"
                    : "hover:bg-white/5 border border-transparent"
                }`}
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
                    {p.name} {p.encrypted && <span title="Ende-zu-Ende verschlüsselt">🔒</span>}
                  </span>
                  <span className="block text-[10px] text-white/35">
                    {p.typing || isTyping(p.id) ? (
                      <span className="text-gold/80">tippt …</span>
                    ) : p.waiting ? (
                      "Anfrage gesendet"
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
                    void remove(p.id, false);
                  }}
                  className="opacity-0 group-hover:opacity-100 text-white/30 hover:text-red-300 text-[12px] transition"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          {groupMode ? (
            <div className="p-2 border-t border-white/10 space-y-1.5">
              <input
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                placeholder="Gruppenname"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-[12px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50"
              />
              <div className="max-h-24 overflow-y-auto space-y-0.5">
                {peers.map((p) => (
                  <label
                    key={p.id}
                    className="flex items-center gap-2 text-[12px] text-white/70 px-1 py-0.5 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={groupMembers.includes(p.id)}
                      onChange={(e) =>
                        setGroupMembers((prev) =>
                          e.target.checked
                            ? [...prev, p.id]
                            : prev.filter((id) => id !== p.id)
                        )
                      }
                      className="accent-gold"
                    />
                    {p.avatar} {p.name}
                  </label>
                ))}
              </div>
              <div className="flex gap-1.5">
                <button
                  onClick={() => void saveGroup()}
                  className="flex-1 text-[12px] py-1.5 rounded-lg bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold"
                >
                  Erstellen
                </button>
                <button
                  onClick={() => setGroupMode(false)}
                  className="px-3 text-[12px] py-1.5 rounded-lg border border-white/15 text-white/60"
                >
                  ✕
                </button>
              </div>
            </div>
          ) : (
            <div className="p-2 border-t border-white/10 space-y-1.5">
              <div className="flex gap-1">
                {(["name", "code"] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => setAddMode(m)}
                    className={`flex-1 text-[10px] py-1 rounded-lg border transition ${
                      addMode === m
                        ? "border-gold/40 bg-gold/15 text-gold"
                        : "border-white/10 text-white/40 hover:bg-white/5"
                    }`}
                  >
                    {m === "name" ? "Name (WLAN)" : "Jon-Code (Internet)"}
                  </button>
                ))}
              </div>
              <div className="flex gap-1.5">
                <input
                  value={friendInput}
                  onChange={(e) => setFriendInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void connect();
                  }}
                  placeholder={
                    addMode === "name" ? "Name des Freundes" : "Jon-Code"
                  }
                  className="flex-1 bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-[12px] text-white/90 placeholder-white/30 outline-none focus:border-gold/50"
                />
                <button
                  onClick={() => void connect()}
                  disabled={adding}
                  className="px-2.5 rounded-lg bg-gold/20 border border-gold/40 text-gold text-[12px] hover:bg-gold/30 disabled:opacity-50 transition"
                >
                  {adding ? "…" : "+"}
                </button>
              </div>
              <button
                onClick={() => setGroupMode(true)}
                disabled={peers.length === 0}
                className="w-full text-[11px] py-1.5 rounded-lg border border-white/10 text-white/50 hover:bg-white/5 disabled:opacity-40 transition"
              >
                👥 Gruppe erstellen
              </button>
            </div>
          )}
        </div>

        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex items-center justify-between px-5 h-14 border-b border-white/10">
            <div className="text-[14px] text-white/90">
              {group ? (
                <span className="flex items-center gap-2">
                  <span className="text-xl">👥</span>
                  {group.name}
                  <span className="text-[11px] text-white/35">
                    {group.member_names.join(", ")}
                  </span>
                </span>
              ) : peer ? (
                <span className="flex items-center gap-2">
                  <span className="text-xl">{peer.avatar}</span>
                  {peer.name}
                  {peer.typing || isTyping(peer.id) ? (
                    <span className="text-[11px] text-gold/90 flex items-center gap-1.5">
                      <TypingDots /> tippt …
                    </span>
                  ) : (
                    <span
                      className={`text-[11px] ${
                        peer.online ? "text-emerald-400" : "text-white/30"
                      }`}
                    >
                      {peer.online ? "online" : "offline"}
                    </span>
                  )}
                  {peer.encrypted && (
                    <span
                      title="Ende-zu-Ende verschlüsselt"
                      className="text-[11px] text-emerald-400/70"
                    >
                      🔒
                    </span>
                  )}
                </span>
              ) : (
                <span className="text-white/40">💬 Freunde-Chat</span>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              {activeId && (
                <button
                  onClick={() => void clearHistory()}
                  title="Chatverlauf bei mir löschen"
                  className="text-[11px] px-2 py-1 rounded-lg border border-white/10 text-white/45 hover:text-red-300 hover:border-red-400/30 transition"
                >
                  Verlauf löschen
                </button>
              )}
              {group && (
                <button
                  onClick={() => void leave()}
                  title="Gruppe verlassen"
                  className="text-[11px] px-2 py-1 rounded-lg border border-white/10 text-white/45 hover:text-red-300 hover:border-red-400/30 transition"
                >
                  Gruppe verlassen
                </button>
              )}
              <button
                onClick={onClose}
                className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition"
              >
                ✕
              </button>
            </div>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
            {!activeId && (
              <div className="h-full flex flex-col items-center justify-center text-center text-white/35 text-[13px] leading-relaxed px-10">
                <div className="text-4xl mb-3">💬</div>
                Wähle links einen Freund oder eine Gruppe.
                <br />
                Nachrichten, Bilder, Videos und Sprachnachrichten gehen{" "}
                <span className="text-gold/70">direkt</span> und{" "}
                <span className="text-emerald-400/80">verschlüsselt</span>{" "}
                zwischen euren PCs — ohne Server.
              </div>
            )}
            {activeId && messages.length === 0 && (
              <div className="text-center text-white/30 text-[12px] py-10">
                Noch keine Nachrichten. Schreib {activeName} etwas!
              </div>
            )}
            {messages.map((m) => {
              const mine = m.direction === "out";
              const shown = transcripts[m.id] ?? m.transcript;
              const mentioned =
                !mine &&
                identity.name &&
                m.text.toLowerCase().includes(`@${identity.name.toLowerCase()}`);
              if (m.deleted)
                return (
                  <div
                    key={m.id}
                    className={`flex ${mine ? "justify-end" : "justify-start"}`}
                  >
                    <div className="px-3 py-2 rounded-2xl border border-white/10 bg-white/5 text-white/35 text-[12px] italic">
                      🚫 Diese Nachricht wurde gelöscht
                    </div>
                  </div>
                );
              return (
                <div
                  key={m.id}
                  className={`group/msg flex items-center gap-1.5 ${
                    mine ? "justify-end" : "justify-start"
                  }`}
                >
                  {mine && (
                    <button
                      onClick={() => setMenuFor(menuFor === m.id ? null : m.id)}
                      className="opacity-0 group-hover/msg:opacity-100 text-white/30 hover:text-gold text-[13px] transition"
                    >
                      ⋯
                    </button>
                  )}
                  <div
                    className={`relative max-w-[70%] px-3 py-2 rounded-2xl ${
                      mine
                        ? "bg-gradient-to-br from-gold-light/90 to-gold-dark/90 text-black rounded-br-md"
                        : mentioned
                          ? "bg-gold/15 border border-gold/40 text-white/90 rounded-bl-md"
                          : "bg-white/8 border border-white/10 text-white/90 rounded-bl-md"
                    }`}
                  >
                    {menuFor === m.id && (
                      <div
                        className={`absolute z-10 top-full mt-1 ${
                          mine ? "right-0" : "left-0"
                        } glass rounded-xl border border-white/15 p-1.5 w-44`}
                      >
                        <div className="flex gap-1 pb-1.5 mb-1 border-b border-white/10">
                          {EMOJIS.map((e) => (
                            <button
                              key={e}
                              onClick={() => void react(m.id, e)}
                              className="text-[15px] hover:scale-125 transition"
                            >
                              {e}
                            </button>
                          ))}
                        </div>
                        <button
                          onClick={() => {
                            setReplyTo(m);
                            setMenuFor(null);
                          }}
                          className="w-full text-left text-[12px] px-2 py-1 rounded-lg text-white/70 hover:bg-white/10"
                        >
                          ↩ Antworten
                        </button>
                        <button
                          onClick={() => void removeMessage(m.id, false)}
                          className="w-full text-left text-[12px] px-2 py-1 rounded-lg text-white/70 hover:bg-white/10"
                        >
                          🗑 Bei mir löschen
                        </button>
                        {mine && (
                          <button
                            onClick={() => void removeMessage(m.id, true)}
                            className="w-full text-left text-[12px] px-2 py-1 rounded-lg text-red-300/80 hover:bg-red-400/10"
                          >
                            🗑 Für alle löschen
                          </button>
                        )}
                      </div>
                    )}
                    {group && !mine && (
                      <div className="text-[10px] font-semibold text-gold/80 mb-0.5">
                        {m.sender_name}
                      </div>
                    )}
                    {m.reply_preview && (
                      <div
                        className={`text-[11px] mb-1 pl-2 border-l-2 rounded ${
                          mine
                            ? "border-black/30 text-black/60"
                            : "border-gold/50 text-white/50"
                        }`}
                      >
                        {m.reply_preview}
                      </div>
                    )}
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
                    {m.media_kind === "audio" && (
                      <div className="mb-1">
                        <audio src={mediaUrl(m.id)} controls className="h-9 w-56" />
                        {!shown && (
                          <button
                            onClick={() => void transcribe(m.id)}
                            className={`block mt-1 text-[11px] underline ${
                              mine ? "text-black/70" : "text-gold/80 hover:text-gold"
                            }`}
                          >
                            📝 Text anzeigen (nicht anhören)
                          </button>
                        )}
                        {shown && (
                          <div
                            className={`mt-1 text-[12px] italic ${
                              mine ? "text-black/70" : "text-white/70"
                            }`}
                          >
                            „{shown}"
                          </div>
                        )}
                      </div>
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
                    {Object.keys(m.reactions ?? {}).length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {Object.entries(m.reactions).map(([emoji, people]) => (
                          <button
                            key={emoji}
                            onClick={() => void react(m.id, emoji)}
                            title={people.join(", ")}
                            className={`text-[11px] px-1.5 py-0.5 rounded-full border ${
                              mine
                                ? "border-black/20 bg-black/10 text-black/80"
                                : "border-white/15 bg-white/10 text-white/80"
                            }`}
                          >
                            {emoji} {people.length}
                          </button>
                        ))}
                      </div>
                    )}
                    <div
                      className={`flex items-center gap-1 text-[10px] mt-0.5 ${
                        mine ? "text-black/45" : "text-white/30"
                      }`}
                    >
                      {new Date(m.created_at).toLocaleTimeString("de-DE", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                      {mine && (
                        <span
                          title={
                            m.read
                              ? "Gelesen"
                              : m.delivered
                                ? "Zugestellt"
                                : "Wird zugestellt, sobald er online ist"
                          }
                          className={m.read ? "text-sky-700 font-bold" : ""}
                        >
                          {m.read ? "✓✓" : m.delivered ? "✓✓" : "🕑"}
                        </span>
                      )}
                    </div>
                  </div>
                  {!mine && (
                    <button
                      onClick={() => setMenuFor(menuFor === m.id ? null : m.id)}
                      className="opacity-0 group-hover/msg:opacity-100 text-white/30 hover:text-gold text-[13px] transition"
                    >
                      ⋯
                    </button>
                  )}
                </div>
              );
            })}
            {peer && (peer.typing || isTyping(peer.id)) && (
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

          {activeId && (
            <div className="p-3 border-t border-white/10">
              {replyTo && (
                <div className="flex items-center gap-2 mb-2 px-2 py-1.5 rounded-lg bg-white/5 border-l-2 border-gold/50">
                  <span className="flex-1 text-[11px] text-white/60 truncate">
                    ↩ {replyTo.direction === "out" ? "Du" : replyTo.sender_name}:{" "}
                    {replyTo.text || `[${replyTo.media_kind}]`}
                  </span>
                  <button
                    onClick={() => setReplyTo(null)}
                    className="text-white/30 hover:text-white/70 text-[12px]"
                  >
                    ✕
                  </button>
                </div>
              )}
              {mentionOpen && group && (
                <div className="flex flex-wrap gap-1 mb-2">
                  {group.member_names.map((name) => (
                    <button
                      key={name}
                      onClick={() => insertMention(name)}
                      className="text-[11px] px-2 py-1 rounded-lg border border-gold/30 bg-gold/10 text-gold/90 hover:bg-gold/20"
                    >
                      @{name}
                    </button>
                  ))}
                </div>
              )}
              <div className="flex items-end gap-2">
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/*,video/*,audio/*,.pdf,.txt,.zip"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) attach(file);
                    e.target.value = "";
                  }}
                />
                <button
                  onClick={() => fileRef.current?.click()}
                  disabled={busy || recording}
                  title="Bild, Video oder Datei senden"
                  className="w-9 h-9 rounded-xl border border-white/10 bg-white/5 text-white/40 hover:text-gold hover:border-gold/40 disabled:opacity-40 transition"
                >
                  📎
                </button>
                <button
                  onClick={() => void toggleRecording()}
                  disabled={busy}
                  title={recording ? "Aufnahme beenden und senden" : "Sprachnachricht aufnehmen"}
                  className={`w-9 h-9 rounded-xl border transition ${
                    recording
                      ? "border-red-400/60 bg-red-500/20 text-red-300 animate-pulse"
                      : "border-white/10 bg-white/5 text-white/40 hover:text-gold hover:border-gold/40"
                  } disabled:opacity-40`}
                >
                  {recording ? "⏹" : "🎙"}
                </button>
                <textarea
                  value={text}
                  onChange={(e) => {
                    const value = e.target.value;
                    setText(value);
                    setMentionOpen(!!group && /@[\wÀ-ſ]*$/.test(value));
                    const now = Date.now();
                    if (!group && value && now - typingSentRef.current > 1200) {
                      typingSentRef.current = now;
                      void sendTyping(activeId);
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void submit();
                    }
                  }}
                  rows={1}
                  placeholder={
                    recording
                      ? "Nimmt auf … zum Senden auf ⏹ drücken"
                      : `Nachricht an ${activeName} …`
                  }
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
