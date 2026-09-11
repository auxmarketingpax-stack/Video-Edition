const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("workflow", {
  selectFolder: () => ipcRenderer.invoke("select-folder"),
  selectTemplate: () => ipcRenderer.invoke("select-template"),
  selectMusic: () => ipcRenderer.invoke("select-music"),
  selectMusicFolder: () => ipcRenderer.invoke("select-music-folder"),
  selectCoverMedia: () => ipcRenderer.invoke("select-cover-media"),
  analyzeMusicFolder: (payload) => ipcRenderer.invoke("analyze-music-folder", payload),
  getDefaults: () => ipcRenderer.invoke("get-defaults"),
  run: (payload) => ipcRenderer.invoke("run-workflow", payload),
  stop: () => ipcRenderer.invoke("stop-workflow"),
  onLog: (callback) => {
    const listener = (_event, payload) => callback(payload);
    ipcRenderer.on("workflow-log", listener);
    return () => ipcRenderer.removeListener("workflow-log", listener);
  }
});
