//! Embedded Web GUI & REST API Server for Synergy Next in pure Rust.

use std::sync::{Arc, Mutex};
use std::thread;
use tiny_http::{Header, Method, Response, Server, StatusCode};

use crate::config::AppConfig;

const HTML_CONTENT: &str = include_str!("static/index.html");
const CSS_CONTENT: &str = include_str!("static/barrier.css");
const JS_CONTENT: &str = include_str!("static/barrier.js");

pub struct WebStatus {
    pub running: bool,
    pub role: String,
    pub active_screen: String,
    pub connected_clients_count: usize,
    pub logs: Vec<String>,
}

pub fn start_web_gui(
    config: Arc<Mutex<AppConfig>>,
    status: Arc<Mutex<WebStatus>>,
    port: u16,
    open_window: bool,
) {
    let addr = format!("0.0.0.0:{}", port);
    let server = match Server::http(&addr) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("[Web GUI] Failed to start HTTP server on {}: {}", addr, e);
            return;
        }
    };

    println!("⚡ [Barrier GUI] Desktop window starting on port {}", port);

    if open_window {
        let url = format!("http://localhost:{}", port);
        thread::spawn(move || {
            launch_native_desktop_window(&url);
        });
    }

    thread::spawn(move || {
        for mut request in server.incoming_requests() {
            let url = request.url().to_string();
            let method = request.method().clone();

            match (method, url.as_str()) {
                (Method::Get, "/") | (Method::Get, "/index.html") => {
                    let mut resp = Response::from_string(HTML_CONTENT);
                    resp.add_header(Header::from_bytes(&b"Content-Type"[..], &b"text/html; charset=utf-8"[..]).unwrap());
                    let _ = request.respond(resp);
                }
                (Method::Get, "/barrier.css") | (Method::Get, "/app.css") => {
                    let mut resp = Response::from_string(CSS_CONTENT);
                    resp.add_header(Header::from_bytes(&b"Content-Type"[..], &b"text/css; charset=utf-8"[..]).unwrap());
                    let _ = request.respond(resp);
                }
                (Method::Get, "/barrier.js") | (Method::Get, "/app.js") => {
                    let mut resp = Response::from_string(JS_CONTENT);
                    resp.add_header(Header::from_bytes(&b"Content-Type"[..], &b"application/javascript; charset=utf-8"[..]).unwrap());
                    let _ = request.respond(resp);
                }
                (Method::Get, "/api/status") => {
                    let st = status.lock().unwrap();
                    let json = serde_json::json!({
                        "running": st.running,
                        "role": st.role,
                        "active_screen": st.active_screen,
                        "connected_clients": vec![0; st.connected_clients_count],
                        "logs": st.logs,
                    });
                    let mut resp = Response::from_string(json.to_string());
                    resp.add_header(Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap());
                    let _ = request.respond(resp);
                }
                (Method::Get, "/api/config") => {
                    let cfg = config.lock().unwrap();
                    let json = serde_json::to_string(&*cfg).unwrap_or_default();
                    let mut resp = Response::from_string(json);
                    resp.add_header(Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap());
                    let _ = request.respond(resp);
                }
                (Method::Post, "/api/config") => {
                    let mut body = String::new();
                    let _ = request.as_reader().read_to_string(&mut body);
                    if let Ok(new_cfg) = serde_json::from_str::<AppConfig>(&body) {
                        let mut cfg = config.lock().unwrap();
                        *cfg = new_cfg;
                        let _ = cfg.save();
                    }
                    let resp = Response::from_string(r#"{"success":true}"#);
                    let _ = request.respond(resp);
                }
                (Method::Post, "/api/start") => {
                    let mut st = status.lock().unwrap();
                    st.running = true;
                    let resp = Response::from_string(r#"{"success":true,"running":true}"#);
                    let _ = request.respond(resp);
                }
                (Method::Post, "/api/stop") => {
                    let mut st = status.lock().unwrap();
                    st.running = false;
                    let resp = Response::from_string(r#"{"success":true,"running":false}"#);
                    let _ = request.respond(resp);
                }
                _ => {
                    let resp = Response::empty(StatusCode(404));
                    let _ = request.respond(resp);
                }
            }
        }
    });
}

/// Spawns a dedicated native desktop window (App Mode without URL bar or tabs).
fn launch_native_desktop_window(url: &str) {
    // Wait briefly for HTTP server socket to be ready
    thread::sleep(std::time::Duration::from_millis(300));

    #[cfg(target_os = "linux")]
    {
        let browsers = [
            "google-chrome",
            "google-chrome-stable",
            "chromium-browser",
            "chromium",
            "brave-browser",
            "microsoft-edge",
        ];
        let app_arg = format!("--app={}", url);
        for b in browsers {
            let mut cmd = std::process::Command::new(b);
            cmd.env("TMPDIR", "/tmp");
            cmd.args([
                &app_arg,
                "--window-size=680,620",
                "--user-data-dir=/tmp/syn_gui",
                "--class=barrier",
            ]);
            if cmd.spawn().is_ok() {
                return;
            }
        }
        let _ = std::process::Command::new("xdg-open").arg(url).spawn();
    }

    #[cfg(target_os = "windows")]
    {
        let win_browsers = ["msedge.exe", "chrome.exe", "brave.exe"];
        let app_arg = format!("--app={}", url);
        for b in win_browsers {
            if std::process::Command::new(b)
                .args([&app_arg, "--window-size=680,620"])
                .spawn()
                .is_ok()
            {
                return;
            }
        }
        let _ = std::process::Command::new("cmd").args(["/c", "start", url]).spawn();
    }

    #[cfg(target_os = "macos")]
    {
        let mac_browsers = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ];
        let app_arg = format!("--app={}", url);
        for b in mac_browsers {
            if std::path::Path::new(b).exists() {
                if std::process::Command::new(b)
                    .args([
                        &app_arg,
                        "--window-size=680,620",
                        "--user-data-dir=/tmp/synergy_next_gui",
                    ])
                    .spawn()
                    .is_ok()
                {
                    return;
                }
            }
        }
        let _ = std::process::Command::new("open").arg(url).spawn();
    }
}
