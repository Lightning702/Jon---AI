const { contextBridge, ipcRenderer, webUtils } = require("electron");

contextBridge.exposeInMainWorld("jon", {
  minimize: () => ipcRenderer.invoke("window:minimize"),
  maximize: () => ipcRenderer.invoke("window:maximize"),
  close: () => ipcRenderer.invoke("window:close"),
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
  getPathForFile: (file) => {
    try {
      return webUtils.getPathForFile(file);
    } catch {
      return "";
    }
  },
  platform: process.platform,
});
