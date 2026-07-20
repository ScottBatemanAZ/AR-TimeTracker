# Settings Polish + Project-Scoped Printer Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Color-code the Settings modal's section headers, replace the raw `formlabs://` URL entry with a guided popout, and gate printer auto-tracking behind an explicit per-load project choice plus a per-project/per-track on/off switch.

**Architecture:** Everything lives in `index.html` — no `server.py` changes. Four additive, mostly-independent slices: (1) CSS-only section coloring, (2) a new small modal + list-rendering branch for Formlabs credentials, (3) a new blocking startup modal that replaces an unconditional auto-select, (4) two new optional project fields plus one new guard clause in the existing auto-tracking function.

**Tech Stack:** Vanilla HTML/CSS/JS (single inline `<script>` block, no build step, no framework, no test runner).

## Global Constraints

- Single file touched across all tasks: `r:\Azazel's Razer\timetracker\index.html`. No `server.py` changes anywhere in this plan.
- This project has no automated test suite (confirmed: no test files, no package.json, no pytest config). Each task's verification step instead does two things, in order:
  1. A fast Node.js syntax check of the inline `<script>` block (catches typos immediately, no browser needed).
  2. A live check against the running dev server (`python server.py`, port 5757) using the Playwright MCP browser tools (`mcp__plugin_playwright_playwright__browser_navigate`, `browser_click`, `browser_evaluate`, `browser_snapshot`, etc.) — these are available in this environment and give a real, repeatable check instead of a hand-wavy "look at it in a browser."
- The file has exactly one `<script>` tag, opening at line 1039 (no `src` attribute) — the syntax-check extraction below relies on that; re-verify with `grep -n "<script" index.html` if a prior task shifted things unexpectedly (it won't — no task adds a second `<script>` tag).
- Follow existing code density/style inside the `<script>` block (compact, minimal whitespace, `const`/arrow functions, no semicolon-omission inconsistency) — don't reformat surrounding code you're not touching.
- New CSS custom properties go in the existing `:root { ... }` block (`index.html:14-21`), not a new block.
- Modal dismiss-ability follows the existing two allow-lists:
  - `index.html:2361` — array of modal IDs closed by the `Escape` key.
  - `index.html:2365` — array of modal IDs closed by clicking the backdrop.
  - `formlabsModal` (Task 2) is a normal modal: add it to the `Escape` list only (matching `manualModal`/`subtypeModal`, which are ESC-closable but not backdrop-click-closable).
  - `projectPickerModal` (Task 3) is a **blocking** modal: add it to **neither** list, matching the existing `firstRunModal` precedent.
- Line numbers below were captured against the current file state at the start of this plan. If an earlier task in this plan shifts a later task's target lines, re-`grep` the anchor text quoted in that step before editing — the plan gives you the exact surrounding text to search for either way.

---

### Task 1: Settings section title colors

**Files:**
- Modify: `index.html:14-21` (CSS `:root` block — add 2 vars)
- Modify: `index.html:255` (`.settings-section` rule — add modifier classes)
- Modify: `index.html:874,895,931,950,968,985,1003,1018,1025` (9 section header `<div>`s — add a class each)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing consumed by other tasks — this is a pure CSS/markup change, fully self-contained.

- [ ] **Step 1: Add the two new CSS variables**

Read the current block first to confirm line numbers haven't shifted, then edit `index.html:14-21`:

Current:
```css
  :root {
    --bg: #0e0e0f; --surface: #161618; --surface2: #1e1e21; --surface3: #26262b;
    --border: #2e2e34; --border2: #3e3e46; --text: #e8e8ec; --muted: #7a7a86; --dim: #4a4a54;
    --accent: #7f77dd; --accent-dim: #3c3489;
    --green: #1d9e75; --green-bright: #5dcaa5;
    --amber: #ef9f27; --blue: #378add; --blue-bright: #85b7eb; --red: #e24b4a;
    --mono: 'IBM Plex Mono', monospace; --sans: 'IBM Plex Sans', sans-serif;
  }
```

New (adds one line after the `--amber...` line):
```css
  :root {
    --bg: #0e0e0f; --surface: #161618; --surface2: #1e1e21; --surface3: #26262b;
    --border: #2e2e34; --border2: #3e3e46; --text: #e8e8ec; --muted: #7a7a86; --dim: #4a4a54;
    --accent: #7f77dd; --accent-dim: #3c3489;
    --green: #1d9e75; --green-bright: #5dcaa5;
    --amber: #ef9f27; --blue: #378add; --blue-bright: #85b7eb; --red: #e24b4a;
    --orange: #db6b3f; --magenta: #d874c7;
    --mono: 'IBM Plex Mono', monospace; --sans: 'IBM Plex Sans', sans-serif;
  }
```

- [ ] **Step 2: Add color modifier classes to `.settings-section`**

Current (`index.html:255-256`):
```css
  .settings-section { font-family: var(--mono); font-size: 9px; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); border-top: 1px solid var(--border); padding-top: 14px; margin-top: 10px; margin-bottom: 10px; }
  .settings-section:first-child { border-top: none; padding-top: 0; margin-top: 0; }
```

New (adds 5 modifier rules right after):
```css
  .settings-section { font-family: var(--mono); font-size: 9px; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); border-top: 1px solid var(--border); padding-top: 14px; margin-top: 10px; margin-bottom: 10px; }
  .settings-section:first-child { border-top: none; padding-top: 0; margin-top: 0; }
  .settings-section.sec-green   { color: var(--green-bright); }
  .settings-section.sec-blue    { color: var(--blue-bright); }
  .settings-section.sec-amber   { color: var(--amber); }
  .settings-section.sec-magenta { color: var(--magenta); }
  .settings-section.sec-orange  { color: var(--orange); }
```

- [ ] **Step 3: Apply the modifier classes to each of the 9 section headers**

Each is a one-word class addition. Find-and-replace each line exactly (all 9 currently read `class="settings-section"` with no modifier):

| Line | Find | Replace |
|---|---|---|
| 874 | `<div class="settings-section">Branding</div>` | `<div class="settings-section sec-magenta">Branding</div>` |
| 895 | `<div class="settings-section">Hourly Rates</div>` | `<div class="settings-section sec-amber">Hourly Rates</div>` |
| 931 | `<div class="settings-section">Filament Types, Costs &amp; Density</div>` | `<div class="settings-section sec-green">Filament Types, Costs &amp; Density</div>` |
| 950 | `<div class="settings-section">Resin Types, Costs &amp; Density</div>` | `<div class="settings-section sec-blue">Resin Types, Costs &amp; Density</div>` |
| 968 | `<div class="settings-section">FDM Printers</div>` | `<div class="settings-section sec-green">FDM Printers</div>` |
| 985 | `<div class="settings-section">Resin Printers</div>` | `<div class="settings-section sec-blue">Resin Printers</div>` |
| 1003 | `<div class="settings-section">Spoolman <span style="color:var(--dim);font-weight:400;">(optional — filament spool tracking)</span></div>` | `<div class="settings-section sec-orange">Spoolman <span style="color:var(--dim);font-weight:400;">(optional — filament spool tracking)</span></div>` |
| 1018 | `<div class="settings-section">Storage</div>` | `<div class="settings-section sec-orange">Storage</div>` |
| 1025 | `<div class="settings-section">Desktop App</div>` | `<div class="settings-section sec-orange">Desktop App</div>` |

Use the Edit tool once per row (`old_string`/`new_string` exactly as shown in the table — each `old_string` is unique in the file so no `replace_all` needed).

- [ ] **Step 4: Syntax check**

```bash
cd "r:/Azazel's Razer/timetracker"
node -e "const fs=require('fs');const h=fs.readFileSync('index.html','utf8');const s=h.indexOf('<script>')+8;const e=h.indexOf('</script>',s);fs.writeFileSync('.tmp-syntax-check.js',h.slice(s,e));"
node --check .tmp-syntax-check.js && echo SYNTAX_OK
rm .tmp-syntax-check.js
```
Expected: `SYNTAX_OK` (Task 1 touches no JS, so this should trivially pass — it's here to catch a stray typo in the HTML edits that happened to land inside the script block, which it won't, but it's cheap insurance and establishes the pattern used by every later task).

- [ ] **Step 5: Visual verification via Playwright**

```bash
cd "r:/Azazel's Razer/timetracker"
AR_NO_BROWSER=1 python server.py &
sleep 2
```

Then, using the Playwright MCP tools:
1. `browser_navigate` to `http://127.0.0.1:5757`
2. Click the ⚙ Settings button (sidebar) — `browser_click`
3. `browser_snapshot` and confirm 9 section headers render, and `browser_evaluate` this against the page to confirm each header's computed color matches its assigned var (spot-check 2-3, e.g.):
   ```js
   () => {
     const headers = [...document.querySelectorAll('.settings-section')].map(el => el.textContent.trim().slice(0,20) + ' → ' + getComputedStyle(el).color);
     return headers;
   }
   ```
   Expected: 9 entries, with visibly distinct `rgb(...)` values across the amber/green/blue/magenta/orange groups (not all identical, which was the pre-fix state).

Stop the server afterward: find and kill the background `python server.py` process (e.g. `pkill -f "python server.py"` or note its PID from step 1 and `kill` it).

- [ ] **Step 6: Commit**

```bash
cd "r:/Azazel's Razer/timetracker"
git add index.html
git commit -m "$(cat <<'EOF'
feat: color-code Settings modal section headers

Nine flat-gray section titles made the Settings modal hard to scan.
Colors now follow the app's existing track palette (green=FDM,
blue=Resin, amber=money) plus two new vars for sections that don't
map to a track.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Formlabs credential popout

**Files:**
- Modify: `index.html:968-1001` (Resin Printers settings section — trim the inline hint, add a "+ Formlabs printer" entry point)
- Modify: `index.html` (new `formlabsModal` HTML block, placed near the other simple modals — after `subtypeModal`, i.e. after the `</div>` that currently closes at line 759)
- Modify: `index.html` (`renderResinPrintersList()`, currently `index.html:1217-1229`)
- Modify: `index.html:2361` (Escape-key close list — add `'formlabsModal'`)

**Interfaces:**
- Consumes: `settings.resinPrinters` array (existing global, shape `{id, name, moonrakerUrl, wattage}` — unchanged shape, only how `moonrakerUrl` gets built/displayed changes for Formlabs entries).
- Produces: `openFormlabsModal(idx)` (idx omitted/undefined = add mode, a number = edit mode for `settings.resinPrinters[idx]`), `saveFormlabsPrinter()`, `_flParseUrl(url)` → `{serial, clientId, clientSecret}`, `_flBuildUrl(serial, clientId, clientSecret)` → string. `renderResinPrintersList()` keeps its existing signature/behavior for non-Formlabs rows.

- [ ] **Step 1: Trim the Resin Printers hint text and add the popout entry point**

Read `index.html:985-1001` first to confirm it still matches (this was touched by an earlier Formlabs session, so double-check before editing). Current:
```html
    <div class="settings-section sec-blue">Resin Printers</div>
    <div style="font-size:10px;color:var(--muted);font-family:var(--mono);margin-bottom:8px;">
      Works with Moonraker (Klipper) or OctoPrint like FDM above. For a Formlabs printer
      (no LAN status endpoint — polled via Formlabs' Dashboard Cloud API instead), use
      <code>formlabs://SERIAL?client_id=YOUR_ID&client_secret=YOUR_SECRET</code>
      (credentials from dashboard.formlabs.com → Developer).
    </div>
    <div style="display:grid;grid-template-columns:1fr 1.5fr 62px 24px;gap:8px;margin-bottom:4px;">
      <span class="col-header">Name</span><span class="col-header">Printer URL</span><span class="col-header">⚡ Watts</span><span></span>
    </div>
    <div class="type-list" id="resinPrintersList"></div>
    <div class="type-add-row printer-add" style="grid-template-columns:1fr 1.5fr 62px 24px;">
      <input type="text" id="newResinPrinterName" placeholder="e.g. Mars 4 Ultra" />
      <input type="text" id="newResinPrinterUrl"  placeholder="http://192.168.0.xx (or formlabs://SERIAL?client_id=...)" />
      <input type="number" id="newResinPrinterWatts" placeholder="W" min="0" step="10" />
      <button class="type-add-btn" onclick="addResinPrinter()">+</button>
    </div>
```

(Note: the class is `sec-blue` now, since Task 1 already ran — if executing Task 2 before Task 1 for any reason, match on `class="settings-section"` instead.)

Replace with:
```html
    <div class="settings-section sec-blue">Resin Printers</div>
    <div style="font-size:10px;color:var(--muted);font-family:var(--mono);margin-bottom:8px;">
      Works with Moonraker (Klipper) or OctoPrint like FDM above — paste the printer's URL. For a
      Formlabs printer (polled via Formlabs' Dashboard Cloud API, not the LAN), use the
      <strong>+ Formlabs printer</strong> button below instead of typing a URL by hand.
    </div>
    <div style="display:grid;grid-template-columns:1fr 1.5fr 62px 24px;gap:8px;margin-bottom:4px;">
      <span class="col-header">Name</span><span class="col-header">Printer URL</span><span class="col-header">⚡ Watts</span><span></span>
    </div>
    <div class="type-list" id="resinPrintersList"></div>
    <div class="type-add-row printer-add" style="grid-template-columns:1fr 1.5fr 62px 24px;">
      <input type="text" id="newResinPrinterName" placeholder="e.g. Mars 4 Ultra" />
      <input type="text" id="newResinPrinterUrl"  placeholder="http://192.168.0.xx" />
      <input type="number" id="newResinPrinterWatts" placeholder="W" min="0" step="10" />
      <button class="type-add-btn" onclick="addResinPrinter()">+</button>
    </div>
    <button class="manual-link" style="margin-top:4px;" onclick="openFormlabsModal()">+ Formlabs printer (guided setup)</button>
```

- [ ] **Step 2: Add the `formlabsModal` HTML block**

Find the `<!-- SUBTYPE MODAL -->` block's closing (search for this exact closing sequence, which currently ends at line 759):
```html
    <div class="modal-actions" style="justify-content:flex-start;margin-top:14px;">
      <button class="btn" onclick="closeModal('subtypeModal')">Cancel</button>
    </div>
  </div>
</div>
```

Insert this new block immediately after that closing `</div>` (and before the next `<!-- EDIT DESIGN SESSION MODAL -->` comment):
```html

<!-- FORMLABS PRINTER MODAL -->
<div class="modal-backdrop" id="formlabsModal" style="z-index:150;">
  <div class="modal" style="width:380px;">
    <div class="modal-title" id="formlabsModalTitle">Add Formlabs Printer</div>
    <div class="form-row">
      <label class="form-label">Name</label>
      <input type="text" id="flName" placeholder="e.g. Form 4" />
    </div>
    <div class="form-row">
      <label class="form-label">Serial Number</label>
      <input type="text" id="flSerial" placeholder="e.g. FL4A1234567" />
    </div>
    <div class="form-row">
      <label class="form-label">Client ID</label>
      <input type="text" id="flClientId" placeholder="from dashboard.formlabs.com → Developer" />
    </div>
    <div class="form-row">
      <label class="form-label">Client Secret</label>
      <input type="password" id="flClientSecret" placeholder="" autocomplete="off" />
      <div class="form-hint" id="flSecretHint" style="display:none;">Leave blank to keep the existing secret.</div>
    </div>
    <div class="form-row" style="margin-bottom:0;">
      <label class="form-label">⚡ Watts (optional)</label>
      <input type="number" id="flWatts" placeholder="W" min="0" step="10" />
    </div>
    <div class="modal-actions">
      <button class="btn" onclick="closeModal('formlabsModal')">Cancel</button>
      <button class="btn-create" id="flSaveBtn" onclick="saveFormlabsPrinter()">Add Printer</button>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Add the JS functions**

Find `renderResinPrintersList()` (currently `index.html:1217-1229`):
```js
function renderResinPrintersList() {
  const el = document.getElementById('resinPrintersList');
  if (!settings.resinPrinters.length) { el.innerHTML='<div class="empty-state">No resin printers defined.</div>'; return; }
  el.innerHTML = settings.resinPrinters.map((p,i) =>
    `<div class="type-row printer-row" style="grid-template-columns:1fr 1.5fr 62px 24px;">
      <span class="type-row-name">${esc(p.name)}</span>
      <span class="type-row-cost" style="color:var(--muted);text-align:left;">${esc(p.moonrakerUrl)}</span>
      <input type="number" min="0" step="10" value="${p.wattage||0}" placeholder="W"
        style="font-family:var(--mono);font-size:11px;background:var(--surface2);border:1px solid var(--border2);color:var(--text);border-radius:3px;padding:2px 4px;width:100%;"
        oninput="settings.resinPrinters[${i}].wattage=parseFloat(this.value)||0" />
      <button class="type-del-btn" onclick="removeResinPrinter(${i})">✕</button>
    </div>`).join('');
}
```

Replace with (adds a Formlabs-aware branch for the URL cell, plus the new functions above/below it):
```js
function _flParseUrl(url) {
  try {
    const u = new URL(url);
    const serial = u.hostname || u.pathname.replace(/^\/+/, '');
    return { serial, clientId: u.searchParams.get('client_id')||'', clientSecret: u.searchParams.get('client_secret')||'' };
  } catch { return { serial:'', clientId:'', clientSecret:'' }; }
}
function _flBuildUrl(serial, clientId, clientSecret) {
  return `formlabs://${encodeURIComponent(serial)}?client_id=${encodeURIComponent(clientId)}&client_secret=${encodeURIComponent(clientSecret)}`;
}
let editingFormlabsIdx = null;
function openFormlabsModal(idx) {
  editingFormlabsIdx = (typeof idx === 'number') ? idx : null;
  const hint = document.getElementById('flSecretHint');
  const secretEl = document.getElementById('flClientSecret');
  if (editingFormlabsIdx !== null) {
    const p = settings.resinPrinters[editingFormlabsIdx];
    const parsed = _flParseUrl(p.moonrakerUrl);
    document.getElementById('formlabsModalTitle').textContent = 'Edit Formlabs Printer';
    document.getElementById('flName').value = p.name;
    document.getElementById('flSerial').value = parsed.serial;
    document.getElementById('flClientId').value = parsed.clientId;
    secretEl.value = ''; secretEl.placeholder = '••••••••';
    document.getElementById('flWatts').value = p.wattage||'';
    document.getElementById('flSaveBtn').textContent = 'Save Changes';
    hint.style.display = '';
  } else {
    document.getElementById('formlabsModalTitle').textContent = 'Add Formlabs Printer';
    document.getElementById('flName').value = '';
    document.getElementById('flSerial').value = '';
    document.getElementById('flClientId').value = '';
    secretEl.value = ''; secretEl.placeholder = '';
    document.getElementById('flWatts').value = '';
    document.getElementById('flSaveBtn').textContent = 'Add Printer';
    hint.style.display = 'none';
  }
  document.getElementById('formlabsModal').classList.add('open');
  setTimeout(()=>document.getElementById('flName').focus(),50);
}
function saveFormlabsPrinter() {
  const name = document.getElementById('flName').value.trim();
  const serial = document.getElementById('flSerial').value.trim();
  const clientId = document.getElementById('flClientId').value.trim();
  const secretInput = document.getElementById('flClientSecret').value.trim();
  const watts = parseFloat(document.getElementById('flWatts').value) || 0;
  if (!name || !serial || !clientId) return;
  let clientSecret = secretInput;
  if (editingFormlabsIdx !== null && !secretInput) {
    clientSecret = _flParseUrl(settings.resinPrinters[editingFormlabsIdx].moonrakerUrl).clientSecret;
  }
  if (!clientSecret) return;
  const url = _flBuildUrl(serial, clientId, clientSecret);
  if (editingFormlabsIdx !== null) {
    const p = settings.resinPrinters[editingFormlabsIdx];
    p.name = name; p.moonrakerUrl = url; p.wattage = watts;
  } else {
    settings.resinPrinters.push({id:'resin-'+Date.now(), name, moonrakerUrl:url, wattage:watts});
  }
  closeModal('formlabsModal');
  renderResinPrintersList();
}
function renderResinPrintersList() {
  const el = document.getElementById('resinPrintersList');
  if (!settings.resinPrinters.length) { el.innerHTML='<div class="empty-state">No resin printers defined.</div>'; return; }
  el.innerHTML = settings.resinPrinters.map((p,i) => {
    const isFormlabs = (p.moonrakerUrl||'').startsWith('formlabs://');
    const urlCell = isFormlabs
      ? `<span class="type-row-cost" style="color:var(--muted);text-align:left;display:flex;align-items:center;gap:5px;">🧪 Formlabs · SN${esc(_flParseUrl(p.moonrakerUrl).serial)}<button onclick="openFormlabsModal(${i})" title="Edit Formlabs credentials" style="background:none;border:none;color:var(--muted);cursor:pointer;font-size:11px;padding:0;">✎</button></span>`
      : `<span class="type-row-cost" style="color:var(--muted);text-align:left;">${esc(p.moonrakerUrl)}</span>`;
    return `<div class="type-row printer-row" style="grid-template-columns:1fr 1.5fr 62px 24px;">
      <span class="type-row-name">${esc(p.name)}</span>
      ${urlCell}
      <input type="number" min="0" step="10" value="${p.wattage||0}" placeholder="W"
        style="font-family:var(--mono);font-size:11px;background:var(--surface2);border:1px solid var(--border2);color:var(--text);border-radius:3px;padding:2px 4px;width:100%;"
        oninput="settings.resinPrinters[${i}].wattage=parseFloat(this.value)||0" />
      <button class="type-del-btn" onclick="removeResinPrinter(${i})">✕</button>
    </div>`;
  }).join('');
}
```

- [ ] **Step 4: Make `formlabsModal` closable with Escape**

Find (`index.html:2361`):
```js
  if(e.key==='Escape'){['projectModal','materialModal','settingsModal','manualModal','subtypeModal','editSessionModal','resinSourcesModal','exportModal','archiveModal'].forEach(closeModal);pendingMaterial=null;manualType=null;editingSession=null;}
```
Replace with:
```js
  if(e.key==='Escape'){['projectModal','materialModal','settingsModal','manualModal','subtypeModal','editSessionModal','resinSourcesModal','exportModal','archiveModal','formlabsModal'].forEach(closeModal);pendingMaterial=null;manualType=null;editingSession=null;editingFormlabsIdx=null;}
```

- [ ] **Step 5: Syntax check**

```bash
cd "r:/Azazel's Razer/timetracker"
node -e "const fs=require('fs');const h=fs.readFileSync('index.html','utf8');const s=h.indexOf('<script>')+8;const e=h.indexOf('</script>',s);fs.writeFileSync('.tmp-syntax-check.js',h.slice(s,e));"
node --check .tmp-syntax-check.js && echo SYNTAX_OK
rm .tmp-syntax-check.js
```
Expected: `SYNTAX_OK`.

- [ ] **Step 6: Behavioral verification via Playwright**

```bash
cd "r:/Azazel's Razer/timetracker"
AR_NO_BROWSER=1 python server.py &
sleep 2
```

1. `browser_navigate` to `http://127.0.0.1:5757`, open Settings.
2. Click "+ Formlabs printer (guided setup)" — `browser_click` — confirm the popout opens (`browser_snapshot`), title reads "Add Formlabs Printer".
3. Fill fields via `browser_fill_form` or individual `browser_type`: Name=`Test Form 4`, Serial=`FLTEST123`, Client ID=`abc123`, Client Secret=`shh-secret`, Watts=`250`.
4. Click "Add Printer" — confirm modal closes and the Resin Printers list now shows a row reading `🧪 Formlabs · SNFLTEST123` (not the raw secret).
5. `browser_evaluate`: `() => settings.resinPrinters[settings.resinPrinters.length-1].moonrakerUrl` — expected: `formlabs://FLTEST123?client_id=abc123&client_secret=shh-secret`.
6. Click the ✎ edit icon on that row — confirm the popout reopens with Name/Serial/Client ID pre-filled, Client Secret **blank** with placeholder `••••••••`, title reads "Edit Formlabs Printer".
7. Leave Client Secret blank, change Watts to `300`, save — `browser_evaluate` the same expression as step 5, confirm `client_secret=shh-secret` is unchanged and wattage updated.
8. Reopen edit, type a new secret `new-secret-456`, save — confirm the URL's `client_secret` is now `new-secret-456`.
9. Press Escape while the popout is open (reopen it first) — confirm it closes.
10. Delete the test printer row (✕ button) so it doesn't linger in `settings.resinPrinters` for later manual testing — click Cancel on the outer Settings modal so nothing is persisted to `printers.json`.

Stop the background server afterward.

- [ ] **Step 7: Commit**

```bash
cd "r:/Azazel's Razer/timetracker"
git add index.html
git commit -m "$(cat <<'EOF'
feat: guided Formlabs printer setup (popout instead of raw URL)

Hand-typing formlabs://SERIAL?client_id=...&client_secret=... into
the Printer URL field already caused one live bug (a stray <> from a
copy-pasted placeholder). Replaced with a small modal that takes
Serial/Client ID/Client Secret as separate fields, URL-encodes them
itself, and shows a compact "Formlabs · SN..." row instead of the
raw credential string. Editing leaves the secret blank (unchanged
unless retyped) rather than redisplaying it.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Startup project picker (blocking modal)

**Files:**
- Modify: `index.html` (new `projectPickerModal` HTML block, placed near `firstRunModal`)
- Modify: `index.html:3235` (remove the auto-select line, call the new picker instead)
- Modify: `index.html:2340` (inside `saveProject()` — close the picker if it was open)

**Interfaces:**
- Consumes: `data.projects` (existing global), `selectProject(id)` (existing function, unchanged), `openNewProject()` (existing function, unchanged), `closeModal(id)` (existing function, unchanged).
- Produces: `openProjectPicker()` (called once at startup), `renderProjectPicker()`, `pickStartupProject(id)`.

- [ ] **Step 1: Add the `projectPickerModal` HTML block**

Find `firstRunModal`'s opening tag (`index.html:569`):
```html
<div class="modal-backdrop" id="firstRunModal" style="z-index:200;">
```

Insert this new block immediately **before** that line:
```html
<!-- PROJECT PICKER MODAL (blocking — intentionally absent from both the Escape-key and backdrop-click close lists) -->
<div class="modal-backdrop" id="projectPickerModal" style="z-index:150;">
  <div class="modal" style="width:420px;">
    <div class="modal-title">Choose a Project</div>
    <p style="font-family:var(--mono);font-size:10px;color:var(--muted);margin-bottom:14px;">
      Pick which project to work in — printer auto-tracking won't start until you do.
    </p>
    <div id="projectPickerList" style="max-height:320px;overflow-y:auto;display:flex;flex-direction:column;gap:4px;margin-bottom:14px;"></div>
    <div class="modal-actions" style="justify-content:flex-start;">
      <button class="btn-create" onclick="closeModal('projectPickerModal');openNewProject();">+ New Project</button>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Add the picker's render/open/pick JS functions**

Find `toggleParent(id)` (currently `index.html:1549-1552`, right after `renderSidebar()`):
```js
function toggleParent(id){
  if(collapsedParents.has(id)) collapsedParents.delete(id); else collapsedParents.add(id);
  renderSidebar();
}
```

Insert these three new functions immediately after it:
```js
function renderProjectPicker() {
  const el = document.getElementById('projectPickerList');
  const projects = data.projects.filter(p=>!p.archived);
  el.innerHTML = projects.map(p=>{
    const status = p.status||'active';
    const indent = p.parentId ? 'margin-left:16px;' : '';
    return `<div class="project-item" style="border-radius:4px;${indent}" onclick="pickStartupProject('${p.id}')">
      <div class="proj-name"><span class="status-dot ${status}"></span><span class="proj-name-text">${esc(p.name)}</span></div>
      <div class="proj-meta">${esc(p.scope||'')}</div>
    </div>`;
  }).join('');
}
function pickStartupProject(id) {
  closeModal('projectPickerModal');
  selectProject(id);
}
function openProjectPicker() {
  if (!data.projects.length) { openNewProject(); return; }
  renderProjectPicker();
  document.getElementById('projectPickerModal').classList.add('open');
}
```

- [ ] **Step 3: Replace the auto-select-first-project line**

Find (`index.html:3234-3235`):
```js
  renderSidebar(); loadFilamentLibrary(); loadResinLibrary();
  if (data.projects.length > 0) selectProject(data.projects[0].id);
```

Replace with:
```js
  renderSidebar(); loadFilamentLibrary(); loadResinLibrary();
  openProjectPicker();
```

- [ ] **Step 4: Close the picker when a brand-new project is created**

Find, inside `saveProject()` (`index.html:2339-2340`):
```js
    data.projects.push(proj);
    saveData(); closeModal('projectModal'); renderSidebar(); selectProject(proj.id);
```

Replace with:
```js
    data.projects.push(proj);
    saveData(); closeModal('projectModal'); closeModal('projectPickerModal'); renderSidebar(); selectProject(proj.id);
```

(`closeModal()` on an already-closed modal is a harmless no-op — this line runs whether or not the picker was the thing that triggered `openNewProject()`.)

- [ ] **Step 5: Syntax check**

```bash
cd "r:/Azazel's Razer/timetracker"
node -e "const fs=require('fs');const h=fs.readFileSync('index.html','utf8');const s=h.indexOf('<script>')+8;const e=h.indexOf('</script>',s);fs.writeFileSync('.tmp-syntax-check.js',h.slice(s,e));"
node --check .tmp-syntax-check.js && echo SYNTAX_OK
rm .tmp-syntax-check.js
```
Expected: `SYNTAX_OK`.

- [ ] **Step 6: Behavioral verification via Playwright**

Requires at least 2 existing projects in the test data — if the local `ar_tracker_v1` localStorage is empty, create 2 quick projects first (via the picker's own "+ New Project" flow) before testing the "existing projects" path.

```bash
cd "r:/Azazel's Razer/timetracker"
AR_NO_BROWSER=1 python server.py &
sleep 2
```

1. `browser_navigate` to `http://127.0.0.1:5757`.
2. **Zero-project case** (if starting fresh/no localStorage): confirm the New Project modal opens directly, no picker shown first. Create one project.
3. Reload the page (`browser_navigate` to the same URL again, or `browser_evaluate: () => location.reload()`). Confirm `projectPickerModal` is open (`browser_snapshot`) and the underlying app (empty state) is visible-but-inert behind it.
4. Try pressing Escape — confirm the picker does **not** close (`browser_evaluate: () => document.getElementById('projectPickerModal').classList.contains('open')` → expect `true`).
5. Try clicking directly on the semi-transparent backdrop (not the modal box) — confirm it does **not** close either.
6. Click "+ New Project" from inside the picker, create a second project — confirm both the New Project modal and the picker are gone afterward, and the new project is now the active one (`browser_evaluate: () => activeProject?.name`).
7. Reload again — confirm the picker reopens, now listing both projects. Click the first project's row — confirm the picker closes and that project becomes active (`browser_evaluate: () => activeProject?.id`).
8. If you have a printer configured and reachable in your test environment: with one project selected via the picker, confirm printer polling only affects `activeProject` (this is already covered indirectly — full auto-track behavior is exercised in Task 4's verification, since the toggle sits on top of this same gate).

Stop the background server afterward.

- [ ] **Step 7: Commit**

```bash
cd "r:/Azazel's Razer/timetracker"
git add index.html
git commit -m "$(cat <<'EOF'
fix: require explicit project choice before printer auto-tracking

index.html auto-selected data.projects[0] on every page load, so a
refresh while a printer was mid-print could silently resume
auto-tracking into whatever project happened to be first in the
array — not necessarily the one the user intended. Replaced the
auto-select with a blocking "Choose a Project" modal (same
non-dismissable pattern as the existing first-run wizard) shown on
every load; auto-tracking already requires an active project, so
removing the auto-select is sufficient to close the gap.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Per-project, per-track auto-tracking toggle

**Files:**
- Modify: `index.html:88-101` area (clock-track CSS — add `.track-toggle` rules)
- Modify: `index.html:392` (FDM track-label — add toggle markup)
- Modify: `index.html:413` (Resin track-label — add toggle markup)
- Modify: `index.html:1655-1661` (`renderClock()` — sync toggle checkbox state)
- Modify: `index.html:2817` (`processPrinterState()` — add the gating condition)
- Modify: `index.html` (new `setTrackEnabled(type, checked)` function)

**Interfaces:**
- Consumes: `activeProject` (existing global), `saveData()` (existing function).
- Produces: `setTrackEnabled(type, checked)` — called from the new checkbox inputs' `onchange`. New project fields `trackFdm`/`trackResin` (booleans, absent = `true`) — read by `processPrinterState()`.

- [ ] **Step 1: Add `.track-toggle` CSS**

Find (`index.html:97-101`, end of the `.pcard-dot` rules):
```css
  .pcard-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
  .pcard-dot.printing { background: var(--green-bright); animation: pulse 2s ease-in-out infinite; }
  .pcard-dot.idle     { background: var(--dim); }
  .pcard-dot.offline  { background: var(--red); }
  .pcard-dot.unknown  { background: var(--dim); opacity: .5; }
```

Insert immediately after:
```css
  .track-toggle { display:inline-flex; align-items:center; gap:3px; margin-left:8px; font-family:var(--mono); font-size:9px; color:var(--muted); cursor:pointer; user-select:none; vertical-align:middle; text-transform:none; letter-spacing:0; }
  .track-toggle input[type=checkbox] { width:11px; height:11px; cursor:pointer; margin:0; }
  .track-toggle.fdm input[type=checkbox]   { accent-color: var(--green-bright); }
  .track-toggle.resin input[type=checkbox] { accent-color: var(--blue-bright); }
```

- [ ] **Step 2: Add the toggle to the FDM track label**

Find (`index.html:392`):
```html
            <div class="track-label fdm-label">FDM Printer<span class="printer-dot dim" id="printerDot" title="Printer status unknown"></span></div>
```

Replace with:
```html
            <div class="track-label fdm-label">FDM Printer<span class="printer-dot dim" id="printerDot" title="Printer status unknown"></span><label class="track-toggle fdm" title="Auto-track FDM printers for this project"><input type="checkbox" id="fdmTrackToggle" onchange="setTrackEnabled('fdm', this.checked)" checked><span>auto</span></label></div>
```

- [ ] **Step 3: Add the toggle to the Resin track label**

Find (`index.html:413`):
```html
            <div class="track-label resin-label">Resin Printer</div>
```

Replace with:
```html
            <div class="track-label resin-label">Resin Printer<label class="track-toggle resin" title="Auto-track Resin printers for this project"><input type="checkbox" id="resinTrackToggle" onchange="setTrackEnabled('resin', this.checked)" checked><span>auto</span></label></div>
```

- [ ] **Step 4: Add `setTrackEnabled()` and sync the checkboxes in `renderClock()`**

Find `renderResinPrintersList()`'s closing (end of Task 2's replacement — the function ends with `}).join('');\n}`). Add the new function directly after `renderResinPrintersList()`'s closing brace (anywhere at top level in the script is fine; placing it near the other project-mutation helpers like `togglePunch` keeps related code together — insert it right before `function togglePunch(type) {`, currently preceded by the `// ── PUNCH ─...` comment around `index.html:1836`):
```js
function setTrackEnabled(type, checked) {
  if (!activeProject) return;
  activeProject[type==='fdm'?'trackFdm':'trackResin'] = checked;
  saveData();
}
```

Then find, inside `renderClock(type)` (`index.html:1655-1661`):
```js
  if (type==='fdm'||type==='resin') {
    const printers = type==='fdm' ? settings.fdmPrinters : settings.resinPrinters;
    const multi = printers.length > 1;
    const btnWrap = document.getElementById(type+'Btn')?.parentElement;
    if (btnWrap) btnWrap.style.display = multi ? 'none' : '';
    renderPrinterCards(type);
  }
```

Replace with:
```js
  if (type==='fdm'||type==='resin') {
    const printers = type==='fdm' ? settings.fdmPrinters : settings.resinPrinters;
    const multi = printers.length > 1;
    const btnWrap = document.getElementById(type+'Btn')?.parentElement;
    if (btnWrap) btnWrap.style.display = multi ? 'none' : '';
    renderPrinterCards(type);
    const toggle = document.getElementById(type+'TrackToggle');
    if (toggle) toggle.checked = p[type==='fdm'?'trackFdm':'trackResin'] !== false;
  }
```

- [ ] **Step 5: Gate auto-tracking on the new project fields**

Find, inside `processPrinterState(type, printer, ps)` (`index.html:2817`):
```js
  if (!reachable || !activeProject) return;
```

Replace with:
```js
  if (!reachable || !activeProject) return;
  if (activeProject[type==='fdm'?'trackFdm':'trackResin'] === false) return;
```

- [ ] **Step 6: Syntax check**

```bash
cd "r:/Azazel's Razer/timetracker"
node -e "const fs=require('fs');const h=fs.readFileSync('index.html','utf8');const s=h.indexOf('<script>')+8;const e=h.indexOf('</script>',s);fs.writeFileSync('.tmp-syntax-check.js',h.slice(s,e));"
node --check .tmp-syntax-check.js && echo SYNTAX_OK
rm .tmp-syntax-check.js
```
Expected: `SYNTAX_OK`.

- [ ] **Step 7: Behavioral verification via Playwright**

```bash
cd "r:/Azazel's Razer/timetracker"
AR_NO_BROWSER=1 python server.py &
sleep 2
```

1. `browser_navigate` to `http://127.0.0.1:5757`, select a project via the picker (from Task 3).
2. `browser_snapshot` the clock area — confirm an "auto" checkbox appears next to "FDM Printer" and next to "Resin Printer", both checked by default (project has no `trackFdm`/`trackResin` set yet).
3. `browser_evaluate: () => [activeProject.trackFdm, activeProject.trackResin]` — expected `[undefined, undefined]` (absent, not explicitly `true` — confirms the "absent means on" behavior, no eager defaulting).
4. Click the FDM "auto" checkbox to uncheck it. `browser_evaluate: () => activeProject.trackFdm` — expected `false`.
5. `browser_evaluate` this to simulate an FDM printer transitioning idle→printing without touching `server.py` (exercises the exact guard added in Step 5, since driving a real printer isn't practical in this check):
   ```js
   () => {
     const before = (activeProject.fdmSessions||[]).length;
     processPrinterState('fdm', settings.fdmPrinters[0] || {id:'test-fdm', name:'Test'}, {status:'printing', reachable:true, print_duration:0});
     return { before, after: (activeProject.fdmSessions||[]).length };
   }
   ```
   Expected: `before === after` (no session was created — the toggle blocked it). If `settings.fdmPrinters` is empty in the test environment, this still exercises the guard correctly since `processPrinterState` doesn't require the printer to be a real configured entry.
6. Re-check the FDM toggle, re-run the same `browser_evaluate` snippet — expected: `after === before + 1` this time (auto-track re-enabled, session created).
7. Switch to a second project via the sidebar (not the picker, since it's only used at startup) — confirm its FDM/Resin toggles independently show as checked (project-scoped, not global).
8. Reload the page, pick the first project again via the picker — confirm its FDM toggle is still unchecked (persisted via `saveData()`).
9. Undo the test session created in step 6 if it polluted real project data (delete it via the session log's delete control, or just use a disposable test project for this whole verification pass).

Stop the background server afterward.

- [ ] **Step 8: Commit**

```bash
cd "r:/Azazel's Razer/timetracker"
git add index.html
git commit -m "$(cat <<'EOF'
feat: per-project FDM/Resin auto-tracking toggle

Some projects should never be touched by printer state changes (e.g.
working on something unrelated while a different project's print
runs). Adds a small "auto" checkbox next to each track's status
indicator; unchecking it sets trackFdm/trackResin=false on the
project, which processPrinterState() now checks before doing any
auto punch-in/out. Manual punch buttons and printer-connectivity
monitoring are unaffected — only auto-detection is gated. Absent on
existing projects means "on," so nothing changes for anyone who
doesn't touch the new toggle.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Plan Self-Review

**Spec coverage:**
- Section 1 (colored headers) → Task 1. ✅
- Section 2 (Formlabs popout, masked secret, compact display) → Task 2. ✅
- Section 3 (blocking startup picker, no ESC/backdrop dismiss) → Task 3. ✅
- Section 4 (per-project/per-track toggle, placement, default-on, gating) → Task 4. ✅
- "No server.py changes" / "no data-shape changes beyond 2 optional booleans" constraints → respected throughout; no task touches `server.py`.

**Placeholder scan:** No TBD/TODO markers; every step has complete, exact code — none deferred to "similar to Task N."

**Type/name consistency check:**
- `_flParseUrl` / `_flBuildUrl` (Task 2) used consistently by name in both `renderResinPrintersList()` and `openFormlabsModal()`/`saveFormlabsPrinter()`.
- `openProjectPicker()` / `renderProjectPicker()` / `pickStartupProject()` (Task 3) — names match between their definitions (Step 2) and call sites (Step 3, the `+ New Project` button's inline `onclick`, and Task 3 Step 4's verification).
- `setTrackEnabled(type, checked)` (Task 4) matches the `onchange` handlers added in Steps 2-3 and its own definition in Step 4.
- `trackFdm`/`trackResin` field names are identical across Task 4's CSS/HTML/JS steps and the design spec.
- `formlabsModal` / `projectPickerModal` IDs match between their HTML `id` attributes and every `document.getElementById(...)` / `closeModal(...)` / array-membership reference across Tasks 2 and 3.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-19-settings-polish-and-project-tracking-gate.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**

