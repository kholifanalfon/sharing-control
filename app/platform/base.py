"""
Abstract Platform Screen and Input Provider.
Standardizes mouse and keyboard capture and injection across macOS, Linux, and Windows.
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional, Tuple


class BasePlatformScreen(ABC):
    def __init__(self):
        self._is_capturing = False

    @abstractmethod
    def get_screen_size(self) -> Tuple[int, int]:
        """Return (width, height) of primary desktop."""
        pass

    @abstractmethod
    def get_cursor_pos(self) -> Tuple[int, int]:
        """Return current (x, y) coordinates of mouse cursor."""
        pass

    @abstractmethod
    def warp_cursor(self, x: int, y: int) -> None:
        """Move hardware cursor to absolute position (x, y)."""
        pass

    @abstractmethod
    def inject_mouse_move(self, x: int, y: int) -> None:
        pass

    @abstractmethod
    def inject_mouse_rel_move(self, dx: int, dy: int) -> None:
        pass

    @abstractmethod
    def inject_mouse_down(self, button: int) -> None:
        pass

    @abstractmethod
    def inject_mouse_up(self, button: int) -> None:
        pass

    @abstractmethod
    def inject_mouse_wheel(self, x_delta: int, y_delta: int) -> None:
        pass

    @abstractmethod
    def inject_key_down(self, key: int, mask: int, code: int) -> None:
        pass

    @abstractmethod
    def inject_key_up(self, key: int, mask: int, code: int) -> None:
        pass

    @abstractmethod
    def get_clipboard(self) -> str:
        pass

    @abstractmethod
    def set_clipboard(self, text: str) -> None:
        pass

    @abstractmethod
    def start_capture(
        self,
        on_move: Optional[Callable[[int, int], None]] = None,
        on_click: Optional[Callable[[int, bool], None]] = None,
        on_wheel: Optional[Callable[[int, int], None]] = None,
        on_key: Optional[Callable[[int, int, int, bool], None]] = None,
    ) -> None:
        """Start capturing local hardware inputs (used when running as Server)."""
        pass

    @abstractmethod
    def stop_capture(self) -> None:
        pass
