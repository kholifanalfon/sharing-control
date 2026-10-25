//! Linux X11 Platform Screen Driver via Pure Rust x11rb + xtest.

#[cfg(target_os = "linux")]
use std::process::Command;
#[cfg(target_os = "linux")]
use x11rb::connection::Connection;
#[cfg(target_os = "linux")]
use x11rb::protocol::xproto::{ConnectionExt as XProtoExt, Window};
#[cfg(target_os = "linux")]
use x11rb::protocol::xtest::ConnectionExt as XTestExt;
#[cfg(target_os = "linux")]
use x11rb::rust_connection::RustConnection;
#[cfg(target_os = "linux")]
use crate::platform::PlatformScreen;

#[cfg(target_os = "linux")]
pub struct LinuxScreen {
    conn: RustConnection,
    #[allow(dead_code)]
    screen_num: usize,
    root: Window,
    width: u16,
    height: u16,
}

#[cfg(target_os = "linux")]
impl LinuxScreen {
    pub fn new() -> Result<Self, Box<dyn std::error::Error + Send + Sync>> {
        // Auto fallback to :1 or :0 if DISPLAY is unset
        if std::env::var("DISPLAY").is_err() {
            if std::path::Path::new("/tmp/.X11-unix/X1").exists() {
                std::env::set_var("DISPLAY", ":1");
            } else if std::path::Path::new("/tmp/.X11-unix/X0").exists() {
                std::env::set_var("DISPLAY", ":0");
            }
        }

        let (conn, screen_num) = x11rb::connect(None)?;
        let setup = conn.setup();
        let screen = &setup.roots[screen_num];
        let root = screen.root;
        let width = screen.width_in_pixels;
        let height = screen.height_in_pixels;

        Ok(Self {
            conn,
            screen_num,
            root,
            width,
            height,
        })
    }
}

#[cfg(target_os = "linux")]
impl PlatformScreen for LinuxScreen {
    fn get_screen_size(&self) -> (u16, u16) {
        (self.width, self.height)
    }

    fn get_cursor_pos(&self) -> (u16, u16) {
        if let Ok(cookie) = self.conn.query_pointer(self.root) {
            if let Ok(reply) = cookie.reply() {
                return (reply.root_x as u16, reply.root_y as u16);
            }
        }
        (0, 0)
    }

    fn warp_cursor(&self, x: u16, y: u16) {
        let _ = self.conn.warp_pointer(0u32, self.root, 0, 0, 0, 0, x as i16, y as i16);
        let _ = self.conn.flush();
    }

    fn inject_mouse_move(&self, x: u16, y: u16) {
        let _ = self.conn.xtest_fake_input(
            6, // MotionNotify event type
            0,
            0,
            self.root,
            x as i16,
            y as i16,
            0,
        );
        let _ = self.conn.flush();
    }

    fn inject_mouse_rel_move(&self, dx: i16, dy: i16) {
        let (cx, cy) = self.get_cursor_pos();
        self.inject_mouse_move(
            (cx as i32 + dx as i32).max(0) as u16,
            (cy as i32 + dy as i32).max(0) as u16,
        );
    }

    fn inject_mouse_down(&self, button: u8) {
        let _ = self.conn.xtest_fake_input(
            4, // ButtonPress
            button,
            0,
            self.root,
            0,
            0,
            0,
        );
        let _ = self.conn.flush();
    }

    fn inject_mouse_up(&self, button: u8) {
        let _ = self.conn.xtest_fake_input(
            5, // ButtonRelease
            button,
            0,
            self.root,
            0,
            0,
            0,
        );
        let _ = self.conn.flush();
    }

    fn inject_mouse_wheel(&self, x_delta: i16, y_delta: i16) {
        let btn = if y_delta > 0 {
            4 // Wheel up
        } else if y_delta < 0 {
            5 // Wheel down
        } else if x_delta < 0 {
            6 // Wheel left
        } else if x_delta > 0 {
            7 // Wheel right
        } else {
            return;
        };

        self.inject_mouse_down(btn);
        self.inject_mouse_up(btn);
    }

    fn inject_key_down(&self, _key: u16, _mask: u16, code: u16) {
        if code > 0 {
            let _ = self.conn.xtest_fake_input(
                2, // KeyPress
                code as u8,
                0,
                self.root,
                0,
                0,
                0,
            );
            let _ = self.conn.flush();
        }
    }

    fn inject_key_up(&self, _key: u16, _mask: u16, code: u16) {
        if code > 0 {
            let _ = self.conn.xtest_fake_input(
                3, // KeyRelease
                code as u8,
                0,
                self.root,
                0,
                0,
                0,
            );
            let _ = self.conn.flush();
        }
    }

    fn get_clipboard(&self) -> String {
        for cmd in &["xclip", "xsel"] {
            let output = if *cmd == "xclip" {
                Command::new("xclip").args(["-selection", "clipboard", "-o"]).output()
            } else {
                Command::new("xsel").args(["--clipboard", "--output"]).output()
            };
            if let Ok(out) = output {
                if out.status.success() {
                    return String::from_utf8_lossy(&out.stdout).to_string();
                }
            }
        }
        String::new()
    }

    fn set_clipboard(&self, text: &str) {
        use std::io::Write;
        for cmd in &["xclip", "xsel"] {
            let process = if *cmd == "xclip" {
                Command::new("xclip")
                    .args(["-selection", "clipboard"])
                    .stdin(std::process::Stdio::piped())
                    .spawn()
            } else {
                Command::new("xsel")
                    .args(["--clipboard", "--input"])
                    .stdin(std::process::Stdio::piped())
                    .spawn()
            };
            if let Ok(mut child) = process {
                if let Some(mut stdin) = child.stdin.take() {
                    let _ = stdin.write_all(text.as_bytes());
                }
                let _ = child.wait();
                return;
            }
        }
    }
}
