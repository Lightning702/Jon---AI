import { jonHealth, saveSettings, settings } from "./jon.js";

const fields = {
  server: document.getElementById("server"),
  token: document.getElementById("token"),
  provider: document.getElementById("provider"),
  model: document.getElementById("model"),
};
const shareEl = document.getElementById("sharePage");
const statusEl = document.getElementById("status");

function status(text, ok = null) {
  statusEl.textContent = text;
  statusEl.style.color =
    ok === true ? "#6ee7a8" : ok === false ? "#f0a5a5" : "rgba(255,255,255,.55)";
}

async function requestHost(server) {
  try {
    const origin = new URL(server).origin + "/*";
    if (/^https?:\/\/(127\.0\.0\.1|localhost)(:|\/)/.test(server)) return true;
    return await chrome.permissions.request({ origins: [origin] });
  } catch {
    return false;
  }
}

(async () => {
  const config = await settings();
  fields.server.value = config.server;
  fields.token.value = config.token;
  fields.provider.value = config.provider;
  fields.model.value = config.model;
  shareEl.checked = config.sharePage;
})();

document.getElementById("save").addEventListener("click", async () => {
  const server = fields.server.value.trim() || "http://127.0.0.1:8756";
  const granted = await requestHost(server);
  if (!granted) {
    status("Ohne Zugriff auf diese Adresse kann die Erweiterung Jon nicht erreichen.", false);
    return;
  }
  await saveSettings({
    server,
    token: fields.token.value.trim(),
    provider: fields.provider.value.trim(),
    model: fields.model.value.trim(),
    sharePage: shareEl.checked,
  });
  status("Gespeichert.", true);
});

document.getElementById("test").addEventListener("click", async () => {
  status("Teste …");
  const health = await jonHealth();
  if (health.online) {
    status(`Verbunden mit ${health.app ?? "Jon"} ${health.version ?? ""}`.trim(), true);
  } else {
    status("Jon antwortet nicht. Läuft Jon und stimmt die Adresse?", false);
  }
});
