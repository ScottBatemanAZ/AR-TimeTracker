#!/usr/bin/env python3
import http.server
import socketserver
import os
import re
import signal
import sys
import webbrowser
import threading
import urllib.request
import urllib.error
import urllib.parse
import json
import time
import io
import zipfile
import socket
import subprocess
from datetime import datetime

# Force UTF-8 output on Windows consoles (prevents crash on → ⬆ etc. in cp1252 terminals)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

PORT = 5757
SERVER_VERSION  = "1.5"
TRACKER_VERSION = "Beta 10.4.0"
POLL_INTERVAL   = 5  # seconds

# ── PATH SETUP ────────────────────────────────────────────────────────
# PyInstaller bundles read-only assets into a temp dir (sys._MEIPASS).
# Writable user files (config, printers, data) must live next to the exe.
IS_FROZEN  = getattr(sys, 'frozen', False)
STATIC_DIR = sys._MEIPASS if IS_FROZEN else os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.dirname(sys.executable) if IS_FROZEN else STATIC_DIR
DIR        = STATIC_DIR   # kept for SimpleHTTPRequestHandler directory= arg

# ── EARLY ERROR LOGGING ───────────────────────────────────────────────
# Set up crash logging as early as possible so any startup error is captured.
def _write_error_log(msg):
    try:
        log_path = os.path.join(DATA_DIR, 'ar-error.log')
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"AR Time Tracker crash log\n")
            f.write(f"Version : {TRACKER_VERSION}\n")
            f.write(f"Frozen  : {IS_FROZEN}\n")
            f.write(f"DATA_DIR: {DATA_DIR}\n")
            f.write(f"STATIC  : {STATIC_DIR}\n\n")
            f.write(msg + "\n")
        print(f"\nCrash log written to: {log_path}", flush=True)
    except Exception as le:
        print(f"\nCould not write crash log: {le}", flush=True)

def _excepthook(exc_type, exc_value, exc_tb):
    import traceback
    msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(f"\nFATAL ERROR:\n{msg}", flush=True)
    _write_error_log(f"Unhandled exception:\n{msg}")
    if IS_FROZEN:
        input("\nPress Enter to exit...")
    sys.exit(1)

sys.excepthook = _excepthook

PRINTERS_FILE = os.path.join(DATA_DIR, 'printers.json')
CONFIG_FILE   = os.path.join(DATA_DIR, 'config.json')

GITHUB_REPO   = 'ScottBatemanAZ/AR-TimeTracker'
_latest_release = {'checked': False, 'available': False, 'version': '', 'url': ''}

DEFAULT_PRINTERS = {
    'fdm':   [],
    'resin': []
}

# Known filament types to scan for in filenames (order matters — longer matches first)
FILENAME_MATERIAL_PATTERNS = [
    'PETG-CF', 'PLA-CF', 'ABS-CF', 'ABS-GF', 'ASA-CF', 'PC-CF', 'PC-FR',
    'PAHT-CF', 'PA6-CF', 'PA6-GF', 'PA12-CF', 'PA-CF',
    'PETG', 'PLA+', 'PLA', 'ABS', 'ASA', 'TPU', 'TPE', 'HIPS',
    'PA6', 'PA12', 'Nylon', 'PA', 'PC', 'PVA', 'PP', 'PEEK', 'PEKK',
]

# App config — loaded from config.json (storageMode, dataPath)
app_config = {}

# Printer config — loaded from printers.json, hot-reloaded via /update-printers
printers_config = dict(DEFAULT_PRINTERS)
config_lock = threading.Lock()

# Per-printer state dict keyed by printer id
printer_states = {}   # {printerId: {status, filename, ...}}
states_lock = threading.Lock()
_last_meta = {}       # {printerId: last_filename} — avoids redundant metadata fetches

def _blank_state(name=''):
    return {"name": name, "status": "unknown", "filename": "",
            "print_duration": 0, "filament_used": 0,
            "filament_type": "", "filament_name": "",
            "estimated_time": 0,
            "last_checked": 0, "reachable": False}

def load_printers_config():
    global printers_config
    try:
        with open(PRINTERS_FILE) as f:
            data = json.load(f)
        with config_lock:
            printers_config = data
        total = sum(len(v) for v in data.values())
        print(f"  Loaded printers.json: {total} printer(s) configured")
    except FileNotFoundError:
        pass  # use defaults
    except Exception as e:
        print(f"  Warning: could not load printers.json: {e}")

def save_printers_config(config):
    global printers_config
    with open(PRINTERS_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    with config_lock:
        printers_config = config

# ── APP CONFIG ───────────────────────────────────────────────────────
def load_config():
    global app_config
    try:
        with open(CONFIG_FILE, encoding='utf-8') as f:
            app_config = json.load(f)
    except FileNotFoundError:
        app_config = {}
    except Exception as e:
        print(f"  Warning: could not load config.json: {e}")
        app_config = {}

def save_app_config(cfg):
    global app_config
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)
    app_config = cfg

# ── FILE STORAGE ──────────────────────────────────────────────────────
def resolve_data_path(data_path):
    """Resolve relative paths relative to the data directory (writable location)."""
    if not os.path.isabs(data_path):
        return os.path.join(DATA_DIR, data_path)
    return data_path

def load_data_from_path(data_path):
    """Load ar-data-live.json, falling back to the most recent dated backup."""
    resolved = resolve_data_path(data_path)
    live = os.path.join(resolved, 'ar-data-live.json')
    try:
        if os.path.exists(live):
            with open(live, encoding='utf-8') as f:
                return json.load(f)
        # Fallback: most recently modified .json in the directory
        candidates = [
            os.path.join(resolved, fn)
            for fn in os.listdir(resolved)
            if fn.endswith('.json') and fn != 'ar-data-live.json'
        ]
        if candidates:
            with open(max(candidates, key=os.path.getmtime), encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"  Warning: could not load data file from {resolved!r}: {e}")
    return None

def save_data_to_path(data_path, payload):
    """Write payload to ar-data-live.json (overwrites each time — acts as live save)."""
    resolved = resolve_data_path(data_path)
    os.makedirs(resolved, exist_ok=True)
    live = os.path.join(resolved, 'ar-data-live.json')
    with open(live, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)

# ── FILENAME FALLBACK ─────────────────────────────────────────────────
def material_from_filename(filename):
    """Extract material type from filename when metadata is unavailable."""
    base = os.path.basename(filename).upper()
    for mat in FILENAME_MATERIAL_PATTERNS:
        # Word-boundary match: surrounded by non-alphanumeric or string edges
        if re.search(r'(?<![A-Za-z0-9])' + re.escape(mat.upper()) + r'(?![A-Za-z0-9])', base):
            return mat
    return ""

# ── MOONRAKER POLLER ──────────────────────────────────────────────────
def fetch_metadata(printer_id, base_url, filename):
    """Fetch slicer-embedded filament info from Moonraker for the current file."""
    if not filename or _last_meta.get(printer_id) == filename:
        return
    filament_type = ""
    filament_name = ""
    try:
        url = f"{base_url}/server/files/metadata?filename={urllib.request.quote(filename, safe='')}"
        req = urllib.request.urlopen(url, timeout=8)
        body = json.loads(req.read().decode())
        meta = body.get("result", {})
        # OrcaSlicer / PrusaSlicer embed arrays (one entry per extruder)
        ft = meta.get("filament_type", [])
        fn = meta.get("filament_name", [])
        if isinstance(ft, list) and ft:   filament_type = ft[0]
        elif isinstance(ft, str):         filament_type = ft
        if isinstance(fn, list) and fn:   filament_name = fn[0]
        elif isinstance(fn, str):         filament_name = fn
    except Exception as e:
        print(f"  [meta:{printer_id}] fetch failed for {filename!r}: {e}")

    if not filament_type and not filament_name:
        filament_type = material_from_filename(filename)
        if filament_type:
            print(f"  [meta:{printer_id}] {filename}: inferred type={filament_type!r} from filename")
        else:
            print(f"  [meta:{printer_id}] {filename}: type unknown")
    else:
        print(f"  [meta:{printer_id}] {filename}: type={filament_type!r} name={filament_name!r}")

    estimated_time = 0
    try:
        estimated_time = float(meta.get("estimated_time", 0) or 0)
    except Exception:
        pass

    with states_lock:
        if printer_id in printer_states:
            printer_states[printer_id]["filament_type"]  = filament_type
            printer_states[printer_id]["filament_name"]  = filament_name
            printer_states[printer_id]["estimated_time"] = estimated_time
    _last_meta[printer_id] = filename

def _split_printer_url(url):
    """Split a configured printer URL into (base_url, api_key).

    OctoPrint users append `?apikey=...` to the URL — OctoPrint's own documented
    way of supplying an API key via query string. Its presence is what tells us
    we're talking to OctoPrint rather than a (keyless) Moonraker instance, so
    no separate "printer type" setting is needed — just the one URL field.
    """
    parsed  = urllib.parse.urlsplit((url or '').strip())
    api_key = (urllib.parse.parse_qs(parsed.query).get('apikey') or [''])[0]
    base    = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), '', ''))
    return base, api_key

def poll_moonraker(printer, base_url):
    """Poll a single Moonraker instance and update its state entry."""
    pid       = printer['id']
    query_url = f"{base_url}/printer/objects/query?print_stats"
    try:
        req  = urllib.request.urlopen(query_url, timeout=8)
        body = json.loads(req.read().decode())
        ps   = body.get("result", {}).get("status", {}).get("print_stats", {})
        with states_lock:
            printer_states[pid].update({
                "status":         ps.get("state", "unknown"),
                "filename":       ps.get("filename", ""),
                "print_duration": ps.get("print_duration", 0),
                "filament_used":  ps.get("filament_used", 0),
                "last_checked":   time.time(),
                "reachable":      True,
            })
            filename = printer_states[pid]["filename"]
        if filename:
            fetch_metadata(pid, base_url, filename)
    except Exception:
        with states_lock:
            printer_states[pid].update({
                "status":       "unreachable",
                "last_checked": time.time(),
                "reachable":    False,
            })

def poll_octoprint(printer, base_url, api_key):
    """Poll a single OctoPrint instance (via /api/job) and update its state entry.

    OctoPrint doesn't expose slicer filament metadata the way Moonraker does, so
    material type falls back to material_from_filename() — same as the Moonraker
    path takes for slicers whose metadata Moonraker can't parse.
    """
    pid = printer['id']
    try:
        req  = urllib.request.Request(f"{base_url}/api/job", headers={'X-Api-Key': api_key})
        body = json.loads(urllib.request.urlopen(req, timeout=8).read().decode())
        job      = body.get('job', {}) or {}
        progress = body.get('progress', {}) or {}
        state    = (body.get('state') or '').lower()

        if 'printing' in state:               status = 'printing'
        elif 'paus' in state:                 status = 'paused'
        elif 'cancelling' in state:           status = 'cancelled'
        elif 'error' in state or 'closed' in state: status = 'error'
        else:                                 status = 'standby'

        filename = ((job.get('file') or {}).get('name')) or ''
        filament = job.get('filament') or {}
        tool0    = filament.get('tool0') or (next(iter(filament.values()), {}) or {})

        with states_lock:
            printer_states[pid].update({
                "status":         status,
                "filename":       filename,
                "print_duration": progress.get('printTime', 0) or 0,
                "filament_used":  tool0.get('length', 0) or 0,
                "filament_type":  material_from_filename(filename) if filename else "",
                "filament_name":  "",
                "estimated_time": job.get('estimatedPrintTime', 0) or 0,
                "last_checked":   time.time(),
                "reachable":      True,
            })
    except Exception:
        with states_lock:
            printer_states[pid].update({
                "status":       "unreachable",
                "last_checked": time.time(),
                "reachable":    False,
            })

def poll_printer(printer):
    """Poll a single printer — Moonraker or OctoPrint, auto-detected from its URL
    (see _split_printer_url) — and update its shared printer_states entry."""
    pid = printer['id']
    with states_lock:
        if pid not in printer_states:
            printer_states[pid] = _blank_state(printer.get('name', pid))

    base_url, api_key = _split_printer_url(printer.get('moonrakerUrl', ''))
    if api_key:
        poll_octoprint(printer, base_url, api_key)
    else:
        poll_moonraker(printer, base_url)

def poll_all_printers():
    """Background thread — polls every configured printer once per interval."""
    while True:
        with config_lock:
            all_printers = list(printers_config.get('fdm', [])) + list(printers_config.get('resin', []))
        for printer in all_printers:
            poll_printer(printer)
        time.sleep(POLL_INTERVAL)

# ── SPOOLMAN PROXY ────────────────────────────────────────────────────
# Browser → Spoolman direct calls would hit CORS; the server proxies instead
# (same reason Moonraker is polled server-side and exposed via /printer-status).
def spoolman_call(base_url, path, method='GET', body=None, timeout=8):
    url     = f"{base_url.rstrip('/')}/api/v1{path}"
    data    = json.dumps(body).encode() if body is not None else None
    headers = {'Content-Type': 'application/json'} if data is not None else {}
    req     = urllib.request.Request(url, data=data, method=method, headers=headers)
    raw     = urllib.request.urlopen(req, timeout=timeout).read().decode()
    return json.loads(raw) if raw else {}

# ── ODS GENERATOR ────────────────────────────────────────────────────
def generate_ods(payload):
    """Build a 5-tab ODS spreadsheet from project+settings data. Returns bytes."""
    proj       = payload.get('project', {})
    sett       = payload.get('settings', {})
    markup_pct = float(payload.get('markupPct', 3))
    labor_rate = float(sett.get('laborRate', 40))
    fdm_rate   = float(sett.get('fdmRate', 5))
    resin_rate = float(sett.get('resinRate', 2))
    elec_rate  = float(sett.get('electricityRate', 0.12))
    fdm_printers   = {p['id']: p for p in sett.get('fdmPrinters',   [])}
    resin_printers = {p['id']: p for p in sett.get('resinPrinters', [])}
    proj_name  = proj.get('name', 'Project')

    # ── helpers ───────────────────────────────────────────────────────────
    def xe(s):
        return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

    def ts_date(ts):  return datetime.fromtimestamp(int(ts)/1000).strftime('%Y-%m-%d')
    def ts_time(ts):  return datetime.fromtimestamp(int(ts)/1000).strftime('%H:%M')

    def ms_hm(ms):
        h = int(ms // 3600000); m = int((ms % 3600000) // 60000)
        return f'{h}h {m:02d}m'

    def ms_hrs(ms): return ms / 3600000

    def fil_cost(s):
        g = float(s.get('filamentG') or 0); c = float(s.get('filamentCostPerKg') or 0)
        return (g / 1000) * c if g > 0 and c > 0 else 0.0

    def res_cost(s):
        ml = float(s.get('resinMl') or 0); c = float(s.get('resinCostPerKg') or 0)
        d  = float(s.get('resinDensity') or 1.10)
        return (ml * d / 1000) * c if ml > 0 and c > 0 else float(s.get('resinCost') or 0)

    def elec_cost(s, printer_map):
        pid   = s.get('printerId', '')
        watt  = float((printer_map.get(pid) or {}).get('wattage') or 0)
        ms    = int(s.get('end', s.get('start', 0))) - int(s.get('start', 0))
        return ms_hrs(ms) * (watt / 1000) * elec_rate

    # ── cell / row / sheet builders ───────────────────────────────────────
    def sc(v, sty=''):
        sa = f' table:style-name="{sty}"' if sty else ''
        if v is None or str(v).strip() == '':
            return f'<table:table-cell{sa}/>'
        return f'<table:table-cell office:value-type="string"{sa}><text:p>{xe(str(v))}</text:p></table:table-cell>'

    def nc(v, dec=2, sty=''):
        sa = f' table:style-name="{sty}"' if sty else ''
        try:    fv = float(v)
        except: return f'<table:table-cell{sa}/>'
        return f'<table:table-cell office:value-type="float" office:value="{fv}"{sa}><text:p>{fv:.{dec}f}</text:p></table:table-cell>'

    def cc(v, sty=''):
        sa = f' table:style-name="{sty}"' if sty else ''
        try:    fv = float(v)
        except: return f'<table:table-cell{sa}/>'
        return f'<table:table-cell office:value-type="currency" office:currency="USD" office:value="{fv}"{sa}><text:p>${fv:.2f}</text:p></table:table-cell>'

    def row(*cells):   return '<table:table-row>' + ''.join(cells) + '</table:table-row>'
    def blank():       return '<table:table-row><table:table-cell/></table:table-row>'
    def mksheet(name, rows, ncols=11):
        cols = f'<table:table-column table:style-name="CO" table:number-columns-repeated="{ncols}"/>'
        return f'<table:table table:name="{xe(name)}">{cols}{"".join(rows)}</table:table>'

    B, H = 'B', 'H'   # bold, header style shorthand

    # ── DESIGN tab ────────────────────────────────────────────────────────
    d_sess = sorted([s for s in (proj.get('designSessions') or []) if s.get('end')],
                    key=lambda s: s.get('start', 0))
    d_rows = [
        row(sc(f'Design Time — {proj_name}', B)),
        row(sc(f'Labor Rate: ${labor_rate:.2f}/hr')),
        blank(),
        row(sc('Date',H), sc('Start',H), sc('End',H), sc('Duration',H), sc('Subtype',H), sc('Cost',H), sc('Note',H)),
    ]
    d_ms = 0; sub_tots = {}
    for s in d_sess:
        ms   = int(s['end']) - int(s['start']); hrs = ms_hrs(ms)
        cost = hrs * labor_rate
        sub  = (s.get('designSubtype') or 'unspecified').replace('-',' ').title()
        note = s.get('note') or ''
        d_ms += ms
        sub_tots.setdefault(sub, {'ms':0,'cost':0.0})
        sub_tots[sub]['ms'] += ms; sub_tots[sub]['cost'] += cost
        d_rows.append(row(sc(ts_date(s['start'])), sc(ts_time(s['start'])), sc(ts_time(s['end'])),
                          sc(ms_hm(ms)), sc(sub), cc(cost), sc(note)))
    d_rows += [blank(), row(sc('Subtotals by Type', B)),
               row(sc('Subtype',H), sc('',H), sc('',H), sc('Duration',H), sc('',H), sc('Cost',H))]
    for sub, t in sub_tots.items():
        d_rows.append(row(sc(sub), sc(''), sc(''), sc(ms_hm(t['ms'])), sc(''), cc(t['cost'])))
    d_rows.append(row(sc('Total',B), sc(''), sc(''), sc(ms_hm(d_ms),B), sc(''), cc(ms_hrs(d_ms)*labor_rate, B)))
    design_total = ms_hrs(d_ms) * labor_rate

    # ── FDM tab ───────────────────────────────────────────────────────────
    f_sess = sorted([s for s in (proj.get('fdmSessions') or []) if s.get('end')],
                    key=lambda s: s.get('start', 0))
    f_rows = [
        row(sc(f'FDM Sessions — {proj_name}', B)),
        row(sc(f'Machine Rate: ${fdm_rate:.2f}/hr  |  Electricity: ${elec_rate:.3f}/kWh')),
        blank(),
        row(sc('Date',H), sc('Start',H), sc('End',H), sc('Duration',H), sc('Material',H),
            sc('Grams',H), sc('$/kg',H), sc('Fil. Cost',H), sc('Machine Cost',H), sc('Elec. Cost',H), sc('Total',H), sc('Note',H)),
    ]
    f_ms = 0; f_fil = 0.0; f_mach = 0.0; f_g = 0.0; f_elec = 0.0; f_mat_tots = {}
    f_failed_cost = 0.0
    for s in f_sess:
        ms   = int(s['end']) - int(s['start']); mach = ms_hrs(ms) * fdm_rate
        fc   = fil_cost(s); ec = elec_cost(s, fdm_printers)
        g    = float(s.get('filamentG') or 0)
        cpkg = float(s.get('filamentCostPerKg') or 0)
        mat  = (s.get('filamentType') or '—') + (' ⚠FAILED' if s.get('failed') else '')
        f_ms += ms; f_fil += fc; f_mach += mach; f_g += g; f_elec += ec
        if s.get('failed'): f_failed_cost += fc + mach + ec
        f_mat_tots.setdefault(mat, {'ms':0,'g':0.0,'fil':0.0,'mach':0.0,'elec':0.0})
        f_mat_tots[mat]['ms'] += ms; f_mat_tots[mat]['g'] += g
        f_mat_tots[mat]['fil'] += fc; f_mat_tots[mat]['mach'] += mach; f_mat_tots[mat]['elec'] += ec
        f_rows.append(row(
            sc(ts_date(s['start'])), sc(ts_time(s['start'])), sc(ts_time(s['end'])),
            sc(ms_hm(ms)), sc(mat),
            nc(g,2) if g else sc('—'), nc(cpkg,2) if cpkg else sc('—'),
            cc(fc) if fc else sc('—'), cc(mach), cc(ec) if ec else sc('—'), cc(fc+mach+ec),
            sc(s.get('note') or '')))
    f_rows += [blank(), row(sc('Subtotals by Material', B)),
               row(sc('Material',H), sc('',H), sc('',H), sc('Duration',H), sc('Grams',H),
                   sc('',H), sc('',H), sc('Fil. Cost',H), sc('Machine Cost',H), sc('Elec. Cost',H), sc('Total',H))]
    for mat, t in f_mat_tots.items():
        f_rows.append(row(sc(mat), sc(''), sc(''), sc(ms_hm(t['ms'])), nc(t['g'],2),
                          sc(''), sc(''), cc(t['fil']), cc(t['mach']), cc(t['elec']), cc(t['fil']+t['mach']+t['elec'])))
    f_rows.append(row(sc('Total',B), sc(''), sc(''), sc(ms_hm(f_ms),B), nc(f_g,2,B),
                      sc(''), sc(''), cc(f_fil,B), cc(f_mach,B), cc(f_elec,B), cc(f_fil+f_mach+f_elec,B)))
    fdm_total = f_fil + f_mach + f_elec

    # ── RESIN tab ─────────────────────────────────────────────────────────
    r_sess = sorted([s for s in (proj.get('resinSessions') or []) if s.get('end')],
                    key=lambda s: s.get('start', 0))
    r_rows = [
        row(sc(f'Resin Sessions — {proj_name}', B)),
        row(sc(f'Machine Rate: ${resin_rate:.2f}/hr  |  Electricity: ${elec_rate:.3f}/kWh')),
        blank(),
        row(sc('Date',H), sc('Start',H), sc('End',H), sc('Duration',H), sc('Material',H),
            sc('mL',H), sc('$/kg',H), sc('Density',H), sc('Mat. Cost',H), sc('Machine Cost',H), sc('Elec. Cost',H), sc('Total',H), sc('Note',H)),
    ]
    r_ms = 0; r_mat = 0.0; r_mach = 0.0; r_ml = 0.0; r_elec = 0.0; r_mat_tots = {}
    r_failed_cost = 0.0
    for s in r_sess:
        ms   = int(s['end']) - int(s['start']); mach = ms_hrs(ms) * resin_rate
        rc   = res_cost(s); ec = elec_cost(s, resin_printers)
        ml   = float(s.get('resinMl') or 0)
        cpkg = float(s.get('resinCostPerKg') or 0); dens = float(s.get('resinDensity') or 1.10)
        mat  = (s.get('resinType') or '—') + (' ⚠FAILED' if s.get('failed') else '')
        r_ms += ms; r_mat += rc; r_mach += mach; r_ml += ml; r_elec += ec
        if s.get('failed'): r_failed_cost += rc + mach + ec
        r_mat_tots.setdefault(mat, {'ms':0,'ml':0.0,'mat':0.0,'mach':0.0,'elec':0.0})
        r_mat_tots[mat]['ms'] += ms; r_mat_tots[mat]['ml'] += ml
        r_mat_tots[mat]['mat'] += rc; r_mat_tots[mat]['mach'] += mach; r_mat_tots[mat]['elec'] += ec
        r_rows.append(row(
            sc(ts_date(s['start'])), sc(ts_time(s['start'])), sc(ts_time(s['end'])),
            sc(ms_hm(ms)), sc(mat),
            nc(ml,2) if ml else sc('—'), nc(cpkg,2) if cpkg else sc('—'), nc(dens,2),
            cc(rc) if rc else sc('—'), cc(mach), cc(ec) if ec else sc('—'), cc(rc+mach+ec),
            sc(s.get('note') or '')))
    r_rows += [blank(), row(sc('Subtotals by Material', B)),
               row(sc('Material',H), sc('',H), sc('',H), sc('Duration',H), sc('mL',H),
                   sc('',H), sc('',H), sc('',H), sc('Mat. Cost',H), sc('Machine Cost',H), sc('Elec. Cost',H), sc('Total',H))]
    for mat, t in r_mat_tots.items():
        r_rows.append(row(sc(mat), sc(''), sc(''), sc(ms_hm(t['ms'])), nc(t['ml'],2),
                          sc(''), sc(''), sc(''), cc(t['mat']), cc(t['mach']), cc(t['elec']), cc(t['mat']+t['mach']+t['elec'])))
    r_rows.append(row(sc('Total',B), sc(''), sc(''), sc(ms_hm(r_ms),B), nc(r_ml,2,B),
                      sc(''), sc(''), sc(''), cc(r_mat,B), cc(r_mach,B), cc(r_elec,B), cc(r_mat+r_mach+r_elec,B)))
    resin_total = r_mat + r_mach + r_elec

    # ── RECEIPTS tab ──────────────────────────────────────────────────────
    receipts = proj.get('receipts') or []
    rec_rows = [
        row(sc(f'Receipts / Expenses — {proj_name}', B)),
        blank(),
        row(sc('Description',H), sc('Amount',H)),
    ]
    rec_total = 0.0
    for r_ in receipts:
        amt = float(r_.get('amount') or 0); rec_total += amt
        rec_rows.append(row(sc(r_.get('desc','')), cc(amt)))
    if not receipts:
        rec_rows.append(row(sc('No receipts recorded.')))
    rec_rows += [blank(), row(sc('Total',B), cc(rec_total,B))]

    # ── SUMMARY tab ───────────────────────────────────────────────────────
    actual      = design_total + fdm_total + resin_total + rec_total
    markup_amt  = actual * (markup_pct / 100)
    grand_total = actual + markup_amt
    gen_dt      = datetime.now().strftime('%Y-%m-%d %H:%M')
    s_rows = [
        row(sc(f'{proj_name} — AR Tracking Log', B)),
        row(sc(f'Generated: {gen_dt}')),
        blank(),
        row(sc('Track',H),              sc('Hours / Units',H),                  sc('Actual Cost',H)),
        row(sc('Design Labor'),         sc(f'{ms_hrs(d_ms):.2f} hrs'),          cc(design_total)),
        row(sc('FDM Machine Time'),     sc(f'{ms_hrs(f_ms):.2f} hrs'),          cc(f_mach)),
        row(sc('FDM Filament'),         sc(f'{f_g:.1f}g'),                       cc(f_fil)),
        row(sc('FDM Electricity'),      sc(f'{elec_rate:.3f}/kWh'),              cc(f_elec)),
        row(sc('Resin Machine Time'),   sc(f'{ms_hrs(r_ms):.2f} hrs'),          cc(r_mach)),
        row(sc('Resin Material'),       sc(f'{r_ml:.1f} mL'),                    cc(r_mat)),
        row(sc('Resin Electricity'),    sc(f'{elec_rate:.3f}/kWh'),              cc(r_elec)),
        row(sc('Receipts / Expenses'),  sc(''),                                  cc(rec_total)),
        blank(),
        row(sc('Subtotal',B),           sc(''),                                  cc(actual,B)),
        row(sc(f'Markup ({markup_pct:.1f}%)'), sc(''),                           cc(markup_amt)),
        row(sc('Total (with markup)',B),sc(''),                                  cc(grand_total,B)),
    ]
    if f_failed_cost or r_failed_cost:
        s_rows.append(blank())
        s_rows.append(row(sc('— Failed Prints (not billed, included above) —')))
        if f_failed_cost:
            s_rows.append(row(sc('Failed FDM Prints'), sc(''), cc(-f_failed_cost)))
        if r_failed_cost:
            s_rows.append(row(sc('Failed Resin Prints'), sc(''), cc(-r_failed_cost)))

    # ── ASSEMBLE XML ──────────────────────────────────────────────────────
    auto_styles = '''
  <style:style style:name="CO" style:family="table-column">
    <style:table-column-properties style:use-optimal-column-width="true"/>
  </style:style>
  <style:style style:name="B" style:family="table-cell">
    <style:text-properties fo:font-weight="bold" fo:font-weight-asian="bold" fo:font-weight-complex="bold"/>
  </style:style>
  <style:style style:name="H" style:family="table-cell">
    <style:table-cell-properties fo:background-color="#26262b"/>
    <style:text-properties fo:font-weight="bold" fo:font-weight-asian="bold" fo:font-weight-complex="bold" fo:color="#e8e8ec"/>
  </style:style>'''

    content = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
  xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
  xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
  xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
  xmlns:number="urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0"
  office:version="1.2">
  <office:automatic-styles>{auto_styles}
  </office:automatic-styles>
  <office:body><office:spreadsheet>
    {mksheet("Summary",  s_rows,  ncols=3)}
    {mksheet("Design",   d_rows,  ncols=7)}
    {mksheet("FDM",      f_rows,  ncols=12)}
    {mksheet("Resin",    r_rows,  ncols=13)}
    {mksheet("Receipts", rec_rows,ncols=2)}
  </office:spreadsheet></office:body>
</office:document-content>'''

    manifest = '''<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">
  <manifest:file-entry manifest:full-path="/" manifest:version="1.2" manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/>
  <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
</manifest:manifest>'''

    styles = '<?xml version="1.0" encoding="UTF-8"?>\n<office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" office:version="1.2"></office:document-styles>'

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        mi = zipfile.ZipInfo('mimetype'); mi.compress_type = zipfile.ZIP_STORED
        zf.writestr(mi, 'application/vnd.oasis.opendocument.spreadsheet')
        zf.writestr('META-INF/manifest.xml', manifest)
        zf.writestr('styles.xml', styles)
        zf.writestr('content.xml', content)
    return buf.getvalue()

# ── HTTP HANDLER ──────────────────────────────────────────────────────
# File extensions that should never be cached (app files)
NO_CACHE_EXTS = {'.html', '.js', '.css', '.json'}

_SILENT_ERRORS = (ConnectionAbortedError, BrokenPipeError, ConnectionResetError)

class QuietTCPServer(socketserver.TCPServer):
    """TCPServer that silently drops harmless browser-closed-connection errors."""
    def handle_error(self, request, client_address):
        exc_type = sys.exc_info()[0]
        if exc_type and issubclass(exc_type, _SILENT_ERRORS):
            return
        super().handle_error(request, client_address)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def _send_json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(length).decode())

    def do_POST(self):
        if self.path == '/spoolman/check':
            try:
                url = (self._read_json_body().get('url') or '').strip()
                if not url:
                    raise ValueError('No URL provided')
                spoolman_call(url, '/health')
                version = ''
                try:
                    version = spoolman_call(url, '/info').get('version', '')
                except Exception:
                    pass
                self._send_json({'ok': True, 'version': version})
            except Exception as e:
                self._send_json({'ok': False, 'error': str(e)})
            return
        if self.path == '/spoolman/spools':
            try:
                url = (self._read_json_body().get('url') or '').strip()
                if not url:
                    raise ValueError('No URL provided')
                spools  = spoolman_call(url, '/spool?allow_archived=false')
                trimmed = [{
                    'id':               s.get('id'),
                    'name':             (s.get('filament') or {}).get('name') or f"Spool #{s.get('id')}",
                    'material':         (s.get('filament') or {}).get('material') or '',
                    'vendor':           ((s.get('filament') or {}).get('vendor') or {}).get('name') or '',
                    'remaining_weight': s.get('remaining_weight'),
                } for s in spools]
                self._send_json({'ok': True, 'spools': trimmed})
            except Exception as e:
                self._send_json({'ok': False, 'error': str(e), 'spools': []})
            return
        if self.path == '/spoolman/use':
            try:
                payload  = self._read_json_body()
                url      = (payload.get('url') or '').strip()
                spool_id = int(payload.get('spoolId'))
                grams    = float(payload.get('grams'))
                if not url or grams <= 0:
                    raise ValueError('Missing url or grams')
                updated = spoolman_call(url, f'/spool/{spool_id}/use', method='PUT', body={'use_weight': grams})
                self._send_json({'ok': True, 'remaining_weight': updated.get('remaining_weight')})
            except Exception as e:
                self._send_json({'ok': False, 'error': str(e)})
            return
        if self.path == '/save-config':
            try:
                length = int(self.headers.get('Content-Length', 0))
                cfg    = json.loads(self.rfile.read(length).decode())
                save_app_config(cfg)
                mode = cfg.get('storageMode', 'local')
                path = cfg.get('dataPath', '')
                print(f"  Config saved: storageMode={mode!r}" + (f", dataPath={path!r}" if path else ''))
                body = b'{"ok":true}'
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(str(e).encode())
            return
        if self.path == '/save-data':
            try:
                length  = int(self.headers.get('Content-Length', 0))
                payload = json.loads(self.rfile.read(length).decode())
                data_path = app_config.get('dataPath', '')
                if data_path:
                    save_data_to_path(data_path, payload)
                body = b'{"ok":true}'
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(str(e).encode())
            return
        if self.path == '/update-printers':
            try:
                length = int(self.headers.get('Content-Length', 0))
                config = json.loads(self.rfile.read(length).decode())
                save_printers_config(config)
                body = b'{"ok":true}'
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(str(e).encode())
            return
        if self.path == '/generate-ods':
            try:
                length  = int(self.headers.get('Content-Length', 0))
                payload = json.loads(self.rfile.read(length).decode())
                ods     = generate_ods(payload)
                safe    = ''.join(c if c.isalnum() or c in '-_' else '_'
                                  for c in payload.get('project',{}).get('name','Project'))
                fname   = f'AR-TrackingLog-{safe}.ods'
                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.oasis.opendocument.spreadsheet')
                self.send_header('Content-Disposition', f'attachment; filename="{fname}"')
                self.send_header('Content-Length', str(len(ods)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(ods)
                self.wfile.flush()
            except Exception as e:
                import traceback; traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == '/app-config':
            mode = app_config.get('storageMode')
            body = json.dumps({
                'configured': mode is not None,
                'storageMode': mode or 'local',
                'dataPath':    app_config.get('dataPath', ''),
            }).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == '/load-data':
            data_path = app_config.get('dataPath', '')
            loaded = load_data_from_path(data_path) if data_path else None
            body = json.dumps(loaded or {}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == '/release-info':
            body = json.dumps(_latest_release).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/printer-status":
            with states_lock:
                payload = json.dumps(printer_states).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(payload)
        else:
            super().do_GET()

    def end_headers(self):
        # Add no-cache headers for app files so hard refresh always works
        ext = os.path.splitext(self.path.split('?')[0])[1].lower()
        if ext in NO_CACHE_EXTS:
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, format, *args):
        pass  # suppress request logging

    def log_error(self, format, *args):
        # Suppress harmless "browser closed the connection" noise from the ZIP server
        msg = format % args if args else format
        if 'WinError 10053' in msg or 'ConnectionAbortedError' in msg or 'BrokenPipe' in msg:
            return
        print(f'[server error] {msg}')

# ── STARTUP ───────────────────────────────────────────────────────────
def get_lan_ip():
    """Return the machine's LAN IP by probing an outbound connection."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None

def _version_tuple(v):
    """Parse version string like 'Beta 10.2.1' or 'v10.2.1' into a comparable tuple."""
    nums = re.findall(r'\d+', v)
    return tuple(int(x) for x in nums) if nums else (0,)

def check_latest_release():
    """Check GitHub releases API for a newer version. Runs in a background thread."""
    global _latest_release
    try:
        url = f'https://api.github.com/repos/{GITHUB_REPO}/releases/latest'
        req = urllib.request.Request(url, headers={'User-Agent': f'AR-TimeTracker/{TRACKER_VERSION}'})
        resp = urllib.request.urlopen(req, timeout=8)
        data = json.loads(resp.read().decode())
        tag  = data.get('tag_name', '').lstrip('v')
        html = data.get('html_url', f'https://github.com/{GITHUB_REPO}/releases/latest')
        if tag and _version_tuple(tag) > _version_tuple(TRACKER_VERSION):
            _latest_release = {'checked': True, 'available': True,
                               'version': tag, 'url': html}
            print(f"  ⬆  Update available: v{tag}  →  {html}", flush=True)
        else:
            _latest_release = {'checked': True, 'available': False,
                               'version': tag, 'url': html}
            if tag:
                print(f"  Up to date (latest release: v{tag})", flush=True)
    except urllib.error.HTTPError as e:
        _latest_release = {'checked': True, 'available': False, 'version': '', 'url': ''}
        if e.code == 404:
            print("  No GitHub release published yet", flush=True)
        else:
            print(f"  Release check skipped: HTTP {e.code}", flush=True)
    except Exception as e:
        _latest_release = {'checked': True, 'available': False, 'version': '', 'url': ''}
        print(f"  Release check skipped: {e}", flush=True)

def check_for_updates():
    """Git-based auto-update: fetch → pull → re-exec. Skipped in frozen/EXE mode."""
    if IS_FROZEN:
        # EXE build — no git, no source to pull. Use check_latest_release() instead.
        threading.Thread(target=check_latest_release, daemon=True).start()
        return
    try:
        # Confirm we're inside a git repo
        subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            cwd=DATA_DIR, capture_output=True, check=True, timeout=5
        )
        print("  Checking for updates...", flush=True)
        fetch = subprocess.run(
            ['git', 'fetch', 'origin'],
            cwd=DATA_DIR, capture_output=True, timeout=20
        )
        if fetch.returncode != 0:
            print("  Could not reach remote — skipping update check", flush=True)
            threading.Thread(target=check_latest_release, daemon=True).start()
            return
        local  = subprocess.run(['git', 'rev-parse', 'HEAD'],
                                cwd=DATA_DIR, capture_output=True, text=True, timeout=5)
        remote = subprocess.run(['git', 'rev-parse', '@{u}'],
                                cwd=DATA_DIR, capture_output=True, text=True, timeout=5)
        if local.stdout.strip() == remote.stdout.strip():
            print("  Up to date", flush=True)
            return
        print("  New version found — pulling updates...", flush=True)
        subprocess.run(['git', 'pull'], cwd=DATA_DIR, check=True, timeout=30)
        print("  Restarting with updated code...\n", flush=True)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except FileNotFoundError:
        print("  git not found — skipping auto-update", flush=True)
        threading.Thread(target=check_latest_release, daemon=True).start()
    except subprocess.CalledProcessError:
        print("  Not a git repo — skipping auto-update", flush=True)
        threading.Thread(target=check_latest_release, daemon=True).start()
    except Exception as e:
        print(f"  Update check skipped: {e}", flush=True)
        threading.Thread(target=check_latest_release, daemon=True).start()

def open_browser():
    # Poll until the server is actually accepting connections before opening the browser.
    # In a frozen EXE, startup takes longer than the old 0.6s fixed delay.
    for _ in range(40):
        try:
            s = socket.create_connection(('127.0.0.1', PORT), timeout=0.5)
            s.close()
            break
        except OSError:
            time.sleep(0.25)
    webbrowser.open(f"http://127.0.0.1:{PORT}")

def shutdown(sig, frame):
    print("\n  Server stopped.")
    sys.exit(0)

signal.signal(signal.SIGINT,  shutdown)
signal.signal(signal.SIGTERM, shutdown)

def _fatal(msg, exc=None):
    """Write a crash report next to the exe/script and pause the console."""
    log_path = os.path.join(DATA_DIR, 'ar-error.log')
    lines = [
        f"AR Time Tracker — startup error\n",
        f"Version : {TRACKER_VERSION}\n",
        f"Build   : {'EXE (frozen)' if IS_FROZEN else 'Python (source)'}\n",
        f"Time    : {datetime.now().isoformat()}\n\n",
        f"{msg}\n",
    ]
    if exc:
        import traceback
        lines.append(traceback.format_exc())
    try:
        with open(log_path, 'w') as f:
            f.writelines(lines)
        print(f"\n  Error log written to: {log_path}", flush=True)
    except Exception:
        pass
    print(f"\n  FATAL: {msg}", flush=True)
    if IS_FROZEN:
        input("\n  Press Enter to exit...\n")
    sys.exit(1)

try:
    check_for_updates()
    load_config()
    load_printers_config()
except Exception as _e:
    _fatal(f"Startup failed during init: {_e}", _e)

all_fdm   = printers_config.get('fdm', [])
all_resin = printers_config.get('resin', [])
lan_ip    = get_lan_ip()
build_type = 'EXE (standalone)' if IS_FROZEN else 'Python (source)'
print(f"\n  Azazel's Razer Time Tracker")
print(f"  Server v{SERVER_VERSION} running AR Tracker v{TRACKER_VERSION}  [{build_type}]")
print(f"  Local  →  http://localhost:{PORT}")
if lan_ip:
    print(f"  LAN    →  http://{lan_ip}:{PORT}")
storage_mode = app_config.get('storageMode')
if storage_mode == 'file':
    print(f"  Storage → file  ({app_config.get('dataPath','')})")
elif storage_mode == 'local':
    print(f"  Storage → localStorage (browser)")
else:
    print(f"  Storage → not configured (first-run modal will appear)")
for p in all_fdm:
    print(f"  FDM   [{p['id']}] {p['name']}  →  {p['moonrakerUrl']}")
for p in all_resin:
    print(f"  Resin [{p['id']}] {p['name']}  →  {p['moonrakerUrl']}")
if not all_fdm and not all_resin:
    print(f"  No printers configured — add them in Settings")
print(f"  Polling every {POLL_INTERVAL}s  |  Press Ctrl+C to stop\n")

try:
    socketserver.TCPServer.allow_reuse_address = True
    threading.Thread(target=poll_all_printers, daemon=True).start()
    if not os.environ.get('DOCKER'):
        threading.Thread(target=open_browser, daemon=True).start()

    with QuietTCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()
except OSError as _e:
    if 'address already in use' in str(_e).lower() or _e.errno == 10048:
        _fatal(f"Port {PORT} is already in use.\n\n"
               f"  Another instance of AR Time Tracker (or another app) is already\n"
               f"  running on port {PORT}. Close it and try again.", _e)
    else:
        _fatal(f"Could not start server: {_e}", _e)
except Exception as _e:
    _fatal(f"Unexpected server error: {_e}", _e)
