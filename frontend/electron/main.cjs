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

const isDev = !app.isPackaged;
let mainWindow = null;
let petWindow = null;
let quickWindow = null;
let quickWriteWindow = null;
const API_BASE = "http://127.0.0.1:8756/api";
let backendProcess = null;
let tray = null;
let quitting = false;

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
    const res = await fetch(`${API_BASE}/quickwrite/grab`);
    data = await res.json();
    if (!res.ok) data = { error: data.detail || "Kein Text markiert." };
  } catch (e) {
    data = { error: "Backend nicht erreichbar." };
  }
  if (quickWriteWindow) quickWriteWindow.webContents.send("quickwrite:data", data);
}

ipcMain.handle("quickwrite:apply", async (_e, mode) => {
  let result = { ok: false, error: "Fehlgeschlagen." };
  try {
    const res = await fetch(`${API_BASE}/quickwrite/apply`, {
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
    const s = await (await fetch(`${API_BASE}/settings`)).json();
    roamOn = s.pet_roam === true;
  } catch (e) {
    roamOn = false;
  }
  try {
    const idle = Number((await (await fetch(`${API_BASE}/system/idle`)).json()).seconds || 0);
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
      env: { ...process.env },
      stdio: ["ignore", out, out],
      windowsHide: true,
    });
    backendProcess.on("error", () => {});
    return;
  }

  const backendDir = path.join(process.resourcesPath, "backend");
  if (!fs.existsSync(backendDir)) return;
  const py = resolvePython();
  const cmd = py[0];
  const pre = py.slice(1);
  const env = { ...process.env };
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
}

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
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.once("ready-to-show", () => mainWindow.show());

  mainWindow.on("close", (event) => {
    if (!quitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  if (isDev) {
    mainWindow.loadURL("http://127.0.0.1:5173");
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
ipcMain.handle("window:close", () => mainWindow && mainWindow.close());
ipcMain.handle("window:moveBy", (_event, dx, dy) => {
  if (!mainWindow) return;
  if (mainWindow.isMaximized()) {
    mainWindow.unmaximize();
    return;
  }
  const [x, y] = mainWindow.getPosition();
  mainWindow.setPosition(Math.round(x + dx), Math.round(y + dy));
});

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
  globalShortcut.register("Control+Alt+J", toggleWindow);
  globalShortcut.register("Control+Alt+K", togglePet);
  globalShortcut.register("Control+Alt+Space", toggleQuickAsk);
  globalShortcut.register("Control+Alt+H", () => void openQuickWrite());
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
      { type: "separator" },
      {
        label: "Beenden",
        click: () => {
          quitting = true;
          app.quit();
        },
      },
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
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

function stopBackend() {
  if (!backendProcess) return;
  const pid = backendProcess.pid;
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
}

app.on("before-quit", stopBackend);
app.on("quit", stopBackend);
