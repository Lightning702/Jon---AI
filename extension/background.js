import { jonJson, pageContext, settings } from "./jon.js";

const MENU = [
  { id: "jon-erklaeren", title: "Erklären" },
  { id: "jon-zusammenfassen", title: "Zusammenfassen" },
  { id: "jon-uebersetzen", title: "Übersetzen" },
  { id: "jon-recherchieren", title: "Recherchieren" },
  { id: "jon-senden", title: "Zu Jon senden" },
  { id: "jon-projekt", title: "Zu Projekt hinzufügen" },
  { id: "jon-notiz", title: "Als Notiz speichern" },
];

const PROMPTS = {
  "jon-erklaeren": "Erkläre mir das verständlich und knapp.",
  "jon-zusammenfassen": "Fasse das in wenigen Sätzen zusammen.",
  "jon-uebersetzen": "Übersetze das ins Deutsche. Ist es schon Deutsch, übersetze es ins Englische.",
  "jon-recherchieren": "Recherchiere dieses Thema und nenne mir die wichtigsten aktuellen Punkte mit Quellen.",
  "jon-senden": "Schau dir das an und sag mir, was dabei wichtig ist.",
};

function store() {
  return chrome.storage.session ?? chrome.storage.local;
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: "jon-root",
      title: "Mit Jon …",
      contexts: ["selection", "page", "link"],
    });
    for (const entry of MENU) {
      chrome.contextMenus.create({
        id: entry.id,
        parentId: "jon-root",
        title: entry.title,
        contexts: ["selection", "page", "link"],
      });
    }
  });
});

async function openPopup() {
  try {
    if (chrome.action.openPopup) {
      await chrome.action.openPopup();
      return;
    }
  } catch {}
  await chrome.windows.create({
    url: chrome.runtime.getURL("popup.html?task=1"),
    type: "popup",
    width: 420,
    height: 620,
  });
}

async function badge(text, color = "#d4af37") {
  await chrome.action.setBadgeBackgroundColor({ color });
  await chrome.action.setBadgeText({ text });
  setTimeout(() => chrome.action.setBadgeText({ text: "" }), 3200);
}

async function saveToProject(context) {
  const config = await settings();
  const line = [
    context.selection || context.description || context.title,
    context.url,
  ]
    .filter(Boolean)
    .join(" — ");
  if (!config.project) {
    await store().set({
      pending: {
        kind: "projekt",
        context,
        note: line,
        at: Date.now(),
      },
    });
    await openPopup();
    return;
  }
  await jonJson(`/projects/${config.project}/note`, {
    method: "POST",
    body: JSON.stringify({ note: line.slice(0, 400) }),
  });
  await badge("✓");
}

async function saveAsNote(context) {
  const text = [context.selection || context.title, context.url]
    .filter(Boolean)
    .join("\n");
  await jonJson("/notes", {
    method: "POST",
    body: JSON.stringify({ text: text.slice(0, 1000), color: "blau" }),
  });
  await badge("✓");
}

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!tab?.id) return;
  let context = null;
  try {
    context = await pageContext(tab.id, info.menuItemId !== "jon-uebersetzen");
  } catch {
    context = {
      url: info.pageUrl || tab.url || "",
      title: tab.title || "",
      description: "",
      site: "",
      selection: "",
      text: "",
    };
  }
  if (info.selectionText) context.selection = info.selectionText.slice(0, 6000);
  if (info.linkUrl) context.url = info.linkUrl;

  try {
    if (info.menuItemId === "jon-projekt") {
      await saveToProject(context);
      return;
    }
    if (info.menuItemId === "jon-notiz") {
      await saveAsNote(context);
      return;
    }
    const prompt = PROMPTS[info.menuItemId];
    if (!prompt) return;
    await store().set({
      pending: { kind: "frage", prompt, context, at: Date.now() },
    });
    await openPopup();
  } catch (error) {
    await badge("!", "#e05a5a");
    await store().set({
      pending: { kind: "fehler", message: String(error.message || error), at: Date.now() },
    });
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "jon-context" && message.tabId) {
    pageContext(message.tabId, message.withText !== false)
      .then((data) => sendResponse({ ok: true, data }))
      .catch((error) => sendResponse({ ok: false, error: String(error.message || error) }));
    return true;
  }
  return false;
});
