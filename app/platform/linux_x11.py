"""
Linux X11 Platform Screen & Input Provider.
Uses native ctypes calls into libX11 and libXtst (zero external C++ dependencies).
"""

import ctypes
import os
import subprocess
import threading
import time
from ctypes import (
    c_int,
    c_uint,
    c_ulong,
    c_void_p,
    c_char_p,
    c_bool,
    byref,
    POINTER,
)
from typing import Callable, Optional, Tuple
from app.platform.base import BasePlatformScreen

# Load shared libraries
try:
    _x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
    _xtst = ctypes.cdll.LoadLibrary("libXtst.so.6")
except Exception:
    _x11 = None
    _xtst = None


class LinuxX11Screen(BasePlatformScreen):
    def __init__(self, display_name: Optional[str] = None):
        super().__init__()
        self._display_name = display_name or os.environ.get("DISPLAY", ":1")
        self._display = None
        self._root_window = 0
        self._capture_thread = None
        self._stop_capture_event = threading.Event()
        self._setup_x11()

    def _setup_x11(self):
        if not _x11:
            return

        _x11.XOpenDisplay.restype = c_void_p
        _x11.XOpenDisplay.argtypes = [c_char_p]

        _x11.XCloseDisplay.restype = c_int
        _x11.XCloseDisplay.argtypes = [c_void_p]

        _x11.XDefaultRootWindow.restype = c_ulong
        _x11.XDefaultRootWindow.argtypes = [c_void_p]

        _x11.XDefaultScreen.restype = c_int
        _x11.XDefaultScreen.argtypes = [c_void_p]

        _x11.XDisplayWidth.restype = c_int
        _x11.XDisplayWidth.argtypes = [c_void_p, c_int]

        _x11.XDisplayHeight.restype = c_int
        _x11.XDisplayHeight.argtypes = [c_void_p, c_int]

        _x11.XQueryPointer.restype = c_int
        _x11.XQueryPointer.argtypes = [
            c_void_p,
            c_ulong,
            POINTER(c_ulong),
            POINTER(c_ulong),
            POINTER(c_int),
            POINTER(c_int),
            POINTER(c_int),
            POINTER(c_int),
            POINTER(c_uint),
        ]

        _x11.XWarpPointer.restype = c_int
        _x11.XWarpPointer.argtypes = [
            c_void_p,
            c_ulong,
            c_ulong,
            c_int,
            c_int,
            c_uint,
            c_uint,
            c_int,
            c_int,
        ]

        _x11.XFlush.restype = c_int
        _x11.XFlush.argtypes = [c_void_p]

        _x11.XKeysymToKeycode.restype = c_uint
        _x11.XKeysymToKeycode.argtypes = [c_void_p, c_ulong]

        if _xtst:
            _xtst.XTestFakeMotionEvent.restype = c_int
            _xtst.XTestFakeMotionEvent.argtypes = [c_void_p, c_int, c_int, c_int, c_ulong]

            _xtst.XTestFakeButtonEvent.restype = c_int
            _xtst.XTestFakeButtonEvent.argtypes = [c_void_p, c_uint, c_int, c_ulong]

            _xtst.XTestFakeKeyEvent.restype = c_int
            _xtst.XTestFakeKeyEvent.argtypes = [c_void_p, c_uint, c_int, c_ulong]

        d_bytes = self._display_name.encode("utf-8")
        self._display = _x11.XOpenDisplay(d_bytes)
        if not self._display:
            self._display = _x11.XOpenDisplay(None)

        if self._display:
            self._root_window = _x11.XDefaultRootWindow(self._display)

    def get_screen_size(self) -> Tuple[int, int]:
        if not self._display:
            return 1920, 1080
        screen_num = _x11.XDefaultScreen(self._display)
        w = _x11.XDisplayWidth(self._display, screen_num)
        h = _x11.XDisplayHeight(self._display, screen_num)
        return int(w), int(h)

    def get_cursor_pos(self) -> Tuple[int, int]:
        if not self._display:
            return 0, 0
        r_root = c_ulong()
        r_child = c_ulong()
        rx = c_int()
        ry = c_int()
        wx = c_int()
        wy = c_int()
        mask = c_uint()

        res = _x11.XQueryPointer(
            self._display,
            self._root_window,
            byref(r_root),
            byref(r_child),
            byref(rx),
            byref(ry),
            byref(wx),
            byref(wy),
            byref(mask),
        )
        if res:
            return int(rx.value), int(ry.value)
        return 0, 0

    def warp_cursor(self, x: int, y: int) -> None:
        if not self._display:
            return
        _x11.XWarpPointer(self._display, 0, self._root_window, 0, 0, 0, 0, c_int(x), c_int(y))
        _x11.XFlush(self._display)

    def inject_mouse_move(self, x: int, y: int) -> None:
        if not self._display or not _xtst:
            return
        _xtst.XTestFakeMotionEvent(self._display, -1, c_int(x), c_int(y), c_ulong(0))
        _x11.XFlush(self._display)

    def inject_mouse_rel_move(self, dx: int, dy: int) -> None:
        cx, cy = self.get_cursor_pos()
        self.inject_mouse_move(cx + dx, cy + dy)

    def inject_mouse_down(self, button: int) -> None:
        if not self._display or not _xtst:
            return
        _xtst.XTestFakeButtonEvent(self._display, c_uint(button), c_int(1), c_ulong(0))
        _x11.XFlush(self._display)

    def inject_mouse_up(self, button: int) -> None:
        if not self._display or not _xtst:
            return
        _xtst.XTestFakeButtonEvent(self._display, c_uint(button), c_int(0), c_ulong(0))
        _x11.XFlush(self._display)

    def inject_mouse_wheel(self, x_delta: int, y_delta: int) -> None:
        if not self._display or not _xtst:
            return
        if y_delta > 0:
            btn = 4
        elif y_delta < 0:
            btn = 5
        elif x_delta < 0:
            btn = 6
        elif x_delta > 0:
            btn = 7
        else:
            return

        _xtst.XTestFakeButtonEvent(self._display, c_uint(btn), c_int(1), c_ulong(0))
        _xtst.XTestFakeButtonEvent(self._display, c_uint(btn), c_int(0), c_ulong(0))
        _x11.XFlush(self._display)

    def inject_key_down(self, key: int, mask: int, code: int) -> None:
        if not self._display or not _xtst:
            return
        keycode = code if code > 0 else _x11.XKeysymToKeycode(self._display, c_ulong(key))
        if keycode > 0:
            _xtst.XTestFakeKeyEvent(self._display, c_uint(keycode), c_int(1), c_ulong(0))
            _x11.XFlush(self._display)

    def inject_key_up(self, key: int, mask: int, code: int) -> None:
        if not self._display or not _xtst:
            return
        keycode = code if code > 0 else _x11.XKeysymToKeycode(self._display, c_ulong(key))
        if keycode > 0:
            _xtst.XTestFakeKeyEvent(self._display, c_uint(keycode), c_int(0), c_ulong(0))
            _x11.XFlush(self._display)

    def get_clipboard(self) -> str:
        for tool in [["xclip", "-selection", "clipboard", "-o"], ["xsel", "--clipboard", "--output"]]:
            try:
                res = subprocess.run(tool, capture_output=True, text=True, timeout=1)
                if res.returncode == 0:
                    return res.stdout
            except Exception:
                continue
        return ""

    def set_clipboard(self, text: str) -> None:
        for tool in [["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
            try:
                p = subprocess.Popen(tool, stdin=subprocess.PIPE, text=True)
                p.communicate(input=text, timeout=1)
                if p.returncode == 0:
                    return
            except Exception:
                continue

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

        self._capture_thread = threading.Thread(target=loop, daemon=True, name="LinuxCaptureThread")
        self._capture_thread.start()

    def stop_capture(self) -> None:
        self._stop_capture_event.set()
        self._is_capturing = False
        if self._capture_thread:
            self._capture_thread.join(timeout=1.0)
            self._capture_thread = None
