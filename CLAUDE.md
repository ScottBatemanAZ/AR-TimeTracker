# Azazel's Razer — Time Tracker

Self-contained time tracker for a 3D printing/design LLC. Vanilla HTML/CSS/JS front-end
served by a Python stdlib HTTP server. No framework, no build step, no database.

**Current version:** Beta 10.10.0 | **Server:** v1.10
**Git remote:** https://github.com/ScottBatemanAZ/AR-TimeTracker
**Project root (NAS):** `R:\Azazel's Razer\timetracker\`

---

## Files

| File | Purpose |
|---|---|
| `index.html` | Entire app — HTML + CSS + JS (~1700 lines) |
| `server.py` | Python stdlib HTTP server (port 5757) + Moonraker poller + ODS generator |
| `filament-library.json` | 50-material filament reference (density, cost, thenextlayer.com slugs) |
| `launch.bat` | `py -3 server.py` + opens browser |
| `Dockerfile` | `python:3.12-slim`, exposes 5757 |
| `docker-compose.yml` | Volume-mounts source, `restart: unless-stopped`, sets `DOCKER=1` |
| `.dockerignore` | Excludes `.git`, `.claude`, `__pycache__` |
| `ARLogo-FullTrans.png` | Full logo — dark bg, 100px tall in sidebar |
| `ARSymbol.png` / `.ico` | Symbol variant for desktop shortcut |
| `printers.json` | Printer config written by `/update-printers` — auto-created on first Settings save |
| `AR-TimeTracker.spec` | PyInstaller spec — one-file `console=True` EXE; bundles index.html, libraries, fonts, icons |
| `electron/` | Optional native desktop wrapper (Electron) — spawns `server.py`/bundled binary, adds tray/notifications/installer. See `electron/README.md` |
| `CLAUDE.md` | This file |

---

## Running the app

```
python server.py          # localhost:5757 — hard refresh picks up HTML/JS/CSS changes
docker compose up -d      # Docker: git pull && docker compose restart to deploy
```

---

## Architecture

### Storage
- All project data → `localStorage` key `ar_tracker_v1`
- Settings → `localStorage` key `ar_tracker_settings`
- No server-side persistence. Backup/restore via sidebar buttons (⬇ Backup / ⬆ Restore).

### Server endpoints
| Path | Method | Purpose |
|---|---|---|
| `/*` | GET | Static file serving (SimpleHTTPRequestHandler) |
| `/printer-status` | GET | JSON snapshot of printer state |
| `/generate-ods` | POST | Accepts project+settings JSON, returns ODS file |
| `/generate-xlsx` | POST | Accepts project+settings JSON, returns XLSX file |
| `/spoolman/check` | POST | `{url}` → pings a Spoolman instance, returns `{ok, version}` |
| `/spoolman/spools` | POST | `{url}` → proxies spool list, returns trimmed `{ok, spools[]}` |
| `/spoolman/use` | POST | `{url, spoolId, grams}` → deducts weight from a spool via Spoolman's REST API |
| `/auto-backup` | POST | Same payload shape as manual Backup → writes a deduped, retained dated snapshot to `Backups/` |

### Frontend
- Single `<script>` block in `index.html`. Section anchors: `// ── SECTION NAME ──────`
- Three tracks: Design (labor), FDM (machine+filament), Resin (machine+material)
- Stats recomputed from raw session data on every render — no cached totals

---

## Data structures

```js
// Project (ar_tracker_v1 → data.projects[])
{
  id, name, scope, created,
  status?,           // 'active' | 'on-hold' | 'complete' — sidebar dot color
  trackFdm?,         // boolean, default true (absent = on) — gates FDM auto punch in/out from printer polling
  trackResin?,       // boolean, default true (absent = on) — gates Resin auto punch in/out from printer polling
  designSessions: [{
    id, start, end,
    manual?,           // true = logged manually
    designSubtype?     // 'designing' | 'modeling' | 'post-processing'
  }],
  fdmSessions: [{
    id, start, end,
    manual?, auto?,    // auto = started/stopped by Moonraker
    printerId?,        // links session to a specific printer in settings.fdmPrinters
    filamentG,         // grams used (saved after material modal)
    filamentType,      // e.g. 'PLA'
    filamentCostPerKg,
    filamentUsedMm?,   // raw mm from Moonraker — used to calc grams
    slicerFilamentType?, slicerFilamentName?,  // from Moonraker metadata
    spoolmanSpoolId?, spoolmanSpoolName?       // linked Spoolman spool — grams deducted on save
  }],
  resinSessions: [{
    id, start, end,
    manual?,
    printerId?,        // links session to a specific printer in settings.resinPrinters
    resinMl, resinType, resinCostPerKg, resinDensity
  }],
  receipts: [{ id, desc, amount }]
}

// Settings (ar_tracker_settings)
{
  laborRate, fdmRate, resinRate,
  fdmPrinters:   [{ id, name, moonrakerUrl }],  // synced to printers.json via /update-printers
  resinPrinters: [{ id, name, moonrakerUrl }],
  filamentTypes: [{ name, costPerKg, densityGPerCm3 }],
  resinTypes:    [{ name, costPerKg, densityGPerMl }],
  spoolman:      { url }                        // optional — base URL of a Spoolman instance
}
```

---

## Cost model

| Track | Formula |
|---|---|
| Design | `hours × laborRate` |
| FDM machine | `hours × fdmRate` |
| FDM filament | `(grams / 1000) × filamentCostPerKg` |
| Resin machine | `hours × resinRate` |
| Resin material | `(mL × densityGPerMl / 1000) × resinCostPerKg` |
| Receipts | flat dollar sum |

Filament mm→grams: `π × (0.0875cm)² × (mm/10) × densityGPerCm3` (1.75mm diameter)

---

## UI layout

```
Sidebar (260px)                Main
────────────────────────────   ─────────────────────────────────────────────
Logo (100px)                   Topbar: title / scope / Edit / Export / Delete
[+ New Project]  [⚙ Settings]  ─────────────────────────────────────────────
─────────────────────────────  Clock Area (3 cols):
Project list (scrollable)        Design (btn+DES/MDL/PST code) | FDM (btn+MAT) | Resin (btn+MAT)
─────────────────────────────  Stats Bar (6 cells)
[⬇ Backup]  [⬆ Restore]        Panels (4 cols): Design | FDM | Resin | Receipts
                               ─────────────────────────────────────────────
                               Footer: © AR LLC (link) | ❤️ Claude Code | v9.0
```

---

## Key behaviors

**Design punch-in**: Opens subtype picker (Designing / Modeling / Post-Processing) before
starting clock. `DES`/`MDL`/`PST` code shown below button in accent purple. Clickable
mid-session to switch. Subtype stored as `designSubtype` on session, shown as tag in log.

**FDM/Resin punch-out**: Auto-opens Material Modal to log filament/resin. FDM gets
Moonraker-calculated gram hint if `filamentUsedMm` is present and a density is known.

**Moonraker auto-sessions**: `idle→printing` = FDM punch in (backdated by `print_duration`
on first poll). `printing→idle/complete/error` = punch out + material modal.
12+ consecutive unreachable polls → dot goes red (offline). Fewer → dot dims but no transition.
With multiple printers, each is tracked independently via `processPrinterState()`.

**Multi-printer cards**: When 2+ FDM or Resin printers configured, the main punch button is
hidden and compact printer cards render below the clock track — one per printer, each with
its own status dot, live timer, and Start/Stop button. Single-printer = no change to layout.

**Startup project picker**: `projectPickerModal` blocks the UI on every load until a project
is chosen or created — replaces the old behavior of silently auto-selecting `data.projects[0]`,
which could resume printer auto-tracking into the wrong project after a refresh. Non-dismissable
(same pattern as `firstRunModal`). Zero projects → skips straight to New Project.

**Per-project auto-tracking toggle**: Checkbox next to the FDM/Resin status indicators sets
`trackFdm`/`trackResin` on the active project (absent = on). Gates only the automatic
printer-driven punch-in/out in `processPrinterState()` — manual punch buttons and
printer-connectivity/offline monitoring still run regardless.

**Resume bar**: If printer is printing but FDM track is not running, amber bar appears in
FDM panel with "Resume Tracking" button.

**Export modal** (topbar "Export" button):
- `Invoice — Actual` / `Invoice — + Markup` → opens styled HTML invoice in new window
- `Tracking Log` + format selector (`.ods` / `.xlsx` / `.csv`) → ODS/XLSX POST to
  `/generate-ods` or `/generate-xlsx` and download the returned file; CSV is built
  client-side (no server round-trip)
- Markup default: **3%**
- Reduced Rate: $30/hr for Design Labor (invoice only)

**ODS/XLSX export** (5 tabs each): Summary | Design | FDM | Resin | Receipts
- Both formats render the same dataset from `build_tracking_log()` — session rows
  sorted by date + subtotals block (by subtype or material)
- Summary: per-track totals → Subtotal → Markup → Grand Total
- Header rows: dark bg / light text (matches app palette) in both formats
- ODS: `style:use-optimal-column-width="true"` (LibreOffice respects this)
- XLSX: inline strings (no sharedStrings.xml), numFmt currency/number cell styles

**Backup/Restore**: Sidebar footer buttons. Backup exports both localStorage keys to
dated JSON. Restore reads file, confirms, writes both keys, reloads. Used for
localhost→Docker migration and general data safety.

**Auto-backup**: Silent safety net for the manual Backup button — the only backup that
existed before Beta 10.7.0 was whatever the user remembered to click. `autoBackup()` fires
once on load and every 6h while the app stays open (`AUTO_BACKUP_INTERVAL_MS`), POSTing the
same payload shape as manual Backup to `/auto-backup`. The server (`auto_backup()` in
server.py) writes a dated snapshot to `Backups/`, skips the write if it's byte-identical to
the last snapshot (no bloat from an idle app), and prunes down to the newest
`AUTO_BACKUP_RETAIN` (30) files. Works regardless of `storageMode` — local-storage-only
installs get the same protection as file-storage installs. Sidebar footer shows a small
"🛟 auto-backup HH:MM" line (same row style as the file-sync indicator) after each
successful run; throttle timestamp lives in `localStorage['ar_tracker_last_autobackup']`.

**Spoolman integration** (Settings → "Spoolman" section, optional): URL field + "Test
Connection" button (proxied through `/spoolman/check` to avoid browser CORS — same reason
Moonraker is polled server-side). When set, the FDM material modal fetches the spool list
(`/spoolman/spools`) and shows a "Spoolman Spool" picker; selecting one + saving grams fires
`/spoolman/use` to deduct that weight from the spool's remaining weight (server proxies a
`PUT /api/v1/spool/{id}/use` with `use_weight`). Linked spool name is stored on the session
(`spoolmanSpoolId`/`spoolmanSpoolName`) and shown as a green 🧵 tag in the session log.
A `_spoolmanLogged` flag prevents re-deducting on subsequent edits/saves of the same session.
No Spoolman configured/reachable → picker stays hidden, app behaves exactly as before.

---

## Printer integration

- **Hardware**: Neptune 4 Plus, Klipper + Moonraker at `192.168.0.74`
- **Slicer**: OrcaSlicer (PrusaSlicer-based)
- **Printer UI**: Fluidd
- Moonraker `filament_type`/`filament_name` fields are empty for OrcaSlicer files (and some
  other slicers Moonraker's metadata parser doesn't recognize) → server.py falls back to
  `material_from_filename()` regex parse on the filename (e.g. `Base_0.2mm_PLA_Neptune4Plus.gcode`
  → `PLA`)
- `FILENAME_MATERIAL_PATTERNS` in server.py: ordered list, longer matches first to avoid
  `PLA` matching before `PLA-CF`; covers 30+ codes spanning PrusaSlicer, OrcaSlicer, Bambu
  Studio, Cura, SuperSlicer, and others (engineering blends like `PA6-CF`/`PC-FR`/`PEKK`
  included) — slicer-agnostic by design, since it only scans the filename string

### Moonraker / OctoPrint auto-detection

Both backends are configured through the same single **Printer URL** field — no "printer
type" picker. `_split_printer_url()` in server.py looks for a `?apikey=...` query string
(OctoPrint's own documented way to pass an API key): present → poll as OctoPrint
(`poll_octoprint`, hits `/api/job` with `X-Api-Key`); absent → poll as Moonraker
(`poll_moonraker`, hits `/printer/objects/query?print_stats`, no key needed). `poll_printer()`
is the dispatcher. OctoPrint doesn't expose slicer filament metadata, so its material type
always comes from `material_from_filename()`. Both pollers normalize into the same
`printer_states[pid]` shape (`status`, `filename`, `print_duration`, `filament_used`,
`filament_type`/`filament_name`, `estimated_time`, `reachable`) — the frontend
(`processPrinterState()`) is completely backend-agnostic and only checks `status === 'printing'`
for auto punch in/out.

### Formlabs (Dashboard Cloud API)

Formlabs SLA printers (Form 3/4/etc.) expose no LAN status endpoint for third parties —
unlike Moonraker/OctoPrint, live status only comes from Formlabs' internet-hosted
Dashboard Cloud API, for printers registered to a formlabs.com account. Configured via the
same Printer URL field using a distinct scheme: `formlabs://SERIAL?client_id=...&client_secret=...`
(OAuth client credentials from `dashboard.formlabs.com/#developer`). `poll_printer()` detects
the `formlabs://` prefix and routes to `_parse_formlabs_url()` + `poll_formlabs()` instead of
`_split_printer_url()`. `poll_formlabs()`:

- Exchanges client_id/secret for a bearer token at `/developer/v1/o/token/`, caching it in
  `_formlabs_tokens` until near-expiry (tokens last ~24h) to avoid re-authing every poll
- Fetches `/developer/v1/printers/{serial}/`, maps `printer_status.current_print_run.status`
  (`PRINTING`/`FINISHED`/etc.) to the same `printing`/`complete`/`error`/`idle` vocabulary
  the frontend expects, converts Formlabs' millisecond durations to the seconds convention
  Moonraker uses
- Throttled to `FORMLABS_POLL_INTERVAL` (30s, vs. the 5s `POLL_INTERVAL` used for
  Moonraker/OctoPrint) to respect Formlabs' documented rate limit (1500 req/hr/user) — it
  self-skips most ticks of the shared poll loop by checking `last_checked`
- No filament/resin material metadata is exposed by the API, so `filament_type`/`filament_used`
  stay empty — resin material entry in the material modal remains fully manual, same as before

---

## Filament library (`filament-library.json`)

Fetched once on load via `loadFilamentLibrary()`. Stored in `filamentLibrary[]`.
- Used to populate the "add from library" picker in Settings
- On load: backfills `densityGPerCm3` on any saved filament types that lack it
- `slug` field → `https://filament.thenextlayer.com/?f={slug}` (? button in settings)
- 50 materials; null slug = no thenextlayer page exists for it

---

## Modals

All modals: `<div class="modal-backdrop" id="xModal">` → `.classList.add('open')` to open,
`closeModal('xModal')` to close. ESC key closes all. Backdrop click closes project/settings.

| Modal ID | Purpose |
|---|---|
| `projectModal` | New / edit project |
| `settingsModal` | Rates, filament types, resin types, filament library picker |
| `manualModal` | Log manual time for any track |
| `subtypeModal` | Design subtype picker (punch-in + mid-session switch) |
| `materialModal` | Log filament (FDM) or resin after punch-out; includes session time editor |
| `editSessionModal` | Edit start/end times + subtype for completed Design sessions |
| `exportModal` | Invoice / ODS export options |
| `formlabsModal` | Guided Formlabs printer credential entry (Name/Serial/Client ID/Client Secret), opened from Settings' Resin Printers section |
| `projectPickerModal` | Blocking startup project chooser (same non-dismissable pattern as `firstRunModal`), shown on every load until a project is picked or created |

---

## Design tokens (CSS vars)

```css
--bg: #0e0e0f          /* page background */
--surface / --surface2 / --surface3   /* layered surfaces */
--border / --border2                  /* borders */
--text: #e8e8ec        /* primary text */
--muted: #7a7a86       /* secondary text */
--dim: #4a4a54         /* tertiary / disabled */
--accent: #7f77dd      /* purple — Design track */
--green-bright: #5dcaa5  /* FDM track */
--blue-bright: #85b7eb   /* Resin track */
--amber: #ef9f27       /* receipts / expenses */
--red: #e24b4a         /* danger / stop */
--mono: 'IBM Plex Mono'
--sans: 'IBM Plex Sans'
```

Footer color: `#636370` (between `--dim` and `--muted`).
Design subtype colors: designing=`var(--accent)`, modeling=`#a077dd`, post-processing=`#c4a0f0`.

---

## server.py structure

```python
SERVER_VERSION  = "1.8"
TRACKER_VERSION = "Beta 10.6.0"
POLL_INTERVAL   = 5   # seconds

# Launcher env overrides (all unset for launch.bat / Docker / standalone EXE — Electron sets them):
#   AR_PORT          bind a launcher-chosen port instead of 5757
#   AR_NO_BROWSER    don't open the system browser
#   AR_NO_AUTOUPDATE don't git-pull + self-restart (launcher owns updates)
#   AR_DATA_DIR      writable dir for config/data (install dir may be read-only)
#   AR_PARENT_PID    self-exit when this PID dies (no orphaned server on parent crash)

# Key globals:
printers_config   # {fdm:[{id,name,moonrakerUrl}], resin:[...]} — hot-reloadable via /update-printers
printer_states    # {printerId: {status,filename,...}} — keyed per-printer state

# Key functions (in order):
material_from_filename(filename)               # word-boundary regex fallback (slicer-agnostic)
fetch_metadata(printer_id, base_url, filename) # Moonraker metadata → falls back to filename parse
_split_printer_url(url)                        # (base_url, api_key) — apikey query param ⇒ OctoPrint
poll_moonraker(printer, base_url)              # polls Moonraker's print_stats, updates printer_states
poll_octoprint(printer, base_url, api_key)     # polls OctoPrint's /api/job, updates printer_states
poll_printer(printer)                          # dispatches to the right poller, updates printer_states
poll_all_printers()                            # background thread, loops all configured printers
_pid_alive(pid) / watch_parent(ppid)          # parent-PID watchdog (AR_PARENT_PID) — self-exit if parent dies
load_printers_config() / save_printers_config()# reads/writes printers.json
build_tracking_log(payload)                    # shared data model — returns 5 tabs of (kind,value,style) cells
_render_ods(tabs)                              # renders tabs to an ODS ZIP (content/manifest/styles XML)
_render_xlsx(tabs)                             # renders tabs to an XLSX ZIP (OOXML, inline strings, numFmt styles)
generate_ods(payload)                          # build_tracking_log() → _render_ods() → bytes
generate_xlsx(payload)                         # build_tracking_log() → _render_xlsx() → bytes
auto_backup(payload)                           # dated+deduped snapshot to Backups/, prunes to AUTO_BACKUP_RETAIN
class Handler(SimpleHTTPRequestHandler):
    do_POST()   # /update-printers + /generate-ods + /generate-xlsx + /auto-backup endpoints
    do_GET()    # /printer-status (keyed by printer ID) + static files
    end_headers()  # injects Cache-Control: no-cache for .html/.js/.css/.json
    log_message()  # suppressed
```

---

## Docker deployment

```powershell
# On the Windows 11 server — one-time setup:
git clone https://github.com/ScottBatemanAZ/AR-TimeTracker.git
cd AR-TimeTracker
docker compose up -d

# Deploy after changes:
git pull && docker compose restart
```

- Container mounts source dir as volume → HTML/JS/CSS changes live on hard refresh
- Python changes require `docker compose restart`
- `DOCKER=1` env var suppresses browser auto-open
- Moonraker at 192.168.0.74 is reachable from container via normal bridge networking

---

## Known issues / open items

| Issue | Status |
|---|---|
| Ctrl+C not stopping server on Windows | signal handlers added in v7.9 — user still reports sometimes not working; may be terminal-specific |
| Hard refresh not always picking up changes | Cache-Control headers added in v7.9; should be fixed — verify after Docker deploy |
| ODS decimal places | User reported "got more numbers" after v8.2.2 fix; needs re-test after LibreOffice restart (was mid-update) |
| Proton Sheets ODS rendering | PS is in beta, opened blank — revisit when PS matures |

---

## Pending features (not yet built)

| Feature | Notes |
|---|---|
| **Proton Drive integration** | Waiting for public Proton Drive API |
| **Configurable branding** | config.json for logo, colors, company name — for self-hosters; server serves /app-config, frontend applies on load |
| **Hosted version (SaaS)** | Requires full backend DB rewrite (localStorage won't work multi-user); Moonraker integration breaks without local agent or VPN/tunnel solution (Tailscale, Cloudflare Tunnel, etc.) — different product, not a deployment change |
| **Client-side DB for hosted** | File System Access API or IndexedDB as a local data store — "website is just the UI, data lives on the user's machine"; meaningful data layer refactor but same UI; solves privacy/cost concerns for hosted; Moonraker still needs tunnel |

---

## Claude Code workflow notes

- **Version bumps**: After any significant feature or code update, automatically bump the version number (footer in `index.html`, `TRACKER_VERSION` in server.py if changed, `**Current version:**` and footer ref in this file, version history table) and commit. No need to ask first.
- **CLAUDE.md updates**: Keep this file current after every session — move shipped features from Pending to version history, update modal table, fix any stale references.

---

## Version history

| Version | Summary |
|---|---|
| v1–v4 | Initial build → dual timers → FDM+Resin split → manual time + filament types |
| v5.0–v5.1 | Resin mL+density; AR branding; desktop shortcut |
| v6.0–v6.2 | Moonraker auto FDM; filament density; offline detection |
| v7.0 | Invoice export (actual / +markup) |
| v7.1 | Reduced rate export ($30/hr); markup default → 3% |
| v7.2 | Moonraker polling implemented in frontend (was undocumented/missing) |
| v7.3–v7.4 | External filament-library.json; thenextlayer.com ? button |
| v7.5 | Moonraker mm→grams auto-calculation in material modal |
| v7.6–v7.8 | Mat code (3-char) under FDM/Resin buttons; live filamentType from poll |
| v7.9 | Filename material fallback (OrcaSlicer); Ctrl+C fix; no-cache headers |
| v8.0 | Design sub-types (Designing/Modeling/Post-Processing); DES/MDL/PST code |
| v8.1 | Subtype font matches mat-code; site footer; server version in startup |
| v8.2 | ODS tracking log export (5 tabs, server-side Python zipfile+XML) |
| v8.2.1 | ODS column auto-width |
| v8.2.2 | 2 decimal places consistency (cpkg, density display) |
| v8.3 | Footer polish (font, color, azazelsrazer.com link); ODS flush fix |
| v8.4 | Docker support (Dockerfile, docker-compose.yml, .dockerignore) |
| v8.5 | JSON backup/restore (sidebar footer buttons) |
| v8.6 | Global stats bar above clock area — all-projects totals (hours + billed) |
| v8.7 | Editable session times — time editor in material modal (FDM/Resin) + dedicated edit modal for Design sessions |
| v8.8 | Project status dots in sidebar — Active (green/pulses), On Hold (red), Complete (gray); click to cycle |
| v9.0 | Multi-printer support — Settings UI, per-printer session stamping, keyed Moonraker polling, printer cards in FDM/Resin clock tracks |
| Beta v9.1 | Nested project folders — parent projects with sub-projects; rollup summary view; resin library (12 types) with density sources card; versioning prefixed Beta |
| Beta v9.2 | Electricity cost tracking — $/kWh rate in Settings, per-printer wattage (inline editable), elec cost in stats bar (⚡ sub-line), FDM/Resin ODS tabs + Summary |
| Beta v9.3 | Failed print logging — "⚠ log failed print" on FDM/Resin tracks; creates session with failed:true; red badge + left border in session log; excluded from invoices; ⚠FAILED marked in ODS |
| Beta v9.4 | Session notes — optional note field on all session types (material modal + design edit modal); italic sub-line in session log; Note column in all ODS tabs |
| Beta v9.5 | CSV export — flat session dump (Design + FDM + Resin) as downloadable .csv; "Tracking Log (.csv)" button in Export modal; pure frontend, no server needed |
| Beta v9.6 | Client field on projects — optional Client input in project modal; stored as `client` on project; auto-fills invoice Bill To on Export modal open |
| Beta v9.7 | Time estimates — Settings toggle (`showEstimates`); FDM `estimatedSecs` auto-captured from Moonraker `estimated_time` at punch-in; Design `estimatedHours` field per project; Est / Actual shown in parent summary table |
| Beta v9.8 | ODS failed print cost lines — Summary tab shows blank row + "Failed FDM/Resin Prints -$x" below Grand Total when failed sessions exist; cost tracked, not billed |
| Beta 10.0.0 | Sidebar search, keyboard shortcuts, running cost badge — live filter in sidebar; Space/N/E/? shortcuts; amber cost badge in topbar ticks with active timers |
| Beta 10.0.1 | Export modal persistent — stays open after each export; X close button (top-right) to dismiss when done; Cancel closes without exporting; Bill To cached per project in memory |
| Beta 10.1.0 | Project archiving — complete projects show orange ✓ in sidebar; clicking archives with paid flag; archive panel (box icon, muted orange, next to ⚙) lists archived projects with ✓✓ in green; Restore button to unarchive; sticky sidebar footer (Backup/Restore) and app footer always visible via height:100vh shell layout |
| Beta 10.2.0 | Configurable storage — first-run modal on new installs chooses localStorage vs server file storage; server writes ar-data-live.json (1s debounced auto-sync on every saveData/persistSettings); Restore also syncs to server; .gitignore added (config.json, Logs/); Server v1.4 |
| Beta 10.2.1 | QoL polish — sync indicator in sidebar footer (file mode only); Storage section in Settings shows current mode + Reconfigure button reopens first-run modal; stale version string in syncToServer/confirmFirstRun fixed (TRACKER_VERSION const); git-not-found in server.py now prints instead of silently passing; README updated to current feature set |
| Beta 10.2.2 | Release packaging — GitHub Actions workflow builds ZIP + EXE on tag push; PyInstaller spec (AR-TimeTracker.spec) with frozen-mode path split (STATIC_DIR/DATA_DIR); GitHub releases API update check with in-app ⬆ badge in footer; improved launch.bat with Python detection; VERIFY.md with checksum + SmartScreen docs; Server v1.5 |
| Beta 10.2.7 | Fast browser launch — `open_browser()` polls socket until server accepts connections (no more 15-20s blank-browser wait on EXE startup); first-run confirm button disables with "Starting…" to prevent multi-clicks; suppress `ConnectionAbortedError [WinError 10053]` console spam in ZIP mode |
| Beta 10.2.8 | Self-hosted fonts — IBM Plex Mono (400/500/600) and IBM Plex Sans (300–500 variable) bundled in `fonts/`; eliminates render-blocking Google Fonts request; page loads instantly in incognito and offline |
| Beta 10.2.9 | Clean startup log — `CalledProcessError` replaced with readable "Not a git repo" message; 404 from GitHub API shows "No GitHub release published yet"; `launch.bat` title uses `--` to avoid garbled em-dash in OEM console |
| Beta 10.2.10 | `open_browser()` uses `127.0.0.1` instead of `localhost` (skips Windows IPv6-first DNS delay on cold start); `QuietTCPServer` suppresses WinError 10053 / BrokenPipe tracebacks at the server level |
| Beta 10.3.0 | First-run onboarding wizard (storage → branding → settings); `applyBranding()` sets sidebar logo/name, page title, accent CSS var, invoice header; `DEFAULT_SETTINGS` rates/printers zeroed; `setupComplete` flag detects existing installs; no default printer in server `DEFAULT_PRINTERS` |
| Beta 10.3.1 | Tax rate on invoices — configurable `taxRate`/`taxLabel` in Settings, applied as a line item on generated invoices |
| Beta 10.4.0 | Spoolman integration — Settings → Spoolman URL + Test Connection (proxied via `/spoolman/check` to dodge CORS, like Moonraker); FDM material modal gets a spool picker (`/spoolman/spools`) that deducts logged grams from the spool's remaining weight on save (`/spoolman/use` → Spoolman `PUT /spool/{id}/use`); linked spool shown as 🧵 tag in session log; fully optional — hidden when not configured. OctoPrint support — same single Printer URL field auto-detects Moonraker vs OctoPrint via a `?apikey=...` query string (`_split_printer_url`/`poll_octoprint`, polls `/api/job` with `X-Api-Key`), no new settings UI needed. Broadened slicer/material detection — `FILENAME_MATERIAL_PATTERNS` now covers 30+ codes spanning PrusaSlicer, OrcaSlicer, Bambu Studio, Cura, SuperSlicer, etc. |
| Beta 10.4.1 | `_split_printer_url` auto-prepends `http://` to printer URLs entered without a scheme (e.g. a bare `192.168.0.74`) — previously caused `urlopen` to throw on a malformed URL, silently marked the printer "unreachable" with no log trail; Server v1.6 |
| Beta 10.5.0 | XLSX tracking-log export — `/generate-xlsx` (OOXML SpreadsheetML via stdlib zipfile, inline strings, numFmt currency/number styles) joins `/generate-ods`, both built from a new shared `build_tracking_log()` data model (5 tabs of generic `(kind,value,style)` cells) consumed by `_render_ods`/`_render_xlsx`; export modal's two Tracking Log buttons replaced with one "Tracking Log" button + `.ods`/`.xlsx`/`.csv` format selector; Server v1.7 |
| Beta 10.6.0 | Electron desktop app — optional native wrapper in `electron/` that spawns the existing `server.py`/PyInstaller binary (zero backend porting); system tray (minimize-to-tray, live tooltip), native notifications (auto punch-out, printer-offline), window-state persistence, auto-launch-on-login toggle (Settings → Desktop App), single-instance lock; `electron-builder` NSIS installer (per-user, no admin, bundles the server binary — needs no Python/Node on the target). New `server.py` launcher env hooks: `AR_PORT` / `AR_NO_BROWSER` / `AR_NO_AUTOUPDATE` / `AR_DATA_DIR` / `AR_PARENT_PID` (parent-PID watchdog — server self-exits if the wrapper crashes, no orphaned port). Fixed a latent Windows `os.execv` bug in the git auto-update restart (spaces in the path broke the relaunch). All renderer hooks feature-detected via `window.electronAPI`, so browser/Docker are unchanged; Server v1.8 |
| Beta 10.7.0 | Automatic backups — the manual ⬇ Backup button was the only backup mechanism (one stale file in `Backups/` was 16 days old); `autoBackup()` now fires silently on load + every 6h while the app stays open, POSTing the same payload shape as manual Backup to new `/auto-backup` endpoint; `auto_backup()` in server.py writes a dated snapshot, skips the write if byte-identical to the last one, prunes to newest `AUTO_BACKUP_RETAIN` (30); works under both storage modes; sidebar footer shows "🛟 auto-backup HH:MM" after each run; Server v1.9 |
| Beta 10.8.0 | Formlabs printer support (Resin Printers) — Formlabs SLA printers have no LAN status endpoint like Moonraker/OctoPrint, so status now polls Formlabs' Dashboard Cloud API instead; configured via the same Printer URL field with a new scheme, `formlabs://SERIAL?client_id=...&client_secret=...` (OAuth client credentials from dashboard.formlabs.com); `poll_printer()` routes `formlabs://` URLs to new `poll_formlabs()` (OAuth token exchange + caching, `printer_status.current_print_run.status` mapped to the existing printing/idle/complete/error vocabulary, ms→s duration conversion), throttled to 30s polling (vs. 5s for Moonraker/OctoPrint) to respect Formlabs' rate limits; frontend unchanged — `processPrinterState()` was already backend-agnostic; Server v1.10 |
| Beta 10.9.0 | Settings modal section headers color-coded by track (green=FDM, blue=Resin, amber=Rates, magenta=Branding, orange=Spoolman/Storage/Desktop App). Formlabs credential popout — new `formlabsModal` (Name/Serial/Client ID/Client Secret fields) replaces raw `formlabs://...` URL text entry in Settings' Resin Printers section; builds the URL via `encodeURIComponent`, shows a compact `🧪 Formlabs · SN...` row instead of the raw URL, masks the secret on re-edit (blank + `••••••••` placeholder — leave blank to keep, type to replace). Blocking startup project picker — new `projectPickerModal` shown on every load (non-dismissable, same pattern as `firstRunModal`: excluded from the Escape-key and backdrop-click close lists), replacing the old auto-select-`data.projects[0]` behavior that could silently resume printer auto-tracking into the wrong project after a refresh; zero projects skips straight to New Project. Per-project auto-tracking toggle — new optional `trackFdm`/`trackResin` project fields (absent = on, preserving existing behavior) surfaced as a checkbox next to the FDM/Resin status indicators; gates only the automatic printer-driven punch-in/out inside `processPrinterState()` — manual punch buttons and offline/connectivity monitoring are unaffected. No server.py changes; Server v1.10 |
| Beta 10.10.0 | Master resin library — resin-library.json expanded from 12 generic entries to an 84-material brand-tagged catalog (48 Formlabs SLA resins with real per-SKU mechanical specs + printer/tank compatibility sourced from Formlabs' product pages/TDS, plus family-level entries for Anycubic/Elegoo/Siraya Tech/Phrozen/HeyGears, original 12 kept as brand:"Generic"). Formlabs printer settings gain optional Printer Model + Installed Tank fields (guided setup modal); material modal shows a non-blocking amber warning when a picked resin's required tank doesn't match what's set as installed. Flat resin picker replaced with a searchable/brand-filterable library browser modal. No server.py changes. |
