"""
Windows Win32 Platform Screen & Input Provider.
Uses native user32.dll with Per-Monitor V2 DPI awareness and SendInput.
"""

import ctypes
import os
import subprocess
import threading
import time
from ctypes import (
    c_int,
    c_uint,
    c_long,
    c_ulong,
    c_void_p,
    c_short,
    Structure,
    Union,
    byref,
    POINTER,
    sizeof,
)
from typing import Callable, Optional, Tuple
from app.platform.base import BasePlatformScreen

_user32 = None
try:
    _user32 = ctypes.windll.user32
except Exception:
    pass


class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


class MOUSEINPUT(Structure):
    _fields_ = [
        ("dx", c_long),
        ("dy", c_long),
        ("mouseData", c_ulong),
        ("dwFlags", c_ulong),
        ("time", c_ulong),
        ("dwExtraInfo", POINTER(c_ulong)),
    ]


class KEYBDINPUT(Structure):
    _fields_ = [
        ("wVk", c_short),
        ("wScan", c_short),
        ("dwFlags", c_ulong),
        ("time", c_ulong),
        ("dwExtraInfo", POINTER(c_ulong)),
    ]


class HARDWAREINPUT(Structure):
    _fields_ = [("uMsg", c_ulong), ("wParamL", c_short), ("wParamH", c_short)]


class INPUT_UNION(Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(Structure):
    _fields_ = [("type", c_ulong), ("union", INPUT_UNION)]


class Win32Screen(BasePlatformScreen):
    INPUT_MOUSE = 0
    INPUT_KEYBOARD = 1

    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_MIDDLEDOWN = 0x0020
    MOUSEEVENTF_MIDDLEUP = 0x0040
    MOUSEEVENTF_WHEEL = 0x0800
    MOUSEEVENTF_ABSOLUTE = 0x8000

    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004

    def __init__(self):
        super().__init__()
        self._capture_thread = None
        self._stop_capture_event = threading.Event()
        self._setup_win32()

    def _setup_win32(self):
        if not _user32:
            return
        try:
            # Enable Per-Monitor DPI awareness V2
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                _user32.SetProcessDPIAware()
            except Exception:
                pass

    def get_screen_size(self) -> Tuple[int, int]:
        if not _user32:
            return 1920, 1080
        w = _user32.GetSystemMetrics(0)  # SM_CXSCREEN
        h = _user32.GetSystemMetrics(1)  # SM_CYSCREEN
        return int(w), int(h)

    def get_cursor_pos(self) -> Tuple[int, int]:
        if not _user32:
            return 0, 0
        pt = POINT()
        if _user32.GetCursorPos(byref(pt)):
            return int(pt.x), int(pt.y)
        return 0, 0

    def warp_cursor(self, x: int, y: int) -> None:
        if not _user32:
            return
        _user32.SetCursorPos(int(x), int(y))

    def inject_mouse_move(self, x: int, y: int) -> None:
        self.warp_cursor(x, y)

    def inject_mouse_rel_move(self, dx: int, dy: int) -> None:
        if not _user32:
            return
        inp = INPUT()
        inp.type = self.INPUT_MOUSE
        inp.union.mi.dx = int(dx)
        inp.union.mi.dy = int(dy)
        inp.union.mi.dwFlags = self.MOUSEEVENTF_MOVE
        _user32.SendInput(1, byref(inp), sizeof(INPUT))

    def inject_mouse_down(self, button: int) -> None:
        if not _user32:
            return
        flag = self.MOUSEEVENTF_LEFTDOWN if button == 1 else self.MOUSEEVENTF_RIGHTDOWN if button == 3 else self.MOUSEEVENTF_MIDDLEDOWN
        inp = INPUT()
        inp.type = self.INPUT_MOUSE
        inp.union.mi.dwFlags = flag
        _user32.SendInput(1, byref(inp), sizeof(INPUT))

    def inject_mouse_up(self, button: int) -> None:
        if not _user32:
            return
        flag = self.MOUSEEVENTF_LEFTUP if button == 1 else self.MOUSEEVENTF_RIGHTUP if button == 3 else self.MOUSEEVENTF_MIDDLEUP
        inp = INPUT()
        inp.type = self.INPUT_MOUSE
        inp.union.mi.dwFlags = flag
        _user32.SendInput(1, byref(inp), sizeof(INPUT))

    def inject_mouse_wheel(self, x_delta: int, y_delta: int) -> None:
        if not _user32:
            return
        inp = INPUT()
        inp.type = self.INPUT_MOUSE
        inp.union.mi.dwFlags = self.MOUSEEVENTF_WHEEL
        inp.union.mi.mouseData = int(y_delta * 120)
        _user32.SendInput(1, byref(inp), sizeof(INPUT))

    def inject_key_down(self, key: int, mask: int, code: int) -> None:
        if not _user32:
            return
        inp = INPUT()
        inp.type = self.INPUT_KEYBOARD
        inp.union.ki.wVk = code
        inp.union.ki.dwFlags = 0
        _user32.SendInput(1, byref(inp), sizeof(INPUT))

    def inject_key_up(self, key: int, mask: int, code: int) -> None:
        if not _user32:
            return
        inp = INPUT()
        inp.type = self.INPUT_KEYBOARD
        inp.union.ki.wVk = code
        inp.union.ki.dwFlags = self.KEYEVENTF_KEYUP
        _user32.SendInput(1, byref(inp), sizeof(INPUT))

    def get_clipboard(self) -> str:
        try:
            # Fallback to powershell for quick clipboard read if ctypes clipboard lock fails
            res = subprocess.run(["powershell", "-command", "Get-Clipboard"], capture_output=True, text=True, timeout=1)
            if res.returncode == 0:
                return res.stdout
        except Exception:
            pass
        return ""

    def set_clipboard(self, text: str) -> None:
        try:
            cmd = f"Set-Clipboard -Value @'\n{text}\n'@"
            subprocess.run(["powershell", "-command", cmd], capture_output=True, timeout=1)
        except Exception:
            pass

    def start_capture(
        self,
        on_move: Optional[Callable[[int, int], None]] = None,
        on_click: Optional[Callable[[int, bool], None]] = None,
        on_wheel: Optional[Callable[[int, int], None]] = None,
        on_key: Optional[Callable[[int, int, int, bool], None]] = None,
    ) -> None:
        self._stop_capture_event.clear()
        self._is_capturing = True

        def loop():
            last_x, last_y = self.get_cursor_pos()
            while not self._stop_capture_event.is_set():
                cur_x, cur_y = self.get_cursor_pos()
                if (cur_x != last_x or cur_y != last_y) and on_move:
                    on_move(cur_x, cur_y)
                    last_x, last_y = cur_x, cur_y
                time.sleep(0.008)

        self._capture_thread = threading.Thread(target=loop, daemon=True, name="Win32CaptureThread")
        self._capture_thread.start()

    def stop_capture(self) -> None:
        self._stop_capture_event.set()
        self._is_capturing = False
        if self._capture_thread:
            self._capture_thread.join(timeout=1.0)
            self._capture_thread = None
