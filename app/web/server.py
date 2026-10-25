"""
Embedded HTTP and WebSocket/Polling Web GUI Server.
Provides a clean browser dashboard for configuring and controlling Synergy Next.
"""

import json
import mimetypes
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from app.config import Config

STATIC_DIR = Path(__file__).parent / "static"


class SynergyWebHandler(SimpleHTTPRequestHandler):
    config: Config = None
    server_instance = None
    client_instance = None
    recent_logs: List[str] = []
    log_lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    @classmethod
    def add_log(cls, msg: str):
        with cls.log_lock:
            cls.recent_logs.append(msg)
            if len(cls.recent_logs) > 100:
                cls.recent_logs.pop(0)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            is_srv = self.server_instance and self.server_instance.is_running
            is_cli = self.client_instance and self.client_instance.is_running
            connected_clients = []
            if is_srv:
                with self.server_instance._lock:
                    connected_clients = [
                        {"name": name, "ip": s.addr[0], "width": s.width, "height": s.height}
                        for name, s in self.server_instance.clients.items()
                    ]

            status_data = {
                "running": is_srv or is_cli,
                "role": "server" if is_srv else ("client" if is_cli else self.config.mode),
                "is_connected": self.client_instance.is_connected if is_cli else bool(connected_clients),
                "screen_name": self.config.screen_name,
                "server_host": self.config.server_host,
                "port": self.config.port,
                "tls_enabled": self.config.tls_enabled,
                "connected_clients": connected_clients,
                "links": self.config.links,
                "logs": self.recent_logs[-30:],
            }
            self.wfile.write(json.dumps(status_data).encode("utf-8"))
            return

        elif parsed.path == "/api/config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.config.to_dict()).encode("utf-8"))
            return

        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(length) if length > 0 else b"{}"

        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            body = {}

        if parsed.path == "/api/config":
            # Update configuration
            for k, v in body.items():
                if hasattr(self.config, k):
                    setattr(self.config, k, v)
            self.config.save()
            self._send_json({"success": True, "config": self.config.to_dict()})
            return

        elif parsed.path == "/api/start":
            mode = body.get("mode", self.config.mode)
            self.config.mode = mode
            self.config.save()

            if mode == "server":
                if self.client_instance and self.client_instance.is_running:
                    self.client_instance.stop()
                if self.server_instance and not self.server_instance.is_running:
                    self.server_instance.start()
            else:
                if self.server_instance and self.server_instance.is_running:
                    self.server_instance.stop()
                if self.client_instance and not self.client_instance.is_running:
                    self.client_instance.start()

            self._send_json({"success": True, "mode": mode, "running": True})
            return

        elif parsed.path == "/api/stop":
            if self.server_instance and self.server_instance.is_running:
                self.server_instance.stop()
            if self.client_instance and self.client_instance.is_running:
                self.client_instance.stop()
            self._send_json({"success": True, "running": False})
            return

        self.send_response(404)
        self.end_headers()

    def _send_json(self, data: Dict[str, Any]):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


def start_web_server(config: Config, server_instance, client_instance, log_callback: Callable[[str], None]) -> ThreadingHTTPServer:
    SynergyWebHandler.config = config
    SynergyWebHandler.server_instance = server_instance
    SynergyWebHandler.client_instance = client_instance

    def log_bridge(msg: str):
        SynergyWebHandler.add_log(msg)
        log_callback(msg)

    server_address = ("0.0.0.0", config.web_port)
    httpd = ThreadingHTTPServer(server_address, SynergyWebHandler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True, name="SynergyWebThread")
    t.start()
    return httpd
