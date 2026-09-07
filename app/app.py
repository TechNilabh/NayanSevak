"""
Nayan Sevak AI Dashboard - Zero-Dependency Web Server
Uses Python's built-in http.server (ThreadingHTTPServer) to serve static
files, HUD base template, screen partials, and live AI telemetry API.

API endpoints
-------------
GET /api/telemetry/latest   — live fusion telemetry (4 Hz worker)
GET /api/hazards/recent     — hazard event history (persisted)
GET /api/trip/summary       — session aggregates (total, by-type, duration)
"""

import json
import logging
import os
import sys
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# ---------------------------------------------------------------------------
# Path bootstrap: src/ must be importable before pulling in the worker
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import telemetry_worker  # noqa: E402  (after sys.path is patched)

PORT = 5000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# ---------------------------------------------------------------------------
# Request Handler
# ---------------------------------------------------------------------------

class HUDRequestHandler(SimpleHTTPRequestHandler):
    """Serves the HUD shell, screen partials, static assets, and API routes."""

    # Silence noisy access log in production; set to DEBUG to re-enable
    def log_message(self, fmt, *args):  # noqa: N802
        logging.debug("HTTP %s", fmt % args)

    # ------------------------------------------------------------------
    # Path routing
    # ------------------------------------------------------------------

    def translate_path(self, path):
        # Strip query strings
        path = path.split("?", 1)[0].split("#", 1)[0]

        # Root → base HUD shell
        if path in ("/", "/index.html"):
            return os.path.join(BASE_DIR, "frontend", "templates", "hud", "base_hud.html")

        # Screen partials
        if path.startswith("/templates/hud/screens/"):
            filename = os.path.basename(path)
            return os.path.join(BASE_DIR, "frontend", "templates", "hud", "screens", filename)

        # Static assets
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            return os.path.join(BASE_DIR, "frontend", "static", rel)

        return super().translate_path(path)

    # ------------------------------------------------------------------
    # CORS / JSON helper
    # ------------------------------------------------------------------

    def _send_json(self, payload: dict | list, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.end_headers()
        self.wfile.write(body)

    # ------------------------------------------------------------------
    # GET handler
    # ------------------------------------------------------------------

    def do_GET(self):  # noqa: N802
        path = self.path.split("?", 1)[0]

        # --- Live telemetry (replaces random mock) ---
        if path in ("/api/telemetry/latest", "/api/telemetry/latest/"):
            try:
                data = telemetry_worker.get_latest_telemetry()
            except Exception as exc:
                logging.warning("Telemetry read error: %s", exc)
                data = {"error": str(exc), "timestamp": time.time()}
            self._send_json(data)
            return

        # --- Hazard event history ---
        if path in ("/api/hazards/recent", "/api/hazards/recent/"):
            try:
                data = telemetry_worker.get_hazard_log()
            except Exception as exc:
                logging.warning("Hazard log read error: %s", exc)
                data = []
            self._send_json(data)
            return

        # --- Trip summary ---
        if path in ("/api/trip/summary", "/api/trip/summary/"):
            try:
                data = telemetry_worker.get_trip_summary()
            except Exception as exc:
                logging.warning("Trip summary error: %s", exc)
                data = {
                    "total_hazards": 0,
                    "by_type": {},
                    "duration_seconds": 0.0,
                    "session_start": 0.0,
                    "distance_km": None,
                    "route": None,
                }
            self._send_json(data)
            return

        # --- All other paths: static file serving ---
        return super().do_GET()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    os.chdir(BASE_DIR)

    # Start telemetry background worker before accepting HTTP connections
    telemetry_worker.start_worker()

    server = ThreadingHTTPServer(("127.0.0.1", PORT), HUDRequestHandler)

    print("=" * 60)
    print(f"  Nayan Sevak HUD  ->  http://127.0.0.1:{PORT}")
    print("  Telemetry worker : RUNNING (4 Hz, daemon)")
    print("  Endpoints:")
    print("    GET /api/telemetry/latest")
    print("    GET /api/hazards/recent")
    print("    GET /api/trip/summary")
    print("=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
