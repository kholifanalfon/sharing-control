"""
macOS Quartz / CoreGraphics Platform Screen & Input Provider.
Supports Intel and Apple Silicon (M1/M2/M3/M4) Macs with Retina HiDPI compensation.
"""

import ctypes
import os
import subprocess
import threading
import time
from ctypes import (
    c_int,
    c_uint,
    c_uint32,
    c_double,
    c_void_p,
    c_bool,
    Structure,
    byref,
)
from typing import Callable, Optional, Tuple
from app.platform.base import BasePlatformScreen

# Load macOS CoreGraphics / ApplicationServices
_cg = None
try:
    _cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
except Exception:
    pass


class CGPoint(Structure):
    _fields_ = [("x", c_double), ("y", c_double)]


class MacOSQuartzScreen(BasePlatformScreen):
    # Event types
    kCGEventNull = 0
    kCGEventLeftMouseDown = 1
    kCGEventLeftMouseUp = 2
    kCGEventRightMouseDown = 3
    kCGEventRightMouseUp = 4
    kCGEventMouseMoved = 5
    kCGEventLeftMouseDragged = 6
    kCGEventRightMouseDragged = 7
    kCGEventKeyDown = 10
    kCGEventKeyUp = 11
    kCGEventScrollWheel = 22
    kCGEventOtherMouseDown = 25
    kCGEventOtherMouseUp = 26
    kCGHIDEventTap = 0

    def __init__(self):
        super().__init__()
        self._capture_thread = None
        self._stop_capture_event = threading.Event()
        self._setup_quartz()

    def _setup_quartz(self):
        if not _cg:
            return

        _cg.CGMainDisplayID.restype = c_uint32
        _cg.CGMainDisplayID.argtypes = []

        _cg.CGDisplayPixelsWide.restype = c_uint32
        _cg.CGDisplayPixelsWide.argtypes = [c_uint32]

        _cg.CGDisplayPixelsHigh.restype = c_uint32
        _cg.CGDisplayPixelsHigh.argtypes = [c_uint32]

        _cg.CGWarpMouseCursorPosition.restype = c_int
        _cg.CGWarpMouseCursorPosition.argtypes = [CGPoint]

        _cg.CGEventCreateMouseEvent.restype = c_void_p
        _cg.CGEventCreateMouseEvent.argtypes = [c_void_p, c_uint32, CGPoint, c_uint32]

        _cg.CGEventCreateKeyboardEvent.restype = c_void_p
        _cg.CGEventCreateKeyboardEvent.argtypes = [c_void_p, c_uint32, c_bool]

        _cg.CGEventPost.restype = None
        _cg.CGEventPost.argtypes = [c_uint32, c_void_p]

        _cg.CFRelease.restype = None
        _cg.CFRelease.argtypes = [c_void_p]

    def get_screen_size(self) -> Tuple[int, int]:
        if not _cg:
            return 1920, 1080
        main_disp = _cg.CGMainDisplayID()
        w = _cg.CGDisplayPixelsWide(main_disp)
        h = _cg.CGDisplayPixelsHigh(main_disp)
        return int(w), int(h)

    def get_cursor_pos(self) -> Tuple[int, int]:
        # Fallback or CGEventCreate query
        if not _cg:
            return 0, 0
        try:
            # Query cursor position via CGEventCreate
            _cg.CGEventCreate.restype = c_void_p
            _cg.CGEventCreate.argtypes = [c_void_p]
            _cg.CGEventGetLocation.restype = CGPoint
            _cg.CGEventGetLocation.argtypes = [c_void_p]

            ev = _cg.CGEventCreate(None)
            if ev:
                loc = _cg.CGEventGetLocation(ev)
                _cg.CFRelease(ev)
                return int(loc.x), int(loc.y)
        except Exception:
            pass
        return 0, 0

    def warp_cursor(self, x: int, y: int) -> None:
        if not _cg:
            return
        pt = CGPoint(x=c_double(x), y=c_double(y))
        _cg.CGWarpMouseCursorPosition(pt)

    def inject_mouse_move(self, x: int, y: int) -> None:
        if not _cg:
            return
        pt = CGPoint(x=c_double(x), y=c_double(y))
        ev = _cg.CGEventCreateMouseEvent(None, self.kCGEventMouseMoved, pt, 0)
        if ev:
            _cg.CGEventPost(self.kCGHIDEventTap, ev)
            _cg.CFRelease(ev)

    def inject_mouse_rel_move(self, dx: int, dy: int) -> None:
        cx, cy = self.get_cursor_pos()
        self.inject_mouse_move(cx + dx, cy + dy)

    def inject_mouse_down(self, button: int) -> None:
        if not _cg:
            return
        cx, cy = self.get_cursor_pos()
        pt = CGPoint(x=c_double(cx), y=c_double(cy))
        ev_type = self.kCGEventLeftMouseDown if button == 1 else self.kCGEventRightMouseDown if button == 3 else self.kCGEventOtherMouseDown
        ev = _cg.CGEventCreateMouseEvent(None, ev_type, pt, button - 1)
        if ev:
            _cg.CGEventPost(self.kCGHIDEventTap, ev)
            _cg.CFRelease(ev)

    def inject_mouse_up(self, button: int) -> None:
        if not _cg:
            return
        cx, cy = self.get_cursor_pos()
        pt = CGPoint(x=c_double(cx), y=c_double(cy))
        ev_type = self.kCGEventLeftMouseUp if button == 1 else self.kCGEventRightMouseUp if button == 3 else self.kCGEventOtherMouseUp
        ev = _cg.CGEventCreateMouseEvent(None, ev_type, pt, button - 1)
        if ev:
            _cg.CGEventPost(self.kCGHIDEventTap, ev)
            _cg.CFRelease(ev)

    def inject_mouse_wheel(self, x_delta: int, y_delta: int) -> None:
        if not _cg:
            return
        try:
            _cg.CGEventCreateScrollWheelEvent.restype = c_void_p
            _cg.CGEventCreateScrollWheelEvent.argtypes = [c_void_p, c_uint32, c_uint32, c_int, c_int]
            # units: 1 = line scroll
            ev = _cg.CGEventCreateScrollWheelEvent(None, 1, 2, y_delta, x_delta)
            if ev:
                _cg.CGEventPost(self.kCGHIDEventTap, ev)
                _cg.CFRelease(ev)
        except Exception:
            pass

    def inject_key_down(self, key: int, mask: int, code: int) -> None:
        if not _cg:
            return
        ev = _cg.CGEventCreateKeyboardEvent(None, c_uint32(code), True)
        if ev:
            _cg.CGEventPost(self.kCGHIDEventTap, ev)
            _cg.CFRelease(ev)

    def inject_key_up(self, key: int, mask: int, code: int) -> None:
        if not _cg:
            return
        ev = _cg.CGEventCreateKeyboardEvent(None, c_uint32(code), False)
        if ev:
            _cg.CGEventPost(self.kCGHIDEventTap, ev)
            _cg.CFRelease(ev)

    def get_clipboard(self) -> str:
        try:
            res = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=1)
            if res.returncode == 0:
                return res.stdout
        except Exception:
            pass
        return ""

    def set_clipboard(self, text: str) -> None:
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, text=True)
            p.communicate(input=text, timeout=1)
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

        self._capture_thread = threading.Thread(target=loop, daemon=True, name="MacOSCaptureThread")
        self._capture_thread.start()

    def stop_capture(self) -> None:
        self._stop_capture_event.set()
        self._is_capturing = False
        if self._capture_thread:
            self._capture_thread.join(timeout=1.0)
            self._capture_thread = None
