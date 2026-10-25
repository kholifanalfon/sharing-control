"""
Synergy / Barrier Client Engine.
Connects to a Synergy or Barrier server, receives inputs, and injects them locally.
"""

import socket
import ssl
import threading
import time
from typing import Callable, Optional
from app.config import Config
from app.platform import get_platform_screen
from app.protocol.constants import (
    PROTOCOL_MAJOR_VERSION,
    PROTOCOL_MINOR_VERSION,
    MSG_Q_INFO,
    MSG_C_INFO_ACK,
    MSG_C_KEEP_ALIVE,
    MSG_C_ENTER,
    MSG_C_LEAVE,
    MSG_D_MOUSE_MOVE,
    MSG_D_MOUSE_REL_MOVE,
    MSG_D_MOUSE_DOWN,
    MSG_D_MOUSE_UP,
    MSG_D_MOUSE_WHEEL,
    MSG_D_KEY_DOWN,
    MSG_D_KEY_REPEAT,
    MSG_D_KEY_UP,
    MSG_D_CLIPBOARD,
)
from app.protocol.packet import PacketBuilder, PacketParser, frame_packet, unframe_packet
from app.protocol.crypto import create_client_ssl_context


class SynergyClient:
    def __init__(self, config: Config, log_callback: Optional[Callable[[str], None]] = None):
        self.config = config
        self.platform = get_platform_screen()
        self.log_callback = log_callback or print
        self.is_running = False
        self.is_connected = False
        self.is_active = False  # Cursor is on this screen
        self._thread: Optional[threading.Thread] = None
        self._sock: Optional[socket.socket] = None

    def log(self, msg: str):
        self.log_callback(f"[Client] {msg}")

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="SynergyClientLoop")
        self._thread.start()
        self.log(f"Started client (Target server: {self.config.server_host}:{self.config.port})")

    def stop(self):
        self.is_running = False
        self.is_connected = False
        self.is_active = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        self.log("Client stopped")

    def _run_loop(self):
        while self.is_running:
            try:
                self._connect_and_process()
            except Exception as e:
                if self.is_running:
                    self.log(f"Connection error: {e}, retrying in 3s...")
                    time.sleep(3)

    def _connect_and_process(self):
        self.log(f"Connecting to {self.config.server_host}:{self.config.port}...")
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.settimeout(10.0)

        if self.config.tls_enabled:
            ctx = create_client_ssl_context()
            sock = ctx.wrap_socket(raw_sock)
        else:
            sock = raw_sock

        sock.connect((self.config.server_host, self.config.port))
        sock.settimeout(None)  # Blocking with select
        self._sock = sock
        self.is_connected = True
        self.log("Connected to server! Starting handshake...")

        rx_buffer = bytearray()
        handshake_complete = False

        while self.is_running and self.is_connected:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    self.log("Server closed connection")
                    break
                rx_buffer.extend(chunk)

                while True:
                    packet = unframe_packet(rx_buffer)
                    if packet is None:
                        break
                    self._handle_packet(packet, sock)
            except Exception as e:
                self.log(f"Socket receive error: {e}")
                break

        self.is_connected = False
        self.is_active = False
        try:
            sock.close()
        except Exception:
            pass

    def _handle_packet(self, packet: bytes, sock: socket.socket):
        if len(packet) < 4:
            return

        cmd = packet[:4].decode("latin-1", errors="replace")

        # Handshake: Server Hello ("Barrier" or "Synergy")
        if packet.startswith(b"Barrier") or packet.startswith(b"Synergy"):
            brand = "Barrier" if packet.startswith(b"Barrier") else "Synergy"
            self.log(f"Received Server Hello ({brand}). Responding with HelloBack ({self.config.screen_name})...")
            reply = PacketBuilder.hello_back(self.config.screen_name, brand=brand)
            sock.sendall(frame_packet(reply))

        # Server Query Info (QINF)
        elif cmd == MSG_Q_INFO:
            w, h = self.platform.get_screen_size()
            cx, cy = self.platform.get_cursor_pos()
            self.log(f"Received QINF. Sending screen resolution: {w}x{h} (cursor at {cx},{cy})")
            info_reply = PacketBuilder.client_info(0, 0, w, h, warp_size=0, mx=cx, my=cy)
            sock.sendall(frame_packet(info_reply))

        # Info Ack (CIAK)
        elif cmd == MSG_C_INFO_ACK:
            self.log("Handshake complete! Ready to receive remote input.")

        # Keep Alive (CALV)
        elif cmd == MSG_C_KEEP_ALIVE:
            reply = PacketBuilder.keep_alive()
            sock.sendall(frame_packet(reply))

        # Cursor Enter (CINN%2i%2i%4i%2i)
        elif cmd == MSG_C_ENTER:
            args, _ = PacketParser.unpack_format("CINN%2i%2i%4i%2i", packet)
            x, y, seq, mask = args
            self.is_active = True
            self.platform.warp_cursor(x, y)
            self.log(f"Cursor ENTER -> ({x}, {y})")

        # Cursor Leave (COUT)
        elif cmd == MSG_C_LEAVE:
            self.is_active = False
            self.log("Cursor LEAVE")

        # Mouse Move (DMMV%2i%2i)
        elif cmd == MSG_D_MOUSE_MOVE:
            args, _ = PacketParser.unpack_format("DMMV%2i%2i", packet)
            x, y = args
            self.platform.inject_mouse_move(x, y)

        # Mouse Relative Move (DMRM%2i%2i)
        elif cmd == MSG_D_MOUSE_REL_MOVE:
            args, _ = PacketParser.unpack_format("DMRM%2i%2i", packet)
            dx, dy = args
            self.platform.inject_mouse_rel_move(dx, dy)

        # Mouse Down (DMDN%1i)
        elif cmd == MSG_D_MOUSE_DOWN:
            args, _ = PacketParser.unpack_format("DMDN%1i", packet)
            btn = args[0]
            self.platform.inject_mouse_down(btn)

        # Mouse Up (DMUP%1i)
        elif cmd == MSG_D_MOUSE_UP:
            args, _ = PacketParser.unpack_format("DMUP%1i", packet)
            btn = args[0]
            self.platform.inject_mouse_up(btn)

        # Mouse Wheel (DMWM%2i%2i)
        elif cmd == MSG_D_MOUSE_WHEEL:
            args, _ = PacketParser.unpack_format("DMWM%2i%2i", packet)
            x_delta, y_delta = args
            # Convert unsigned 16-bit to signed delta
            if y_delta > 32767:
                y_delta -= 65536
            if x_delta > 32767:
                x_delta -= 65536
            self.platform.inject_mouse_wheel(x_delta, y_delta)

        # Key Down (DKDN%2i%2i%2i)
        elif cmd == MSG_D_KEY_DOWN:
            try:
                args, _ = PacketParser.unpack_format("DKDN%2i%2i%2i", packet)
                key, mask, code = args
            except Exception:
                args, _ = PacketParser.unpack_format("DKDN%2i%2i", packet)
                key, mask = args
                code = 0
            self.platform.inject_key_down(key, mask, code)

        # Key Up (DKUP%2i%2i%2i)
        elif cmd == MSG_D_KEY_UP:
            try:
                args, _ = PacketParser.unpack_format("DKUP%2i%2i%2i", packet)
                key, mask, code = args
            except Exception:
                args, _ = PacketParser.unpack_format("DKUP%2i%2i", packet)
                key, mask = args
                code = 0
            self.platform.inject_key_up(key, mask, code)

        # Clipboard (DCLP%1i%4i%1i%s)
        elif cmd == MSG_D_CLIPBOARD:
            try:
                args, _ = PacketParser.unpack_format("DCLP%1i%4i%1i%s", packet)
                clip_id, seq, mark, data = args
                if self.config.clipboard_sharing and data:
                    self.platform.set_clipboard(data)
                    self.log(f"Synchronized clipboard ({len(data)} chars)")
            except Exception as e:
                self.log(f"Clipboard decode error: {e}")
