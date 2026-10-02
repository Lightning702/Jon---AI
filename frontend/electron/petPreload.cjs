const { contextBridge, ipcRenderer } = require("electron");

const jonToken = (process.argv.find((a) => a.startsWith("--jon-token=")) || "").slice(12);
contextBridge.exposeInMainWorld("jonToken", jonToken);
contextBridge.exposeInMainWorld("jonTokenHolen", () =>
  ipcRenderer.invoke("auth:token")
);

contextBridge.exposeInMainWorld("jonpet", {
  showApp: () => ipcRenderer.invoke("app:show"),
  prepareScreen: () => ipcRenderer.invoke("pet:prepareScreen"),
  restoreScreen: () => ipcRenderer.invoke("pet:restoreScreen"),
  hide: () => ipcRenderer.invoke("pet:hide"),
  beginDrag: () => ipcRenderer.invoke("pet:beginDrag"),
  endDrag: () => ipcRenderer.invoke("pet:endDrag"),
  setIgnore: (ignore) => ipcRenderer.invoke("pet:setIgnore", ignore),
  openPrivate: () => ipcRenderer.invoke("private:open"),
  openPrivateInApp: () => ipcRenderer.invoke("private:open-in-app"),
  onRead: (cb) => ipcRenderer.on("pet:read", (_e, text) => cb(text)),
});
