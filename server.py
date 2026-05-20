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
import json
import time
import io
import zipfile
from datetime import datetime

PORT = 5757
DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_VERSION  = "1.1"
TRACKER_VERSION = "8.2"
MOONRAKER_IP = "192.168.0.74"
MOONRAKER_URL      = f"http://{MOONRAKER_IP}/printer/objects/query?print_stats"
MOONRAKER_META_URL = f"http://{MOONRAKER_IP}/server/files/metadata?filename={{filename}}"
# print_stats returns: state, filename, print_duration, filament_used (mm)
POLL_INTERVAL = 5  # seconds

# Known filament types to scan for in filenames (order matters — longer matches first)
FILENAME_MATERIAL_PATTERNS = [
    'PETG-CF', 'PLA-CF', 'ABS-CF', 'ASA-CF', 'PC-CF', 'PA-CF',
    'PETG', 'PLA+', 'PLA', 'ABS', 'ASA', 'TPU', 'TPE', 'HIPS',
    'Nylon', 'PC', 'PVA', 'PP', 'PEEK',
]

# Shared printer state — read by HTTP handler, written by poller thread
printer_state = {
    "status": "unknown",
    "filename": "",
    "print_duration": 0,
    "filament_used": 0,
    "filament_type": "",   # from G-code metadata or filename parse
    "filament_name": "",   # from G-code metadata
    "last_checked": 0,
    "reachable": False
}
state_lock = threading.Lock()
_last_meta_filename = ""   # track which file we last fetched metadata for

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
def fetch_metadata(filename):
    """Fetch slicer-embedded filament info from Moonraker for the current file."""
    global _last_meta_filename
    if not filename or filename == _last_meta_filename:
        return
    filament_type = ""
    filament_name = ""
    try:
        url = MOONRAKER_META_URL.format(filename=urllib.request.quote(filename, safe=''))
        req = urllib.request.urlopen(url, timeout=8)
        body = json.loads(req.read().decode())
        meta = body.get("result", {})
        # OrcaSlicer / PrusaSlicer embed arrays (one entry per extruder)
        ft = meta.get("filament_type", [])
        fn = meta.get("filament_name", [])
        if isinstance(ft, list) and ft:
            filament_type = ft[0]
        elif isinstance(ft, str):
            filament_type = ft
        if isinstance(fn, list) and fn:
            filament_name = fn[0]
        elif isinstance(fn, str):
            filament_name = fn
    except Exception as e:
        print(f"  [meta] fetch failed for {filename!r}: {e}")

    # Fallback: parse material from filename if metadata came back empty
    if not filament_type and not filament_name:
        filament_type = material_from_filename(filename)
        if filament_type:
            print(f"  [meta] {filename}: metadata empty — inferred type={filament_type!r} from filename")
        else:
            print(f"  [meta] {filename}: type={filament_type!r} name={filament_name!r}")
    else:
        print(f"  [meta] {filename}: type={filament_type!r} name={filament_name!r}")

    with state_lock:
        printer_state["filament_type"] = filament_type
        printer_state["filament_name"] = filament_name
    _last_meta_filename = filename

def poll_moonraker():
    while True:
        try:
            req = urllib.request.urlopen(MOONRAKER_URL, timeout=8)
            body = json.loads(req.read().decode())
            ps = body.get("result", {}).get("status", {}).get("print_stats", {})
            status         = ps.get("state", "unknown")
            filename       = ps.get("filename", "")
            print_duration = ps.get("print_duration", 0)   # seconds actually printing
            filament_used  = ps.get("filament_used", 0)    # mm extruded
            with state_lock:
                printer_state["status"]         = status
                printer_state["filename"]       = filename
                printer_state["print_duration"] = print_duration
                printer_state["filament_used"]  = filament_used
                printer_state["last_checked"]   = time.time()
                printer_state["reachable"]      = True
            if filename:
                fetch_metadata(filename)
        except Exception:
            with state_lock:
                printer_state["status"]       = "unreachable"
                printer_state["last_checked"] = time.time()
                printer_state["reachable"]    = False
        time.sleep(POLL_INTERVAL)

# ── ODS GENERATOR ────────────────────────────────────────────────────
def generate_ods(payload):
    """Build a 5-tab ODS spreadsheet from project+settings data. Returns bytes."""
    proj       = payload.get('project', {})
    sett       = payload.get('settings', {})
    markup_pct = float(payload.get('markupPct', 3))
    labor_rate = float(sett.get('laborRate', 40))
    fdm_rate   = float(sett.get('fdmRate', 5))
    resin_rate = float(sett.get('resinRate', 2))
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
    def mksheet(name, rows): return f'<table:table table:name="{xe(name)}">{"".join(rows)}</table:table>'

    B, H = 'B', 'H'   # bold, header style shorthand

    # ── DESIGN tab ────────────────────────────────────────────────────────
    d_sess = sorted([s for s in (proj.get('designSessions') or []) if s.get('end')],
                    key=lambda s: s.get('start', 0))
    d_rows = [
        row(sc(f'Design Time — {proj_name}', B)),
        row(sc(f'Labor Rate: ${labor_rate:.2f}/hr')),
        blank(),
        row(sc('Date',H), sc('Start',H), sc('End',H), sc('Duration',H), sc('Subtype',H), sc('Cost',H)),
    ]
    d_ms = 0; sub_tots = {}
    for s in d_sess:
        ms   = int(s['end']) - int(s['start']); hrs = ms_hrs(ms)
        cost = hrs * labor_rate
        sub  = (s.get('designSubtype') or 'unspecified').replace('-',' ').title()
        d_ms += ms
        sub_tots.setdefault(sub, {'ms':0,'cost':0.0})
        sub_tots[sub]['ms'] += ms; sub_tots[sub]['cost'] += cost
        d_rows.append(row(sc(ts_date(s['start'])), sc(ts_time(s['start'])), sc(ts_time(s['end'])),
                          sc(ms_hm(ms)), sc(sub), cc(cost)))
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
        row(sc(f'Machine Rate: ${fdm_rate:.2f}/hr')),
        blank(),
        row(sc('Date',H), sc('Start',H), sc('End',H), sc('Duration',H), sc('Material',H),
            sc('Grams',H), sc('$/kg',H), sc('Fil. Cost',H), sc('Machine Cost',H), sc('Total',H)),
    ]
    f_ms = 0; f_fil = 0.0; f_mach = 0.0; f_g = 0.0; f_mat_tots = {}
    for s in f_sess:
        ms   = int(s['end']) - int(s['start']); mach = ms_hrs(ms) * fdm_rate
        fc   = fil_cost(s); g = float(s.get('filamentG') or 0)
        cpkg = float(s.get('filamentCostPerKg') or 0); mat = s.get('filamentType') or '—'
        f_ms += ms; f_fil += fc; f_mach += mach; f_g += g
        f_mat_tots.setdefault(mat, {'ms':0,'g':0.0,'fil':0.0,'mach':0.0})
        f_mat_tots[mat]['ms'] += ms; f_mat_tots[mat]['g'] += g
        f_mat_tots[mat]['fil'] += fc; f_mat_tots[mat]['mach'] += mach
        f_rows.append(row(
            sc(ts_date(s['start'])), sc(ts_time(s['start'])), sc(ts_time(s['end'])),
            sc(ms_hm(ms)), sc(mat),
            nc(g,1) if g else sc('—'), nc(cpkg,2) if cpkg else sc('—'),
            cc(fc) if fc else sc('—'), cc(mach), cc(fc+mach)))
    f_rows += [blank(), row(sc('Subtotals by Material', B)),
               row(sc('Material',H), sc('',H), sc('',H), sc('Duration',H), sc('Grams',H),
                   sc('',H), sc('',H), sc('Fil. Cost',H), sc('Machine Cost',H), sc('Total',H))]
    for mat, t in f_mat_tots.items():
        f_rows.append(row(sc(mat), sc(''), sc(''), sc(ms_hm(t['ms'])), nc(t['g'],1),
                          sc(''), sc(''), cc(t['fil']), cc(t['mach']), cc(t['fil']+t['mach'])))
    f_rows.append(row(sc('Total',B), sc(''), sc(''), sc(ms_hm(f_ms),B), nc(f_g,1,B),
                      sc(''), sc(''), cc(f_fil,B), cc(f_mach,B), cc(f_fil+f_mach,B)))
    fdm_total = f_fil + f_mach

    # ── RESIN tab ─────────────────────────────────────────────────────────
    r_sess = sorted([s for s in (proj.get('resinSessions') or []) if s.get('end')],
                    key=lambda s: s.get('start', 0))
    r_rows = [
        row(sc(f'Resin Sessions — {proj_name}', B)),
        row(sc(f'Machine Rate: ${resin_rate:.2f}/hr')),
        blank(),
        row(sc('Date',H), sc('Start',H), sc('End',H), sc('Duration',H), sc('Material',H),
            sc('mL',H), sc('$/kg',H), sc('Density',H), sc('Mat. Cost',H), sc('Machine Cost',H), sc('Total',H)),
    ]
    r_ms = 0; r_mat = 0.0; r_mach = 0.0; r_ml = 0.0; r_mat_tots = {}
    for s in r_sess:
        ms   = int(s['end']) - int(s['start']); mach = ms_hrs(ms) * resin_rate
        rc   = res_cost(s); ml = float(s.get('resinMl') or 0)
        cpkg = float(s.get('resinCostPerKg') or 0); dens = float(s.get('resinDensity') or 1.10)
        mat  = s.get('resinType') or '—'
        r_ms += ms; r_mat += rc; r_mach += mach; r_ml += ml
        r_mat_tots.setdefault(mat, {'ms':0,'ml':0.0,'mat':0.0,'mach':0.0})
        r_mat_tots[mat]['ms'] += ms; r_mat_tots[mat]['ml'] += ml
        r_mat_tots[mat]['mat'] += rc; r_mat_tots[mat]['mach'] += mach
        r_rows.append(row(
            sc(ts_date(s['start'])), sc(ts_time(s['start'])), sc(ts_time(s['end'])),
            sc(ms_hm(ms)), sc(mat),
            nc(ml,1) if ml else sc('—'), nc(cpkg,2) if cpkg else sc('—'), nc(dens,2),
            cc(rc) if rc else sc('—'), cc(mach), cc(rc+mach)))
    r_rows += [blank(), row(sc('Subtotals by Material', B)),
               row(sc('Material',H), sc('',H), sc('',H), sc('Duration',H), sc('mL',H),
                   sc('',H), sc('',H), sc('',H), sc('Mat. Cost',H), sc('Machine Cost',H), sc('Total',H))]
    for mat, t in r_mat_tots.items():
        r_rows.append(row(sc(mat), sc(''), sc(''), sc(ms_hm(t['ms'])), nc(t['ml'],1),
                          sc(''), sc(''), sc(''), cc(t['mat']), cc(t['mach']), cc(t['mat']+t['mach'])))
    r_rows.append(row(sc('Total',B), sc(''), sc(''), sc(ms_hm(r_ms),B), nc(r_ml,1,B),
                      sc(''), sc(''), sc(''), cc(r_mat,B), cc(r_mach,B), cc(r_mat+r_mach,B)))
    resin_total = r_mat + r_mach

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
        row(sc('Resin Machine Time'),   sc(f'{ms_hrs(r_ms):.2f} hrs'),          cc(r_mach)),
        row(sc('Resin Material'),       sc(f'{r_ml:.1f} mL'),                    cc(r_mat)),
        row(sc('Receipts / Expenses'),  sc(''),                                  cc(rec_total)),
        blank(),
        row(sc('Subtotal',B),           sc(''),                                  cc(actual,B)),
        row(sc(f'Markup ({markup_pct:.1f}%)'), sc(''),                           cc(markup_amt)),
        row(sc('Total (with markup)',B),sc(''),                                  cc(grand_total,B)),
    ]

    # ── ASSEMBLE XML ──────────────────────────────────────────────────────
    auto_styles = '''
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
    {mksheet("Summary",  s_rows)}
    {mksheet("Design",   d_rows)}
    {mksheet("FDM",      f_rows)}
    {mksheet("Resin",    r_rows)}
    {mksheet("Receipts", rec_rows)}
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

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def do_POST(self):
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
        if self.path == "/printer-status":
            with state_lock:
                payload = json.dumps(printer_state).encode()
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

# ── STARTUP ───────────────────────────────────────────────────────────
def open_browser():
    time.sleep(0.6)
    webbrowser.open(f"http://localhost:{PORT}")

def shutdown(sig, frame):
    print("\n  Server stopped.")
    sys.exit(0)

signal.signal(signal.SIGINT,  shutdown)
signal.signal(signal.SIGTERM, shutdown)

print(f"\n  Azazel's Razer Time Tracker")
print(f"  Server v{SERVER_VERSION} running AR Tracker v{TRACKER_VERSION}")
print(f"  Running at http://localhost:{PORT}")
print(f"  Moonraker polling: {MOONRAKER_IP} every {POLL_INTERVAL}s")
print(f"  Press Ctrl+C to stop\n")

socketserver.TCPServer.allow_reuse_address = True
threading.Thread(target=poll_moonraker, daemon=True).start()
threading.Thread(target=open_browser,   daemon=True).start()

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()
