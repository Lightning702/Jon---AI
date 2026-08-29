const { contextBridge, ipcRenderer, webUtils } = require("electron");

const jonToken = (process.argv.find((a) => a.startsWith("--jon-token=")) || "").slice(12);

contextBridge.exposeInMainWorld("jon", {
  minimize: () => ipcRenderer.invoke("window:minimize"),
  maximize: () => ipcRenderer.invoke("window:maximize"),
  close: () => ipcRenderer.invoke("window:close"),
  hide: () => ipcRenderer.invoke("window:hide"),
  installUpdate: (path) => ipcRenderer.invoke("update:install", path),
  moveBy: (dx, dy) => ipcRenderer.invoke("window:moveBy", dx, dy),
  pickFolder: () => ipcRenderer.invoke("dialog:openFolder"),
  openVscode: (folder) => ipcRenderer.invoke("shell:openVscode", folder),
  togglePet: () => ipcRenderer.invoke("pet:toggle"),
  openPrivateBrowser: () => ipcRenderer.invoke("private:open"),
  flashWindow: () => ipcRenderer.invoke("app:flash"),
  focusWindow: () => ipcRenderer.invoke("app:focus"),
  getStartup: () => ipcRenderer.invoke("startup:get"),
  setStartup: (enabled) => ipcRenderer.invoke("startup:set", enabled),
  onExplainScreen: (cb) => ipcRenderer.on("jon:explain-screen", () => cb()),
  onOpenPrivate: (cb) => ipcRenderer.on("jon:open-private", () => cb()),
  getPathForFile: (file) => {
    try {
      return webUtils.getPathForFile(file);
    } catch {
      return "";
    }
  },
  platform: process.platform,
});
