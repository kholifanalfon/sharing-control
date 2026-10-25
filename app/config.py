"""
Configuration Manager for Synergy Next.
Supports JSON configuration and auto-migrates existing Barrier.conf settings.
"""

import json
import os
import socket
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_DIR = Path.home() / ".config" / "synergy-next"
CONFIG_FILE = CONFIG_DIR / "config.json"
BARRIER_CONFIG = Path.home() / ".config" / "Debauchee" / "Barrier.conf"


def get_default_screen_name() -> str:
    return socket.gethostname().split(".")[0]


class Config:
    def __init__(self):
        self.screen_name: str = get_default_screen_name()
        self.mode: str = "server"  # 'server' or 'client'
        self.server_host: str = "127.0.0.1"
        self.port: int = 24800
        self.web_port: int = 24801
        self.tls_enabled: bool = False
        self.clipboard_sharing: bool = True

        # Screen grid links: screen_name -> {'left': ..., 'right': ..., 'up': ..., 'down': ...}
        self.links: Dict[str, Dict[str, str]] = {}
        # Known screen resolutions: screen_name -> {'width': w, 'height': h}
        self.screens: Dict[str, Dict[str, int]] = {}

        self.load()

    def load(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.screen_name = data.get("screen_name", self.screen_name)
                self.mode = data.get("mode", self.mode)
                self.server_host = data.get("server_host", self.server_host)
                self.port = data.get("port", self.port)
                self.web_port = data.get("web_port", self.web_port)
                self.tls_enabled = data.get("tls_enabled", self.tls_enabled)
                self.clipboard_sharing = data.get("clipboard_sharing", self.clipboard_sharing)
                self.links = data.get("links", self.links)
                self.screens = data.get("screens", self.screens)
                return
            except Exception as e:
                print(f"[Config] Error loading config.json: {e}")

        # Check for legacy Barrier.conf migration
        self._import_barrier_conf()

    def _import_barrier_conf(self):
        if not BARRIER_CONFIG.exists():
            return
        try:
            with open(BARRIER_CONFIG, "r", encoding="utf-8") as f:
                lines = f.readlines()

            screens = []
            for line in lines:
                line = line.strip()
                if line.startswith("screenName="):
                    self.screen_name = line.split("=", 1)[1].strip()
                elif line.startswith("serverHostname="):
                    self.server_host = line.split("=", 1)[1].strip()
                elif "name=" in line and "screens\\" in line:
                    val = line.split("=", 1)[1].strip()
                    if val and val not in screens:
                        screens.append(val)
                elif line.startswith("groupClientChecked=true"):
                    self.mode = "client"
                elif line.startswith("groupServerChecked=true"):
                    self.mode = "server"
                elif line.startswith("port="):
                    try:
                        self.port = int(line.split("=", 1)[1].strip())
                    except ValueError:
                        pass

            # Auto create default links if 2 screens found
            if len(screens) >= 2:
                s1, s2 = screens[0], screens[1]
                self.links[s1] = {"right": s2}
                self.links[s2] = {"left": s1}

            self.save()
            print(f"[Config] Imported settings from Barrier.conf (Screens: {screens})")
        except Exception as e:
            print(f"[Config] Failed to import Barrier.conf: {e}")

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "screen_name": self.screen_name,
            "mode": self.mode,
            "server_host": self.server_host,
            "port": self.port,
            "web_port": self.web_port,
            "tls_enabled": self.tls_enabled,
            "clipboard_sharing": self.clipboard_sharing,
            "links": self.links,
            "screens": self.screens,
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "screen_name": self.screen_name,
            "mode": self.mode,
            "server_host": self.server_host,
            "port": self.port,
            "web_port": self.web_port,
            "tls_enabled": self.tls_enabled,
            "clipboard_sharing": self.clipboard_sharing,
            "links": self.links,
            "screens": self.screens,
        }
