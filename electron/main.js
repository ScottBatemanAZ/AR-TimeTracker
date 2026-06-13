// Azazel's Razer Time Tracker — Electron wrapper
//
// A thin native shell around the existing server.py / bundled server binary.
// The Electron main process spawns the server on localhost, waits for it to
// accept connections, then opens a BrowserWindow pointed at it. The server is
// the one true backend — zero porting. Adds: system tray, native
// notifications, window-state persistence, and auto-launch-on-login.

const { app, BrowserWindow, Tray, Menu, Notification, ipcMain, nativeImage } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const net = require('net');

const DEFAULT_PORT = 5757;

let serverProc = null;
let mainWindow = null;
let tray = null;
let serverPort = DEFAULT_PORT;

const ICON_PATH = path.join(__dirname, 'assets', 'ARSymbol.ico');
const APP_NAME = "Azazel's Razer Time Tracker";

// Use the product name for the userData folder (config/data live here) instead
// of the package "name". Must be set before the app is ready / any getPath call.
app.setName(APP_NAME);

// ── Single instance ───────────────────────────────────────────────────
// A second launch should focus the running window, not spawn a second server.
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      if (!mainWindow.isVisible()) mainWindow.show();
      mainWindow.focus();
    }
  });
  start();
}

function start() {
  app.whenReady().then(async () => {
    try {
      serverPort = await choosePort();
      serverProc = spawnServer(serverPort);
      wireServerExit(serverProc);
      await waitForServer(serverPort);
      createWindow(serverPort);
      createTray();
    } catch (err) {
      console.error('Startup failed:', err);
      app.quit();
    }

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow(serverPort);
      else if (mainWindow) mainWindow.show();
    });
  });
}

// ── Port selection ────────────────────────────────────────────────────
// Prefer 5757 (matches the standalone/Docker default). If it's already bound
// — e.g. a local Docker instance — grab an OS-assigned free port instead.
function isPortFree(port) {
  return new Promise((resolve) => {
    const tester = net.createServer()
      .once('error', () => resolve(false))
      .once('listening', () => tester.close(() => resolve(true)))
      .listen(port, '127.0.0.1');
  });
}

function getFreePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.once('error', reject);
    srv.listen(0, '127.0.0.1', () => {
      const { port } = srv.address();
      srv.close(() => resolve(port));
    });
  });
}

async function choosePort() {
  if (await isPortFree(DEFAULT_PORT)) return DEFAULT_PORT;
  return getFreePort();
}

// ── Wait for the server to accept connections ─────────────────────────
function waitForServer(port, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    const tryConnect = () => {
      const sock = net.connect(port, '127.0.0.1');
      sock.once('connect', () => { sock.destroy(); resolve(); });
      sock.once('error', () => {
        sock.destroy();
        if (Date.now() > deadline) reject(new Error('Server did not start in time'));
        else setTimeout(tryConnect, 250);
      });
    };
    tryConnect();
  });
}

// ── Spawn the backend ─────────────────────────────────────────────────
function spawnServer(port) {
  const env = {
    ...process.env,
    AR_PORT: String(port),
    AR_NO_BROWSER: '1',     // server must not open the system browser — Electron owns the window
    AR_NO_AUTOUPDATE: '1',  // Electron owns update/lifecycle — server must not git-pull + self-restart
    AR_DATA_DIR: app.getPath('userData'), // writable location for config/data (install dir may be read-only)
    AR_PARENT_PID: String(process.pid),   // server self-exits if we die/crash — no orphaned process
  };

  if (app.isPackaged) {
    // Packaged: PyInstaller-built binary copied into resources/server/ at build time.
    // windowsHide hides the bundled server's console window; stdio piped to a log file.
    const binDir = path.join(process.resourcesPath, 'server');
    const binName = process.platform === 'win32' ? 'AR-TimeTracker.exe' : 'AR-TimeTracker';
    const logPath = path.join(app.getPath('userData'), 'ar-server.log');
    let out = 'ignore';
    try { out = fs.openSync(logPath, 'a'); } catch (_) { /* fall back to ignore */ }
    const proc = spawn(path.join(binDir, binName), [], {
      env, cwd: binDir, windowsHide: true,
      stdio: ['ignore', out, out],
    });
    return proc;
  }

  // Dev: run server.py with the system Python. Prefer the Windows `py -3` launcher,
  // fall back to `python` if it isn't present.
  const serverPath = path.join(__dirname, '..', 'server.py');
  const cwd = path.join(__dirname, '..');
  const opts = { env, cwd, stdio: 'inherit', windowsHide: true };
  const launcher = process.platform === 'win32' ? 'py' : 'python3';
  const args = process.platform === 'win32' ? ['-3', serverPath] : [serverPath];
  const proc = spawn(launcher, args, opts);
  proc.once('error', (err) => {
    if (err.code === 'ENOENT') {
      // `py` (or `python3`) not found — retry with plain `python`.
      serverProc = spawn('python', [serverPath], opts);
      wireServerExit(serverProc);
    } else {
      console.error('Failed to spawn server:', err);
    }
  });
  return proc;
}

function wireServerExit(proc) {
  proc.once('exit', (code, signal) => {
    if (!app.isQuitting) {
      console.error(`Server process exited unexpectedly (code=${code}, signal=${signal})`);
    }
  });
}

// ── Window state persistence ──────────────────────────────────────────
function windowStatePath() {
  return path.join(app.getPath('userData'), 'window-state.json');
}

function loadWindowState() {
  try {
    const s = JSON.parse(fs.readFileSync(windowStatePath(), 'utf-8'));
    if (Number.isInteger(s.width) && Number.isInteger(s.height)) return s;
  } catch (_) { /* no saved state */ }
  return { width: 1280, height: 900 };
}

function saveWindowState() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  try {
    const b = mainWindow.getBounds();
    fs.writeFileSync(windowStatePath(), JSON.stringify({
      x: b.x, y: b.y, width: b.width, height: b.height,
      maximized: mainWindow.isMaximized(),
    }));
  } catch (_) { /* best effort */ }
}

// ── Window ────────────────────────────────────────────────────────────
function createWindow(port) {
  const state = loadWindowState();
  mainWindow = new BrowserWindow({
    x: state.x,
    y: state.y,
    width: state.width,
    height: state.height,
    minWidth: 900,
    minHeight: 600,
    backgroundColor: '#0e0e0f',
    icon: ICON_PATH,
    title: APP_NAME,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });
  if (state.maximized) mainWindow.maximize();
  mainWindow.loadURL(`http://127.0.0.1:${port}`);

  ['resize', 'move', 'close'].forEach((evt) => mainWindow.on(evt, saveWindowState));

  // Close = minimize to tray (unless actually quitting from the tray/menu).
  mainWindow.on('close', (e) => {
    if (!app.isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });
  mainWindow.on('closed', () => { mainWindow = null; });
}

// ── System tray ───────────────────────────────────────────────────────
function createTray() {
  let image = nativeImage.createFromPath(ICON_PATH);
  if (!image.isEmpty()) image = image.resize({ width: 16, height: 16 });
  tray = new Tray(image.isEmpty() ? ICON_PATH : image);
  tray.setToolTip(APP_NAME);
  tray.setContextMenu(buildTrayMenu());
  tray.on('double-click', showWindow);
}

function buildTrayMenu(statusLabel) {
  return Menu.buildFromTemplate([
    ...(statusLabel ? [{ label: statusLabel, enabled: false }, { type: 'separator' }] : []),
    { label: 'Show', click: showWindow },
    { label: 'Hide', click: () => mainWindow && mainWindow.hide() },
    { type: 'separator' },
    { label: 'Quit', click: () => { app.isQuitting = true; app.quit(); } },
  ]);
}

function showWindow() {
  if (!mainWindow) { createWindow(serverPort); return; }
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
}

// ── IPC: notifications, tray status, auto-launch (renderer ⇄ main) ─────
ipcMain.on('ar-notify', (_e, { title, body }) => {
  if (!Notification.isSupported()) return;
  const n = new Notification({ title: title || APP_NAME, body: body || '', icon: ICON_PATH });
  n.on('click', showWindow);
  n.show();
});

ipcMain.on('ar-status', (_e, status) => {
  // status: { text, tooltip } — text drives the tray tooltip + menu header.
  if (!tray) return;
  const text = (status && status.text) || APP_NAME;
  tray.setToolTip(text);
  tray.setContextMenu(buildTrayMenu(status && status.text ? status.text : null));
});

ipcMain.handle('ar-get-autolaunch', () => app.getLoginItemSettings().openAtLogin);
ipcMain.handle('ar-set-autolaunch', (_e, enabled) => {
  app.setLoginItemSettings({ openAtLogin: !!enabled });
  return app.getLoginItemSettings().openAtLogin;
});

// ── Lifecycle / teardown ──────────────────────────────────────────────
app.on('window-all-closed', () => {
  // On Windows the app lives in the tray; only quit if explicitly requested.
  if (process.platform === 'darwin') return;
  if (app.isQuitting) app.quit();
});

app.on('before-quit', () => { app.isQuitting = true; });

// Kill the child server on every quit path so it never orphans the port.
function killServer() {
  if (serverProc && !serverProc.killed) {
    try { serverProc.kill(); } catch (_) { /* already gone */ }
  }
}
app.on('will-quit', killServer);
process.on('exit', killServer);
