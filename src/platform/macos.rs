//! macOS Platform Screen Driver via CoreGraphics Quartz.

#[cfg(target_os = "macos")]
use std::process::Command;
#[cfg(target_os = "macos")]
use core_graphics::display::CGMainDisplayID;
#[cfg(target_os = "macos")]
use core_graphics::event::{
    CGEvent, CGEventTapLocation, CGEventType, CGMouseButton, ScrollEventUnit,
};
#[cfg(target_os = "macos")]
use core_graphics::event_source::{CGEventSource, CGEventSourceStateID};
#[cfg(target_os = "macos")]
use core_graphics::geometry::CGPoint;
#[cfg(target_os = "macos")]
use crate::platform::PlatformScreen;

#[cfg(target_os = "macos")]
pub struct MacOSScreen;

#[cfg(target_os = "macos")]
impl MacOSScreen {
    pub fn new() -> Result<Self, Box<dyn std::error::Error + Send + Sync>> {
        Ok(Self)
    }

    fn create_event_source() -> Result<CGEventSource, ()> {
        CGEventSource::new(CGEventSourceStateID::CombinedSessionState)
    }
}

#[cfg(target_os = "macos")]
impl PlatformScreen for MacOSScreen {
    fn get_screen_size(&self) -> (u16, u16) {
        let display_id = unsafe { CGMainDisplayID() };
        let mode = core_graphics::display::CGDisplay::new(display_id);
        (mode.pixels_wide() as u16, mode.pixels_high() as u16)
    }

    fn get_cursor_pos(&self) -> (u16, u16) {
        if let Ok(source) = Self::create_event_source() {
            if let Ok(event) = CGEvent::new(source) {
                let loc = event.location();
                return (loc.x as u16, loc.y as u16);
            }
        }
        (0, 0)
    }

    fn warp_cursor(&self, x: u16, y: u16) {
        let pt = CGPoint::new(x as f64, y as f64);
        unsafe {
            core_graphics::display::CGWarpMouseCursorPosition(pt);
        }
    }

    fn inject_mouse_move(&self, x: u16, y: u16) {
        let pt = CGPoint::new(x as f64, y as f64);
        if let Ok(source) = Self::create_event_source() {
            if let Ok(event) = CGEvent::new_mouse_event(
                source,
                CGEventType::MouseMoved,
                pt,
                CGMouseButton::Left,
            ) {
                event.post(CGEventTapLocation::HID);
            }
        }
    }

    fn inject_mouse_rel_move(&self, dx: i16, dy: i16) {
        let (cx, cy) = self.get_cursor_pos();
        self.inject_mouse_move(
            (cx as i32 + dx as i32).max(0) as u16,
            (cy as i32 + dy as i32).max(0) as u16,
        );
    }

    fn inject_mouse_down(&self, button: u8) {
        let (cx, cy) = self.get_cursor_pos();
        let pt = CGPoint::new(cx as f64, cy as f64);
        let (ev_type, btn) = match button {
            1 => (CGEventType::LeftMouseDown, CGMouseButton::Left),
            3 => (CGEventType::RightMouseDown, CGMouseButton::Right),
            _ => (CGEventType::OtherMouseDown, CGMouseButton::Center),
        };
        if let Ok(source) = Self::create_event_source() {
            if let Ok(event) = CGEvent::new_mouse_event(source, ev_type, pt, btn) {
                event.post(CGEventTapLocation::HID);
            }
        }
    }

    fn inject_mouse_up(&self, button: u8) {
        let (cx, cy) = self.get_cursor_pos();
        let pt = CGPoint::new(cx as f64, cy as f64);
        let (ev_type, btn) = match button {
            1 => (CGEventType::LeftMouseUp, CGMouseButton::Left),
            3 => (CGEventType::RightMouseUp, CGMouseButton::Right),
            _ => (CGEventType::OtherMouseUp, CGMouseButton::Center),
        };
        if let Ok(source) = Self::create_event_source() {
            if let Ok(event) = CGEvent::new_mouse_event(source, ev_type, pt, btn) {
                event.post(CGEventTapLocation::HID);
            }
        }
    }

    fn inject_mouse_wheel(&self, x_delta: i16, y_delta: i16) {
        if let Ok(source) = Self::create_event_source() {
            if let Ok(event) = CGEvent::new_scroll_event(
                source,
                ScrollEventUnit::LINE,
                2,
                y_delta as i32,
                x_delta as i32,
                0,
            ) {
                event.post(CGEventTapLocation::HID);
            }
        }
    }

    fn inject_key_down(&self, _key: u16, _mask: u16, code: u16) {
        if let Ok(source) = Self::create_event_source() {
            if let Ok(event) = CGEvent::new_keyboard_event(source, code, true) {
                event.post(CGEventTapLocation::HID);
            }
        }
    }

    fn inject_key_up(&self, _key: u16, _mask: u16, code: u16) {
        if let Ok(source) = Self::create_event_source() {
            if let Ok(event) = CGEvent::new_keyboard_event(source, code, false) {
                event.post(CGEventTapLocation::HID);
            }
        }
    }

    fn get_clipboard(&self) -> String {
        if let Ok(out) = Command::new("pbpaste").output() {
            if out.status.success() {
                return String::from_utf8_lossy(&out.stdout).to_string();
            }
        }
        String::new()
    }

    fn set_clipboard(&self, text: &str) {
        use std::io::Write;
        if let Ok(mut child) = Command::new("pbcopy")
            .stdin(std::process::Stdio::piped())
            .spawn()
        {
            if let Some(mut stdin) = child.stdin.take() {
                let _ = stdin.write_all(text.as_bytes());
            }
            let _ = child.wait();
        }
    }
}
