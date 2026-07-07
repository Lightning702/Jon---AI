const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("jonpet", {
  showApp: () => ipcRenderer.invoke("app:show"),
  hide: () => ipcRenderer.invoke("pet:hide"),
});
