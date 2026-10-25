"""
Synergy / Barrier Packet Framing and Serialization.
Implements the exact wire protocol format (%1i, %2i, %4i, %s, %4I) over TCP.
"""

import struct
from typing import Any, List, Optional, Tuple
from app.protocol.constants import (
    PROTOCOL_MAJOR_VERSION,
    PROTOCOL_MINOR_VERSION,
    MSG_HELLO_BARRIER,
    MSG_HELLO_SYNERGY,
    MSG_C_ENTER,
    MSG_C_LEAVE,
    MSG_C_KEEP_ALIVE,
    MSG_C_INFO_ACK,
    MSG_Q_INFO,
    MSG_D_INFO,
    MSG_D_MOUSE_MOVE,
    MSG_D_MOUSE_REL_MOVE,
    MSG_D_MOUSE_DOWN,
    MSG_D_MOUSE_UP,
    MSG_D_MOUSE_WHEEL,
    MSG_D_KEY_DOWN,
    MSG_D_KEY_REPEAT,
    MSG_D_KEY_UP,
    MSG_D_CLIPBOARD,
    MSG_C_CLIPBOARD,
)


def frame_packet(payload: bytes) -> bytes:
    """Prefix payload with 4-byte big-endian length."""
    return struct.pack(">I", len(payload)) + payload


def unframe_packet(stream_buffer: bytearray) -> Optional[bytes]:
    """
    Extract one framed packet from stream_buffer if available.
    Removes the consumed bytes from stream_buffer in-place.
    """
    if len(stream_buffer) < 4:
        return None
    length = struct.unpack(">I", stream_buffer[:4])[0]
    if len(stream_buffer) < 4 + length:
        return None
    packet = bytes(stream_buffer[4 : 4 + length])
    del stream_buffer[: 4 + length]
    return packet


class PacketBuilder:
    """Helper to serialize binary messages according to Synergy protocol rules."""

    @staticmethod
    def pack_format(fmt: str, *args) -> bytes:
        out = bytearray()
        i = 0
        arg_idx = 0
        while i < len(fmt):
            if fmt[i] == "%":
                i += 1
                length_str = ""
                while i < len(fmt) and fmt[i].isdigit():
                    length_str += fmt[i]
                    i += 1
                length = int(length_str) if length_str else 0
                type_char = fmt[i]
                i += 1

                val = args[arg_idx]
                arg_idx += 1

                if type_char == "i":
                    if length == 1:
                        out.extend(struct.pack("B", val & 0xFF))
                    elif length == 2:
                        out.extend(struct.pack(">H", val & 0xFFFF))
                    elif length == 4:
                        out.extend(struct.pack(">I", val & 0xFFFFFFFF))
                    else:
                        raise ValueError(f"Unsupported integer length %{length}i")
                elif type_char == "s":
                    # String: 4-byte length prefix followed by utf-8 bytes
                    if isinstance(val, str):
                        s_bytes = val.encode("utf-8")
                    elif isinstance(val, bytes):
                        s_bytes = val
                    else:
                        s_bytes = str(val).encode("utf-8")
                    out.extend(struct.pack(">I", len(s_bytes)))
                    out.extend(s_bytes)
                elif type_char == "I":
                    # List of integers: 4-byte count followed by items
                    items = val if isinstance(val, (list, tuple)) else []
                    out.extend(struct.pack(">I", len(items)))
                    for item in items:
                        if length == 1:
                            out.extend(struct.pack("B", item & 0xFF))
                        elif length == 2:
                            out.extend(struct.pack(">H", item & 0xFFFF))
                        elif length == 4:
                            out.extend(struct.pack(">I", item & 0xFFFFFFFF))
            else:
                out.append(ord(fmt[i]))
                i += 1
        return bytes(out)

    @classmethod
    def hello(cls, brand: str = "Barrier", major: int = PROTOCOL_MAJOR_VERSION, minor: int = PROTOCOL_MINOR_VERSION) -> bytes:
        fmt = f"{brand}%2i%2i"
        return cls.pack_format(fmt, major, minor)

    @classmethod
    def hello_back(cls, name: str, brand: str = "Barrier", major: int = PROTOCOL_MAJOR_VERSION, minor: int = PROTOCOL_MINOR_VERSION) -> bytes:
        fmt = f"{brand}%2i%2i%s"
        return cls.pack_format(fmt, major, minor, name)

    @classmethod
    def query_info(cls) -> bytes:
        return MSG_Q_INFO.encode("ascii")

    @classmethod
    def info_ack(cls) -> bytes:
        return MSG_C_INFO_ACK.encode("ascii")

    @classmethod
    def keep_alive(cls) -> bytes:
        return MSG_C_KEEP_ALIVE.encode("ascii")

    @classmethod
    def client_info(cls, x: int, y: int, width: int, height: int, warp_size: int = 0, mx: int = 0, my: int = 0) -> bytes:
        fmt = "DINF%2i%2i%2i%2i%2i%2i%2i"
        return cls.pack_format(fmt, x, y, width, height, warp_size, mx, my)

    @classmethod
    def enter(cls, x: int, y: int, seq: int = 0, mask: int = 0) -> bytes:
        fmt = "CINN%2i%2i%4i%2i"
        return cls.pack_format(fmt, x, y, seq, mask)

    @classmethod
    def leave(cls) -> bytes:
        return MSG_C_LEAVE.encode("ascii")

    @classmethod
    def mouse_move(cls, x: int, y: int) -> bytes:
        fmt = "DMMV%2i%2i"
        return cls.pack_format(fmt, x, y)

    @classmethod
    def mouse_rel_move(cls, dx: int, dy: int) -> bytes:
        fmt = "DMRM%2i%2i"
        return cls.pack_format(fmt, dx, dy)

    @classmethod
    def mouse_down(cls, button_id: int) -> bytes:
        fmt = "DMDN%1i"
        return cls.pack_format(fmt, button_id)

    @classmethod
    def mouse_up(cls, button_id: int) -> bytes:
        fmt = "DMUP%1i"
        return cls.pack_format(fmt, button_id)

    @classmethod
    def mouse_wheel(cls, x_delta: int, y_delta: int) -> bytes:
        fmt = "DMWM%2i%2i"
        return cls.pack_format(fmt, x_delta, y_delta)

    @classmethod
    def key_down(cls, key: int, mask: int, code: int) -> bytes:
        fmt = "DKDN%2i%2i%2i"
        return cls.pack_format(fmt, key, mask, code)

    @classmethod
    def key_repeat(cls, key: int, mask: int, count: int, code: int) -> bytes:
        fmt = "DKRP%2i%2i%2i%2i"
        return cls.pack_format(fmt, key, mask, count, code)

    @classmethod
    def key_up(cls, key: int, mask: int, code: int) -> bytes:
        fmt = "DKUP%2i%2i%2i"
        return cls.pack_format(fmt, key, mask, code)

    @classmethod
    def clipboard_data(cls, clip_id: int, seq: int, mark: int, data: str) -> bytes:
        fmt = "DCLP%1i%4i%1i%s"
        return cls.pack_format(fmt, clip_id, seq, mark, data)


class PacketParser:
    """Helper to parse binary messages according to Synergy protocol rules."""

    @staticmethod
    def unpack_format(fmt: str, data: bytes) -> Tuple[List[Any], int]:
        out = []
        i = 0
        offset = 0
        while i < len(fmt):
            if fmt[i] == "%":
                i += 1
                length_str = ""
                while i < len(fmt) and fmt[i].isdigit():
                    length_str += fmt[i]
                    i += 1
                length = int(length_str) if length_str else 0
                type_char = fmt[i]
                i += 1

                if type_char == "i":
                    if length == 1:
                        val = struct.unpack_from("B", data, offset)[0]
                        offset += 1
                    elif length == 2:
                        val = struct.unpack_from(">H", data, offset)[0]
                        offset += 2
                    elif length == 4:
                        val = struct.unpack_from(">I", data, offset)[0]
                        offset += 4
                    else:
                        raise ValueError(f"Invalid integer length {length}")
                    out.append(val)
                elif type_char == "s":
                    s_len = struct.unpack_from(">I", data, offset)[0]
                    offset += 4
                    s_bytes = data[offset : offset + s_len]
                    offset += s_len
                    try:
                        out.append(s_bytes.decode("utf-8"))
                    except UnicodeDecodeError:
                        out.append(s_bytes.decode("latin-1", errors="replace"))
                elif type_char == "I":
                    count = struct.unpack_from(">I", data, offset)[0]
                    offset += 4
                    items = []
                    for _ in range(count):
                        if length == 1:
                            items.append(struct.unpack_from("B", data, offset)[0])
                            offset += 1
                        elif length == 2:
                            items.append(struct.unpack_from(">H", data, offset)[0])
                            offset += 2
                        elif length == 4:
                            items.append(struct.unpack_from(">I", data, offset)[0])
                            offset += 4
                    out.append(items)
            else:
                # Literal character check
                if offset < len(data) and data[offset] == ord(fmt[i]):
                    offset += 1
                    i += 1
                else:
                    raise ValueError(f"Format literal mismatch at {i}: expected {fmt[i]}")
        return out, offset
