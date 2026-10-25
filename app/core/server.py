"""
Synergy / Barrier Server Engine.
Captures local mouse and keyboard, detects screen edges, and forwards events to remote clients.
"""

import select
import socket
import ssl
import threading
import time
from typing import Callable, Dict, Optional, Tuple
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
    MSG_D_INFO,
    MSG_D_CLIPBOARD,
)
from app.protocol.packet import PacketBuilder, PacketParser, frame_packet, unframe_packet
from app.protocol.crypto import create_server_ssl_context


class ClientSession:
    def __init__(self, sock: socket.socket, addr: Tuple[str, int]):
        self.sock = sock
        self.addr = addr
        self.screen_name = ""
        self.width = 1920
        self.height = 1080
        self.cursor_x = 0
        self.cursor_y = 0
        self.rx_buffer = bytearray()
        self.handshake_done = False
        self.last_alive = time.time()

    def send_packet(self, payload: bytes):
        try:
            self.sock.sendall(frame_packet(payload))
        except Exception:
            pass


class SynergyServer:
    def __init__(self, config: Config, log_callback: Optional[Callable[[str], None]] = None):
        self.config = config
        self.platform = get_platform_screen()
        self.log_callback = log_callback or print
        self.is_running = False
        self.active_screen = self.config.screen_name  # which screen currently owns the mouse
        self.clients: Dict[str, ClientSession] = {}  # screen_name -> ClientSession
        self._server_sock: Optional[socket.socket] = None
        self._server_thread: Optional[threading.Thread] = None
        self._keepalive_thread: Optional[threading.Thread] = None
        self._clipboard_thread: Optional[threading.Thread] = None
        self._last_clipboard = ""
        self._lock = threading.Lock()

    def log(self, msg: str):
        self.log_callback(f"[Server] {msg}")

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.active_screen = self.config.screen_name

        self._server_thread = threading.Thread(target=self._listen_loop, daemon=True, name="SynergyServerListen")
        self._server_thread.start()

        self._keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True, name="SynergyServerKeepAlive")
        self._keepalive_thread.start()

        self._clipboard_thread = threading.Thread(target=self._clipboard_loop, daemon=True, name="SynergyServerClipboard")
        self._clipboard_thread.start()

        # Start capturing local mouse cursor for edge detection
        self.platform.start_capture(
            on_move=self._on_local_mouse_move,
            on_click=self._on_local_mouse_click,
            on_wheel=self._on_local_mouse_wheel,
            on_key=self._on_local_key,
        )

        self.log(f"Server started on port {self.config.port} (TLS: {self.config.tls_enabled})")

    def stop(self):
        self.is_running = False
        self.platform.stop_capture()

        with self._lock:
            for s in list(self.clients.values()):
                try:
                    s.sock.close()
                except Exception:
                    pass
            self.clients.clear()

        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
            self._server_sock = None

        self.log("Server stopped")

    def _listen_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", self.config.port))
        sock.listen(5)
        sock.settimeout(1.0)
        self._server_sock = sock

        while self.is_running:
            try:
                client_sock, addr = sock.accept()
                if not self.is_running:
                    client_sock.close()
                    break

                if self.config.tls_enabled:
                    ctx = create_server_ssl_context()
                    client_sock = ctx.wrap_socket(client_sock, server_side=True)

                self.log(f"New client connected from {addr[0]}:{addr[1]}")
                t = threading.Thread(target=self._handle_client_connection, args=(client_sock, addr), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    self.log(f"Listen error: {e}")
                time.sleep(0.5)

    def _handle_client_connection(self, sock: socket.socket, addr: Tuple[str, int]):
        session = ClientSession(sock, addr)
        # Send initial Hello packet
        hello = PacketBuilder.hello(brand="Barrier", major=PROTOCOL_MAJOR_VERSION, minor=PROTOCOL_MINOR_VERSION)
        session.send_packet(hello)

        sock.settimeout(0.5)
        while self.is_running:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                session.rx_buffer.extend(chunk)

                while True:
                    packet = unframe_packet(session.rx_buffer)
                    if packet is None:
                        break
                    self._process_client_packet(session, packet)
            except socket.timeout:
                continue
            except Exception as e:
                break

        self.log(f"Client disconnected: {session.screen_name or addr[0]}")
        with self._lock:
            if session.screen_name in self.clients:
                del self.clients[session.screen_name]
        try:
            sock.close()
        except Exception:
            pass

    def _process_client_packet(self, session: ClientSession, packet: bytes):
        if len(packet) < 4:
            return

        cmd = packet[:4].decode("latin-1", errors="replace")

        # Client HelloBack
        if packet.startswith(b"Barrier") or packet.startswith(b"Synergy"):
            brand = "Barrier" if packet.startswith(b"Barrier") else "Synergy"
            fmt = f"{brand}%2i%2i%s"
            try:
                args, _ = PacketParser.unpack_format(fmt, packet)
                major, minor, client_name = args
                session.screen_name = client_name
                with self._lock:
                    self.clients[client_name] = session
                self.log(f"Handshake step 1: client identified as '{client_name}' (Protocol {major}.{minor})")
                # Request client screen dimensions
                session.send_packet(PacketBuilder.query_info())
            except Exception as e:
                self.log(f"Failed to parse HelloBack: {e}")

        # Client Screen Info (DINF)
        elif cmd == "DINF":
            try:
                args, _ = PacketParser.unpack_format("DINF%2i%2i%2i%2i%2i%2i%2i", packet)
                x, y, w, h, warp_size, mx, my = args
                session.width = w
                session.height = h
                session.cursor_x = mx
                session.cursor_y = my
                session.handshake_done = True
                self.log(f"Client '{session.screen_name}' ready (Resolution: {w}x{h})")
                # Send Info Ack
                session.send_packet(PacketBuilder.info_ack())
            except Exception as e:
                self.log(f"Failed to parse DINF: {e}")

        # Keep Alive reply
        elif cmd == MSG_C_KEEP_ALIVE:
            session.last_alive = time.time()

    def _keepalive_loop(self):
        while self.is_running:
            time.sleep(3)
            with self._lock:
                for name, session in list(self.clients.items()):
                    if session.handshake_done:
                        session.send_packet(PacketBuilder.keep_alive())

    def _clipboard_loop(self):
        while self.is_running:
            time.sleep(1.0)
            if not self.config.clipboard_sharing:
                continue
            try:
                current_text = self.platform.get_clipboard()
                if current_text and current_text != self._last_clipboard:
                    self._last_clipboard = current_text
                    # Broadcast to all clients
                    pkt = PacketBuilder.clipboard_data(0, 0, 0, current_text)
                    with self._lock:
                        for session in self.clients.values():
                            if session.handshake_done:
                                session.send_packet(pkt)
            except Exception:
                pass

    def _on_local_mouse_move(self, x: int, y: int):
        sw, sh = self.platform.get_screen_size()

        # If cursor is on primary local screen
        if self.active_screen == self.config.screen_name:
            neighbor = None
            entry_x = 0
            entry_y = y

            # Check right boundary
            if x >= sw - 2:
                neighbor = self.config.links.get(self.config.screen_name, {}).get("right")
                entry_x = 2
            # Check left boundary
            elif x <= 1:
                neighbor = self.config.links.get(self.config.screen_name, {}).get("left")
                entry_x = 1918  # Will be mapped to neighbor width
            # Check top boundary
            elif y <= 1:
                neighbor = self.config.links.get(self.config.screen_name, {}).get("up")
                entry_y = 1078
            # Check bottom boundary
            elif y >= sh - 2:
                neighbor = self.config.links.get(self.config.screen_name, {}).get("down")
                entry_y = 2

            if neighbor and neighbor in self.clients:
                self._switch_to_screen(neighbor, entry_x, entry_y)
        else:
            # Cursor is currently on a remote client!
            session = self.clients.get(self.active_screen)
            if not session:
                self.active_screen = self.config.screen_name
                return

            # Compute delta from screen center and forward to client
            # Or map virtual coordinate
            session.cursor_x = max(0, min(session.width, session.cursor_x + (x - sw // 2)))
            session.cursor_y = max(0, min(session.height, session.cursor_y + (y - sh // 2)))

            # Re-center cursor on host machine so it doesn't escape
            self.platform.warp_cursor(sw // 2, sh // 2)

            # Check if remote client wants to hop back to host
            if session.cursor_x <= 1:
                left_neighbor = self.config.links.get(session.screen_name, {}).get("left")
                if left_neighbor == self.config.screen_name:
                    self._switch_back_to_host(sw - 10, y)
                    return
            elif session.cursor_x >= session.width - 2:
                right_neighbor = self.config.links.get(session.screen_name, {}).get("right")
                if right_neighbor == self.config.screen_name:
                    self._switch_back_to_host(10, y)
                    return

            # Forward mouse position to client
            session.send_packet(PacketBuilder.mouse_move(int(session.cursor_x), int(session.cursor_y)))

    def _switch_to_screen(self, target_name: str, entry_x: int, entry_y: int):
        session = self.clients.get(target_name)
        if not session or not session.handshake_done:
            return

        self.log(f"Screen switch: '{self.config.screen_name}' -> '{target_name}' at ({entry_x}, {entry_y})")
        self.active_screen = target_name
        session.cursor_x = entry_x
        session.cursor_y = entry_y

        # Send CINN to client
        session.send_packet(PacketBuilder.enter(entry_x, entry_y, 0, 0))

        # Center local cursor to capture relative deltas
        sw, sh = self.platform.get_screen_size()
        self.platform.warp_cursor(sw // 2, sh // 2)

    def _switch_back_to_host(self, host_x: int, host_y: int):
        self.log(f"Screen switch: '{self.active_screen}' -> Host '{self.config.screen_name}'")
        session = self.clients.get(self.active_screen)
        if session:
            session.send_packet(PacketBuilder.leave())

        self.active_screen = self.config.screen_name
        self.platform.warp_cursor(host_x, host_y)

    def _on_local_mouse_click(self, button: int, pressed: bool):
        if self.active_screen != self.config.screen_name:
            session = self.clients.get(self.active_screen)
            if session:
                pkt = PacketBuilder.mouse_down(button) if pressed else PacketBuilder.mouse_up(button)
                session.send_packet(pkt)

    def _on_local_mouse_wheel(self, x_delta: int, y_delta: int):
        if self.active_screen != self.config.screen_name:
            session = self.clients.get(self.active_screen)
            if session:
                session.send_packet(PacketBuilder.mouse_wheel(x_delta, y_delta))

    def _on_local_key(self, key: int, mask: int, code: int, pressed: bool):
        if self.active_screen != self.config.screen_name:
            session = self.clients.get(self.active_screen)
            if session:
                pkt = PacketBuilder.key_down(key, mask, code) if pressed else PacketBuilder.key_up(key, mask, code)
                session.send_packet(pkt)
