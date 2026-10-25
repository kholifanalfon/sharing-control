//! Synergy Next - Ultra-low-latency Cross-Platform Keyboard & Mouse Switch in Rust.

mod client;
mod config;
mod platform;
mod protocol;
mod server;
mod web;

use clap::Parser;
use std::sync::{Arc, Mutex};

use client::SynergyClient;
use config::AppConfig;
use platform::create_platform;
use server::SynergyServer;
use web::{start_web_gui, WebStatus};

#[derive(Parser, Debug)]
#[command(
    name = "synergy-next",
    about = "Ultra-low-latency KM Sharing wire-compatible with Synergy & Barrier 1.6",
    version = "0.1.0"
)]
struct Args {
    #[arg(short, long, help = "Mode: 'server' or 'client'")]
    mode: Option<String>,

    #[arg(short, long, help = "Target server IP (for client mode)")]
    server: Option<String>,

    #[arg(short, long, help = "Synergy protocol port (default: 24800)")]
    port: Option<u16>,

    #[arg(short, long, help = "Local screen name (default: hostname)")]
    name: Option<String>,

    #[arg(long, default_value_t = 24801, help = "GUI Dashboard port (default: 24801)")]
    gui_port: u16,

    #[arg(long, help = "Run in headless CLI mode without launching desktop GUI window")]
    no_gui: bool,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let args = Args::parse();
    let mut config = AppConfig::load_or_default();

    if let Some(m) = args.mode {
        config.mode = m;
    }
    if let Some(s) = args.server {
        config.server_host = s;
    }
    if let Some(p) = args.port {
        config.port = p;
    }
    if let Some(n) = args.name {
        config.screen_name = n;
    }

    println!("========================================================");
    println!(" ⚡ Barrier / Synergy Next (Rust Edition)");
    println!(" Mode        : {}", config.mode.to_uppercase());
    println!(" Screen Name : {}", config.screen_name);
    println!(" Protocol    : Port {}", config.port);
    println!(" GUI Window  : {}", if args.no_gui { "Disabled (--no-gui)" } else { "Launching 1:1 Desktop GUI Window" });
    println!("========================================================");

    let shared_config = Arc::new(Mutex::new(config.clone()));
    let shared_status = Arc::new(Mutex::new(WebStatus {
        running: true,
        role: config.mode.clone(),
        active_screen: config.screen_name.clone(),
        connected_clients_count: 0,
        logs: vec![
            format!("[System] Barrier 1.6 Core initialized in {} mode", config.mode),
            format!("[System] Screen '{}' active on display", config.screen_name),
        ],
    }));

    // Start 1:1 Desktop GUI
    if !args.no_gui {
        start_web_gui(
            shared_config.clone(),
            shared_status.clone(),
            args.gui_port,
            true, // Directly launch native desktop window!
        );
    }

    let platform = Arc::new(create_platform()?);

    if config.mode == "server" {
        let server = SynergyServer::new(config, platform);
        server.run().await?;
    } else {
        let client = SynergyClient::new(config, platform);
        client.run().await;
    }

    Ok(())
}
