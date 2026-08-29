const { contextBridge, ipcRenderer } = require("electron");

const jonToken = (process.argv.find((a) => a.startsWith("--jon-token=")) || "").slice(12);
contextBridge.exposeInMainWorld("jonToken", jonToken);

contextBridge.exposeInMainWorld("quickask", {
  hide: () => ipcRenderer.invoke("quickask:hide"),
  openMain: () => ipcRenderer.invoke("app:show"),
  onFocus: (callback) => ipcRenderer.on("quickask:focus", callback),
});
