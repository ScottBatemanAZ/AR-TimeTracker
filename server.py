#!/usr/bin/env python3
import http.server
import socketserver
import os
import webbrowser
import threading
import urllib.request
import urllib.error
import json
import time

PORT = 5757
DIR = os.path.dirname(os.path.abspath(__file__))
MOONRAKER_IP = "192.168.0.74"
MOONRAKER_URL = f"http://{MOONRAKER_IP}/printer/objects/query?print_stats"
# print_stats returns: state, filename, print_duration, filament_used (mm)
POLL_INTERVAL = 5  # seconds

# Shared printer state — read by HTTP handler, written by poller thread
printer_state = {
    "status": "unknown",
    "filename": "",
    "print_duration": 0,
    "filament_used": 0,
    "last_checked": 0,
    "reachable": False
}
state_lock = threading.Lock()

# ── MOONRAKER POLLER ──────────────────────────────────────────────────
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
        except Exception:
            with state_lock:
                printer_state["status"]       = "unreachable"
                printer_state["last_checked"] = time.time()
                printer_state["reachable"]    = False
        time.sleep(POLL_INTERVAL)

# ── HTTP HANDLER ──────────────────────────────────────────────────────
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
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(payload)
        else:
            super().do_GET()

    def log_message(self, format, *args):
        pass  # suppress request logging

# ── STARTUP ───────────────────────────────────────────────────────────
def open_browser():
    time.sleep(0.6)
    webbrowser.open(f"http://localhost:{PORT}")

print(f"\n  Azazel's Razer Time Tracker")
print(f"  Running at http://localhost:{PORT}")
print(f"  Moonraker polling: {MOONRAKER_IP} every {POLL_INTERVAL}s")
print(f"  Press Ctrl+C to stop\n")

threading.Thread(target=poll_moonraker, daemon=True).start()
threading.Thread(target=open_browser,   daemon=True).start()

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
