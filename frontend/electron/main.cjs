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
const { spawn } = require("node:child_process");

const isDev = !app.isPackaged;
let mainWindow = null;
let petWindow = null;
let backendProcess = null;
let tray = null;
let quitting = false;

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

function startBackend() {
  if (!app.isPackaged) return;
  const backendDir = path.join(process.resourcesPath, "backend");
  if (!fs.existsSync(backendDir)) return;
  const dataDir = path.join(backendDir, "..", "data");
  try {
    fs.mkdirSync(dataDir, { recursive: true });
  } catch (e) {}
  let out = "ignore";
  try {
    out = fs.openSync(path.join(dataDir, "backend.log"), "a");
  } catch (e) {}
  const pyEnv =
    process.env.JON_PYTHON || (process.platform === "win32" ? "python" : "python3");
  const parts = pyEnv.trim().split(/\s+/);
  const cmd = parts[0];
  const preArgs = parts.slice(1);
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  delete env.NODE_OPTIONS;
  backendProcess = spawn(cmd, [...preArgs, "-m", "app.main"], {
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
  startBackend();
  createWindow();
  createPet();
  globalShortcut.register("Control+Alt+J", toggleWindow);
  globalShortcut.register("Control+Alt+K", togglePet);
  tray = new Tray(path.join(__dirname, "tray.png"));
  tray.setToolTip("Jon — Strg+Alt+J");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: "Jon öffnen/verstecken", click: toggleWindow },
      { label: "Kleiner Jon ein/aus", click: togglePet },
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
