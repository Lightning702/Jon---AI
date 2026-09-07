import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { once } from "node:events";

const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9333;

function arg(name, fallback) {
  const hit = process.argv.find((a) => a.startsWith("--" + name + "="));
  return hit ? hit.slice(name.length + 3) : fallback;
}

const page = arg("page", "film.html");
const breite = Number(arg("breite", 1920));
const hoehe = Number(arg("hoehe", 1080));
const fps = Number(arg("fps", 60));
const dauer = Number(arg("dauer", 90));
const ton = arg("ton", "");
const ziel = resolve(arg("ziel", "jon-demo.mp4"));
const von = Number(arg("von", 0));
const bis = Number(arg("bis", dauer));
const crf = arg("crf", "16");

class CDP {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.warten = new Map();
    this.horcher = new Map();
    ws.addEventListener("message", (e) => {
      const nachricht = JSON.parse(e.data);
      if (nachricht.id !== undefined) {
        const eintrag = this.warten.get(nachricht.id);
        if (!eintrag) return;
        this.warten.delete(nachricht.id);
        if (nachricht.error) eintrag.ab(new Error(JSON.stringify(nachricht.error)));
        else eintrag.auf(nachricht.result);
        return;
      }
      const h = this.horcher.get(nachricht.method);
      if (h) {
        this.horcher.delete(nachricht.method);
        h(nachricht.params);
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
  einmal(method) {
    return new Promise((auf) => this.horcher.set(method, auf));
  }
}

async function hole(url, versuche = 60) {
  for (let i = 0; i < versuche; i++) {
    try {
      const r = await fetch(url);
      if (r.ok) return await r.json();
    } catch {}
    await new Promise((a) => setTimeout(a, 250));
  }
  throw new Error("Chrome antwortet nicht: " + url);
}

const profil = mkdtempSync(join(tmpdir(), "jon-film-"));
const chrome = spawn(CHROME, [
  "--headless=new",
  "--remote-debugging-port=" + PORT,
  "--user-data-dir=" + profil,
  "--no-first-run",
  "--no-default-browser-check",
  "--disable-extensions",
  "--disable-background-timer-throttling",
  "--hide-scrollbars",
  "--force-color-profile=srgb",
  "--force-device-scale-factor=1",
  "--allow-file-access-from-files",
  "--window-size=" + breite + "," + hoehe,
], { stdio: "ignore" });

const version = await hole("http://127.0.0.1:" + PORT + "/json/version");
const ws = new WebSocket(version.webSocketDebuggerUrl);
await once(ws, "open");
const cdp = new CDP(ws);

const seite = resolve(process.cwd(), page);
if (!existsSync(seite)) throw new Error("Seite fehlt: " + seite);
const url = "file:///" + seite.replace(/\\/g, "/") + "?breite=" + breite + "&hoehe=" + hoehe;

const ziel0 = await cdp.send("Target.createTarget", { url: "about:blank" });
const sitzung = (await cdp.send("Target.attachToTarget", { targetId: ziel0.targetId, flatten: true })).sessionId;
await cdp.send("Page.enable", {}, sitzung);
await cdp.send("Runtime.enable", {}, sitzung);
await cdp.send("Emulation.setDeviceMetricsOverride", {
  width: breite, height: hoehe, deviceScaleFactor: 1, mobile: false, screenWidth: breite, screenHeight: hoehe,
}, sitzung);
const geladen = cdp.einmal("Page.loadEventFired");
await cdp.send("Page.navigate", { url }, sitzung);
await geladen;
await cdp.send("Runtime.evaluate", { expression: "document.fonts.ready", awaitPromise: true }, sitzung);
await new Promise((a) => setTimeout(a, 400));

const args = [
  "-y", "-f", "image2pipe", "-framerate", String(fps), "-c:v", "png", "-i", "-",
];
if (ton) args.push("-i", resolve(ton));
args.push(
  "-map", "0:v",
  ...(ton ? ["-map", "1:a", "-c:a", "aac", "-b:a", "224k", "-ar", "48000"] : []),
  "-c:v", "libx264", "-preset", "slow", "-crf", crf,
  "-pix_fmt", "yuv420p", "-r", String(fps),
  "-movflags", "+faststart",
  "-shortest",
  ziel,
);
const ff = spawn("ffmpeg", args, { stdio: ["pipe", "ignore", "pipe"] });
let ffFehler = "";
ff.stderr.on("data", (d) => { ffFehler += d.toString(); if (ffFehler.length > 8000) ffFehler = ffFehler.slice(-4000); });

const gesamt = Math.round((bis - von) * fps);
const start = Date.now();
for (let i = 0; i < gesamt; i++) {
  const t = von + i / fps;
  await cdp.send("Runtime.evaluate", {
    expression: "window.__seek(" + t.toFixed(5) + ")",
    awaitPromise: true,
  }, sitzung);
  const schuss = await cdp.send("Page.captureScreenshot", {
    format: "png", optimizeForSpeed: true, captureBeyondViewport: false,
  }, sitzung);
  const puffer = Buffer.from(schuss.data, "base64");
  if (!ff.stdin.write(puffer)) await once(ff.stdin, "drain");
  if (i % 120 === 0 || i === gesamt - 1) {
    const v = (Date.now() - start) / 1000;
    const rest = v / Math.max(1, i + 1) * (gesamt - i - 1);
    process.stdout.write(
      "\r" + (i + 1) + "/" + gesamt + "  " + ((i + 1) / Math.max(0.001, v)).toFixed(1) +
      " B/s  noch " + Math.round(rest) + "s      ",
    );
  }
}
ff.stdin.end();
const [code] = await once(ff, "close");
process.stdout.write("\n");
if (code !== 0) {
  console.error(ffFehler);
  throw new Error("ffmpeg brach ab: " + code);
}
await cdp.send("Browser.close").catch(() => {});
ws.close();
chrome.kill();
try { rmSync(profil, { recursive: true, force: true }); } catch {}
console.log("fertig: " + ziel);
