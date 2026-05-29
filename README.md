# AR Time Tracker

**Self-hosted time & cost tracker for 3D printing and design work.**  
Built for a one-person LLC that runs FDM printers, a resin printer, and does design/modeling work — and needs to know exactly what a job costs before writing an invoice.

![Version](https://img.shields.io/badge/version-v9.0-7f77dd?style=flat-square)
![Python](https://img.shields.io/badge/python-3.12-blue?style=flat-square&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)
![No Framework](https://img.shields.io/badge/frontend-vanilla_JS-f7df1e?style=flat-square&logo=javascript&logoColor=black)
![No Database](https://img.shields.io/badge/storage-localStorage-orange?style=flat-square)

---

## What it does

Three parallel time tracks — **Design**, **FDM**, and **Resin** — each with their own cost model. Punch in, punch out, log materials, and at the end you have a real cost breakdown and a ready-to-send invoice. No cloud dependency, no account, no subscription.

If you run Klipper/Moonraker on your FDM printer, the tracker can punch itself in and out automatically when a print starts and finishes.

---

## Features

### Time Tracking
- **Three independent tracks** — Design (labor), FDM (machine + filament), Resin (machine + material)
- **Punch in / punch out** with a single click per track
- **Manual time entry** — log time after the fact for any track
- **Editable session times** — fix start/end timestamps on any completed session
- **Design subtypes** — tag sessions as Designing, Modeling / CAD, or Post-Processing; switch mid-session

### Cost Calculation
- Configurable hourly rates for Design, FDM machine time, and Resin machine time
- FDM filament cost: grams used × $/kg, with a material library of 50+ filaments (densities included)
- Resin material cost: mL × density × $/kg
- Receipts / expense log per project
- Live running totals update every second while clocked in

### Moonraker Integration
- Polls your Klipper/Moonraker endpoint every 5 seconds
- **Auto punch-in** when a print starts (backdates to actual print start using `print_duration`)
- **Auto punch-out** when the print finishes, with a prompt to log filament used
- Reads filament type from G-code metadata; falls back to filename parsing for OrcaSlicer files
- Online/printing/offline status dot in the UI
- **Multi-printer support** — configure multiple FDM or Resin printers, each polling independently with their own status cards

### Projects
- Unlimited projects, switch instantly from the sidebar
- **Status tags** — Active (green, pulses when running), On Hold (red), Complete (gray); click to cycle
- **Global stats bar** — aggregate hours and total billed across every project, always visible

### Export
- **Invoice — Actual** — clean HTML invoice, opens in a new tab, ready to print or save as PDF
- **Invoice — + Markup** — same invoice with a configurable markup percentage (default 3%)
- **Tracking Log (.ods)** — full session export with 5 tabs: Summary, Design, FDM, Resin, Receipts  
  *(works in LibreOffice Calc; Proton Sheets support pending their maturity)*
- **Reduced rate** option ($30/hr Design labor) for invoice exports

### Data & Settings
- All data lives in `localStorage` — nothing leaves your machine
- **Backup** — download a dated JSON snapshot of all projects and settings
- **Restore** — upload a backup to migrate between devices or recover data
- Material library: 50+ filaments with density and cost data, linkable to [thenextlayer.com](https://filament.thenextlayer.com) profiles

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Vanilla HTML + CSS + JS | No build step, no dependencies, hard refresh = deploy |
| Server | Python 3 stdlib (`http.server`) | Zero dependencies, runs anywhere Python runs |
| Storage | Browser `localStorage` | No database setup, no migrations, no data loss on restart |
| Containerization | Docker + Docker Compose | One command to run anywhere |

No npm. No webpack. No React. No database. The entire frontend is a single `index.html`.

---

## Quick Start

### Local (Python)

```bash
git clone https://github.com/ScottBatemanAZ/AR-TimeTracker.git
cd AR-TimeTracker
python server.py
```

Opens at **http://localhost:5757** automatically.  
Hard refresh (`Ctrl+Shift+R`) picks up any HTML/JS/CSS changes instantly.

### Docker

```bash
git clone https://github.com/ScottBatemanAZ/AR-TimeTracker.git
cd AR-TimeTracker
docker compose up -d
```

Opens at **http://localhost:5757**.

**To deploy updates:**
```bash
git pull && docker compose restart
```

> The container mounts the source directory as a volume — HTML/CSS/JS changes are live on hard refresh. Python (`server.py`) changes require a restart.

---

## Configuration

### Rates & Materials

Open **⚙ Settings** in the sidebar to configure:

- **Hourly rates** — Design labor, FDM machine time, Resin machine time
- **Filament types** — name, $/kg, density (g/cm³); add from the built-in library or enter custom
- **Resin types** — name, $/kg, density (g/mL)
- **Printers** — name and Moonraker URL for each FDM or Resin printer

Changes persist in `localStorage` and sync to `printers.json` on the server for polling.

### Moonraker / Multi-Printer

Add your printer(s) in Settings → **FDM Printers**:

| Field | Example |
|---|---|
| Name | Neptune 4 Plus |
| Moonraker URL | http://192.168.0.74 |

With one printer configured, the tracker behaves exactly as described — single punch button, automatic sessions.  
With two or more, each printer gets its own compact status card below the main clock, with independent tracking and status dots.

---

## Cost Model

| Track | Formula |
|---|---|
| Design | `hours × laborRate` |
| FDM machine | `hours × fdmRate` |
| FDM filament | `(grams / 1000) × filamentCostPerKg` |
| Resin machine | `hours × resinRate` |
| Resin material | `(mL × densityGPerMl / 1000) × resinCostPerKg` |
| Receipts | flat dollar sum |

Filament mm→grams (from Moonraker): `π × (0.0875 cm)² × (mm / 10) × densityGPerCm³`  
*(assumes 1.75mm diameter filament)*

---

## Version History

<details>
<summary>v1.0 – v8.1 (early builds)</summary>

| Version | Summary |
|---|---|
| v1–v4 | Initial build → dual timers → FDM+Resin split → manual time + filament types |
| v5.0–v5.1 | Resin mL+density model; AR branding; desktop shortcut |
| v6.0–v6.2 | Moonraker auto-FDM sessions; filament density; offline detection |
| v7.0 | Invoice export (actual / +markup) |
| v7.1 | Reduced rate ($30/hr); markup default → 3% |
| v7.3–v7.4 | External filament library JSON; thenextlayer.com links |
| v7.5 | Moonraker mm→grams auto-calculation in material modal |
| v7.6–v7.8 | 3-char material code under FDM/Resin buttons; live filament type from poll |
| v7.9 | Filename material fallback for OrcaSlicer; no-cache headers |
| v8.0 | Design subtypes (Designing / Modeling / Post-Processing) |
| v8.1 | Site footer; server version in startup log |

</details>

| Version | Summary |
|---|---|
| **v8.2** | ODS tracking log export — 5-tab spreadsheet, server-side Python |
| **v8.3** | Footer polish; ODS flush fix |
| **v8.4** | Docker support (Dockerfile, docker-compose.yml) |
| **v8.5** | JSON backup / restore (sidebar footer buttons) |
| **v8.6** | Global stats bar — all-projects aggregate totals, always visible |
| **v8.7** | Editable session times — time editor in material modal + dedicated Design session editor |
| **v8.8** | Project status dots — Active / On Hold / Complete, click to cycle |
| **v9.0** | Multi-printer support — per-printer settings, independent Moonraker polling, printer cards UI |

---

## Roadmap

| Feature | Status |
|---|---|
| Configurable branding (logo, colors, company name) for self-hosters | Planned |
| Proton Drive integration | Waiting on public API |

---

## Built With

Made with [Claude Code](https://claude.ai/claude-code) by Anthropic — the entire codebase was written collaboratively in Claude Code sessions, from the first line to v9.0.

---

## License

License TBD. All rights reserved in the meantime.
