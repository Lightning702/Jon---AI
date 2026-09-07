import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { once } from "node:events";

const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9334;

function arg(name, fallback) {
  const hit = process.argv.find((a) => a.startsWith("--" + name + "="));
  return hit ? hit.slice(name.length + 3) : fallback;
}
const page = arg("page", "film.html");
const breite = Number(arg("breite", 1920));
const hoehe = Number(arg("hoehe", 1080));
const zeiten = arg("t", "3").split(",").map(Number);
const ordner = resolve(arg("ordner", "."));
const marke = arg("marke", "bild");

class CDP {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.warten = new Map();
    this.horcher = new Map();
    ws.addEventListener("message", (e) => {
      const n = JSON.parse(e.data);
      if (n.id !== undefined) {
        const w = this.warten.get(n.id);
        if (!w) return;
        this.warten.delete(n.id);
        n.error ? w.ab(new Error(JSON.stringify(n.error))) : w.auf(n.result);
        return;
      }
      const h = this.horcher.get(n.method);
      if (h) {
        this.horcher.delete(n.method);
        h(n.params);
      }
    });
  }
  send(method, params = {}, sessionId) {
    const id = ++this.id;
    const paket = { id, method, params };
    if (sessionId) paket.sessionId = sessionId;
    this.ws.send(JSON.stringify(paket));
    return new Promise((auf, ab) => this.warten.set(id, { auf, ab }));
  }
  einmal(m) {
    return new Promise((auf) => this.horcher.set(m, auf));
  }
}

async function hole(url) {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(url);
      if (r.ok) return await r.json();
    } catch {}
    await new Promise((a) => setTimeout(a, 250));
  }
  throw new Error("Chrome antwortet nicht");
}

const profil = mkdtempSync(join(tmpdir(), "jon-schuss-"));
const chrome = spawn(CHROME, [
  "--headless=new", "--remote-debugging-port=" + PORT, "--user-data-dir=" + profil,
  "--no-first-run", "--no-default-browser-check", "--disable-extensions",
  "--hide-scrollbars", "--force-color-profile=srgb", "--force-device-scale-factor=1",
  "--allow-file-access-from-files", "--window-size=" + breite + "," + hoehe,
], { stdio: "ignore" });

const version = await hole("http://127.0.0.1:" + PORT + "/json/version");
const ws = new WebSocket(version.webSocketDebuggerUrl);
await once(ws, "open");
const cdp = new CDP(ws);
const seite = resolve(process.cwd(), page);
if (!existsSync(seite)) throw new Error("Seite fehlt: " + seite);
const url = "file:///" + seite.replace(/\\/g, "/") + "?breite=" + breite + "&hoehe=" + hoehe;
const ziel = await cdp.send("Target.createTarget", { url: "about:blank" });
const s = (await cdp.send("Target.attachToTarget", { targetId: ziel.targetId, flatten: true })).sessionId;
await cdp.send("Page.enable", {}, s);
await cdp.send("Runtime.enable", {}, s);
await cdp.send("Log.enable", {}, s).catch(() => {});
const fehler = [];
ws.addEventListener("message", (e) => {
  const n = JSON.parse(e.data);
  if (n.method === "Runtime.exceptionThrown")
    fehler.push(n.params.exceptionDetails.exception?.description || n.params.exceptionDetails.text);
  if (n.method === "Log.entryAdded" && n.params.entry.level === "error") fehler.push(n.params.entry.text);
});
await cdp.send("Emulation.setDeviceMetricsOverride", {
  width: breite, height: hoehe, deviceScaleFactor: 1, mobile: false,
}, s);
const geladen = cdp.einmal("Page.loadEventFired");
await cdp.send("Page.navigate", { url }, s);
await geladen;
await cdp.send("Runtime.evaluate", { expression: "document.fonts.ready", awaitPromise: true }, s);
await new Promise((a) => setTimeout(a, 350));

for (const t of zeiten) {
  const r = await cdp.send("Runtime.evaluate", {
    expression: "window.__seek(" + t + ").then(()=>'ok').catch(e=>'FEHLER '+e.message)",
    awaitPromise: true,
  }, s);
  if (r.result && String(r.result.value).startsWith("FEHLER")) fehler.push(t + ": " + r.result.value);
  const bild = await cdp.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false }, s);
  const datei = join(ordner, marke + "-" + String(t).replace(".", "_") + ".png");
  writeFileSync(datei, Buffer.from(bild.data, "base64"));
  console.log(datei);
}
if (fehler.length) console.log("FEHLER:\n" + [...new Set(fehler)].join("\n"));
await cdp.send("Browser.close").catch(() => {});
ws.close();
chrome.kill();
try { rmSync(profil, { recursive: true, force: true }); } catch {}
