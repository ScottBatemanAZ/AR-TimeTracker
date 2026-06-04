# AR Time Tracker — Session Handoff

**Current version:** v9.0 | **Server:** v1.2  
**Project root:** `R:\Azazel's Razer\timetracker\`  
**Git remote:** https://github.com/ScottBatemanAZ/AR-TimeTracker (private)  
**CLAUDE.md** is the authoritative reference — read it first. This file captures session context and next-instance notes.

---

## What was built this session

### Editable session times (v8.7)
- **Material modal** (FDM/Resin): purple divider + Start/End datetime-local inputs added below material fields. Adjusting times live-updates the machine cost hint. Saved alongside material data.
- **Edit Design Session modal** (`editSessionModal`): dedicated modal for completed Design sessions — Start, End, Work Type (subtype selector). Opened via "edit" button that now appears on every completed design session row.
- All completed FDM/Resin sessions always show an "edit" button on the material row (even if material was skipped).

### Polish (no version bump)
- Global stats bar values color-coded by track (purple/green/blue/muted gray)
- Global stats bar field labels bumped from `--dim` to `--muted` for readability
- Favicon wired up (`ARSymbol.ico` referenced in `<head>`)

### Project status dots (v8.8)
- Every project in sidebar has a colored status dot
- Active = `--green-bright` (pulses when a timer is running), On Hold = `--red`, Complete = `#9a9aaa`
- Click the dot to cycle: active → on-hold → complete → active
- `status` field added to project data structure (defaults to `'active'`)
- New projects default to `'active'`

### Multi-printer support (v9.0) — 3 staged commits
**Stage 1 — Settings & data model:**
- `fdmPrinters` / `resinPrinters` arrays added to settings: `[{id, name, moonrakerUrl}]`
- Neptune 4 Plus at `192.168.0.74` migrates in automatically as `fdm-0`
- Settings modal has new FDM Printers + Resin Printers sections (add/remove)
- Sessions stamped with `printerId` going forward

**Stage 2 — Server polling:**
- `server.py` refactored: hardcoded Moonraker URL replaced with `printers_config` dict
- `printer_state` (single) → `printer_states` keyed by printer ID
- `poll_moonraker()` → `poll_all_printers()` iterating all configured printers
- `/printer-status` now returns `{printerId: {status, filename, ...}, ...}`
- New `/update-printers` POST endpoint — saves `printers.json`, hot-reloads config
- `saveSettingsModal()` POSTs printer config to `/update-printers` on save

**Stage 3 — UI cards:**
- 1 printer configured = exactly current behavior, no visible change
- 2+ printers = main punch button hidden; compact printer cards stack below clock track
- Each card: status dot (pcard-dot), printer name, live timer, Start/Stop button
- `togglePrinterPunch(type, printerId)` — per-printer punch in/out
- `processPrinterState()` — extracted from pollPrinter; handles auto punch-in/out per printer
- `prevPrinterStatuses` / `printerUnreachCounts` — dicts keyed by printer ID
- `isClockedInFor(proj, type, printerId)` — checks active session for specific printer
- `updateResumeBar()` / `resumePrintTracking()` — multi-printer aware

### README.md
- Full GitHub README written and committed — features, quick start, cost model, tech stack, version history (collapsed for early versions), roadmap

### Wishlist additions (CLAUDE.md pending features)
- Configurable branding (config.json for self-hosters)
- Hosted SaaS version (requires full backend DB rewrite; Moonraker needs VPN/tunnel)
- Client-side DB for hosted (File System Access API or IndexedDB)

---

## User preferences / workflow notes

- **Auto version bumps**: bump footer, TRACKER_VERSION, CLAUDE.md header, version history, commit — no need to ask. Documented in CLAUDE.md workflow notes.
- **Staged builds for big features**: user prefers "do it right in stages" over patching. v9.0 was deliberately 3 commits.
- **No need to ask** before committing polish/housekeeping changes.
- **Repo is private** for now — goes public eventually with a proper copyleft license (TBD, leaning GPL-3.0). "All rights reserved" placeholder in README until then.
- User runs the app on a vertical monitor; the second printer will likely be a resin printer.

---

## Architecture reminders for next session

- `index.html` is the entire frontend — single `<script>` block with `// ── SECTION NAME ──` anchors
- `server.py` is pure stdlib Python — no pip installs needed
- `printers.json` is auto-created on first Settings save — not committed (machine-specific)
- The `/printer-status` response is now a **keyed dict** `{printerId: state}`, not a flat object
- Multi-printer poll state: `prevPrinterStatuses[pid]` and `printerUnreachCounts[pid]` (dicts)
- Single-printer behavior is fully preserved — the new code only activates when `printers.length > 1`

---

## Known issues / open items

| Issue | Status |
|---|---|
| Ctrl+C not stopping server on Windows | Intermittent; may be terminal-specific |
| ODS decimal places | Needs re-test after LibreOffice full restart |
| Proton Sheets ODS rendering | PS was in beta and opened blank — revisit when mature |
| Screenshot missing from README | Would significantly improve GitHub presence |

---

## Suggested next session starting points

- **Session notes** — freetext field per session (user was noodling on how they want to use it)
- **Docker deploy** — user hasn't actually deployed to Docker yet; `git clone` + `docker compose up -d` on the Windows 11 server
- **Screenshot for README** — grab one while the app is running, add to repo
- **License decision** — user wants copyleft before going public; GPL-3.0 is the leading candidate
