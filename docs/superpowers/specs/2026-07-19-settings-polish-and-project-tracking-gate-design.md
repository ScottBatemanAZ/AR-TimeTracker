# Settings polish + project-scoped printer tracking

Date: 2026-07-19
Status: Approved, not yet implemented

## Problem

Two related annoyances surfaced while using the app day to day:

1. **Settings page is visually flat.** Nine section headers (Branding, Hourly
   Rates, Filament Types, Resin Types, FDM Printers, Resin Printers, Spoolman,
   Storage, Desktop App) all render in the same plain text color, making the
   modal harder to scan. Separately, adding a Formlabs printer requires
   hand-typing a `formlabs://SERIAL?client_id=...&client_secret=...` string
   into a single text field — error-prone (a stray `<>` from a copy-paste
   placeholder already caused a live bug) and it dumps the client secret in
   plain text into the printer list row.

2. **Printer auto-tracking can silently attach to the wrong project.**
   `processPrinterState()` already requires `activeProject` to be truthy
   before it will auto punch-in/out — but `index.html:3235` auto-selects
   `data.projects[0]` on every page load. So a refresh while a printer is
   mid-print silently resumes auto-tracking into whatever project happens to
   be first in the array, not necessarily the one the user intends. There's
   also no way to tell a specific project "never auto-track printers for me,"
   which matters when working on something unrelated to whatever happens to
   be printing.

## Goals

- Settings section headers colored by track/category for faster scanning.
- Formlabs credentials entered via a small dedicated form instead of a raw
  URL string; secret not redisplayed in plain text after first save.
- No project's printer sessions get auto-populated until the user explicitly
  picks (or creates) a project after a page load.
- Per-project, per-track switch to disable auto-tracking entirely, for
  projects that should never be touched by printer state changes.

## Non-goals

- No change to OctoPrint's `?apikey=...` display/masking — only Formlabs gets
  the popout/masking treatment.
- No encryption of credentials at rest — `printers.json` remains a plain
  local config file, same trust model as today (OctoPrint API keys are
  already stored the same way).
- No `server.py` changes. Everything here is `index.html` (+ 2 new CSS vars).
- No per-printer (as opposed to per-project) tracking toggle.

## Design

### 1. Settings section title colors

Two new CSS custom properties alongside the existing track palette:

```css
--orange:  #db6b3f;
--magenta: #d874c7;
```

Each `.settings-section` div gets a second modifier class so color can be
targeted without changing the shared `.settings-section` rule:

| Section | Class | Color |
|---|---|---|
| Branding | `.settings-section--magenta` | `--magenta` |
| Hourly Rates | `.settings-section--amber` | `--amber` |
| Filament Types, Costs & Density | `.settings-section--green` | `--green-bright` |
| Resin Types, Costs & Density | `.settings-section--blue` | `--blue-bright` |
| FDM Printers | `.settings-section--green` | `--green-bright` |
| Resin Printers | `.settings-section--blue` | `--blue-bright` |
| Spoolman | `.settings-section--orange` | `--orange` |
| Storage | `.settings-section--orange` | `--orange` |
| Desktop App | `.settings-section--orange` | `--orange` |

Purely additive CSS + a class on each existing header div. No JS logic.

### 2. Formlabs credential popout

**New modal**, `formlabsPrinterModal`, opened from a small "+ Formlabs
printer" link placed under the existing Resin Printers add-row (which stays
as-is, for Moonraker/OctoPrint resin setups — SLA-only alternative, not a
replacement).

Fields: Name, Serial, Client ID, Client Secret (all text inputs — Client
Secret uses `type="password"` so it isn't shoulder-surfable while typing),
Watts.

**Save behavior:**
- New printer: builds
  `formlabs://${encodeURIComponent(serial)}?client_id=${encodeURIComponent(clientId)}&client_secret=${encodeURIComponent(clientSecret)}`
  and pushes `{id, name, moonrakerUrl, wattage}` into `settings.resinPrinters`
  — same shape as every other printer entry, so `poll_printer()` /
  `_parse_formlabs_url()` on the server need no changes. `encodeURIComponent`
  on each part also closes the query-string-corruption risk flagged during
  the original Formlabs poller work (a `+`/`&`/`=` inside a raw secret would
  have broken naive concatenation).
- Edit existing: reopening the modal for a `formlabs://` row pre-fills Name,
  Serial, and Client ID from the parsed URL; Client Secret is left **blank**
  with a placeholder like `(unchanged — leave blank to keep)`. On save, an
  empty Client Secret field means "keep the previously stored secret";
  anything typed replaces it.

**List rendering:** `renderResinPrintersList()` currently shows
`esc(p.moonrakerUrl)` verbatim for every row. Add a branch: if
`p.moonrakerUrl` starts with `formlabs://`, render `🧪 Formlabs · SN<serial>`
(parsed client-side, same split logic as the popout's pre-fill) with a pencil
icon opening the edit flow above, instead of the raw URL string. All other
URL schemes keep today's plain-text display.

### 3. Startup project picker (blocking modal)

Delete the auto-select line:

```js
if (data.projects.length > 0) selectProject(data.projects[0].id);   // index.html:3235 — removed
```

Add `projectPickerModal`, following the exact non-dismissable pattern already
used by `firstRunModal`:
- **Not** added to the `Escape` key handler's close list (`index.html:2361`).
- **Not** added to the backdrop-click-to-close list (`index.html:2365`).
- Opened unconditionally after the first-run check passes and
  `data`/`settings` are loaded, whenever `data.projects.length > 0`.
- Lists existing projects (reuse the sidebar's row rendering — name, scope,
  status dot); clicking one calls `selectProject(id)` then
  `closeModal('projectPickerModal')`.
- A "+ New Project" button opens the existing New Project modal on top;
  `saveProject()` already calls `selectProject(proj.id)` on success (see
  `index.html:2340`) — add a `closeModal('projectPickerModal')` call there
  too so completing that flow also dismisses the picker underneath it.
- If `data.projects.length === 0`, skip the picker entirely and open the New
  Project modal directly — there's nothing to pick.

No changes needed to `processPrinterState()` or `pollPrinter()` for this
part — `pollPrinter()` keeps running on its normal timer (printer
status/dots still update in the background), but every auto-track branch
inside `processPrinterState()` already bails out via `if (!reachable ||
!activeProject) return;` when nothing is selected yet. Removing the
auto-select is sufficient by itself.

### 4. Per-project, per-track auto-tracking toggle

New optional project fields: `trackFdm`, `trackResin` (booleans). Treated as
`true` when absent — no migration/backfill needed, existing projects keep
today's behavior automatically.

**UI placement:**
- Single-printer mode (0–1 printer configured for that type): a small toggle
  switch next to the existing status dot beside the main FDM/Resin punch
  button.
- Multi-printer mode (2+ printers of that type): one toggle on the track
  panel's header/label — not duplicated per printer card, since the setting
  is project+track scoped, not per-printer.

**Gating logic** — `processPrinterState(type, printer, ps)`'s existing guard:

```js
if (!reachable || !activeProject) return;
```

becomes:

```js
if (!reachable || !activeProject) return;
const trackKey = type === 'fdm' ? 'trackFdm' : 'trackResin';
if (activeProject[trackKey] === false) return;
```

(`=== false` rather than a falsy check, so `undefined` on existing projects
still means "on.")

This is the only change to the auto-tracking code path. Everything
downstream (backdated first-poll punch-in, idle→printing, printing→idle +
material modal) is already gated by this single early return, so no other
call sites need touching. Manual punch-in/out (`togglePunch()`) doesn't go
through `processPrinterState()` at all and is completely unaffected.
Printer-connectivity bookkeeping (`printerUnreachCounts`, offline
notifications, per-card status dots) also lives outside this guard and keeps
working regardless of any project's toggle state.

## Data model changes

```js
// Project (ar_tracker_v1 → data.projects[])
{
  ...
  trackFdm?:   boolean,   // default true (absent = true) — gates FDM auto punch in/out
  trackResin?: boolean,   // default true (absent = true) — gates Resin auto punch in/out
}
```

No changes to `settings`, printer config shape, or any session/receipt
structure. No `server.py` changes.

## Testing

Manual verification (no automated test suite exists in this project):

1. **Section colors** — open Settings, confirm each of the 9 section headers
   renders in its mapped color against both the app's dark theme.
2. **Formlabs popout** — add a new Formlabs printer via the popout, confirm
   the composed `formlabs://...` URL round-trips correctly through
   `save → /update-printers → printers.json → poll_formlabs()` (reuse the
   printer already configured from the earlier live-debugging session).
   Reopen for edit, confirm Serial/Client ID pre-fill and secret field is
   blank; save with secret blank, confirm polling keeps working (old secret
   preserved); save with a new secret typed, confirm it's actually replaced
   in `printers.json`.
3. **Startup picker** — with 2+ existing projects, refresh the page mid-print
   on a tracked printer; confirm no session gets created until a project is
   explicitly chosen in the picker, and confirm ESC/backdrop-click do not
   dismiss it. With 0 projects, confirm it skips straight to New Project.
4. **Per-project toggle** — flip a project's FDM toggle off, start a print,
   confirm no auto punch-in occurs for that project while another project
   with the toggle on (or absent) still auto-tracks normally. Confirm manual
   punch-in still works on the toggled-off project.

## Open questions

None — all decisions were confirmed during brainstorming (color mapping,
popout field set, blocking-modal behavior, toggle granularity/placement,
default-on).
