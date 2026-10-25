//! Platform abstraction interface for mouse, keyboard, and screen metrics.

pub trait PlatformScreen: Send + Sync {
    fn get_screen_size(&self) -> (u16, u16);
    fn get_cursor_pos(&self) -> (u16, u16);
    fn warp_cursor(&self, x: u16, y: u16);
    fn inject_mouse_move(&self, x: u16, y: u16);
    fn inject_mouse_rel_move(&self, dx: i16, dy: i16);
    fn inject_mouse_down(&self, button: u8);
    fn inject_mouse_up(&self, button: u8);
    fn inject_mouse_wheel(&self, x_delta: i16, y_delta: i16);
    fn inject_key_down(&self, key: u16, mask: u16, code: u16);
    fn inject_key_up(&self, key: u16, mask: u16, code: u16);
    fn get_clipboard(&self) -> String;
    fn set_clipboard(&self, text: &str);
}

#[cfg(target_os = "linux")]
pub mod linux;
#[cfg(target_os = "macos")]
pub mod macos;
#[cfg(target_os = "windows")]
pub mod windows;

pub fn create_platform() -> Result<Box<dyn PlatformScreen>, Box<dyn std::error::Error + Send + Sync>> {
    #[cfg(target_os = "linux")]
    {
        Ok(Box::new(linux::LinuxScreen::new()?))
    }

    #[cfg(target_os = "macos")]
    {
        Ok(Box::new(macos::MacOSScreen::new()?))
    }

    #[cfg(target_os = "windows")]
    {
        Ok(Box::new(windows::WindowsScreen::new()?))
    }

    #[cfg(not(any(target_os = "linux", target_os = "macos", target_os = "windows")))]
    {
        compile_error!("Unsupported target OS platform");
    }
}
