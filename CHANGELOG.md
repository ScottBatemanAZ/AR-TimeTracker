# Changelog

All notable changes to AR Time Tracker are documented here.

---

## Beta 10.2.10
- **Instant first load** — browser now opens to `http://127.0.0.1:5757` instead of `localhost`, bypassing the Windows IPv6-first DNS lookup that caused a multi-second delay on every cold start.
- **Silent connection errors** — WinError 10053 / BrokenPipe / ConnectionReset tracebacks no longer flood the console; suppressed at the server level via a custom `handle_error` override.

## Beta 10.3.0
- **First-run onboarding wizard** — new installs now walk through three steps: storage selection, branding setup, then Settings auto-opens so rates can be configured before use.
- **Branding** — business name, logo upload (stored as base64), and accent color are configurable from both the first-run wizard and Settings. Applied immediately to sidebar, page title, and invoice header/footer.
- **Clean new-install defaults** — all rates start at $0, no printers pre-configured, no assumed business name. Existing installs are automatically detected and skipped past the setup flow.
- **Configurable accent color** — one color picker in Settings controls the primary accent (Design track, buttons, highlights) with live preview on save.

## Beta 10.2.9
- **Clean startup log** — ZIP/source mode no longer shows the raw `CalledProcessError` when run outside a git repo; shows "Not a git repo — skipping auto-update" instead. GitHub 404 (no release published yet) shows "No GitHub release published yet" instead of an HTTP error string.
- **Fixed console title** — `launch.bat` title command now uses `--` instead of an em-dash, preventing garbled `ΓÇö` characters in the Windows terminal tab title.

## Beta 10.2.8
- **Self-hosted fonts** — IBM Plex Mono and IBM Plex Sans are now bundled with the app instead of loaded from Google Fonts. Page renders instantly in all browsers (including incognito), works fully offline, and no longer leaks page-load events to Google.

## Beta 10.2.7
- **Instant browser launch** — the EXE now waits until the server is actually accepting connections before opening the browser, eliminating the 15-20 second blank-page wait on first startup.
- **First-run modal loading state** — "Confirm & Continue" button disables immediately on click and shows "Starting…" so users know something is happening and don't double-click.
- **Cleaner console output** — harmless `ConnectionAbortedError [WinError 10053]` errors (browser closing the connection) are no longer printed to the console in ZIP/git mode.

## Beta 10.2.2
- **Windows EXE** — standalone executable, no Python required. Download and double-click.
- **ZIP release** — distributable archive for users with Python already installed.
- **Automated releases** — pushing a version tag builds both artifacts via GitHub Actions and publishes them as a GitHub Release with SHA-256 checksums attached.
- **In-app update badge** — footer shows "⬆ vX.X.X available" when a newer release is detected on GitHub.
- **Improved launch.bat** — detects missing Python and shows a friendly install prompt with the python.org URL.
- **VERIFY.md** — documents how to verify checksums and why Windows SmartScreen warns about unsigned EXEs.
- **Error logging** — startup crashes now write `ar-error.log` next to the executable and pause the console so the error is readable.

## Beta 10.2.1
- **Sync indicator** — sidebar footer shows last sync time ("📁 synced HH:MM") when using file storage mode.
- **Storage section in Settings** — shows current mode and a "Reconfigure…" button that reopens the first-run modal.
- **Version constant** — introduced `TRACKER_VERSION` JS const; fixed stale hardcoded version string in server sync payloads.
- **Startup log** — git-not-found now prints a message instead of silently passing.

## Beta 10.2.0
- **Configurable storage** — first-run modal on new installs lets you choose between browser localStorage and server file storage.
- **File storage** — data saved as `ar-data-live.json` on the server; auto-syncs every save (1-second debounce); survives browser clears; accessible from any browser on the network.
- **Restore sync** — restoring a backup in file mode pushes the restored data to the server before reloading.

## Beta 10.1.0
- **Project archiving** — complete projects show an orange ✓ in the sidebar; clicking it archives the project with a paid flag. An archive panel (box icon) lists all archived projects with a Restore button.
- **Persistent export modal** — stays open after each export; X button to dismiss when done.
- **Sticky layout** — sidebar footer (Backup/Restore) and app footer always visible via 100vh shell layout.

## Beta 10.0.0 – 10.0.1
- **Sidebar search** — live filter projects by name.
- **Keyboard shortcuts** — Space (punch Design), N (new project), E (export), ? (help overlay).
- **Running cost badge** — amber dollar amount in the topbar ticks up in real time while any timer is running.
- **Export modal persistent** — stays open after each export; Cancel closes without exporting.
- **Bill To cached** — invoice Bill To field remembers the last value per project.

## Beta 9.8
- Failed print costs shown in ODS Summary tab — blank row + "Failed FDM/Resin Prints -$x" below Grand Total when failed sessions exist.

## Beta 9.7
- **Time estimates** — Settings toggle to show estimates. FDM estimates auto-captured from Moonraker `estimated_time`; Design estimates set per-project. Est vs Actual shown in parent summary table.

## Beta 9.6
- **Client field** — optional client name on projects, auto-fills the invoice Bill To field.

## Beta 9.5
- **CSV export** — flat session dump (Design + FDM + Resin) as a downloadable `.csv`. Pure frontend, no server required.

## Beta 9.4
- **Session notes** — optional note field on all session types (material modal + design edit modal). Shown as italic sub-line in session log. Note column in all ODS tabs.

## Beta 9.3
- **Failed print logging** — "⚠ log failed print" link on FDM/Resin tracks. Creates a session with `failed: true`. Red badge + left border in session log. Excluded from invoices. ⚠FAILED marked in ODS.

## Beta 9.2
- **Electricity cost tracking** — $/kWh rate in Settings, per-printer wattage (inline editable), electricity cost in stats bar (⚡ sub-line) and FDM/Resin ODS tabs + Summary.

## Beta 9.1
- **Nested project folders** — parent projects with sub-projects; rollup summary view with Est/Actual columns.
- **Resin library** — 12 built-in resin types with density sources card.

## v9.0
- **Multi-printer support** — configure multiple FDM or Resin printers. Each polls independently via Moonraker. Compact printer cards appear in the clock area when 2+ printers are configured, each with its own status dot, live timer, and Start/Stop button.

## v8.8
- **Project status dots** — Active (green, pulses when a timer is running), On Hold (red), Complete (gray). Click to cycle.

## v8.7
- **Editable session times** — time editor in the material modal (FDM/Resin) and a dedicated edit modal for Design sessions.

## v8.6
- **Global stats bar** — aggregate hours and total billed across all active projects, always visible above the clock area.

## v8.5
- **Backup / Restore** — sidebar footer buttons. Backup exports both localStorage keys to a dated JSON file. Restore reads the file, confirms, writes both keys, and reloads.

## v8.4
- **Docker support** — Dockerfile, docker-compose.yml, .dockerignore. One command to run on any server.

## v8.2 – v8.3
- **ODS tracking log export** — 5-tab spreadsheet (Summary, Design, FDM, Resin, Receipts) generated server-side in Python. Column auto-width. Decimal consistency fixes.

## v8.0 – v8.1
- **Design subtypes** — tag sessions as Designing, Modeling / CAD, or Post-Processing. Switch mid-session. DES/MDL/PST code shown under the punch button.
- Site footer with azazelsrazer.com link and Claude Code credit.

## v7.0 – v7.9
- Invoice export (Actual and +Markup variants). Reduced rate ($30/hr) option.
- External filament library JSON with thenextlayer.com links.
- Moonraker mm→grams auto-calculation in material modal.
- 3-character material code under FDM/Resin buttons.
- Filename material fallback for OrcaSlicer files.
- No-cache headers so hard refresh always picks up changes.

## v6.0 – v6.2
- Moonraker auto punch-in/out (backdated using `print_duration`).
- Filament density support.
- Offline detection (red dot after 12 consecutive unreachable polls).

## v5.0 – v5.1
- Resin mL + density cost model.
- AR branding (logo, icon, desktop shortcut).

## v1.0 – v4.0
- Initial build: single Design timer → dual timers → FDM + Resin split → manual time entry + filament types.
