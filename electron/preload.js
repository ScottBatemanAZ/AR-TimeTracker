// Context bridge — the only surface the renderer (index.html) can touch.
// index.html guards every call with `if (window.electronAPI)`, so the browser
// and Docker deployments behave exactly as before (no electronAPI present).
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  isElectron: true,
  // Fire a native OS notification.
  notify: (title, body) => ipcRenderer.send('ar-notify', { title, body }),
  // Update the tray tooltip / menu header with a short status line.
  setStatus: (text) => ipcRenderer.send('ar-status', { text }),
  // Auto-launch-on-login toggle (Settings).
  getAutoLaunch: () => ipcRenderer.invoke('ar-get-autolaunch'),
  setAutoLaunch: (enabled) => ipcRenderer.invoke('ar-set-autolaunch', enabled),
});
