# AR Time Tracker

**Self-hosted time & cost tracker for 3D printing and design work.**  
Built for a one-person LLC that runs FDM printers, a resin printer, and does design/modeling work — and needs to know exactly what a job costs before writing an invoice.

![Version](https://img.shields.io/badge/version-Beta_10.3.0-7f77dd?style=flat-square)
![Python](https://img.shields.io/badge/python-3.12-blue?style=flat-square&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)
![No Framework](https://img.shields.io/badge/frontend-vanilla_JS-f7df1e?style=flat-square&logo=javascript&logoColor=black)
![License](https://img.shields.io/badge/license-AGPL--3.0-green?style=flat-square)

---

![AR Time Tracker — active tracking with live costs](Screenshots/Screenshot%202026-06-06%20171547.png)

---

## Download

| Option | Best for | Requirements |
|--------|----------|--------------|
| 🪟 **[Windows EXE](https://github.com/ScottBatemanAZ/AR-TimeTracker/releases/latest)** | Simplest — just double-click | Nothing |
| 📦 **[ZIP archive](https://github.com/ScottBatemanAZ/AR-TimeTracker/releases/latest)** | Already have Python installed | Python 3.10+ |
| 🐳 **Docker** | Server / NAS / always-on | Docker Desktop |
| 🛠 **git clone** | Developers | Python + Git |

> **Windows EXE note:** Windows may show a SmartScreen warning because the EXE is not yet code-signed. See [VERIFY.md](VERIFY.md) for why this happens and how to confirm the file is safe before running it.

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
- **Session notes** — optional note on any session, shown in the log and exported to ODS
- **Failed print logging** — mark prints as failed; excluded from invoices, flagged in ODS export

### Cost Calculation
- Configurable hourly rates for Design, FDM machine time, and Resin machine time
- Electricity cost tracking — $/kWh rate + per-printer wattage
- FDM filament cost: grams used × $/kg, with a material library of 50+ filaments (densities included)
- Resin material cost: mL × density × $/kg
- Receipts / expense log per project
- Live running cost badge in the topbar while clocked in
- Live running totals update every second while clocked in

### Moonraker Integration
- Polls your Klipper/Moonraker endpoint every 5 seconds
- **Auto punch-in** when a print starts (backdates to actual print start using `print_duration`)
- **Auto punch-out** when the print finishes, with a prompt to log filament used
- Reads filament type from G-code metadata; falls back to filename parsing for OrcaSlicer files
- Online/printing/offline status dot in the UI
- **Multi-printer support** — configure multiple FDM or Resin printers, each polling independently with their own status cards
- Time estimate capture from Moonraker `estimated_time` metadata

### Projects
- Unlimited projects, switch instantly from the sidebar
- **Nested projects** — parent projects with sub-projects; rollup summary view
- **Status tags** — Active (green, pulses when running), On Hold (red), Complete (gray); click to cycle
- **Project archiving** — archive completed/paid projects; restore any time
- **Client field** — optional client name per project, auto-fills invoice Bill To
- **Global stats bar** — aggregate hours and total billed across all active projects, always visible
- **Sidebar search** — live filter projects by name
- **Keyboard shortcuts** — Space (punch in/out Design), N (new project), E (export), ? (help)

### Export
- **Invoice — Actual** — clean HTML invoice, opens in a new tab, ready to print or save as PDF
- **Invoice — + Markup** — same invoice with a configurable markup percentage (default 3%)
- **Tracking Log (.ods)** — full session export with 5 tabs: Summary, Design, FDM, Resin, Receipts  
  *(works in LibreOffice Calc)*
- **Tracking Log (.csv)** — flat session dump, no server required
- **Reduced rate** option ($30/hr Design labor) for invoice exports
- Export modal stays open after each export for easy multi-format downloads

### Data & Storage
- **First-run storage choice** — pick Browser (localStorage) or File (server JSON) on first launch
- **Browser storage** — all data lives in `localStorage`; no setup needed
- **File storage** — data saved as `ar-data-live.json` on the server; survives browser clears, accessible from any browser on the network; auto-syncs on every save (1s debounce)
- **Sync indicator** — sidebar shows last sync time when in file storage mode
- **Backup** — download a dated JSON snapshot of all projects and settings
- **Restore** — upload a backup to migrate between devices or recover data

---

![Settings modal showing rates, filament types, and printer configuration](Screenshots/Screenshot%202026-06-06%20171419.png)

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Vanilla HTML + CSS + JS | No build step, no dependencies, hard refresh = deploy |
| Server | Python 3 stdlib (`http.server`) | Zero dependencies, runs anywhere Python runs |
| Storage | Browser `localStorage` or server JSON file | Your choice on first run |
| Containerization | Docker + Docker Compose | One command to run anywhere |

No npm. No webpack. No React. No database. The entire frontend is a single `index.html`.

---

## Quick Start

### Windows EXE (no install required)

1. Download `AR-TimeTracker-vX.X.X.exe` from the [latest release](https://github.com/ScottBatemanAZ/AR-TimeTracker/releases/latest)
2. Double-click it — a console window opens and your browser launches automatically
3. If Windows SmartScreen warns you, click **More info → Run anyway** ([why?](VERIFY.md))

Data and config files are written to the same folder as the EXE.

### ZIP (Python required)

1. Download `AR-TimeTracker-vX.X.X.zip` from the [latest release](https://github.com/ScottBatemanAZ/AR-TimeTracker/releases/latest)
2. Extract the ZIP anywhere
3. Double-click `launch.bat` — it checks for Python and opens your browser automatically

If Python isn't installed, `launch.bat` will tell you where to download it.

### Git clone (developer / auto-update)

```bash
git clone https://github.com/ScottBatemanAZ/AR-TimeTracker.git
cd AR-TimeTracker
python server.py
```

Opens at **http://localhost:5757** automatically. Also accessible on your LAN at the IP shown in the startup log.  
Hard refresh (`Ctrl+Shift+R`) picks up any HTML/JS/CSS changes instantly.  
The server auto-pulls updates from git on every startup.

### Docker

```bash
git clone https://github.com/ScottBatemanAZ/AR-TimeTracker.git
cd AR-TimeTracker
docker compose up -d
```

Opens at **http://localhost:5757** (and your LAN IP on port 5757).

**To deploy updates:**
```powershell
git pull
docker compose restart
```

> The container mounts the source directory as a volume — HTML/CSS/JS changes are live on hard refresh. Python (`server.py`) changes require a restart.

**Auto-update:** The server checks for new commits from the remote on every startup. If behind, it pulls and re-launches itself automatically.

---

## Configuration

### Rates & Materials

Open **⚙ Settings** in the sidebar to configure:

- **Hourly rates** — Design labor, FDM machine time, Resin machine time, electricity $/kWh
- **Filament types** — name, $/kg, density (g/cm³); add from the built-in library or enter custom
- **Resin types** — name, $/kg, density (g/mL)
- **Printers** — name, Moonraker URL, and wattage for each FDM or Resin printer
- **Storage mode** — shown at the bottom of Settings; click "Reconfigure…" to switch modes

### Moonraker / Multi-Printer

Add your printer(s) in Settings → **FDM Printers**:

| Field | Example |
|---|---|
| Name | Neptune 4 Plus |
| Moonraker URL | http://192.168.0.10 |
| Watts | 350 |

With one printer configured, the tracker behaves exactly as described — single punch button, automatic sessions.  
With two or more, each printer gets its own compact status card below the main clock, with independent tracking and status dots.

### File Storage (Docker / LAN)

On first launch, a setup modal asks whether to use browser localStorage or server file storage.

- **Browser** — works immediately, no path needed. Use Backup/Restore to move data between machines.
- **File** — enter a directory path on the server (e.g. `/app/backups` in Docker). Data is written to `ar-data-live.json` in that directory and loaded on every page open. The sidebar shows a "synced HH:MM" indicator whenever a save completes.

To switch storage mode later: ⚙ Settings → Storage → **Reconfigure…**

---

## Cost Model

| Track | Formula |
|---|---|
| Design | `hours × laborRate` |
| FDM machine | `hours × fdmRate` |
| FDM filament | `(grams / 1000) × filamentCostPerKg` |
| FDM electricity | `hours × (watts / 1000) × electricityRate` |
| Resin machine | `hours × resinRate` |
| Resin material | `(mL × densityGPerMl / 1000) × resinCostPerKg` |
| Resin electricity | `hours × (watts / 1000) × electricityRate` |
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
| **Beta v9.1** | Nested project folders; resin library (12 types) with density sources |
| **Beta v9.2** | Electricity cost tracking — $/kWh rate, per-printer wattage, ⚡ cost in stats + ODS |
| **Beta v9.3** | Failed print logging — ⚠ badge, excluded from invoices, flagged in ODS |
| **Beta v9.4** | Session notes — optional note on all session types, shown in log and ODS |
| **Beta v9.5** | CSV export — flat session dump, no server required |
| **Beta v9.6** | Client field on projects — auto-fills invoice Bill To |
| **Beta v9.7** | Time estimates — FDM from Moonraker, Design per-project; Est vs Actual in summary |
| **Beta v9.8** | Failed print costs in ODS Summary tab |
| **Beta 10.0.0** | Sidebar search, keyboard shortcuts, running cost badge in topbar |
| **Beta 10.0.1** | Export modal stays open; X to dismiss; Bill To cached per project |
| **Beta 10.1.0** | Project archiving — archive/restore completed projects; sticky sidebar footer |
| **Beta 10.2.0** | Configurable storage — first-run modal chooses localStorage vs server file; auto-sync with sync indicator; storage mode visible in Settings with Reconfigure button; Server v1.4 |
| **Beta 10.2.1** | Sync indicator, storage section in Settings, TRACKER_VERSION const, git-not-found logging |
| **Beta 10.2.2** | Windows EXE + ZIP releases via GitHub Actions, in-app update badge, error logging, VERIFY.md |
| **Beta 10.2.7** | Instant browser launch on EXE startup, first-run loading state, cleaner console output |
| **Beta 10.2.8** | Self-hosted fonts — IBM Plex bundled locally, instant load in all browsers, fully offline |
| **Beta 10.2.9** | Clean startup log — readable messages for non-git installs and pre-release update checks; fixed garbled console title in launch.bat |
| **Beta 10.2.10** | Instant first load — opens to 127.0.0.1 to skip Windows IPv6 delay; silent connection-close errors in console |
| **Beta 10.3.0** | First-run onboarding wizard — storage → branding (name, logo, accent color) → Settings auto-opens; clean zero defaults for new installs |

See [CHANGELOG.md](CHANGELOG.md) for full details.

---

## Roadmap

| Feature                  | Status                |
|--------------------------|-----------------------|
| Proton Drive integration | Waiting on public API |

---

## Building from Source (EXE)

If you prefer not to trust a pre-built binary, build the EXE yourself:

```bash
pip install pyinstaller
pyinstaller AR-TimeTracker.spec
# Output: dist/AR-TimeTracker.exe
```

The result is functionally identical to the release EXE — same source, same spec.

## Releasing a New Version

Push a version tag to trigger the automated GitHub Actions build:

```powershell
git tag v10.3.0
git push origin v10.3.0
```

GitHub Actions will:
1. Build a distributable ZIP (Linux runner)
2. Build a Windows EXE via PyInstaller (Windows runner)
3. Generate SHA-256 checksums for both
4. Publish a GitHub Release with all three files attached

---

## Built With

Made with [Claude Code](https://claude.ai/claude-code) by Anthropic — the entire codebase was written collaboratively in Claude Code sessions, from the first line to the current release.

---

## License

[AGPL-3.0](LICENSE) — free to use, modify, and self-host. If you distribute a modified version (including over a network), you must publish the source under the same license.
