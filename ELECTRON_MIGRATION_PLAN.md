# Electron Migration Plan

## Azazel's Razer Time Tracker — Optional Desktop Wrapper

**Current version:** Beta 10.5.0 (localhost Python server v1.7 + browser; also packaged as a standalone EXE/ZIP via PyInstaller)
**Target:** Optional Electron desktop wrapper around the existing `server.py` (bundled via PyInstaller) — native window/tray/notifications for single-machine use
**Drafted:** 2026-06-12 — reality-checked against Beta 10.4.1 / Server v1.6
**Revised:** 2026-06-12 — original plan's Phase 2 retired `server.py` entirely, which conflicts with the documented Docker/multi-device deployment (NAS-hosted, accessed from multiple machines). This revision keeps `server.py` as the one true backend for *every* deployment; Electron becomes a thin native shell around it.

> **✅ STATUS — Implemented (Beta 10.6.0):** Phases 1–3 are shipped in `electron/`. The wrapper spawns the existing server (dev: `py -3 ../server.py`; packaged: bundled PyInstaller binary), with system tray, native notifications, window-state persistence, auto-launch toggle, and single-instance lock. `npm run dist` produces a per-user NSIS installer that needs no Python/Node on the target. Server gained launcher env hooks (`AR_PORT`, `AR_NO_BROWSER`, `AR_NO_AUTOUPDATE`, `AR_DATA_DIR`, `AR_PARENT_PID`) and a parent-PID watchdog (no orphaned server if the wrapper crashes). Build/run details live in `electron/README.md`. "Future Features" below remain unbuilt.

---

## Why Electron (Revised)

- Native desktop integration — system tray, native notifications, auto-launch on login, native file dialogs, no browser chrome — for users running the app on a single machine
- Reuses the *entire* existing stack with zero rewrite: `index.html`, `server.py`, `filament-library.json`/`resin-library.json`, ODS/XLSX/CSV export (Beta 10.5.0), Moonraker/OctoPrint polling, Spoolman proxy
- Docker users (multi-device/NAS deployment, per `CLAUDE.md`) are completely unaffected — this is an *additional* packaging option, not a replacement

**What changed from the original plan:** The original plan ported the entire Python backend — polling, Spoolman proxy, and the ~400-line hand-rolled ODS/XLSX XML generators — into Node/Electron's main process, and retired `server.py`. That's a large rewrite with real correctness risk (re-validating two spreadsheet formats), and it breaks the Docker/multi-device deployment this project actually uses day-to-day. The revised approach: Electron's main process spawns the existing PyInstaller-built server binary as a child process on localhost and loads a `BrowserWindow` pointed at it. Every backend feature — including the brand-new Beta 10.5.0 XLSX export — keeps working with zero porting, in both the Electron wrapper and the Docker deployment.

**Trade-off accepted:** Electron bundles Chromium (~150MB) *and* the PyInstaller server binary (~15-30MB) — a heavier installer than a pure-Node rewrite would have been, but a tiny fraction of the porting effort and risk, and it keeps one backend codebase for everything.

---

## What Stays the Same

- Entire `index.html` UI — HTML, CSS, JS, all logic (Design/FDM/Resin tracks, multi-printer cards, nested projects, archiving, onboarding wizard, Spoolman picker, estimates, ODS/XLSX/CSV export, etc.) — unchanged, served exactly as it is today
- `server.py` — unchanged. Same endpoints (`/printer-status`, `/generate-ods`, `/generate-xlsx`, `/spoolman/*`, `/update-printers`, `/save-data`, etc.), same Moonraker/OctoPrint polling, same Spoolman proxy
- All cost models, session logic, material modals, receipt tracking, invoice export
- `filament-library.json` / `resin-library.json` reference data
- IBM Plex fonts — self-hosted since Beta 10.2.8
- AR branding, color scheme, layout, configurable branding (Beta 10.3.0)
- **Docker deployment** (`Dockerfile`, `docker-compose.yml`) — completely untouched, remains the primary multi-device path documented in `CLAUDE.md`
- **PyInstaller EXE/ZIP pipeline** (Beta 10.2.2) — the Electron build *reuses* this binary rather than retiring it

---

## What Changes

| Current | Electron Equivalent |
| --- | --- |
| User runs `launch.bat` / EXE, browser opens to `localhost:5757` | Electron `main.js` spawns the same server binary as a child process, then opens a `BrowserWindow` pointed at it — no browser chrome, no manual launch step |
| Browser tab (closable independently of the server process) | `BrowserWindow` + server lifecycle tied together — child process killed on app quit |
| No tray icon | System tray icon (`ARSymbol.ico`) — minimize to tray, quit from tray |
| No native notifications | Electron `Notification` API for punch-out alerts, printer-offline alerts, etc. — `index.html` already knows when these happen, just needs an IPC call to trigger the native notification |
| `launch.bat` | Installed `.exe` / Start Menu shortcut |
| Manual update check + ⬆ badge (Beta 10.2.2) | Unchanged for now; `electron-updater` could subsume this later (Future) |
| `/generate-ods`, `/generate-xlsx`, Moonraker/OctoPrint polling, Spoolman proxy, `ar-data-live.json`, first-run wizard, `/update-printers` | **Unchanged — still `server.py`, reused as-is, in both Electron and Docker** |

---

## File Structure (Post-Migration)

```text
R:\Azazel's Razer\timetracker\
├── server.py, index.html, filament-library.json, resin-library.json, ...  # unchanged
├── Dockerfile, docker-compose.yml          # unchanged — Docker deployment path
├── AR-TimeTracker.spec                     # unchanged — PyInstaller build, now also feeds Electron
├── electron/                               # NEW — self-contained wrapper project
│   ├── package.json                        # Electron project config + build scripts
│   ├── main.js                             # spawns bundled server binary, opens BrowserWindow, tray, IPC
│   ├── preload.js                          # context bridge: exposes notify()/tray API to renderer
│   ├── resources/
│   │   └── server/                         # PyInstaller server binary + static assets, copied at build time
│   └── dist/                               # built installer output (gitignored)
```

`electron/` does not move or replace any existing file. A small feature-detected hook is added to `index.html` (`if (window.electronAPI) ...`, no-op in the browser/Docker) so the renderer can optionally trigger native notifications when running inside Electron.

---

## Migration Phases

---

### Phase 1 — Scaffold & Smoke Test

**Goal:** Electron window that spawns the existing server and displays the app, unmodified.

1. Install Node.js (LTS) if not already present
2. `npm init` inside a new `electron/` folder; `npm install --save-dev electron electron-builder`
3. Write `electron/main.js`:
   - On `app.whenReady()`, spawn the server as a child process — dev mode: `py -3 ../server.py`; packaged mode: the bundled PyInstaller binary — on a fixed port (5757), falling back to a free port if 5757 is already bound (e.g. by a local Docker instance)
   - Reuse the existing socket-polling pattern from `open_browser()` (Beta 10.2.7) to wait for the child process's port to accept connections before creating the window
   - Create `BrowserWindow` (1280×900, dark background, `ARSymbol.ico` icon), load `http://127.0.0.1:<port>`
   - On `before-quit`, kill the child process
4. `npm start` — confirm the window opens with no browser chrome, the UI renders, and every existing feature (including Beta 10.5.0's ODS/XLSX/CSV export) works identically to the browser version, because it's the same server

**Exit criteria:** App opens as a window; every existing feature works exactly as it does today, with no server.py changes required.

---

### Phase 2 — Native Notifications & Tray

**Goal:** Make it feel like a desktop app, not a browser in a box. (Replaces the original "retire server.py" Phase 2 — no longer needed.)

#### 2a. System Tray

- Tray icon: `ARSymbol.ico`
- Tray menu: Show/Hide, active session indicator, Quit
- Tray tooltip shows active session count + running cost (mirrors the topbar running-cost badge, Beta 10.0.0)
- Closing the main window minimizes to tray instead of quitting; Quit from tray stops the server child process and exits

#### 2b. Native Notifications

- `preload.js` exposes `window.electronAPI.notify(title, body)` via `contextBridge` (Electron's built-in `Notification` API, no external package)
- `index.html` calls it — guarded by `if (window.electronAPI)`, so the browser/Docker app is unaffected — at existing event points:
  - Auto punch-out: `"FDM session ended — X.Xh logged"`
  - Printer offline (after the existing 12-poll threshold): `"<printer name> unreachable"`

#### 2c. Window State Persistence

- `electron-store` (or a small JSON file) remembers window size/position between launches

#### 2d. Auto-Launch on Login (Optional / User Toggle)

- `electron-auto-launch` package, exposed as a toggle in the Settings modal (Electron-only — feature-detected)

**Exit criteria:** Tray icon present and functional; notifications fire on punch-out/offline; window remembers position; auto-launch toggle works.

---

### Phase 3 — Packaging

**Goal:** Single installer for the desktop wrapper. (Merges/renames the original Phase 5; the original Phase 4 — a new data layer — is unnecessary, since `server.py`'s existing localStorage / `ar-data-live.json` file-storage modes, Beta 10.2.0, are reused untouched by the bundled server.)

1. Build step copies the existing PyInstaller server binary (from `AR-TimeTracker.spec`, Beta 10.2.2) plus `index.html`, fonts, and library JSON files into `electron/resources/server/`
2. Configure `electron-builder` in `electron/package.json`:

   ```json
   "build": {
     "appId": "com.azazelsrazer.timetracker",
     "productName": "Azazel's Razer Time Tracker",
     "extraResources": [{ "from": "resources/server", "to": "server" }],
     "win": {
       "icon": "resources/ARSymbol.ico",
       "target": "nsis"
     },
     "nsis": {
       "oneClick": false,
       "allowToChangeInstallationDirectory": true
     }
   }
   ```

3. `npm run dist` → installer in `electron/dist/`
4. Installer handles: app files + bundled server binary, Start Menu shortcut, Desktop shortcut, uninstaller
5. Confirm `ARSymbol.ico` shows correctly in taskbar/Alt+Tab/installer, and the bundled server binary resolves its static/data paths correctly when launched from `resources/server/` in an installed app (not just a dev folder) — same `STATIC_DIR`/`DATA_DIR` split as the existing PyInstaller frozen mode

**Exit criteria:** Fresh Windows machine install works end-to-end — double-click installer, launch app, no Python/Node prerequisites, all features (including XLSX export) work. Docker deployment is unaffected and remains documented as the multi-device option.

---

## Future Features (Electron-Enabled)

These aren't feasible or practical in the browser version but become natural in the Electron wrapper. (Items already shipped in the browser app — backup/restore, session notes, OctoPrint support, multi-printer tracking, XLSX export — are omitted; see `CLAUDE.md` version history.)

### Near-Term (Low Effort)

- **PDF Invoice Export** — Trigger the existing invoice HTML generation, then use Electron's `webContents.printToPDF()` to save directly to disk instead of relying on the browser print dialog.
- **Native file-dialog Backup/Restore** — Refine the existing Backup/Restore buttons (Beta 8.5) to use `dialog.showSaveDialog`/`showOpenDialog` instead of browser download/upload.
- **Full auto-updater** — Beta 10.2.2 already checks GitHub releases and shows an in-app ⬆ badge; `electron-updater` could upgrade this to background download + one-click install (needs a decision on which mechanism owns version checks — see Risks).

### Medium-Term

- **Multi-monitor awareness** — Remember which monitor the app was on, reopen there.
- **Global keyboard shortcut** — Register a system-wide hotkey (e.g., `Ctrl+Shift+T`) to show/hide the app, even when minimized to tray.
- **Per-project file attachments** — Attach reference files (STLs, customer emails, photos) to a project via Electron's file system access. Stored as references in the existing JSON data file.

### Longer-Term

- **Expanded client records** — Beta 9.6 added a single `client` field per project with invoice auto-fill; a full client table (saved billing info, multi-project history) is the natural extension.
- **Recurring project templates** — Clone a project structure (rates, scope format) for repeat client work.
- **Cost trend charts** — Per-project or across-project cost breakdowns over time. Recharts or Chart.js in the renderer, data already structured for it.
- **Moonraker webhook / push** — Subscribe to Moonraker's websocket for real-time print state instead of polling, eliminating the 5s lag on auto punch-in/out.
- **Cloud sync (optional, opt-in)** — Sync the data file to a user-specified path (Dropbox, OneDrive, network share).

---

## Dependencies Summary

| Package | Purpose | Phase |
| --- | --- | --- |
| `electron` | Core framework | 1 |
| `electron-builder` | Installer packaging — bundles the PyInstaller server binary as an extra resource | 3 |
| `electron-store` | Window state persistence | 2c |
| `electron-auto-launch` | Login auto-start toggle (optional) | 2d |
| `electron-updater` | Auto-update from GitHub releases | Future |

No `jszip` or Node port of `/generate-ods`/`/generate-xlsx` is needed — both continue to run in `server.py`, unchanged, for Electron *and* Docker.

---

## Risks & Gotchas (Revised)

- **Port conflicts** — if a user runs both the Electron app and a Docker instance on the same machine (both default to port 5757), the Electron-spawned server needs to fall back to a free port. Bind to an OS-assigned port (`0`) or scan for the next free port starting at 5757, and point the `BrowserWindow` at whatever port the child process actually bound.
- **Child process lifecycle** — the spawned server must be reliably killed on quit (window close → tray, tray Quit, Alt+F4, unexpected renderer crash) to avoid orphaned processes holding the port. `app.on('before-quit')` plus a fallback `process.on('exit')` handler covers this.
- **Packaged path resolution** — the PyInstaller binary's `STATIC_DIR`/`DATA_DIR` split (Beta 10.2.2 frozen-mode) must resolve correctly when launched from `resources/server/` inside an installed Electron app, not just a dev folder. Verify with a real `electron-builder` build, not just `npm start`.
- **Two update mechanisms** — Beta 10.2.2's GitHub release check (Python side, shows an in-app ⬆ badge) and a future `electron-updater` would both exist for Electron users. Decide which one owns "is there a new version" before adding `electron-updater`, to avoid duplicate/contradictory prompts.
- **Electron security model** — `nodeIntegration: false`, `contextIsolation: true`, all Node access via `preload.js`. Don't shortcut this.
- **Windows code signing** — same caveat as today's PyInstaller EXE (see `VERIFY.md`): unsigned `.exe` triggers SmartScreen on first run on other machines. Fine for personal use; a code-signing cert (~$100-400/yr) is needed for wider distribution.
- **Electron version pinning** — pin the Electron version in `electron/package.json`; major Electron updates occasionally break renderer behavior.
- **Spawned server's console window** — `AR-TimeTracker.spec` currently builds with `console=True` (useful for standalone EXE startup logs). Launched as an Electron child process, that console window would pop up alongside the `BrowserWindow` unless the server is (a) rebuilt with `console=False` for the Electron variant, or (b) spawned with `CREATE_NO_WINDOW` / `windowsHide: true` from `main.js`.
- **Scope discipline vs. Docker** — this wrapper is for single-machine use only; multi-device access still requires the Docker deployment described in `CLAUDE.md`. Any Electron-only feature added to `index.html` must be guarded by `if (window.electronAPI)` so the browser/Docker app behaves exactly as it does today.

---

## Suggested Implementation Order

1. Phase 1 (scaffold: spawn server + window) — ~2-3 hours, mostly process-management plumbing, low risk since the backend is untouched
2. Phase 2 (tray + notifications + window state + auto-launch) — ~3-4 hours
3. Phase 3 (installer, reusing the existing PyInstaller pipeline) — ~2-3 hours
4. Future features — pick from the list as needs arise

Total realistic effort to a shippable Phase 1-3 build: **~1-2 focused evenings** — substantially less than the original plan, because no backend porting (polling, Spoolman proxy, ODS/XLSX export) is required.

---

*Drop this file in `R:\Azazel's Razer\timetracker\` alongside `CLAUDE.md` for reference during implementation.*
