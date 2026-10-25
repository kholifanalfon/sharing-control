# ⚡ Synergy Next (Rust Edition) - Multiplatform KM Sharing

Implementasi modern, ultra-low-latency, dan kompatibel penuh dengan protokol **Synergy 1.6 & Barrier** menggunakan **Rust**.

Dirancang khusus untuk berbagi mouse, keyboard, dan clipboard antar komputer (**macOS**, **Linux**, dan **Windows**) dengan performa mulus (tanpa lag / stutter) dan biner mandiri (*standalone executable*).

---

## 🌟 Keunggulan Versi Rust

1. **Ultra-Low Latency (~125Hz - 1000Hz Motion Tracking)**:
   - Menggunakan asynchronous I/O berkecepatan tinggi via `tokio`.
   - Mengakses langsung driver native OS:
     - **Linux**: Pure Rust X11 via `x11rb` + `xtest` (tidak butuh libxcb/libX11 header).
     - **macOS**: Native Apple Quartz `CoreGraphics` (kompatibel penuh dengan Intel & Apple Silicon M1/M2/M3/M4 Retina Display).
     - **Windows**: Win32 `SendInput` dengan dukungan DPI Awareness V2.
2. **Single Standalone Executable**:
   - Menghasilkan biner mandiri berukuran ~2 MB tanpa dependensi eksternal:
     - Linux: `synergy-next`
     - macOS: `synergy-next`
     - Windows: `synergy-next.exe`
3. **Kompatibilitas Penuh Protokol Barrier & Synergy 1.6**:
   - Dapat langsung berkomunikasi dengan Barrier atau Synergy yang sudah ada di MacBook Anda (`Kholifans-MacBook`) tanpa perlu instalasi ulang.
4. **Auto-Import Konfigurasi Lama**:
   - Otomatis mendeteksi dan mengimpor konfigurasi dari `~/.config/Debauchee/Barrier.conf`.

---

## 📂 Struktur Proyek Rust

```
/home/kholifan/html/synergy/
├── Cargo.toml                         # Dependensi Rust multiplatform
├── build_cross.sh                     # Script kompilasi rilis
├── dist/
│   └── synergy-next-linux-x86_64      # Executable rilis Linux
├── src/
│   ├── main.rs                        # Entrypoint CLI
│   ├── config.rs                      # Konfigurasi & auto-import Barrier.conf
│   ├── protocol/
│   │   ├── types.rs                   # Kode & pesan protokol Barrier 1.6
│   │   ├── packet.rs                  # Binary framing (>I) & serializer
│   │   └── mod.rs
│   ├── platform/
│   │   ├── linux.rs                   # Pure Rust Linux X11 screen driver
│   │   ├── macos.rs                   # macOS CoreGraphics Quartz driver
│   │   ├── windows.rs                 # Windows SendInput driver
│   │   └── mod.rs                     # PlatformScreen trait abstraction
│   ├── server.rs                      # Tokio async server (edge detection)
│   └── client.rs                      # Tokio async client (input injection)
└── .github/workflows/
    └── release.yml                    # CI/CD otomatis kompilasi macOS, Win, Linux
```

---

## 🚀 Cara Menjalankan

### 1. Menjalankan di Linux (PC Ini)
Biner rilis sudah selesai dikompilasi dan siap digunakan:

- **Sebagai Server (Host mouse & keyboard)**:
  ```bash
  ./dist/synergy-next-linux-x86_64 --mode server
  ```
- **Sebagai Client (Menerima input)**:
  ```bash
  ./dist/synergy-next-linux-x86_64 --mode client --server 192.168.12.61
  ```

### 2. Menjalankan di macOS (`Kholifans-MacBook`)
- Salin folder atau biner `synergy-next` ke Mac.
- Jika mengompilasi dari source di Mac:
  ```bash
  cargo build --release
  ./target/release/synergy-next --mode client --server 192.168.12.61
  ```
- *Catatan Mac:* Pastikan aplikasi/Terminal diberi izin di **System Settings > Privacy & Security > Accessibility**.

### 3. Menjalankan di Windows (10 / 11)
- Salin `synergy-next.exe` ke PC Windows.
- Jika mengompilasi dari source di Windows:
  ```cmd
  cargo build --release
  target\release\synergy-next.exe --mode client --server 192.168.12.61
  ```

---

## 📦 Menghasilkan Executable untuk Semua Platform

Proyek ini sudah dilengkapi dengan **GitHub Actions Workflow** di [`.github/workflows/release.yml`](file:///.github/workflows/release.yml).
Setiap kali Anda membuat tag rilis Git (misalnya `git tag v0.1.0 && git push origin v0.1.0`), GitHub Actions akan otomatis mengompilasi dan menyediakan unduhan langsung untuk:
1. `synergy-next-linux-x86_64.tar.gz` (Linux PC)
2. `synergy-next-macos-arm64.tar.gz` (MacBook M1/M2/M3/M4)
3. `synergy-next-macos-intel.tar.gz` (MacBook Intel)
4. `synergy-next-windows-x86_64.zip` (`synergy-next.exe` Windows 10/11)
