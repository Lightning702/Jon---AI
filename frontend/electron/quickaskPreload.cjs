const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("quickask", {
  hide: () => ipcRenderer.invoke("quickask:hide"),
  openMain: () => ipcRenderer.invoke("app:show"),
  onFocus: (callback) => ipcRenderer.on("quickask:focus", callback),
});
