//! Windows Platform Screen Driver via Win32 SendInput.

#[cfg(target_os = "windows")]
use std::process::Command;
#[cfg(target_os = "windows")]
use windows_sys::Win32::Foundation::POINT;
#[cfg(target_os = "windows")]
use windows_sys::Win32::UI::Input::KeyboardAndMouse::{
    SendInput, INPUT, INPUT_0, INPUT_KEYBOARD, INPUT_MOUSE, KEYBDINPUT, KEYEVENTF_KEYUP,
    MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP, MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP,
    MOUSEEVENTF_MOVE, MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP, MOUSEEVENTF_WHEEL, MOUSEINPUT,
};
#[cfg(target_os = "windows")]
use windows_sys::Win32::UI::WindowsAndMessaging::{
    GetCursorPos, GetSystemMetrics, SetCursorPos, SM_CXSCREEN, SM_CYSCREEN,
};
#[cfg(target_os = "windows")]
use crate::platform::PlatformScreen;

#[cfg(target_os = "windows")]
pub struct WindowsScreen;

#[cfg(target_os = "windows")]
impl WindowsScreen {
    pub fn new() -> Result<Self, Box<dyn std::error::Error + Send + Sync>> {
        Ok(Self)
    }
}

#[cfg(target_os = "windows")]
impl PlatformScreen for WindowsScreen {
    fn get_screen_size(&self) -> (u16, u16) {
        unsafe {
            let w = GetSystemMetrics(SM_CXSCREEN) as u16;
            let h = GetSystemMetrics(SM_CYSCREEN) as u16;
            (w, h)
        }
    }

    fn get_cursor_pos(&self) -> (u16, u16) {
        unsafe {
            let mut pt = POINT { x: 0, y: 0 };
            if GetCursorPos(&mut pt) != 0 {
                return (pt.x as u16, pt.y as u16);
            }
        }
        (0, 0)
    }

    fn warp_cursor(&self, x: u16, y: u16) {
        unsafe {
            SetCursorPos(x as i32, y as i32);
        }
    }

    fn inject_mouse_move(&self, x: u16, y: u16) {
        self.warp_cursor(x, y);
    }

    fn inject_mouse_rel_move(&self, dx: i16, dy: i16) {
        unsafe {
            let input = INPUT {
                r#type: INPUT_MOUSE,
                Anonymous: INPUT_0 {
                    mi: MOUSEINPUT {
                        dx: dx as i32,
                        dy: dy as i32,
                        mouseData: 0,
                        dwFlags: MOUSEEVENTF_MOVE,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            };
            SendInput(1, &input, std::mem::size_of::<INPUT>() as i32);
        }
    }

    fn inject_mouse_down(&self, button: u8) {
        let flag = match button {
            1 => MOUSEEVENTF_LEFTDOWN,
            3 => MOUSEEVENTF_RIGHTDOWN,
            _ => MOUSEEVENTF_MIDDLEDOWN,
        };
        unsafe {
            let input = INPUT {
                r#type: INPUT_MOUSE,
                Anonymous: INPUT_0 {
                    mi: MOUSEINPUT {
                        dx: 0,
                        dy: 0,
                        mouseData: 0,
                        dwFlags: flag,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            };
            SendInput(1, &input, std::mem::size_of::<INPUT>() as i32);
        }
    }

    fn inject_mouse_up(&self, button: u8) {
        let flag = match button {
            1 => MOUSEEVENTF_LEFTUP,
            3 => MOUSEEVENTF_RIGHTUP,
            _ => MOUSEEVENTF_MIDDLEUP,
        };
        unsafe {
            let input = INPUT {
                r#type: INPUT_MOUSE,
                Anonymous: INPUT_0 {
                    mi: MOUSEINPUT {
                        dx: 0,
                        dy: 0,
                        mouseData: 0,
                        dwFlags: flag,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            };
            SendInput(1, &input, std::mem::size_of::<INPUT>() as i32);
        }
    }

    fn inject_mouse_wheel(&self, _x_delta: i16, y_delta: i16) {
        unsafe {
            let input = INPUT {
                r#type: INPUT_MOUSE,
                Anonymous: INPUT_0 {
                    mi: MOUSEINPUT {
                        dx: 0,
                        dy: 0,
                        mouseData: (y_delta as i32 * 120) as u32,
                        dwFlags: MOUSEEVENTF_WHEEL,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            };
            SendInput(1, &input, std::mem::size_of::<INPUT>() as i32);
        }
    }

    fn inject_key_down(&self, _key: u16, _mask: u16, code: u16) {
        unsafe {
            let input = INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: code,
                        wScan: 0,
                        dwFlags: 0,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            };
            SendInput(1, &input, std::mem::size_of::<INPUT>() as i32);
        }
    }

    fn inject_key_up(&self, _key: u16, _mask: u16, code: u16) {
        unsafe {
            let input = INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: code,
                        wScan: 0,
                        dwFlags: KEYEVENTF_KEYUP,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            };
            SendInput(1, &input, std::mem::size_of::<INPUT>() as i32);
        }
    }

    fn get_clipboard(&self) -> String {
        if let Ok(out) = Command::new("powershell").args(["-Command", "Get-Clipboard"]).output() {
            if out.status.success() {
                return String::from_utf8_lossy(&out.stdout).trim_end().to_string();
            }
        }
        String::new()
    }

    fn set_clipboard(&self, text: &str) {
        let cmd = format!("Set-Clipboard -Value @'\n{}\n'@", text);
        let _ = Command::new("powershell").args(["-Command", &cmd]).output();
    }
}
