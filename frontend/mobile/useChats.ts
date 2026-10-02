import {MutableRefObject, useEffect, useRef, useState} from "react";
import {api, call, listen, native} from "./bridge";

export type Step = {name?: string; summary?: string; status?: string; ok?: boolean; approval_id?: string; args?: any};
export type Message = {id: string; role: string; content: string; reasoning?: string; cards?: any[]; steps?: Step[]; seconds?: number; model?: string; bilder?: string[]; lokal?: boolean};
export type Thread = {key: string; id?: string; title: string; messages: Message[]; provider: string; model: string; mode: string; workspace: string; temp?: boolean; busy?: boolean; partial?: string; reasoning?: string; steps?: Step[]; approval?: any; error?: string; cards?: any[]; started?: number; lokal?: boolean; fortschritt?: string};
export type Motor = "pi" | "solo" | "lokal";
export type Umgebung = {weg: Motor; freigabe: string; name: string; verbunden: boolean; gekoppelt: boolean};

export const LANG = 45 * 60_000;
export const uid = () => (globalThis.crypto && "randomUUID" in crypto) ? crypto.randomUUID() : `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
const lokaleId = () => `lokal-${uid().replace(/-/g, "").slice(0, 22)}`;

export function modelPrefs(): {provider?: string; model?: string} {
  try {return JSON.parse(localStorage.getItem("jon-model") || "{}");} catch {return {};}
}
export function rememberModel(provider: string, model: string) {
  try {localStorage.setItem("jon-model", JSON.stringify({provider, model}));} catch {}
}

const newThread = (mode = "chat", workspace = ""): Thread => ({key: uid(), title: "Neuer Chat", messages: [], provider: modelPrefs().provider || "", model: modelPrefs().model || "", mode, workspace});

function parseCards(raw: unknown) {
  if (Array.isArray(raw)) return raw;
  try {return JSON.parse(String(raw || "[]"));} catch {return [];}
}

export function motorFuer(thread: Thread, umgebung: Umgebung): Motor {
  if (thread.provider === "handy") return "lokal";
  if (thread.lokal && umgebung.weg === "pi") return umgebung.verbunden ? "pi" : "lokal";
  return umgebung.weg;
}

export function useChats(umgebung: MutableRefObject<Umgebung>) {
  const first = useRef(newThread());
  const [threads, setThreads] = useState<Record<string, Thread>>({[first.current.key]: first.current});
  const [active, setActive] = useState(first.current.key);
  const [list, setList] = useState<any[]>([]);
  const refs = useRef(threads);
  refs.current = threads;
  const activeRef = useRef(active);
  activeRef.current = active;
  const cancelers = useRef(new Map<string, () => void>());
  const current = threads[active];

  function change(key: string, patch: Partial<Thread>) {setThreads(old => old[key] ? {...old, [key]: {...old[key], ...patch}} : old);}

  async function refresh() {
    const [pi, lokal] = await Promise.allSettled([
      umgebung.current.gekoppelt ? api<any[]>("/api/conversations") : Promise.resolve([]),
      call<{chats: any[]}>("lokal-chats")
    ]);
    const entfernt = pi.status === "fulfilled" && Array.isArray(pi.value) ? pi.value : [];
    const eigene = lokal.status === "fulfilled" ? lokal.value.chats || [] : [];
    const alle = [...entfernt, ...eigene].sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
    setList(alle);
    if (pi.status === "rejected" && lokal.status === "rejected") throw pi.reason;
    return alle;
  }

  async function open(id: string, quiet = false) {
    const cached = Object.values(refs.current).find(thread => thread.id === id);
    if (cached?.busy) {if (!quiet) setActive(cached.key); return;}
    const key = cached?.key || uid();
    let thread: Thread;
    if (id.startsWith("lokal-")) {
      const chat = await call<any>("lokal-chat", {chat: id});
      thread = {...newThread(chat.mode || "chat", chat.workspace || ""), ...cached, key, id, lokal: true, title: chat.title || "Chat", provider: chat.provider || "", model: chat.model || "", mode: chat.mode || "chat",
        messages: (chat.messages || []).map((m: any) => ({id: m.id || uid(), role: m.role, content: m.content || "", reasoning: m.reasoning || "", cards: m.cards || [], steps: m.steps || [], seconds: m.seconds, model: m.model}))};
    } else {
      const conv = await api<any>(`/api/conversations/${id}`);
      thread = {
        ...newThread(), ...cached, key, id, title: conv.title || "Chat", provider: conv.provider || cached?.provider || "", model: conv.model || cached?.model || "",
        messages: (conv.messages || []).map((m: any) => ({id: m.id, role: m.role, content: m.content || "", reasoning: m.reasoning || "", cards: parseCards(m.karten)}))
      };
    }
    setThreads(old => ({...old, [key]: thread}));
    if (!quiet) setActive(key);
  }

  function create(mode = current.mode, workspace = "", temp = false) {
    const thread = {...newThread(mode, workspace), provider: current.provider, model: current.model, temp};
    setThreads(old => ({...old, [thread.key]: thread}));
    setActive(thread.key);
    return thread;
  }

  function update(patch: Partial<Thread>) {change(activeRef.current, patch);}

  function hinzufuegen(inhalt: string, extra: Partial<Message> = {}, rolle = "assistant") {
    const key = activeRef.current;
    const thread = refs.current[key];
    if (!thread) return;
    change(key, {messages: [...thread.messages, {id: uid(), role: rolle, content: inhalt, lokal: true, ...extra}]});
  }

  async function lokalSpeichern(thread: Thread, messages: Message[]) {
    if (thread.temp || !thread.id?.startsWith("lokal-")) return;
    await call("lokal-chat-speichern", {chat: {id: thread.id, title: thread.title, provider: thread.provider, model: thread.model, mode: thread.mode, workspace: thread.workspace,
      messages: messages.slice(-400).map(m => ({id: m.id, role: m.role, content: m.content, reasoning: m.reasoning, cards: m.cards, steps: (m.steps || []).map(s => ({name: s.name, summary: s.summary, ok: s.ok, args: s.args})), seconds: m.seconds, model: m.model}))}}).catch(() => {});
  }

  async function send(text: string, attached = "", supplied?: Thread, force = "", bilder: string[] = []): Promise<Message | undefined> {
    const thread = supplied || refs.current[activeRef.current];
    if (!text.trim() || thread.busy) return;
    const key = thread.key;
    const motor = motorFuer(thread, umgebung.current);
    const message: Message = {id: uid(), role: "user", content: text + (attached ? `\n\n${attached}` : ""), bilder: bilder.length ? bilder.slice(0, 1) : undefined};
    const messages = [...thread.messages, message];
    const started = Date.now();
    const id = motor === "pi" ? thread.id : thread.id?.startsWith("lokal-") ? thread.id : thread.temp ? undefined : lokaleId();
    const lokal = motor !== "pi";
    change(key, {messages, busy: true, partial: "", reasoning: "", steps: [], cards: [], error: "", approval: undefined, started, id, lokal, title: thread.id ? thread.title : text.slice(0, 60)});
    let content = "", reasoning = "", cards: any[] = [], steps: Step[] = [], model = thread.model;
    let pending = false, ended = false;
    const paint = () => {
      if (pending) return;
      pending = true;
      setTimeout(() => {pending = false; if (!ended) change(key, {partial: content, reasoning, steps: [...steps], cards: [...cards]});}, 50);
    };
    const handler = (event: any) => {
      if (event.fortschritt) {change(key, {fortschritt: event.fortschritt}); return;}
      if (event.type === "meta") {
        model = event.model || model;
        if (motor === "pi") change(key, {id: thread.temp ? undefined : event.conversation_id || undefined, provider: event.provider || thread.provider, model: event.model || thread.model});
      }
      if (event.type === "content") {content += event.delta || ""; paint();}
      if (event.type === "reasoning") {reasoning += event.delta || ""; paint();}
      if (event.type === "tool") {
        if (event.status === "running") steps.push(event);
        else {
          const index = steps.map(s => s.name).lastIndexOf(event.name);
          if (index >= 0) steps[index] = {...steps[index], ...event, approval_id: undefined, args: steps[index].args};
        }
        if (event.card) cards.push(event.card);
        if (event.approval_id) change(key, {approval: event});
        else if (event.status === "done") change(key, {approval: undefined});
        paint();
      }
      if (event.type === "error") change(key, {error: event.message || "Jon konnte nicht antworten."});
    };
    const verlauf = messages.slice(0, -1).slice(-30).map(m => ({role: m.role, content: m.content}));
    const piStrom = (freigabe: string) => native("stream", {body: {
      messages: messages.slice(-48).map(m => ({role: m.role, content: m.content})),
      conversation_id: thread.id || null, provider: thread.provider && thread.provider !== "handy" ? thread.provider : undefined, model: thread.provider !== "handy" && thread.model ? thread.model : undefined,
      mode: thread.mode === "coding" ? "coding" : "chat", workspace: thread.workspace || null, source: "handy", persist: !thread.temp,
      tool_mode: freigabe, werkzeuge: thread.mode === "coding" ? "alle" : "klein", force_tool: force
    }}, handler, LANG);
    const freigabe = umgebung.current.freigabe || "ask";
    let operation = motor === "pi" ? piStrom(freigabe) : native("ki-stream", {motor, modell: thread.provider === "handy" ? thread.model : "", verlauf, text: message.content, bilder, modus: thread.mode, name: umgebung.current.name}, handler, LANG);
    cancelers.current.set(key, () => {operation.cancel(); if (motor !== "pi") call("ki-stopp").catch(() => {});});
    try {await operation.promise;}
    catch (error) {
      const text = error instanceof Error ? error.message : "";
      if (motor === "pi" && freigabe === "alles" && /422/.test(text) && !content && !steps.length) {
        operation = piStrom("allow");
        try {await operation.promise;}
        catch (zweiter) {change(key, {error: zweiter instanceof Error ? zweiter.message : "Verbindung unterbrochen."});}
      } else change(key, {error: text || "Verbindung unterbrochen."});
    }
    ended = true;
    cancelers.current.delete(key);
    const seconds = Math.max(1, Math.round((Date.now() - started) / 1000));
    const antwort: Message | undefined = content || cards.length ? {id: uid(), role: "assistant", content, reasoning, cards, steps, seconds, model} : undefined;
    const done: Message[] = antwort ? [...messages, antwort] : messages;
    change(key, {busy: false, partial: "", reasoning: "", steps: [], cards: [], approval: undefined, messages: done, fortschritt: ""});
    if (lokal) await lokalSpeichern({...thread, id, title: thread.id ? thread.title : text.slice(0, 60)}, done);
    refresh().catch(() => {});
    return antwort;
  }

  async function approve(approved: boolean) {
    const thread = refs.current[activeRef.current];
    if (!thread.approval) return;
    await api("/api/chat/approve", "POST", {id: thread.approval.approval_id, approved});
    update({approval: undefined});
  }

  async function loeschen(id: string) {
    if (id.startsWith("lokal-")) await call("lokal-chat-loeschen", {chat: id});
    else await api(`/api/conversations/${id}`, "DELETE");
    remove(id);
  }

  function remove(id: string) {
    setThreads(old => {
      const next = {...old};
      for (const [key, thread] of Object.entries(next)) if (thread.id === id && key !== activeRef.current) delete next[key];
      return next;
    });
    setList(old => old.filter(item => item.id !== id));
  }

  useEffect(() => {
    if (current.lokal || current.provider === "handy") return;
    native("context", {conversation_id: current.temp ? "" : current.id || "", provider: current.provider, model: current.model, mode: current.mode, workspace: current.workspace}).promise.catch(() => {});
  }, [current.id, current.key, current.provider, current.model, current.mode, current.workspace, current.temp]);

  useEffect(() => listen("chatChanged", data => {
    refresh().catch(() => {});
    const id = data?.conversation_id;
    if (!id) return;
    const known = Object.values(refs.current).find(t => t.id === id);
    const mine = refs.current[activeRef.current];
    if (known && !known.busy) open(id, mine.key !== known.key).catch(() => {});
    else if (!known && !mine.id && !mine.messages.length) open(id).catch(() => {});
  }), []);

  return {current, list, refresh, open, create, update, send, approve, remove, loeschen, hinzufuegen, stop: () => cancelers.current.get(activeRef.current)?.()};
}

export type Chats = ReturnType<typeof useChats>;
