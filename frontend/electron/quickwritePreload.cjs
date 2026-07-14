const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("quickwrite", {
  onData: (callback) => ipcRenderer.on("quickwrite:data", (_e, data) => callback(data)),
  onResult: (callback) => ipcRenderer.on("quickwrite:result", (_e, data) => callback(data)),
  apply: (mode) => ipcRenderer.invoke("quickwrite:apply", mode),
  hide: () => ipcRenderer.invoke("quickwrite:hide"),
});
