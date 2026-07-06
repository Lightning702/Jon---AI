const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("jon", {
  minimize: () => ipcRenderer.invoke("window:minimize"),
  maximize: () => ipcRenderer.invoke("window:maximize"),
  close: () => ipcRenderer.invoke("window:close"),
  platform: process.platform,
});
