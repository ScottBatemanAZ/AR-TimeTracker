# Azazel's Razer — Time Tracker

Self-contained time tracker for a 3D printing/design LLC. Vanilla HTML/CSS/JS front-end
served by a Python stdlib HTTP server. No framework, no build step, no database.

**Current version:** Beta 10.2.1 | **Server:** v1.4
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
    slicerFilamentType?, slicerFilamentName?  // from Moonraker metadata
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
  resinTypes:    [{ name, costPerKg, densityGPerMl }]
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

**Resume bar**: If printer is printing but FDM track is not running, amber bar appears in
FDM panel with "Resume Tracking" button.

**Export modal** (topbar "Export" button):
- `Invoice — Actual` / `Invoice — + Markup` → opens styled HTML invoice in new window
- `Tracking Log (.ods)` → POSTs to `/generate-ods`, downloads ODS file
- Markup default: **3%**
- Reduced Rate: $30/hr for Design Labor (invoice only)

**ODS export** (5 tabs): Summary | Design | FDM | Resin | Receipts
- Each data tab: session rows sorted by date + subtotals block (by subtype or material)
- Summary: per-track totals → Subtotal → Markup → Grand Total
- Header rows: `#26262b` bg / `#e8e8ec` text (matches app palette)
- Column auto-width: `style:use-optimal-column-width="true"` (LibreOffice respects this)

**Backup/Restore**: Sidebar footer buttons. Backup exports both localStorage keys to
dated JSON. Restore reads file, confirms, writes both keys, reloads. Used for
localhost→Docker migration and general data safety.

---

## Printer integration

- **Hardware**: Neptune 4 Plus, Klipper + Moonraker at `192.168.0.74`
- **Slicer**: OrcaSlicer (PrusaSlicer-based)
- **Printer UI**: Fluidd
- Moonraker `filament_type`/`filament_name` fields are empty for OrcaSlicer files →
  server.py falls back to `material_from_filename()` regex parse on the filename
  (e.g. `Base_0.2mm_PLA_Neptune4Plus.gcode` → `PLA`)
- `FILENAME_MATERIAL_PATTERNS` in server.py: ordered list, longer matches first to avoid
  `PLA` matching before `PLA-CF`

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
SERVER_VERSION  = "1.2"
TRACKER_VERSION = "9.0"
POLL_INTERVAL   = 5   # seconds

# Key globals:
printers_config   # {fdm:[{id,name,moonrakerUrl}], resin:[...]} — hot-reloadable via /update-printers
printer_states    # {printerId: {status,filename,...}} — keyed per-printer state

# Key functions (in order):
material_from_filename(filename)               # word-boundary regex fallback for OrcaSlicer
fetch_metadata(printer_id, base_url, filename) # Moonraker metadata → falls back to filename parse
poll_printer(printer)                          # polls one Moonraker instance, updates printer_states
poll_all_printers()                            # background thread, loops all configured printers
load_printers_config() / save_printers_config()# reads/writes printers.json
generate_ods(payload)                          # builds ODS ZIP from project+settings JSON
class Handler(SimpleHTTPRequestHandler):
    do_POST()   # /update-printers + /generate-ods endpoints
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
