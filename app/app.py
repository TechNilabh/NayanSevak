"""
Nayan Sevak AI Dashboard - Zero-Dependency Web Server
Uses Python's built-in http.server to serve static files, HUD base template, screen partials, and mock telemetry API.
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import random
import time
import os

PORT = 5000
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class HUDRequestHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Route root '/' to base_hud.html
        if path == '/' or path == '/index.html':
            return os.path.join(BASE_DIR, 'frontend', 'templates', 'hud', 'base_hud.html')
        
        # Route '/templates/hud/screens/...' to screen partials
        if path.startswith('/templates/hud/screens/'):
            filename = os.path.basename(path)
            return os.path.join(BASE_DIR, 'frontend', 'templates', 'hud', 'screens', filename)
        
        # Route '/static/...' to frontend/static/...
        if path.startswith('/static/'):
            rel = path[len('/static/'):]
            return os.path.join(BASE_DIR, 'frontend', 'static', rel)
            
        return super().translate_path(path)

    def do_GET(self):
        if self.path.startswith('/api/telemetry/latest'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            data = {
                'yoloConfidence': round(random.uniform(85.0, 98.5), 1),
                'sensorWeight': 12,
                'fusionScore': random.randint(88, 97),
                'mpuVibration': round(random.uniform(0.08, 0.45), 2),
                'ultrasonicDistance': random.randint(110, 180),
                'rearDistance': random.randint(30, 65),
                'aiFps': random.randint(30, 36),
                'batteryPct': 84,
                'speedKmh': 68,
                'tirePressurePsi': 38,
                'timestamp': time.time()
            }
            self.wfile.write(json.dumps(data).encode('utf-8'))
            return
            
        return super().do_GET()

if __name__ == '__main__':
    os.chdir(BASE_DIR)
    server = HTTPServer(('127.0.0.1', PORT), HUDRequestHandler)
    print("==========================================================")
    print(f" Nayan Sevak HUD Server Running on http://127.0.0.1:{PORT}")
    print("==========================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped.")
