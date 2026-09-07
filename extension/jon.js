export const DEFAULTS = {
  server: "http://127.0.0.1:8756",
  token: "",
  provider: "",
  model: "",
  project: "",
  sharePage: true,
};

export async function settings() {
  const stored = await chrome.storage.local.get(DEFAULTS);
  return { ...DEFAULTS, ...stored };
}

export async function saveSettings(patch) {
  await chrome.storage.local.set(patch);
}

function base(server) {
  return String(server || DEFAULTS.server).replace(/\/+$/, "") + "/api";
}

export class JonOffline extends Error {}

export async function jonFetch(path, options = {}) {
  const config = await settings();
  if (!config.token) {
    throw new JonOffline(
      "Kein Geraete-Schluessel hinterlegt. Oeffne die Einstellungen der Erweiterung."
    );
  }
  const headers = {
    "X-Jon-Token": config.token,
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(options.headers || {}),
  };
  let response;
  try {
    response = await fetch(base(config.server) + path, { ...options, headers });
  } catch {
    throw new JonOffline(
      "Jon ist nicht erreichbar. Laeuft Jon auf diesem Rechner?"
    );
  }
  if (response.status === 401) {
    throw new JonOffline(
      "Der Geraete-Schluessel stimmt nicht. Hol dir einen neuen unter Einstellungen -> Diagnose."
    );
  }
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(detail.slice(0, 300) || `Fehler ${response.status}`);
  }
  return response;
}

export async function jonJson(path, options) {
  const response = await jonFetch(path, options);
  return response.json();
}

export async function jonHealth() {
  const config = await settings();
  try {
    const response = await fetch(base(config.server) + "/health", {
      headers: config.token ? { "X-Jon-Token": config.token } : {},
    });
    if (!response.ok) return { online: false };
    const data = await response.json();
    return { online: true, version: data.version, app: data.app };
  } catch {
    return { online: false };
  }
}

export async function askJon(text, context, onDelta, signal) {
  const config = await settings();
  const messages = [];
  if (context && context.url) {
    messages.push({
      role: "user",
      content:
        `Kontext der Seite, die ich gerade offen habe:\n` +
        `Titel: ${context.title || ""}\n` +
        `URL: ${context.url}\n` +
        (context.description ? `Beschreibung: ${context.description}\n` : "") +
        (context.selection ? `Markierter Text:\n${context.selection}\n` : "") +
        (context.text ? `Seiteninhalt (gekuerzt):\n${context.text}\n` : ""),
    });
  }
  messages.push({ role: "user", content: text });
  const response = await jonFetch("/chat", {
    method: "POST",
    signal,
    body: JSON.stringify({
      messages,
      provider: config.provider || undefined,
      model: config.model || undefined,
      persist: false,
      tool_mode: "allow",
      tool_scope: "gast",
      mode: "chat",
      source: "extension",
    }),
  });
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let answer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || "";
    for (const block of blocks) {
      for (const line of block.split("\n")) {
        if (!line.startsWith("data:")) continue;
        const raw = line.slice(5).trim();
        if (!raw) continue;
        let event;
        try {
          event = JSON.parse(raw);
        } catch {
          continue;
        }
        if (event.type === "content" && event.delta) {
          answer += event.delta;
          onDelta?.(event.delta, answer);
        } else if (event.type === "error") {
          throw new Error(event.message || "Jon meldet einen Fehler.");
        }
      }
    }
  }
  return answer.trim();
}

export async function pageContext(tabId, wantText = true) {
  const [result] = await chrome.scripting.executeScript({
    target: { tabId },
    func: (withText) => {
      const meta = (name) =>
        document.querySelector(`meta[name="${name}"], meta[property="${name}"]`)
          ?.content || "";
      const selection = String(window.getSelection?.() || "").trim();
      let text = "";
      if (withText) {
        const main =
          document.querySelector("article") ||
          document.querySelector("main") ||
          document.body;
        text = (main?.innerText || "").replace(/\s+\n/g, "\n").trim().slice(0, 12000);
      }
      return {
        url: location.href,
        title: document.title,
        description: meta("description") || meta("og:description"),
        site: meta("og:site_name") || location.hostname,
        selection: selection.slice(0, 6000),
        text,
      };
    },
    args: [wantText],
  });
  return result?.result ?? null;
}
