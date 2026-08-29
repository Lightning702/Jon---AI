const { contextBridge, ipcRenderer } = require("electron");

const jonToken = (process.argv.find((a) => a.startsWith("--jon-token=")) || "").slice(12);
contextBridge.exposeInMainWorld("jonToken", jonToken);

contextBridge.exposeInMainWorld("jonPrivat", {
  minimize: () => ipcRenderer.invoke("private:minimize"),
  maximize: () => ipcRenderer.invoke("private:maximize"),
  close: () => ipcRenderer.invoke("private:close"),
  clearAll: () => ipcRenderer.invoke("private:clear"),
  onOpenTab: (cb) => ipcRenderer.on("private:open-tab", (_event, url) => cb(url)),
});
