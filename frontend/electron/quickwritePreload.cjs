const { contextBridge, ipcRenderer } = require("electron");

const jonToken = (process.argv.find((a) => a.startsWith("--jon-token=")) || "").slice(12);
contextBridge.exposeInMainWorld("jonToken", jonToken);

contextBridge.exposeInMainWorld("quickwrite", {
  onData: (callback) => ipcRenderer.on("quickwrite:data", (_e, data) => callback(data)),
  onResult: (callback) => ipcRenderer.on("quickwrite:result", (_e, data) => callback(data)),
  apply: (mode) => ipcRenderer.invoke("quickwrite:apply", mode),
  hide: () => ipcRenderer.invoke("quickwrite:hide"),
});
