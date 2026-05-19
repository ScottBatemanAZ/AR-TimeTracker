# Azazel's Razer Time Tracker — Session Handoff

## Context
This document picks up a development session for a locally-hosted time tracking application built for Azazel's Razer, LLC. The app was built iteratively across multiple conversations and is fully functional as of this handoff.

---

## What Was Built

A self-contained, locally-served time tracker running via a Python HTTP server launched by a BAT file. No external dependencies, no database — all data lives in browser `localStorage`.

### Files — all located at `R:\Azazel's Razer\timetracker\`
| File | Purpose |
|---|---|
| `index.html` | The entire application (HTML + CSS + JS) |
| `server.py` | Python HTTP server on port 5757 + Moonraker polling thread |
| `launch.bat` | Tries `py -3` first, falls back to `python`; opens browser automatically |
| `CreateShortcut.ps1` | Run once with `powershell -ExecutionPolicy Bypass -File` to recreate desktop shortcut |
| `ARLogo-FullTrans.png` | Full logo displayed in sidebar at 100px height |
| `ARSymbol.png` | Symbol/icon version of the logo |
| `ARSymbol.ico` | Multi-resolution ICO (16/24/32/48/64/128/256px), built manually via Python struct to avoid Pillow's broken ICO output |
| `Azazel's Razer Time Tracker.lnk` | Desktop shortcut on `C:\Users\sageo\Desktop` pointing to `launch.bat` with `ARSymbol.ico` |

> **Icon note:** The `.lnk` stores the icon as a path reference to `ARSymbol.ico`, not baked-in. If `R:\Azazel's Razer\timetracker` moves, recreate the shortcut with `CreateShortcut.ps1`.

> **pip note:** pip works fine on this machine. Use normally. `uv run --with <package>` is not needed here.

---

## Application Architecture

### Data Storage
- All data in browser `localStorage` under key `ar_tracker_v1`
- Settings stored under `ar_tracker_settings`
- No server-side persistence — Python server serves static files and proxies printer status
- Old `jnb_tracker_v2` key migrates automatically on first load

### Project Data Structure
```json
{
  "projects": [{
    "id": "string",
    "name": "string",
    "scope": "string",
    "created": 1234567890,
    "designSessions": [{ "id", "start", "end", "manual?" }],
    "fdmSessions":    [{ "id", "start", "end", "manual?", "auto?", "filamentG", "filamentType", "filamentCostPerKg" }],
    "resinSessions":  [{ "id", "start", "end", "manual?", "resinMl", "resinType", "resinCostPerKg", "resinDensity" }],
    "receipts":       [{ "id", "desc", "amount" }]
  }]
}
```

> `auto: true` on fdmSessions means the session was started/stopped by the Moonraker integration, not manually. Only auto sessions are eligible for auto punch-out.

### Settings Structure
```json
{
  "laborRate": 40,
  "fdmRate": 5,
  "resinRate": 2,
  "filamentTypes": [
    { "name": "PLA",  "costPerKg": 20, "densityGPerCm3": 1.24 },
    { "name": "PLA+", "costPerKg": 25, "densityGPerCm3": 1.24 },
    { "name": "Wood", "costPerKg": 32, "densityGPerCm3": 1.28 },
    { "name": "TPU",  "costPerKg": 38, "densityGPerCm3": 1.21 },
    { "name": "ASA",  "costPerKg": 28, "densityGPerCm3": 1.07 },
    { "name": "ABS",  "costPerKg": 22, "densityGPerCm3": 1.04 }
  ],
  "resinTypes": [
    { "name": "Standard",       "costPerKg": 13, "densityGPerMl": 1.10 },
    { "name": "ABS-Like",       "costPerKg": 17, "densityGPerMl": 1.15 },
    { "name": "High-Toughness", "costPerKg": 24, "densityGPerMl": 1.12 },
    { "name": "Nylon-Like",     "costPerKg": 30, "densityGPerMl": 1.12 },
    { "name": "High-Clear",     "costPerKg": 36, "densityGPerMl": 1.10 },
    { "name": "Flexible",       "costPerKg": 31, "densityGPerMl": 1.15 },
    { "name": "High-Temp 300C", "costPerKg": 60, "densityGPerMl": 1.18 }
  ]
}
```

---

## Cost Model

### Design Time
`hours × laborRate ($40/hr default)`

### FDM Printer
- **Machine cost:** `hours × fdmRate ($5/hr default)`
- **Filament cost:** `(grams / 1000) × filamentCostPerKg`
- Per-session filament type and $/kg stored on session (override global)
- Fallback $/kg: $20 if session has no rate stored

### Resin Printer
- **Machine cost:** `hours × resinRate ($2/hr default)`
- **Material cost:** `(mL × densityGPerMl / 1000) × resinCostPerKg`
- Backward compat: old sessions with flat `resinCost` field still display correctly
- Density defaults to 1.10 g/mL if not stored

### Filament mm → grams conversion (Moonraker auto-sessions)
`grams = π × (0.0875cm)² × (mm / 10) × densityGPerCm3`
- Assumes 1.75mm diameter filament
- Density pulled from the selected filament type in settings
- Recalculates live if you change filament type in the material modal

### Receipts
Flat dollar line items. Summed directly.

### Project Total
`Design Labor + FDM Machine + FDM Filament + Resin Machine + Resin Material + Receipts`

---

## UI Layout

```
┌─ Sidebar (260px) ──────┬─ Main ──────────────────────────────────────┐
│ Logo (100px)           │ Topbar: project name/scope + Edit/Delete    │
│ [+ New Project] [⚙]   ├─────────────────────────────────────────────┤
│                        │ Clock Area (3 columns)                       │
│ Project list           │  [Design ●]  [FDM ●]    [Resin ●]          │
│  name                  │  timer       timer       timer               │
│  Xh design · Xh fdm   │              printer dot + manual            │
│  · $total              ├─────────────────────────────────────────────┤
│                        │ Stats Bar (6 cells)                          │
│                        │  Design$ | FDM Machine$ | FDM Filament$     │
│                        │  Resin Machine$ | Resin Mat$ | Total$       │
│                        ├─────────────────────────────────────────────┤
│                        │ Panels (4 columns, scrollable)               │
│                        │  Design | FDM | Resin | Receipts            │
└────────────────────────┴─────────────────────────────────────────────┘
```

---

## Moonraker / Printer Integration

### Printer
- **Neptune 4 Plus** running Klipper + Moonraker
- **IP:** `192.168.0.74`
- **Mapped to:** FDM track only

### server.py polling
- Background thread polls `http://192.168.0.74/printer/objects/query?print_stats` every 5 seconds
- Timeout: 8 seconds per request
- Exposes `/printer-status` endpoint returning JSON: `{ status, filename, print_duration, filament_used, reachable, last_checked }`
- `print_duration`: seconds of active print time (pauses excluded)
- `filament_used`: mm of 1.75mm filament extruded

### Frontend polling
- Polls `/printer-status` every 5 seconds, 1.5s after page load
- **Failure handling:** unreachable responses never trigger state transitions; UI dot only goes red after 12 consecutive failures (~60 seconds)
- Failure counter resets on any successful response

### State transitions
| Transition | Action |
|---|---|
| First poll + already printing | Auto punch-in FDM, backdated by `print_duration` seconds |
| idle → printing | Auto punch-in FDM at current time |
| printing → complete/error/cancelled/standby | Auto punch-out FDM, open material modal with grams pre-filled |
| unreachable (< 12 polls) | UI dot dims, no state change |
| unreachable (≥ 12 polls) | UI dot goes red |

### Auto session rules
- Auto punch-out only fires on sessions tagged `auto: true` — manual sessions are never auto-closed
- Material modal pre-fills grams from Moonraker `filament_used` using selected filament density
- Changing filament type in the modal recalculates grams with correct density
- `_autoFilamentMm` temp field is cleaned from localStorage on material save

---

## Key Behaviors

### Punch In/Out
- Circular buttons per track; active state highlighted, hover turns red to stop
- FDM and Resin clockout auto-opens the **Material Modal**
- All three tracks run independently and simultaneously

### Manual Time Entry
- `＋ log manual time` link under each clock
- Enter hours + minutes; live preview shows duration + cost
- Creates session with `end = now`, `start = now - duration`
- Tagged `manual: true` in session log
- FDM/Resin manual entries also trigger material modal
- Manual sessions are never auto-closed by printer integration

### Material Modal (FDM)
- Filament type dropdown (from settings)
- Auto-fills $/kg and density from preset; all fields user-overridable
- Grams field with live cost preview
- Machine cost shown as hint

### Material Modal (Resin)
- Resin type dropdown (from settings)
- Auto-fills $/kg and density g/mL from preset
- mL field; live preview: `mL × g/mL = g → $`

### Session Log
- Per session: timestamp range, duration, machine cost (large, colored)
- Material line: type · amount → cost
- `edit` link re-opens material modal for completed sessions
- Delete button (✕) per session

### Settings (⚙)
- Labor, FDM machine, Resin machine hourly rates
- Filament types: name + $/kg + g/cm³ density (add/remove)
- Resin types: name + $/kg + g/mL density (add/remove)
- Changes apply immediately

---

## Known Limitations / Potential Next Features
- No data export (JSON backup/restore would be straightforward)
- No print/invoice generation
- No multi-machine sync (localStorage is browser+machine specific)
- Resin density on existing sessions stored at time of entry — changing type preset doesn't retroactively update old sessions (intentional)
- Printer integration maps to FDM only — resin printer has no network interface

---

## Technology
- Vanilla HTML/CSS/JS — no framework, no build step
- Fonts: IBM Plex Mono + IBM Plex Sans via Google Fonts (requires internet on load)
- Python `http.server` + `urllib` + `threading` (stdlib only)
- ICO built with Python `struct` + `Pillow` (manual write, not Pillow's ICO save which was broken)
- All editing done via Claude

---

## Version History
| Version | Changes |
|---|---|
| v1.0 | Initial build: single timer, receipts, localStorage |
| v2.0 | Split Design / Print timers; py -3 bat fix |
| v3.0 | Split Print into FDM + Resin; separate cost models; settings modal |
| v4.0 | Manual time entry; filament/resin type management; session $ font size increase |
| v5.0 | Resin mL + density tracking; resin types as objects with $/kg + g/mL |
| v5.1 | Logo → Azazel's Razer LLC; ARSymbol.ico created; desktop shortcut added |
| v6.0 | Moonraker integration: auto FDM punch-in/out, printer status dot, startup backdate |
| v6.1 | Filament density added to types; mm→g conversion on auto sessions; pre-fill in material modal |
| v6.2 | Offline detection hardened: 8s timeout, unreachable never triggers transitions, 12-poll threshold |
| v7.0 | Invoice export: topbar button opens modal (Bill To, Invoice #, dates, markup %, notes). Two export modes: Actual and +Markup (configurable %, default 1.5%). Opens styled HTML invoice in new window — dark header with AR logo, IBM Plex fonts, line items grouped by type (filament/resin), service fee row on markup version, Print/Save PDF button. Only completed sessions included. |
| current | patch.py pattern established for future edits (write script via FileSystem tool, run via PowerShell) |
