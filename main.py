#!/usr/bin/env python3
"""
Synergy Next - Main Application Entrypoint.
Cross-Platform Keyboard and Mouse Sharing (Linux, macOS, Windows).
"""

import argparse
import os
import sys
import time
from app.config import Config
from app.core.client import SynergyClient
from app.core.server import SynergyServer
from app.web.server import start_web_server, SynergyWebHandler


def main():
    parser = argparse.ArgumentParser(description="Synergy Next - Cross-Platform KM Sharing")
    parser.add_argument("--mode", choices=["server", "client", "gui"], default=None, help="Operation mode")
    parser.add_argument("--server", dest="server_host", type=str, default=None, help="Target server IP (for client mode)")
    parser.add_argument("--port", type=int, default=None, help="Synergy protocol port (default 24800)")
    parser.add_argument("--web-port", type=int, default=None, help="Web GUI port (default 24801)")
    parser.add_argument("--no-gui", action="store_true", help="Run headlessly without starting Web GUI")
    parser.add_argument("--tls", action="store_true", help="Enable TLS encryption")
    args = parser.parse_args()

    config = Config()

    if args.port:
        config.port = args.port
    if args.web_port:
        config.web_port = args.web_port
    if args.server_host:
        config.server_host = args.server_host
    if args.tls:
        config.tls_enabled = True

    chosen_mode = args.mode or config.mode

    print("========================================================")
    print(" ⚡ Synergy Next - Modern Cross-Platform KM Sharing")
    print(f" Platform : {sys.platform}")
    print(f" Screen   : {config.screen_name}")
    print(f" Mode     : {chosen_mode.upper()}")
    print("========================================================")

    def log_printer(msg: str):
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {msg}"
        print(formatted)
        SynergyWebHandler.add_log(formatted)

    server = SynergyServer(config, log_callback=log_printer)
    client = SynergyClient(config, log_callback=log_printer)

    if not args.no_gui:
        web_server = start_web_server(config, server, client, log_callback=log_printer)
        print(f"🌐 Web GUI Dashboard running at: http://localhost:{config.web_port}")

    # Start service if specified or default
    if chosen_mode == "server":
        server.start()
    elif chosen_mode == "client":
        client.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[System] Shutting down Synergy Next...")
        if server.is_running:
            server.stop()
        if client.is_running:
            client.stop()
        print("[System] Goodbye!")


if __name__ == "__main__":
    main()
