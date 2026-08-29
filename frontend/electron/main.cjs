const {
  app,
  BrowserWindow,
  ipcMain,
  shell,
  dialog,
  globalShortcut,
  Tray,
  Menu,
  screen,
  session,
} = require("electron");
const path = require("node:path");
const fs = require("node:fs");
const { spawn, spawnSync } = require("node:child_process");
const crypto = require("node:crypto");

const isDev = !app.isPackaged;
const BACKEND_PORTS = [8756, 8758, 8759, 8760];
let mainWindow = null;
let petWindow = null;
let quickWindow = null;
let quickWriteWindow = null;
let privateWindow = null;
const PRIVATE_PARTITION = "jon-privat";
const API_BASE = "http://127.0.0.1:8756/api";
let backendProcess = null;
let tray = null;
let quitting = false;

let jonToken = "";
let backendErreichbar = false;

function tokenCandidates() {
  const list = [];
  if (process.resourcesPath) {
    list.push(
      path.join(process.resourcesPath, "jon-backend", "data", "access.token")
    );
    list.push(path.join(process.resourcesPath, "backend", "data", "access.token"));
  }
  const local = process.env.LOCALAPPDATA;
  if (local) list.push(path.join(local, "Jon", "data", "access.token"));
  list.push(path.join(app.getPath("home"), ".jon", "data", "access.token"));
  return list;
}

function readTokenFile(file) {
  try {
    const value = fs.readFileSync(file, "utf-8").trim();
    return value || "";
  } catch (e) {
    return "";
  }
}

function ensureToken() {
  if (jonToken) return jonToken;
  if (process.env.JON_TOKEN && process.env.JON_TOKEN.trim()) {
    jonToken = process.env.JON_TOKEN.trim();
    return jonToken;
  }
  for (const file of tokenCandidates()) {
    const value = readTokenFile(file);
    if (value) {
      jonToken = value;
      return jonToken;
    }
  }
  jonToken = crypto.randomBytes(32).toString("base64url");
  const target = tokenCandidates().find((file) =>
    file.includes(path.join("Jon", "data"))
  );
  if (target) {
    try {
      fs.mkdirSync(path.dirname(target), { recursive: true });
      fs.writeFileSync(target, jonToken + String.fromCharCode(10), "utf-8");
    } catch (e) {}
  }
  process.env.JON_TOKEN = jonToken;
  return jonToken;
}

function verteileToken(value) {
  for (const win of BrowserWindow.getAllWindows()) {
    if (!win.isDestroyed() && win.webContents) {
      win.webContents.send("jon:token", value);
    }
  }
}

async function refreshToken() {
  const vorher = ensureToken();
  let antwort = null;
  try {
    antwort = await fetch(`${API_BASE}/health`, {
      signal: AbortSignal.timeout(4000),
    });
  } catch (e) {
    return vorher;
  }
  if (!antwort || !antwort.ok) return vorher;
  backendErreichbar = true;
  let info = null;
  try {
    info = await antwort.json();
  } catch (e) {
    return vorher;
  }
  const datei = info && typeof info.token_file === "string" ? info.token_file : "";
  if (!datei) return vorher;
  const value = readTokenFile(datei);
  if (!value || value === vorher) return vorher;
  jonToken = value;
  process.env.JON_TOKEN = value;
  verteileToken(value);
  return value;
}

async function tokenAbgleich() {
  for (let versuch = 0; versuch < 30; versuch += 1) {
    const vorher = jonToken;
    const jetzt = await refreshToken();
    if (jetzt && jetzt !== vorher) return;
    if (backendErreichbar) return;
    await new Promise((r) => setTimeout(r, 1000));
  }
}

async function apiFetch(pfad, init) {
  const ziel = `${API_BASE}${pfad}`;
  const bauen = (wert) => {
    const headers = Object.assign({}, (init && init.headers) || {});
    if (wert) headers["X-Jon-Token"] = wert;
    return Object.assign({}, init, { headers });
  };
  const antwort = await fetch(ziel, bauen(ensureToken()));
  if (antwort.status !== 401) return antwort;
  const frisch = await refreshToken();
  if (!frisch) return antwort;
  return fetch(ziel, bauen(frisch));
}

function tokenArgs() {
  return ["--jon-token=" + ensureToken()];
}

function createQuickAsk() {
  const area = screen.getPrimaryDisplay().workArea;
  const w = 680;
  const h = 520;
  quickWindow = new BrowserWindow({
    width: w,
    height: h,
    x: area.x + Math.round((area.width - w) / 2),
    y: area.y + 120,
    frame: false,
    transparent: true,
    resizable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    hasShadow: false,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "quickaskPreload.cjs"),
      additionalArguments: tokenArgs(),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  quickWindow.setAlwaysOnTop(true, "screen-saver");
  quickWindow.setVisibleOnAllWorkspaces(true);
  quickWindow.loadFile(path.join(__dirname, "quickask.html"));
  quickWindow.on("blur", () => {
    if (quickWindow && quickWindow.isVisible()) quickWindow.hide();
  });
  quickWindow.on("closed", () => {
    quickWindow = null;
  });
}

function createQuickWrite() {
  quickWriteWindow = new BrowserWindow({
    width: 300,
    height: 260,
    frame: false,
    transparent: true,
    resizable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    focusable: false,
    hasShadow: false,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "quickwritePreload.cjs"),
      additionalArguments: tokenArgs(),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  quickWriteWindow.setAlwaysOnTop(true, "screen-saver");
  quickWriteWindow.setVisibleOnAllWorkspaces(true);
  quickWriteWindow.loadFile(path.join(__dirname, "quickwrite.html"));
  quickWriteWindow.on("closed", () => {
    quickWriteWindow = null;
  });
}

async function openQuickWrite() {
  if (!quickWriteWindow) createQuickWrite();
  const point = screen.getCursorScreenPoint();
  const display = screen.getDisplayNearestPoint(point);
  const x = Math.min(point.x + 8, display.workArea.x + display.workArea.width - 300);
  const y = Math.min(point.y + 8, display.workArea.y + display.workArea.height - 260);
  quickWriteWindow.setPosition(Math.round(x), Math.round(y));
  quickWriteWindow.showInactive();
  let data = { error: "Kein Text markiert." };
  try {
    const res = await apiFetch("/quickwrite/grab");
    data = await res.json();
    if (!res.ok) data = { error: data.detail || "Kein Text markiert." };
  } catch (e) {
    data = { error: "Backend nicht erreichbar." };
  }
  if (quickWriteWindow) quickWriteWindow.webContents.send("quickwrite:data", data);
}

async function readAloudSelection() {
  let text = "";
  try {
    const res = await apiFetch("/quickwrite/grab");
    const data = await res.json();
    if (res.ok && data.text) text = String(data.text).trim();
  } catch (e) {}
  if (!text) return;
  if (!petWindow) createPet();
  else petWindow.show();
  if (petWindow) petWindow.webContents.send("pet:read", text.slice(0, 4000));
}

ipcMain.handle("quickwrite:apply", async (_e, mode) => {
  let result = { ok: false, error: "Fehlgeschlagen." };
  try {
    const res = await apiFetch("/quickwrite/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    });
    const data = await res.json();
    result = res.ok ? { ok: true } : { ok: false, error: data.detail || "Fehlgeschlagen." };
  } catch (e) {
    result = { ok: false, error: "Backend nicht erreichbar." };
  }
  if (quickWriteWindow) quickWriteWindow.webContents.send("quickwrite:result", result);
  return result;
});

ipcMain.handle("quickwrite:hide", () => quickWriteWindow && quickWriteWindow.hide());

function toggleQuickAsk() {
  if (!quickWindow) createQuickAsk();
  if (quickWindow.isVisible()) {
    quickWindow.hide();
    return;
  }
  quickWindow.show();
  quickWindow.focus();
  quickWindow.webContents.send("quickask:focus");
}

function createPet() {
  if (petWindow) {
    petWindow.show();
    return;
  }
  const area = screen.getPrimaryDisplay().workAreaSize;
  const w = 320;
  const h = 360;
  petWindow = new BrowserWindow({
    width: w,
    height: h,
    x: area.width - w - 24,
    y: area.height - h - 12,
    frame: false,
    transparent: true,
    resizable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    hasShadow: false,
    focusable: true,
    webPreferences: {
      preload: path.join(__dirname, "petPreload.cjs"),
      additionalArguments: tokenArgs(),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  petWindow.setAlwaysOnTop(true, "screen-saver");
  petWindow.setVisibleOnAllWorkspaces(true);
  petWindow.setIgnoreMouseEvents(true, { forward: true });
  petWindow.loadFile(path.join(__dirname, "pet.html"));
  petWindow.on("closed", () => {
    petWindow = null;
  });
  startPetRoam();
}

let roamOn = false;
let roamAsleep = false;
let roamTarget = null;
let roamStarted = false;
async function refreshRoamState() {
  try {
    const s = await (await apiFetch("/settings")).json();
    roamOn = s.pet_roam === true;
  } catch (e) {
    roamOn = false;
  }
  try {
    const idle = Number((await (await apiFetch("/system/idle")).json()).seconds || 0);
    roamAsleep = idle > 300;
  } catch (e) {
    roamAsleep = false;
  }
}
function startPetRoam() {
  if (roamStarted) return;
  roamStarted = true;
  refreshRoamState();
  setInterval(refreshRoamState, 4000);
  setInterval(() => {
    if (!petWindow || !petWindow.isVisible() || !roamOn || roamAsleep) return;
    const area = screen.getPrimaryDisplay().workAreaSize;
    const b = petWindow.getBounds();
    const y = area.height - b.height - 12;
    if (roamTarget === null || Math.abs(b.x - roamTarget) < 6) {
      roamTarget = Math.round(Math.random() * (area.width - b.width - 40)) + 20;
    }
    const nx = b.x + Math.sign(roamTarget - b.x) * Math.min(3, Math.abs(roamTarget - b.x));
    petWindow.setBounds({ x: Math.round(nx), y, width: b.width, height: b.height });
  }, 45);
}

function togglePet() {
  if (petWindow && petWindow.isVisible()) petWindow.hide();
  else createPet();
}

async function quitJon() {
  if (quitting) return;
  quitting = true;
  for (const win of BrowserWindow.getAllWindows()) {
    if (!win.isDestroyed() && win.webContents) {
      win.webContents.send("jon:quitting");
    }
  }
  await askBackendToStop();
  stopBackend();
  for (const win of BrowserWindow.getAllWindows()) {
    if (!win.isDestroyed()) win.destroy();
  }
  if (tray && !tray.isDestroyed()) {
    tray.destroy();
    tray = null;
  }
  app.quit();
}

function hideWindow() {
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.hide();
}

function toggleWindow() {
  if (!mainWindow) return;
  if (mainWindow.isVisible() && !mainWindow.isMinimized() && mainWindow.isFocused()) {
    mainWindow.hide();
    return;
  }
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
}

function resolvePython() {
  if (process.env.JON_PYTHON) return process.env.JON_PYTHON.trim().split(/\s+/);
  const candidates =
    process.platform === "win32"
      ? [["py", "-3"], ["python"], ["python3"]]
      : [["python3"], ["python"]];
  for (const parts of candidates) {
    try {
      const probe = spawnSync(parts[0], [...parts.slice(1), "-c", "import sys"], {
        stdio: "ignore",
        windowsHide: true,
      });
      if (probe.status === 0) return parts;
    } catch (e) {}
  }
  return process.platform === "win32" ? ["python"] : ["python3"];
}

function runProcess(cmd, args, opts) {
  return new Promise((resolve) => {
    let child;
    try {
      child = spawn(cmd, args, opts);
    } catch (e) {
      resolve(1);
      return;
    }
    child.on("error", () => resolve(1));
    child.on("close", (code) => resolve(code == null ? 1 : code));
  });
}

async function startBackend() {
  if (!app.isPackaged) return;
  const logDir = app.getPath("userData");
  let out = "ignore";
  try {
    fs.mkdirSync(logDir, { recursive: true });
    out = fs.openSync(path.join(logDir, "backend.log"), "a");
  } catch (e) {}

  const bundledExe = path.join(
    process.resourcesPath,
    "jon-backend",
    "jon-backend.exe"
  );
  if (fs.existsSync(bundledExe)) {
    backendProcess = spawn(bundledExe, [], {
      cwd: path.dirname(bundledExe),
      env: {
        ...process.env,
        JON_PARENT_PID: String(process.pid),
        JON_TOKEN: ensureToken(),
      },
      stdio: ["ignore", out, out],
      windowsHide: true,
    });
    backendProcess.on("error", () => {});
    backendProcess.on("exit", () => {
      backendProcess = null;
    });
    return;
  }

  const backendDir = path.join(process.resourcesPath, "backend");
  if (!fs.existsSync(backendDir)) return;
  const py = resolvePython();
  const cmd = py[0];
  const pre = py.slice(1);
  const env = {
    ...process.env,
    JON_PARENT_PID: String(process.pid),
    JON_TOKEN: ensureToken(),
  };
  delete env.ELECTRON_RUN_AS_NODE;
  delete env.NODE_OPTIONS;
  const depCheck =
    "import fastapi,uvicorn,sqlalchemy,openai,anthropic,httpx,pydantic_settings,speech_recognition,pyautogui,pygetwindow,pyperclip,pypdf,cv2,edge_tts,cryptography,paho.mqtt.client";
  const ok = await runProcess(cmd, [...pre, "-c", depCheck], {
    cwd: backendDir,
    env,
    stdio: "ignore",
    windowsHide: true,
  });
  if (ok !== 0) {
    const req = path.join(backendDir, "requirements.txt");
    await runProcess(
      cmd,
      [...pre, "-m", "pip", "install", "--user", "--disable-pip-version-check", "-r", req],
      { cwd: backendDir, env, stdio: ["ignore", out, out], windowsHide: true }
    );
  }
  backendProcess = spawn(cmd, [...pre, "-m", "app.main"], {
    cwd: backendDir,
    env,
    stdio: ["ignore", out, out],
    windowsHide: true,
  });
  backendProcess.on("error", () => {});
  backendProcess.on("exit", () => {
    backendProcess = null;
  });
}

function clearPrivateData() {
  try {
    const ses = session.fromPartition(PRIVATE_PARTITION);
    void ses.clearStorageData();
    void ses.clearCache();
    void ses.clearAuthCache();
    void ses.clearHostResolverCache();
    void ses.clearCodeCaches({});
  } catch {}
}

function openPrivateInApp() {
  if (!mainWindow) createWindow();
  if (!mainWindow) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
  const send = () => mainWindow.webContents.send("jon:open-private");
  if (mainWindow.webContents.isLoading()) {
    mainWindow.webContents.once("did-finish-load", send);
  } else {
    send();
  }
}

function openPrivateBrowser() {
  if (privateWindow) {
    if (privateWindow.isMinimized()) privateWindow.restore();
    privateWindow.show();
    privateWindow.focus();
    return;
  }
  const ses = session.fromPartition(PRIVATE_PARTITION);
  ses.setPermissionRequestHandler((_wc, _permission, cb) => cb(false));
  privateWindow = new BrowserWindow({
    width: 1200,
    height: 820,
    minWidth: 720,
    minHeight: 480,
    backgroundColor: "#0a0a0e",
    frame: false,
    icon: path.join(__dirname, "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "privatePreload.cjs"),
      additionalArguments: tokenArgs(),
      contextIsolation: true,
      nodeIntegration: false,
      webviewTag: true,
    },
  });
  privateWindow.loadFile(path.join(__dirname, "private-browser.html"));
  privateWindow.on("closed", () => {
    privateWindow = null;
    clearPrivateData();
  });
}

app.on("web-contents-created", (_event, contents) => {
  if (contents.getType() !== "webview") return;
  contents.setWindowOpenHandler(({ url }) => {
    const host = contents.hostWebContents;
    if (
      host &&
      privateWindow &&
      !privateWindow.isDestroyed() &&
      host.id === privateWindow.webContents.id &&
      /^https?:/i.test(url)
    ) {
      host.send("private:open-tab", url);
    }
    return { action: "deny" };
  });
  contents.on("will-navigate", (event, url) => {
    if (!/^(https?|about):/i.test(url)) event.preventDefault();
  });
});

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 840,
    minWidth: 960,
    minHeight: 640,
    backgroundColor: "#050506",
    show: false,
    frame: false,
    titleBarStyle: "hidden",
    icon: path.join(__dirname, "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      additionalArguments: tokenArgs(),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.once("ready-to-show", () => mainWindow.show());

  mainWindow.on("close", (event) => {
    if (quitting) return;
    event.preventDefault();
    void quitJon();
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.webContents.on("render-process-gone", () => {
    if (quitting || !mainWindow || mainWindow.isDestroyed()) return;
    mainWindow.reload();
  });

  if (isDev) {
    const devUrl = "http://127.0.0.1:5173";
    let versuche = 0;
    mainWindow.webContents.on("did-fail-load", (_event, _code, _desc, url) => {
      if (quitting || !mainWindow || mainWindow.isDestroyed()) return;
      if (url && !url.startsWith(devUrl)) return;
      versuche += 1;
      if (versuche === 5) mainWindow.show();
      if (versuche > 40) return;
      setTimeout(() => {
        if (!quitting && mainWindow && !mainWindow.isDestroyed()) {
          void mainWindow.loadURL(devUrl);
        }
      }, 700);
    });
    void mainWindow.loadURL(devUrl);
  } else {
    mainWindow.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }
}

ipcMain.handle("dialog:openFolder", async () => {
  if (!mainWindow) return null;
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openDirectory"],
  });
  if (result.canceled || result.filePaths.length === 0) return null;
  return result.filePaths[0];
});

ipcMain.handle("shell:openVscode", (_event, folder) => {
  if (!folder) return false;
  const cmd = process.platform === "win32" ? "code.cmd" : "code";
  try {
    spawn(cmd, [folder], { detached: true, stdio: "ignore", shell: true }).unref();
    return true;
  } catch {
    return false;
  }
});

ipcMain.handle("window:minimize", () => mainWindow && mainWindow.minimize());
ipcMain.handle("window:maximize", () => {
  if (!mainWindow) return;
  if (mainWindow.isMaximized()) mainWindow.unmaximize();
  else mainWindow.maximize();
});
ipcMain.handle("window:close", async () => {
  await quitJon();
});
ipcMain.handle("window:hide", () => hideWindow());

ipcMain.handle("update:install", async (_event, installerPath) => {
  const file = String(installerPath || "").trim();
  if (!file || !/^[A-Za-z]:\\.*Jon-Setup.*\.exe$/i.test(file)) {
    return { ok: false, error: "Unerwarteter Pfad zum Installationsprogramm." };
  }
  if (!fs.existsSync(file)) {
    return { ok: false, error: "Das Installationsprogramm wurde nicht gefunden." };
  }
  const options = {
    type: "question",
    buttons: ["Jetzt aktualisieren", "Abbrechen"],
    defaultId: 0,
    cancelId: 1,
    title: "Jon aktualisieren",
    message: "Jon schliesst sich und installiert die neue Version.",
    detail:
      "Deine Chats, Konten und Einstellungen bleiben erhalten. Nach der " +
      "Installation startet Jon von selbst wieder.",
  };
  const answer =
    mainWindow && !mainWindow.isDestroyed()
      ? await dialog.showMessageBox(mainWindow, options)
      : await dialog.showMessageBox(options);
  if (answer.response !== 0) return { ok: false, error: "Abgebrochen." };

  try {
    spawn(file, [], { detached: true, stdio: "ignore" }).unref();
  } catch (e) {
    return { ok: false, error: "Das Installationsprogramm liess sich nicht starten." };
  }
  setTimeout(() => void quitJon(), 900);
  return { ok: true };
});
ipcMain.handle("window:moveBy", (_event, dx, dy) => {
  if (!mainWindow) return;
  if (mainWindow.isMaximized()) {
    mainWindow.unmaximize();
    return;
  }
  const [x, y] = mainWindow.getPosition();
  mainWindow.setPosition(Math.round(x + dx), Math.round(y + dy));
});

ipcMain.handle("auth:token", async () => refreshToken());
ipcMain.handle("private:open", () => openPrivateBrowser());
ipcMain.handle("private:open-in-app", () => openPrivateInApp());
ipcMain.handle("private:minimize", () => privateWindow && privateWindow.minimize());
ipcMain.handle("private:maximize", () => {
  if (!privateWindow) return;
  if (privateWindow.isMaximized()) privateWindow.unmaximize();
  else privateWindow.maximize();
});
ipcMain.handle("private:close", () => privateWindow && privateWindow.close());
ipcMain.handle("private:clear", () => clearPrivateData());

ipcMain.handle("quickask:hide", () => quickWindow && quickWindow.hide());
ipcMain.handle("pet:toggle", () => togglePet());
ipcMain.handle("pet:hide", () => petWindow && petWindow.hide());
ipcMain.handle("pet:moveBy", (_event, dx, dy) => {
  if (!petWindow) return;
  const [x, y] = petWindow.getPosition();
  petWindow.setPosition(Math.round(x + dx), Math.round(y + dy));
});
ipcMain.handle("pet:setIgnore", (_event, ignore) => {
  if (petWindow) petWindow.setIgnoreMouseEvents(!!ignore, { forward: true });
});
ipcMain.handle("app:show", () => {
  if (!mainWindow) createWindow();
  else {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show();
    mainWindow.focus();
  }
});
ipcMain.handle("app:flash", () => {
  if (!mainWindow) return;
  if (!mainWindow.isFocused()) {
    mainWindow.flashFrame(true);
    if (!mainWindow.isVisible()) mainWindow.show();
  }
});
ipcMain.handle("app:focus", () => {
  if (!mainWindow) return;
  mainWindow.flashFrame(false);
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
});
ipcMain.handle("startup:get", () => app.getLoginItemSettings().openAtLogin);
ipcMain.handle("startup:set", (_event, enabled) => {
  app.setLoginItemSettings({ openAtLogin: !!enabled });
  return !!enabled;
});

app.whenReady().then(() => {
  session.defaultSession.setPermissionRequestHandler((_wc, _permission, cb) => cb(true));
  if (app.isPackaged) {
    app.setLoginItemSettings({ openAtLogin: true });
  }
  createWindow();
  createPet();
  void startBackend();
  void tokenAbgleich();
  globalShortcut.register("Control+Alt+J", toggleWindow);
  globalShortcut.register("Control+Alt+K", togglePet);
  globalShortcut.register("Control+Alt+Space", toggleQuickAsk);
  globalShortcut.register("Control+Alt+H", () => void openQuickWrite());
  globalShortcut.register("Control+Alt+P", openPrivateInApp);
  globalShortcut.register("Control+Alt+V", () => void readAloudSelection());
  globalShortcut.register("Control+Alt+E", () => {
    if (mainWindow) {
      if (!mainWindow.isVisible()) mainWindow.show();
      mainWindow.focus();
      mainWindow.webContents.send("jon:explain-screen");
    }
  });
  tray = new Tray(path.join(__dirname, "tray.png"));
  tray.setToolTip("Jon — Strg+Alt+J");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: "Jon öffnen/verstecken", click: toggleWindow },
      { label: "Schnellfrage (Strg+Alt+Leer)", click: toggleQuickAsk },
      { label: "Text verbessern (Strg+Alt+H)", click: () => void openQuickWrite() },
      {
        label: "Bildschirm erklären (Strg+Alt+E)",
        click: () => {
          if (mainWindow) {
            if (!mainWindow.isVisible()) mainWindow.show();
            mainWindow.focus();
            mainWindow.webContents.send("jon:explain-screen");
          }
        },
      },
      { label: "Mini Jon ein/aus", click: togglePet },
      { label: "Privater Browser (Strg+Alt+P)", click: openPrivateInApp },
      { type: "separator" },
      { label: "Fenster ausblenden (Jon laeuft weiter)", click: hideWindow },
      { label: "Jon beenden (auch das Backend)", click: () => void quitJon() },
    ])
  );
  tray.on("click", toggleWindow);
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("before-quit", () => {
  quitting = true;
  globalShortcut.unregisterAll();
  clearPrivateData();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

function freeBackendPorts() {
  if (process.platform !== "win32") return 0;
  const ports = BACKEND_PORTS.join(",");
  const script =
    `$mine = ${process.pid}; $names = @('jon-backend','python','pythonw','py'); ` +
    `$pids = Get-NetTCPConnection -LocalPort ${ports} -State Listen ` +
    "-ErrorAction SilentlyContinue | " +
    "Select-Object -ExpandProperty OwningProcess -Unique; " +
    "$killed = 0; " +
    "foreach ($p in $pids) { " +
    "  if ($p -eq $mine -or $p -eq 0 -or $p -eq 4) { continue } " +
    "  $proc = Get-Process -Id $p -ErrorAction SilentlyContinue; " +
    "  if (-not $proc) { continue } " +
    "  if ($names -notcontains $proc.ProcessName) { continue } " +
    "  Stop-Process -Id $p -Force -ErrorAction SilentlyContinue; $killed++ " +
    "} " +
    "Write-Output $killed";
  try {
    const out = spawnSync(
      "powershell",
      ["-NoProfile", "-NonInteractive", "-Command", script],
      { windowsHide: true, timeout: 10000, encoding: "utf8" }
    );
    return parseInt(String(out.stdout || "0").trim(), 10) || 0;
  } catch (e) {
    return 0;
  }
}

function askBackendToStop() {
  return new Promise((resolve) => {
    const done = setTimeout(resolve, 2000);
    apiFetch("/system/shutdown", { method: "POST" })
      .then(() => {
        clearTimeout(done);
        setTimeout(resolve, 400);
      })
      .catch(() => {
        clearTimeout(done);
        resolve();
      });
  });
}

let backendStopped = false;
function closeBackendConsole() {
  if (process.platform !== "win32") return;
  const script =
    `$mine = ${process.pid}; ` +
    "$hits = Get-CimInstance Win32_Process | Where-Object { " +
    "  $_.CommandLine -and $_.ProcessId -ne $mine -and " +
    "  $_.Name -in @('cmd.exe','powershell.exe','conhost.exe','jon-backend.exe') -and " +
    "  ($_.CommandLine -match 'start-jon' -or $_.CommandLine -match 'jon-backend' -or " +
    "   $_.CommandLine -match 'app\.main' -or $_.CommandLine -match 'autostart-jon') }; " +
    "foreach ($h in $hits) { Stop-Process -Id $h.ProcessId -Force -ErrorAction SilentlyContinue }";
  try {
    spawnSync("powershell", ["-NoProfile", "-NonInteractive", "-Command", script], {
      windowsHide: true,
      timeout: 6000,
    });
  } catch (e) {}
}

function stopBackend() {
  if (backendStopped) return;
  backendStopped = true;
  const pid = backendProcess ? backendProcess.pid : 0;
  backendProcess = null;
  try {
    if (process.platform === "win32" && pid) {
      spawnSync("taskkill", ["/pid", String(pid), "/t", "/f"], {
        windowsHide: true,
      });
    } else if (pid) {
      process.kill(pid);
    }
  } catch (e) {}
  freeBackendPorts();
  closeBackendConsole();
}

app.on("before-quit", stopBackend);
app.on("quit", stopBackend);
