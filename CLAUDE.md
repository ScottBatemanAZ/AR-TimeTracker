# Azazel's Razer — Time Tracker

Self-contained time tracker for a 3D printing/design LLC. Vanilla HTML/CSS/JS front-end
served by a Python stdlib HTTP server. No framework, no build step, no database.

**Current version:** v8.6 | **Server:** v1.1
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
  designSessions: [{
    id, start, end,
    manual?,           // true = logged manually
    designSubtype?     // 'designing' | 'modeling' | 'post-processing'
  }],
  fdmSessions: [{
    id, start, end,
    manual?, auto?,    // auto = started/stopped by Moonraker
    filamentG,         // grams used (saved after material modal)
    filamentType,      // e.g. 'PLA'
    filamentCostPerKg,
    filamentUsedMm?,   // raw mm from Moonraker — used to calc grams
    slicerFilamentType?, slicerFilamentName?  // from Moonraker metadata
  }],
  resinSessions: [{
    id, start, end,
    manual?,
    resinMl, resinType, resinCostPerKg, resinDensity
  }],
  receipts: [{ id, desc, amount }]
}

// Settings (ar_tracker_settings)
{
  laborRate, fdmRate, resinRate,
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
                               Footer: © AR LLC (link) | ❤️ Claude Code | v8.5
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
| `materialModal` | Log filament (FDM) or resin after punch-out |
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
SERVER_VERSION  = "1.1"
TRACKER_VERSION = "8.5"
MOONRAKER_IP    = "192.168.0.74"
POLL_INTERVAL   = 5   # seconds

# Key functions (in order):
material_from_filename(filename)  # word-boundary regex fallback for OrcaSlicer
fetch_metadata(filename)          # Moonraker metadata → falls back to filename parse
poll_moonraker()                  # background thread, updates printer_state dict
generate_ods(payload)             # builds ODS ZIP from project+settings JSON
class Handler(SimpleHTTPRequestHandler):
    do_POST()   # /generate-ods endpoint
    do_GET()    # /printer-status + static files
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
| **Editable session times** | Allow editing start/end timestamps on existing sessions |
| **Proton Drive integration** | Waiting for public Proton Drive API |

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
