const { contextBridge, ipcRenderer, webUtils } = require("electron");

contextBridge.exposeInMainWorld("jon", {
  minimize: () => ipcRenderer.invoke("window:minimize"),
  maximize: () => ipcRenderer.invoke("window:maximize"),
  close: () => ipcRenderer.invoke("window:close"),
  moveBy: (dx, dy) => ipcRenderer.invoke("window:moveBy", dx, dy),
  pickFolder: () => ipcRenderer.invoke("dialog:openFolder"),
  openVscode: (folder) => ipcRenderer.invoke("shell:openVscode", folder),
  togglePet: () => ipcRenderer.invoke("pet:toggle"),
  getStartup: () => ipcRenderer.invoke("startup:get"),
  setStartup: (enabled) => ipcRenderer.invoke("startup:set", enabled),
  getPathForFile: (file) => {
    try {
      return webUtils.getPathForFile(file);
    } catch {
      return "";
    }
  },
  platform: process.platform,
});
