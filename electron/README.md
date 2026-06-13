# Electron desktop wrapper

A thin native desktop shell around the existing `server.py`. The Electron main
process spawns the server on localhost, waits for it to accept connections, then
opens a `BrowserWindow` pointed at it. **The server is the one true backend** —
every feature (Moonraker/OctoPrint polling, Spoolman proxy, ODS/XLSX/CSV export,
file storage) keeps working exactly as in the browser/Docker app, with zero
porting. The Docker deployment is completely unaffected.

See `../ELECTRON_MIGRATION_PLAN.md` for the full plan and rationale.

## What it adds over the browser app

- **No browser, no manual launch** — double-click the installed app; the window opens directly.
- **System tray** — minimize-to-tray, Show/Hide/Quit, live tooltip showing active session count + running cost.
- **Native notifications** — fired on auto punch-out ("print finished") and printer-offline.
- **Window-state persistence** — size/position/maximized remembered between launches.
- **Auto-launch on login** — toggle in Settings → Desktop App.
- **Single-instance** — a second launch focuses the running window instead of starting a second server.

All renderer-side hooks in `index.html` are guarded by `if (window.electronAPI)`,
so the browser and Docker deployments are untouched.

## Run (dev)

```powershell
cd electron
npm install      # one-time — installs electron + electron-builder
npm start        # spawns py -3 ../server.py and opens the window
```

## Build the installer

Produces a single Windows installer (`.exe`) that needs **no Python and no Node**
on the target machine — the PyInstaller-built server binary is bundled inside.

```powershell
cd electron
npm run dist     # 1) PyInstaller-builds the server, 2) electron-builder packages it
```

Output: `electron/dist/Azazel's Razer Time Tracker Setup <version>.exe`
(per-user install, no admin required).

- `npm run pack` — builds an unpacked app in `dist/win-unpacked/` for quick testing (no installer).
- The server is built with Python **3.11** by default (PyInstaller lags the newest
  CPython). Override with the `AR_PY` env var, e.g. `AR_PY="py -3.12"`.

### How packaging works

`scripts/build-server.js` runs `pyinstaller ../AR-TimeTracker.spec` (one-file,
`console=True`) and copies the resulting `AR-TimeTracker.exe` into
`resources/server/`. `electron-builder` bundles that folder via `extraResources`,
so at runtime the packaged app spawns `resources/server/AR-TimeTracker.exe`
(with `windowsHide:true`, so its console never shows).

## Environment the wrapper sets for the server

| Var | Effect |
| --- | --- |
| `AR_PORT` | Port the server binds. Electron picks 5757 if free, else an OS-assigned free port (avoids clashing with a local Docker instance). |
| `AR_NO_BROWSER` | Server skips opening the system browser — Electron owns the window. |
| `AR_NO_AUTOUPDATE` | Server skips its git-pull + self-restart — Electron owns the update/lifecycle. |
| `AR_DATA_DIR` | Writable location for `config.json` / `ar-data-live.json` / `printers.json` (the install dir may be read-only). Set to Electron's `userData`. |

All are read by `server.py` and are no-ops for the normal `launch.bat` / Docker / EXE paths.

## Notes / gotchas

- **`ELECTRON_RUN_AS_NODE`**: if set (some sandboxed shells set it), Electron runs
  as plain Node and `require('electron')` returns a path string →
  `Cannot read properties of undefined (reading 'whenReady')`. Unset it before `npm start`.
- **Headless/no-GPU environments**: if there's no usable GPU, launch with
  `npm start -- --disable-gpu --disable-software-rasterizer`. Not needed on a normal desktop.
- **Code signing**: the installer is unsigned (same as the standalone EXE — see
  `../VERIFY.md`), so SmartScreen warns on first run on other machines. Fine for
  personal use; a cert is needed for wide distribution.
