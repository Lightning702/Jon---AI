const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("jonPrivat", {
  minimize: () => ipcRenderer.invoke("private:minimize"),
  maximize: () => ipcRenderer.invoke("private:maximize"),
  close: () => ipcRenderer.invoke("private:close"),
  clearAll: () => ipcRenderer.invoke("private:clear"),
  onOpenTab: (cb) => ipcRenderer.on("private:open-tab", (_event, url) => cb(url)),
});
