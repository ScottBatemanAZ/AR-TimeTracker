# Azazel's Razer — Time Tracker

Self-contained, locally-served time tracker for a 3D printing/design LLC. Vanilla HTML/CSS/JS
front-end served by a Python stdlib HTTP server. No framework, no build step, no database.

---

## Files

| File | Purpose |
|---|---|
| `index.html` | Entire application — HTML + CSS + JS, ~1300 lines |
| `server.py` | Python stdlib HTTP server (port 5757) + Moonraker polling thread |
| `launch.bat` | Start server and open browser (`py -3 server.py`) |
| `ARLogo-FullTrans.png` | Full logo — dark background, 100px tall in sidebar |
| `ARSymbol.png` / `.ico` | Symbol variant used for desktop shortcut icon |
| `timetracker_handoff.md` | Full architecture and decision history |
| `patch.py` | Last session's patch script — can be deleted or ignored |
| `CLAUDE.md` | This file |

**Project root:** `D:\timetracker\`

---

## Running the app

```
python server.py        # starts on http://localhost:5757
# or just double-click launch.bat
```

Reload the browser tab to pick up HTML/JS changes — no build step.

---

## Architecture

### Storage
- All project data in `localStorage` under key `ar_tracker_v1`
- Settings in `localStorage` under `ar_tracker_settings`
- No server-side persistence. Python server serves static files + proxies printer status only.

### Server
- `server.py` polls Moonraker (Neptune 4 Plus at `192.168.0.74`) every 5s in a background thread
- Exposes `/printer-status` → `{ status, filename, print_duration, filament_used, reachable, last_checked }`
- Everything else is `SimpleHTTPRequestHandler` serving the project directory

### Frontend
- Single-page app in `index.html`
- Three time tracks: Design (labor), FDM (machine), Resin (machine)
- Sessions stored as `{ id, start, end, manual?, auto? }` plus material fields per type
- Stats recomputed from raw session data on every render — no cached totals

---

## Data structures

```js
// Project
{
  id, name, scope, created,
  designSessions: [{ id, start, end, manual? }],
  fdmSessions:    [{ id, start, end, manual?, auto?, filamentG, filamentType, filamentCostPerKg }],
  resinSessions:  [{ id, start, end, manual?, resinMl, resinType, resinCostPerKg, resinDensity }],
  receipts:       [{ id, desc, amount }]
}

// Settings
{
  laborRate, fdmRate, resinRate,
  filamentTypes: [{ name, costPerKg, densityGPerCm3 }],
  resinTypes:    [{ name, costPerKg, densityGPerMl }]
}
```

`auto: true` on fdmSessions = started/stopped by Moonraker integration. Only auto sessions are
eligible for auto punch-out. Manual sessions are never auto-closed.

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
| **Project total** | all of the above |

Filament mm→grams (from Moonraker auto-sessions): `π × (0.0875cm)² × (mm/10) × densityGPerCm3`
Assumes 1.75mm diameter.

---

## UI layout

```
Sidebar (260px)          Main
─────────────────────    ─────────────────────────────────────────────
Logo                     Topbar: title / scope / Edit / Export Invoice / Delete
[+ New Project] [⚙]     ─────────────────────────────────────────────
Project list             Clock Area (3 cols): Design | FDM | Resin
                         Stats Bar (6 cells): per-track costs + grand total
                         Panels (4 cols, scrollable): Design | FDM | Resin | Receipts
```

---

## Key behaviors

**Punch in/out**: Clicking a track button starts/stops a session. FDM and Resin clockout
auto-opens the Material Modal to log filament/resin used.

**Manual time**: "＋ log manual time" link under each clock. Creates a completed session
ending now, starting N hours/minutes ago. Tagged `manual: true`.

**Moonraker auto-sessions**: FDM track auto punches in/out based on printer state transitions.
`idle → printing` = punch in. `printing → idle/complete/error` = punch out + material modal.
Unreachable state (< 12 consecutive failures) dims the dot but doesn't trigger transitions.

**Invoice export** (v7.0): "Export Invoice" button in topbar opens a modal with Bill To,
Invoice #, dates, markup %, and notes fields. Two export modes:
- "Export — Actual": subtotal only
- "Export — + Markup": adds a "Service Fee (N%)" line, default 1.5%
Opens a styled HTML invoice in a new window. "Print / Save PDF" fires browser print dialog.
Only completed sessions are included (active sessions excluded from invoice totals).

---

## Printer integration

- **Hardware**: Neptune 4 Plus, Klipper + Moonraker, IP `192.168.0.74`
- **Slicer**: OrcaSlicer (PrusaSlicer-based — embeds filament metadata in G-code)
- **Printer UI**: Fluidd (Klipper web interface, separate from this tracker)
- **Mapped to**: FDM track only
- **Resin printer**: no network interface — no auto integration
- Moonraker print_stats endpoint: `GET /printer/objects/query?print_stats`
- Fields used: `state`, `filename`, `print_duration` (seconds), `filament_used` (mm extruded)
- Moonraker metadata endpoint: `GET /server/files/metadata?filename={filename}`
- Fields used: `filament_type`, `filament_name` (slicer-embedded, OrcaSlicer format)

---

## Modals

All modals follow the same pattern:
```html
<div class="modal-backdrop" id="someModal">
  <div class="modal">...</div>
</div>
```
Opened with `document.getElementById('someModal').classList.add('open')`.
Closed with `closeModal('someModal')` (removes the class).
ESC key closes all open modals.

---

## Design tokens (CSS vars)

```css
--bg: #0e0e0f          /* page background */
--surface / surface2 / surface3   /* layered UI surfaces */
--accent: #7f77dd      /* purple — Design track */
--green-bright: #5dcaa5  /* FDM track */
--blue-bright: #85b7eb   /* Resin track */
--amber: #ef9f27       /* receipts / expenses */
--red: #e24b4a         /* danger / stop */
--mono: 'IBM Plex Mono'
--sans: 'IBM Plex Sans'
```

Invoice window uses a separate light-themed stylesheet (white body, `--dark: #0e0e0f` header,
`--red: #b01e22` accent).

---

## Editing index.html

Claude Code can edit `index.html` directly with standard file tools — no workarounds needed.

**When editing JS**: The file has a single `<script>` block. Key section anchors use
`// ── SECTION NAME ──────` comments with U+2500 box-drawing characters.

**Known gotcha**: The `edit_file` MCP tool (claude.ai web interface) eats `$` characters
when they appear before certain chars in replacement strings (e.g. `$'+variable`). This is
a claude.ai-specific issue and does not affect Claude Code. In Claude Code, edit files
directly or write Python patch scripts — both work reliably.

---

## Version history

| Version | Summary |
|---|---|
| v1–v4 | Initial build → dual timers → FDM+Resin split → manual time + filament types |
| v5.0–v5.1 | Resin mL+density tracking; AR branding; desktop shortcut |
| v6.0–v6.2 | Moonraker auto FDM integration; filament density; hardened offline detection |
| v7.0 | Invoice export with two modes (actual / +markup) |

---

## Potential next features (not built)

- JSON backup/restore (export all localStorage data to file, import it back)
- Multi-project totals / reporting view
- Editable session start/end times (currently fixed at creation)
