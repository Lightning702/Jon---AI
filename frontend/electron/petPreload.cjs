const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("jonpet", {
  showApp: () => ipcRenderer.invoke("app:show"),
  hide: () => ipcRenderer.invoke("pet:hide"),
  moveBy: (dx, dy) => ipcRenderer.invoke("pet:moveBy", dx, dy),
  setIgnore: (ignore) => ipcRenderer.invoke("pet:setIgnore", ignore),
  openPrivate: () => ipcRenderer.invoke("private:open"),
  openPrivateInApp: () => ipcRenderer.invoke("private:open-in-app"),
  onRead: (cb) => ipcRenderer.on("pet:read", (_e, text) => cb(text)),
});
