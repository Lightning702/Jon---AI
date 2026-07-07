const { app, BrowserWindow, ipcMain, shell, dialog } = require("electron");
const path = require("node:path");
const { spawn } = require("node:child_process");

const isDev = !app.isPackaged;
let mainWindow = null;
let backendProcess = null;

function startBackend() {
  if (!app.isPackaged) return;
  const root = path.join(process.resourcesPath, "backend");
  const python = process.platform === "win32" ? "python" : "python3";
  backendProcess = spawn(python, ["-m", "app.main"], {
    cwd: root,
    env: { ...process.env },
    stdio: "ignore",
  });
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

app.whenReady().then(() => {
  startBackend();
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("quit", () => {
  if (backendProcess) backendProcess.kill();
});
