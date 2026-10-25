//! Binary Packet Framing, Serialization, and Deserialization for Synergy/Barrier.

use byteorder::{BigEndian, ByteOrder};
use bytes::{Buf, BytesMut};
use crate::protocol::types::*;

pub struct PacketCodec;

impl PacketCodec {
    /// Prefix message bytes with 4-byte big-endian length.
    pub fn frame_packet(payload: &[u8]) -> Vec<u8> {
        let mut out = Vec::with_capacity(4 + payload.len());
        out.extend_from_slice(&(payload.len() as u32).to_be_bytes());
        out.extend_from_slice(payload);
        out
    }

    /// Try to read a framed packet from a stream buffer.
    pub fn unframe_packet(buf: &mut BytesMut) -> Option<Vec<u8>> {
        if buf.len() < 4 {
            return None;
        }
        let length = BigEndian::read_u32(&buf[..4]) as usize;
        if buf.len() < 4 + length {
            return None;
        }
        buf.advance(4);
        let packet = buf.split_to(length).to_vec();
        Some(packet)
    }

    /// Serialize a SynergyMessage into raw wire payload bytes.
    pub fn encode(msg: &SynergyMessage) -> Vec<u8> {
        let mut out = Vec::new();
        match msg {
            SynergyMessage::Hello { brand, major, minor } => {
                out.extend_from_slice(brand.as_bytes());
                out.extend_from_slice(&major.to_be_bytes());
                out.extend_from_slice(&minor.to_be_bytes());
            }
            SynergyMessage::HelloBack {
                brand,
                major,
                minor,
                screen_name,
            } => {
                out.extend_from_slice(brand.as_bytes());
                out.extend_from_slice(&major.to_be_bytes());
                out.extend_from_slice(&minor.to_be_bytes());
                let name_bytes = screen_name.as_bytes();
                out.extend_from_slice(&(name_bytes.len() as u32).to_be_bytes());
                out.extend_from_slice(name_bytes);
            }
            SynergyMessage::QueryInfo => {
                out.extend_from_slice(b"QINF");
            }
            SynergyMessage::InfoAck => {
                out.extend_from_slice(b"CIAK");
            }
            SynergyMessage::KeepAlive => {
                out.extend_from_slice(b"CALV");
            }
            SynergyMessage::ClientInfo {
                x,
                y,
                width,
                height,
                warp_size,
                mouse_x,
                mouse_y,
            } => {
                out.extend_from_slice(b"DINF");
                out.extend_from_slice(&x.to_be_bytes());
                out.extend_from_slice(&y.to_be_bytes());
                out.extend_from_slice(&width.to_be_bytes());
                out.extend_from_slice(&height.to_be_bytes());
                out.extend_from_slice(&warp_size.to_be_bytes());
                out.extend_from_slice(&mouse_x.to_be_bytes());
                out.extend_from_slice(&mouse_y.to_be_bytes());
            }
            SynergyMessage::CursorEnter { x, y, seq, mask } => {
                out.extend_from_slice(b"CINN");
                out.extend_from_slice(&x.to_be_bytes());
                out.extend_from_slice(&y.to_be_bytes());
                out.extend_from_slice(&seq.to_be_bytes());
                out.extend_from_slice(&mask.to_be_bytes());
            }
            SynergyMessage::CursorLeave => {
                out.extend_from_slice(b"COUT");
            }
            SynergyMessage::MouseMove { x, y } => {
                out.extend_from_slice(b"DMMV");
                out.extend_from_slice(&x.to_be_bytes());
                out.extend_from_slice(&y.to_be_bytes());
            }
            SynergyMessage::MouseRelMove { dx, dy } => {
                out.extend_from_slice(b"DMRM");
                out.extend_from_slice(&dx.to_be_bytes());
                out.extend_from_slice(&dy.to_be_bytes());
            }
            SynergyMessage::MouseDown { button } => {
                out.extend_from_slice(b"DMDN");
                out.push(*button);
            }
            SynergyMessage::MouseUp { button } => {
                out.extend_from_slice(b"DMUP");
                out.push(*button);
            }
            SynergyMessage::MouseWheel { x_delta, y_delta } => {
                out.extend_from_slice(b"DMWM");
                out.extend_from_slice(&x_delta.to_be_bytes());
                out.extend_from_slice(&y_delta.to_be_bytes());
            }
            SynergyMessage::KeyDown { key, mask, code } => {
                out.extend_from_slice(b"DKDN");
                out.extend_from_slice(&key.to_be_bytes());
                out.extend_from_slice(&mask.to_be_bytes());
                out.extend_from_slice(&code.to_be_bytes());
            }
            SynergyMessage::KeyRepeat {
                key,
                mask,
                count,
                code,
            } => {
                out.extend_from_slice(b"DKRP");
                out.extend_from_slice(&key.to_be_bytes());
                out.extend_from_slice(&mask.to_be_bytes());
                out.extend_from_slice(&count.to_be_bytes());
                out.extend_from_slice(&code.to_be_bytes());
            }
            SynergyMessage::KeyUp { key, mask, code } => {
                out.extend_from_slice(b"DKUP");
                out.extend_from_slice(&key.to_be_bytes());
                out.extend_from_slice(&mask.to_be_bytes());
                out.extend_from_slice(&code.to_be_bytes());
            }
            SynergyMessage::ClipboardData { id, seq, mark, data } => {
                out.extend_from_slice(b"DCLP");
                out.push(*id);
                out.extend_from_slice(&seq.to_be_bytes());
                out.push(*mark);
                let d_bytes = data.as_bytes();
                out.extend_from_slice(&(d_bytes.len() as u32).to_be_bytes());
                out.extend_from_slice(d_bytes);
            }
            SynergyMessage::Unknown { code } => {
                out.extend_from_slice(code.as_bytes());
            }
        }
        out
    }

    /// Parse a raw wire payload into a SynergyMessage.
    pub fn decode(payload: &[u8]) -> Option<SynergyMessage> {
        if payload.len() < 4 {
            return None;
        }

        // Check Greetings ("Barrier" or "Synergy")
        if payload.starts_with(b"Barrier") || payload.starts_with(b"Synergy") {
            let brand_len = if payload.starts_with(b"Barrier") { 7 } else { 7 };
            let brand = String::from_utf8_lossy(&payload[..brand_len]).to_string();
            if payload.len() >= brand_len + 4 {
                let major = BigEndian::read_u16(&payload[brand_len..brand_len + 2]);
                let minor = BigEndian::read_u16(&payload[brand_len + 2..brand_len + 4]);

                // Check if HelloBack with client name
                if payload.len() >= brand_len + 8 {
                    let name_len = BigEndian::read_u32(&payload[brand_len + 4..brand_len + 8]) as usize;
                    if payload.len() >= brand_len + 8 + name_len {
                        let name = String::from_utf8_lossy(&payload[brand_len + 8..brand_len + 8 + name_len]).to_string();
                        return Some(SynergyMessage::HelloBack {
                            brand,
                            major,
                            minor,
                            screen_name: name,
                        });
                    }
                }
                return Some(SynergyMessage::Hello { brand, major, minor });
            }
        }

        let cmd = &payload[..4];
        match cmd {
            b"QINF" => Some(SynergyMessage::QueryInfo),
            b"CIAK" => Some(SynergyMessage::InfoAck),
            b"CALV" => Some(SynergyMessage::KeepAlive),
            b"COUT" => Some(SynergyMessage::CursorLeave),
            b"DINF" if payload.len() >= 18 => Some(SynergyMessage::ClientInfo {
                x: BigEndian::read_u16(&payload[4..6]),
                y: BigEndian::read_u16(&payload[6..8]),
                width: BigEndian::read_u16(&payload[8..10]),
                height: BigEndian::read_u16(&payload[10..12]),
                warp_size: BigEndian::read_u16(&payload[12..14]),
                mouse_x: BigEndian::read_u16(&payload[14..16]),
                mouse_y: BigEndian::read_u16(&payload[16..18]),
            }),
            b"CINN" if payload.len() >= 16 => Some(SynergyMessage::CursorEnter {
                x: BigEndian::read_u16(&payload[4..6]),
                y: BigEndian::read_u16(&payload[6..8]),
                seq: BigEndian::read_u32(&payload[8..12]),
                mask: BigEndian::read_u16(&payload[12..14]),
            }),
            b"DMMV" if payload.len() >= 8 => Some(SynergyMessage::MouseMove {
                x: BigEndian::read_u16(&payload[4..6]),
                y: BigEndian::read_u16(&payload[6..8]),
            }),
            b"DMRM" if payload.len() >= 8 => Some(SynergyMessage::MouseRelMove {
                dx: BigEndian::read_i16(&payload[4..6]),
                dy: BigEndian::read_i16(&payload[6..8]),
            }),
            b"DMDN" if payload.len() >= 5 => Some(SynergyMessage::MouseDown { button: payload[4] }),
            b"DMUP" if payload.len() >= 5 => Some(SynergyMessage::MouseUp { button: payload[4] }),
            b"DMWM" if payload.len() >= 8 => Some(SynergyMessage::MouseWheel {
                x_delta: BigEndian::read_i16(&payload[4..6]),
                y_delta: BigEndian::read_i16(&payload[6..8]),
            }),
            b"DKDN" if payload.len() >= 10 => Some(SynergyMessage::KeyDown {
                key: BigEndian::read_u16(&payload[4..6]),
                mask: BigEndian::read_u16(&payload[6..8]),
                code: BigEndian::read_u16(&payload[8..10]),
            }),
            b"DKUP" if payload.len() >= 10 => Some(SynergyMessage::KeyUp {
                key: BigEndian::read_u16(&payload[4..6]),
                mask: BigEndian::read_u16(&payload[6..8]),
                code: BigEndian::read_u16(&payload[8..10]),
            }),
            b"DCLP" if payload.len() >= 14 => {
                let id = payload[4];
                let seq = BigEndian::read_u32(&payload[5..9]);
                let mark = payload[9];
                let d_len = BigEndian::read_u32(&payload[10..14]) as usize;
                let data = if payload.len() >= 14 + d_len {
                    String::from_utf8_lossy(&payload[14..14 + d_len]).to_string()
                } else {
                    String::new()
                };
                Some(SynergyMessage::ClipboardData { id, seq, mark, data })
            }
            _ => Some(SynergyMessage::Unknown {
                code: String::from_utf8_lossy(cmd).to_string(),
            }),
        }
    }
}
