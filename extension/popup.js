import {
  askJon,
  jonJson,
  jonHealth,
  pageContext,
  saveSettings,
  settings,
} from "./jon.js";

const stateEl = document.getElementById("state");
const titleEl = document.getElementById("pageTitle");
const urlEl = document.getElementById("pageUrl");
const answerEl = document.getElementById("answer");
const inputEl = document.getElementById("input");
const sendEl = document.getElementById("send");
const actionsEl = document.getElementById("actions");
const projectRow = document.getElementById("projectRow");
const projectEl = document.getElementById("project");

const PROMPTS = {
  zusammenfassen: "Fasse diese Seite in 4-6 Sätzen zusammen.",
  erklaeren: "Erkläre mir diese Seite so, dass ich sie ohne Vorwissen verstehe.",
  recherchieren:
    "Recherchiere das Thema dieser Seite und nenne mir die wichtigsten aktuellen Punkte mit Quellen.",
  verbessern:
    "Verbessere den markierten Text sprachlich, ohne den Inhalt zu verändern. Gib nur den überarbeiteten Text zurück.",
};

let context = null;
let tabId = null;
let busy = false;

function show(text, tone = "") {
  answerEl.hidden = false;
  answerEl.textContent = text;
  if (tone) answerEl.dataset.tone = tone;
  else delete answerEl.dataset.tone;
  answerEl.scrollTop = answerEl.scrollHeight;
}

function setBusy(value) {
  busy = value;
  sendEl.disabled = value;
  for (const button of actionsEl.querySelectorAll("button")) {
    button.disabled = value;
  }
}

async function loadContext() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;
  tabId = tab.id;
  titleEl.textContent = tab.title || "—";
  urlEl.textContent = tab.url || "";
  const config = await settings();
  if (!config.sharePage) return;
  try {
    context = await pageContext(tab.id, true);
    if (context) {
      titleEl.textContent = context.title || tab.title || "—";
      urlEl.textContent = context.url || tab.url || "";
    }
  } catch {
    context = null;
  }
}

async function loadProjects() {
  try {
    const projects = await jonJson("/projects");
    const config = await settings();
    projectEl.innerHTML = "";
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = projects.length ? "— kein Projekt —" : "keine Projekte";
    projectEl.appendChild(empty);
    for (const project of projects) {
      const option = document.createElement("option");
      option.value = project.id;
      option.textContent = project.name;
      if (project.id === config.project) option.selected = true;
      projectEl.appendChild(option);
    }
    projectRow.hidden = projects.length === 0;
  } catch {
    projectRow.hidden = true;
  }
}

async function connect() {
  const health = await jonHealth();
  stateEl.textContent = health.online
    ? `verbunden · ${health.app ?? "Jon"} ${health.version ?? ""}`.trim()
    : "Jon ist offline";
  stateEl.dataset.on = String(health.online);
  if (health.online) await loadProjects();
  return health.online;
}

async function ask(prompt, withContext = true) {
  if (busy) return;
  setBusy(true);
  show("Jon denkt nach …");
  try {
    const answer = await askJon(
      prompt,
      withContext ? context : null,
      (_delta, full) => show(full)
    );
    show(answer || "Jon hat nichts zurückgegeben.");
  } catch (error) {
    show(String(error.message || error), "fehler");
  } finally {
    setBusy(false);
  }
}

async function addToKnowledge() {
  if (!context) {
    show("Für diese Seite liegt kein Inhalt vor.", "fehler");
    return;
  }
  setBusy(true);
  try {
    await jonJson("/knowledge/learn", {
      method: "POST",
      body: JSON.stringify({
        text: `${context.title}\n${context.url}\n\n${context.selection || context.text}`,
        title: context.title || context.url,
      }),
    });
    show("Zu Jons Wissen hinzugefügt.", "ok");
  } catch (error) {
    show(String(error.message || error), "fehler");
  } finally {
    setBusy(false);
  }
}

async function addToProject() {
  const id = projectEl.value;
  if (!id) {
    show("Wähle unten zuerst ein Projekt aus.", "fehler");
    projectRow.hidden = false;
    return;
  }
  setBusy(true);
  try {
    const note = [
      context?.selection || context?.description || context?.title,
      context?.url,
    ]
      .filter(Boolean)
      .join(" — ")
      .slice(0, 400);
    await jonJson(`/projects/${id}/note`, {
      method: "POST",
      body: JSON.stringify({ note }),
    });
    await saveSettings({ project: id });
    show("Im Projekt gespeichert.", "ok");
  } catch (error) {
    show(String(error.message || error), "fehler");
  } finally {
    setBusy(false);
  }
}

async function openInJon() {
  const config = await settings();
  const server = String(config.server).replace(/\/+$/, "");
  const url = `${server}/app/?token=${encodeURIComponent(config.token)}`;
  await chrome.tabs.create({ url });
}

actionsEl.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  const act = button.dataset.act;
  if (act === "wissen") return void addToKnowledge();
  if (act === "projekt") return void addToProject();
  if (act === "oeffnen") return void openInJon();
  if (act === "verbessern" && !context?.selection) {
    show("Markiere zuerst den Text, den Jon verbessern soll.", "fehler");
    return;
  }
  const prompt = PROMPTS[act];
  if (prompt) void ask(prompt);
});

projectEl.addEventListener("change", () => {
  void saveSettings({ project: projectEl.value });
});

sendEl.addEventListener("click", () => {
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = "";
  void ask(text);
});

inputEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendEl.click();
  }
});

document.getElementById("options").addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});

async function runPending() {
  const store = chrome.storage.session ?? chrome.storage.local;
  const { pending } = await store.get("pending");
  if (!pending) return false;
  await store.remove("pending");
  if (Date.now() - (pending.at || 0) > 120000) return false;
  if (pending.kind === "fehler") {
    show(pending.message, "fehler");
    return true;
  }
  if (pending.kind === "projekt") {
    context = pending.context;
    projectRow.hidden = false;
    show("Wähle ein Projekt aus und klick auf „In Projekt speichern“.");
    return true;
  }
  if (pending.kind === "frage") {
    context = pending.context;
    titleEl.textContent = context.title || titleEl.textContent;
    urlEl.textContent = context.url || urlEl.textContent;
    await ask(pending.prompt);
    return true;
  }
  return false;
}

(async () => {
  const online = await connect();
  const handled = await runPending();
  if (!handled) await loadContext();
  if (!online) {
    show(
      "Jon antwortet nicht. Starte Jon auf deinem Rechner und prüfe unter ⚙ die Adresse und den Geräte-Schlüssel.",
      "fehler"
    );
  }
  if (tabId === null && !handled) await loadContext();
})();
