const BASE = "http://127.0.0.1:8756/api";
export async function transcribeAudio(wav) {
    const res = await fetch(`${BASE}/system/transcribe`, {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: wav,
    });
    if (!res.ok)
        return "";
    const data = await res.json();
    return typeof data.text === "string" ? data.text : "";
}
export async function getHealth() {
    const res = await fetch(`${BASE}/health`);
    if (!res.ok)
        throw new Error("health failed");
    return res.json();
}
export async function getProviders() {
    const res = await fetch(`${BASE}/providers`);
    if (!res.ok)
        throw new Error("providers failed");
    return res.json();
}
export async function getConversations() {
    const res = await fetch(`${BASE}/conversations`);
    if (!res.ok)
        return [];
    return res.json();
}
export async function getConversation(id) {
    const res = await fetch(`${BASE}/conversations/${id}`);
    if (!res.ok)
        throw new Error("conversation failed");
    return res.json();
}
export async function deleteConversation(id) {
    await fetch(`${BASE}/conversations/${id}`, { method: "DELETE" });
}
export async function streamChat(body, handlers, signal) {
    const res = await fetch(`${BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal,
    });
    if (!res.ok || !res.body) {
        handlers.onError?.(`HTTP ${res.status}`);
        return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
        const { done, value } = await reader.read();
        if (done)
            break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";
        for (const part of parts) {
            const line = part.trim();
            if (!line.startsWith("data:"))
                continue;
            const json = line.slice(5).trim();
            if (!json)
                continue;
            let evt;
            try {
                evt = JSON.parse(json);
            }
            catch {
                continue;
            }
            if (evt.type === "meta")
                handlers.onMeta?.(evt);
            else if (evt.type === "content")
                handlers.onContent?.(evt.delta ?? "");
            else if (evt.type === "reasoning")
                handlers.onReasoning?.(evt.delta ?? "");
            else if (evt.type === "tool")
                handlers.onTool?.(evt);
            else if (evt.type === "error")
                handlers.onError?.(evt.message ?? "error");
            else if (evt.type === "done")
                handlers.onDone?.(evt.conversation_id);
        }
    }
}
