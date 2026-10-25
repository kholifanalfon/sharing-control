//! Synergy & Barrier 1.6 Protocol Types and Constants.

pub const PROTOCOL_MAJOR_VERSION: u16 = 1;
pub const PROTOCOL_MINOR_VERSION: u16 = 6;
#[allow(dead_code)]
pub const DEFAULT_PORT: u16 = 24800;

#[allow(dead_code)]
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Direction {
    NoDirection = 0,
    Left = 1,
    Right = 2,
    Top = 3,
    Bottom = 4,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SynergyMessage {
    Hello {
        brand: String,
        major: u16,
        minor: u16,
    },
    HelloBack {
        brand: String,
        major: u16,
        minor: u16,
        screen_name: String,
    },
    QueryInfo,
    InfoAck,
    KeepAlive,
    ClientInfo {
        x: u16,
        y: u16,
        width: u16,
        height: u16,
        warp_size: u16,
        mouse_x: u16,
        mouse_y: u16,
    },
    CursorEnter {
        x: u16,
        y: u16,
        seq: u32,
        mask: u16,
    },
    CursorLeave,
    MouseMove {
        x: u16,
        y: u16,
    },
    MouseRelMove {
        dx: i16,
        dy: i16,
    },
    MouseDown {
        button: u8,
    },
    MouseUp {
        button: u8,
    },
    MouseWheel {
        x_delta: i16,
        y_delta: i16,
    },
    KeyDown {
        key: u16,
        mask: u16,
        code: u16,
    },
    #[allow(dead_code)]
    KeyRepeat {
        key: u16,
        mask: u16,
        count: u16,
        code: u16,
    },
    KeyUp {
        key: u16,
        mask: u16,
        code: u16,
    },
    ClipboardData {
        id: u8,
        seq: u32,
        mark: u8,
        data: String,
    },
    Unknown {
        code: String,
    },
}
