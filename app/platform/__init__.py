import sys
from app.platform.base import BasePlatformScreen


def get_platform_screen() -> BasePlatformScreen:
    if sys.platform == "darwin":
        from app.platform.macos_quartz import MacOSQuartzScreen

        return MacOSQuartzScreen()
    elif sys.platform == "win32":
        from app.platform.win32_input import Win32Screen

        return Win32Screen()
    else:
        from app.platform.linux_x11 import LinuxX11Screen

        return LinuxX11Screen()
