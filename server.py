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

PORT = 5757
DIR = os.path.dirname(os.path.abspath(__file__))
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

# ── HTTP HANDLER ──────────────────────────────────────────────────────
# File extensions that should never be cached (app files)
NO_CACHE_EXTS = {'.html', '.js', '.css', '.json'}

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

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
print(f"  Running at http://localhost:{PORT}")
print(f"  Moonraker polling: {MOONRAKER_IP} every {POLL_INTERVAL}s")
print(f"  Press Ctrl+C to stop\n")

socketserver.TCPServer.allow_reuse_address = True
threading.Thread(target=poll_moonraker, daemon=True).start()
threading.Thread(target=open_browser,   daemon=True).start()

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()
