//! Configuration management and Barrier.conf migration in Rust.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub screen_name: String,
    pub mode: String, // "server" or "client"
    pub server_host: String,
    pub port: u16,
    pub clipboard_sharing: bool,
    pub links: HashMap<String, HashMap<String, String>>,
}

impl Default for AppConfig {
    fn default() -> Self {
        let hostname = gethostname::gethostname().to_string_lossy().to_string();
        Self {
            screen_name: hostname,
            mode: "server".to_string(),
            server_host: "127.0.0.1".to_string(),
            port: 24800,
            clipboard_sharing: true,
            links: HashMap::new(),
        }
    }
}

impl AppConfig {
    pub fn config_path() -> PathBuf {
        let mut p = dirs_home().unwrap_or_else(|| PathBuf::from("."));
        p.push(".config");
        p.push("synergy-next");
        p.push("config.json");
        p
    }

    pub fn load_or_default() -> Self {
        let path = Self::config_path();
        if path.exists() {
            if let Ok(content) = fs::read_to_string(&path) {
                if let Ok(cfg) = serde_json::from_str::<AppConfig>(&content) {
                    return cfg;
                }
            }
        }

        // Try migrating from Barrier.conf
        let mut cfg = AppConfig::default();
        if cfg.try_import_barrier_conf() {
            let _ = cfg.save();
        }
        cfg
    }

    pub fn save(&self) -> Result<(), Box<dyn std::error::Error>> {
        let path = Self::config_path();
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let data = serde_json::to_string_pretty(self)?;
        fs::write(path, data)?;
        Ok(())
    }

    fn try_import_barrier_conf(&mut self) -> bool {
        let mut barrier_path = dirs_home().unwrap_or_else(|| PathBuf::from("."));
        barrier_path.push(".config");
        barrier_path.push("Debauchee");
        barrier_path.push("Barrier.conf");

        if !barrier_path.exists() {
            return false;
        }

        if let Ok(content) = fs::read_to_string(barrier_path) {
            let mut screens = Vec::new();
            for line in content.lines() {
                let trimmed = line.trim();
                if let Some(name) = trimmed.strip_prefix("screenName=") {
                    self.screen_name = name.trim().to_string();
                } else if let Some(host) = trimmed.strip_prefix("serverHostname=") {
                    self.server_host = host.trim().to_string();
                } else if trimmed.starts_with("screens\\") && trimmed.contains("name=") {
                    if let Some((_, val)) = trimmed.split_once('=') {
                        let name = val.trim();
                        if !name.is_empty() && !screens.contains(&name.to_string()) {
                            screens.push(name.to_string());
                        }
                    }
                } else if trimmed == "groupClientChecked=true" {
                    self.mode = "client".to_string();
                } else if trimmed == "groupServerChecked=true" {
                    self.mode = "server".to_string();
                }
            }

            if screens.len() >= 2 {
                let mut map1 = HashMap::new();
                map1.insert("right".to_string(), screens[1].clone());
                self.links.insert(screens[0].clone(), map1);

                let mut map2 = HashMap::new();
                map2.insert("left".to_string(), screens[0].clone());
                self.links.insert(screens[1].clone(), map2);
            }
            return true;
        }
        false
    }
}

fn dirs_home() -> Option<PathBuf> {
    std::env::var_os("HOME").map(PathBuf::from)
}
