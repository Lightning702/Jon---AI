const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("jon", {
  minimize: () => ipcRenderer.invoke("window:minimize"),
  maximize: () => ipcRenderer.invoke("window:maximize"),
  close: () => ipcRenderer.invoke("window:close"),
  pickFolder: () => ipcRenderer.invoke("dialog:openFolder"),
  openVscode: (folder) => ipcRenderer.invoke("shell:openVscode", folder),
  platform: process.platform,
});
