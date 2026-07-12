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
  const backendDir = path.join(process.resourcesPath, "backend");
  if (!fs.existsSync(backendDir)) return;
  const logDir = app.getPath("userData");
  let out = "ignore";
  try {
    fs.mkdirSync(logDir, { recursive: true });
    out = fs.openSync(path.join(logDir, "backend.log"), "a");
  } catch (e) {}
  const py = resolvePython();
  const cmd = py[0];
  const pre = py.slice(1);
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  delete env.NODE_OPTIONS;
  const depCheck =
    "import fastapi,uvicorn,sqlalchemy,openai,anthropic,httpx,pydantic_settings,speech_recognition,pyautogui,pygetwindow,pyperclip,pypdf,cv2,edge_tts";
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
  tray = new Tray(path.join(__dirname, "tray.png"));
  tray.setToolTip("Jon — Strg+Alt+J");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: "Jon öffnen/verstecken", click: toggleWindow },
      { label: "Schnellfrage (Strg+Alt+Leer)", click: toggleQuickAsk },
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

app.on("quit", () => {
  if (backendProcess) backendProcess.kill();
});
