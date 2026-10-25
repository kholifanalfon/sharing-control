# ⚡ Synergy Next (Rust Edition) - Multiplatform KM Sharing

Implementasi modern, ultra-low-latency, dan kompatibel penuh dengan protokol **Synergy 1.6 & Barrier** menggunakan **Rust**.

Dirancang khusus untuk berbagi mouse, keyboard, dan clipboard antar komputer (**macOS**, **Linux**, dan **Windows**) dengan performa mulus (tanpa lag / stutter) dan biner mandiri (*standalone executable*) yang dilengkapi antarmuka desktop **GUI 1:1 identik dengan Barrier & Synergy**.

---

## 🌟 Keunggulan Versi Rust

1. **Langsung Membuka GUI 1:1 Barrier / Synergy**:
   - Saat file executable dibuka atau di-*double click*, langsung memunculkan jendela aplikasi desktop Barrier 1:1 lengkap dengan:
     - Menu Bar klasik (*Barrier, Edit, Window, Help*)
     - Pemilih mode interaktif (*Server* vs *Client*)
     - Tombol **Configure Server...** dengan **Grid 5x3** interaktif (*drag & drop* monitor)
     - Status & log aktivitas *real-time*
2. **Ultra-Low Latency (~125Hz - 1000Hz Motion Tracking)**:
   - Menggunakan asynchronous I/O berkecepatan tinggi via `tokio`.
   - Mengakses langsung driver native OS:
     - **Linux**: Pure Rust X11 via `x11rb` + `xtest` (tidak butuh libxcb/libX11 C header).
     - **macOS**: Native Apple Quartz `CoreGraphics` (kompatibel penuh dengan Intel & Apple Silicon M1/M2/M3/M4 Retina Display).
     - **Windows**: Win32 `SendInput` dengan dukungan DPI Awareness V2.
3. **Single Standalone Executable**:
   - Seluruh kode, resource GUI, dan engine input di-*bundle* langsung ke dalam 1 file biner mandiri (~2.8 MB) tanpa perlu instalasi runtime terpisah:
     - Linux: `synergy-next`
     - macOS: `synergy-next`
     - Windows: `synergy-next.exe`
4. **Kompatibilitas Penuh Protokol Barrier & Synergy 1.6**:
   - Dapat langsung berkomunikasi dengan Barrier atau Synergy yang sudah ada di MacBook Anda (`Kholifans-MacBook`) tanpa perlu instalasi ulang.
5. **Auto-Import Konfigurasi Lama**:
   - Otomatis mendeteksi dan mengimpor konfigurasi dari `~/.config/Debauchee/Barrier.conf`.

---

## 🛠️ Panduan Build (Kompilasi) di Linux, macOS, dan Windows

Pastikan compiler **Rust & Cargo** sudah terpasang di sistem Anda. Jika belum, pasang melalui [rustup.rs](https://rustup.rs):
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

---

### 🐧 1. Cara Build di Linux (Ubuntu, Debian, Zorin, Fedora, Arch)

Driver Linux dibuat menggunakan pure Rust `x11rb`, sehingga **tidak membutuhkan C header libxcb atau libX11**.

#### Langkah-langkah:
1. Pasang dependensi dasar (toolchain build & clipboard utility):
   ```bash
   # Ubuntu / Debian / Zorin OS
   sudo apt update
   sudo apt install -y build-essential xclip
   
   # Fedora
   sudo dnf install -y gcc xclip
   
   # Arch Linux
   sudo pacman -S --needed base-devel xclip
   ```

2. Buka folder proyek dan kompilasi rilis:
   ```bash
   cd /path/to/synergy
   cargo build --release
   ```

3. File executable hasil kompilasi akan berada di:
   ```bash
   target/release/synergy-next
   ```
   *(Atau jalankan `./build_cross.sh` untuk otomatis meng-copy ke `dist/synergy-next-linux-x86_64`)*.

---

### 🍏 2. Cara Build di macOS (Apple Silicon M1/M2/M3/M4 & Intel)

Driver macOS menggunakan native framework Apple `CoreGraphics` untuk mengontrol kursor dan injeksi keyboard secara presisi pada layar Retina.

#### Langkah-langkah:
1. Pastikan **Xcode Command Line Tools** sudah terpasang:
   ```bash
   xcode-select --install
   ```

2. Kompilasi untuk arsitektur Mac Anda saat ini:
   ```bash
   cd /path/to/synergy
   cargo build --release
   ```
   File binary biner rilis akan berada di: `target/release/synergy-next`.

3. *(Opsional)* **Membuat Universal Binary (Mendukung Apple Silicon + Intel sekaligus)**:
   ```bash
   # Tambahkan target arsitektur
   rustup target add aarch64-apple-darwin
   rustup target add x86_64-apple-darwin

   # Kompilasi kedua arsitektur
   cargo build --release --target aarch64-apple-darwin
   cargo build --release --target x86_64-apple-darwin

   # Gabungkan menjadi Universal Binary menggunakan lipo
   mkdir -p dist
   lipo -create -output dist/synergy-next-macos-universal \
     target/aarch64-apple-darwin/release/synergy-next \
     target/x86_64-apple-darwin/release/synergy-next
   ```

4. **Izin Aksesibilitas (Penting di macOS)**:
   Agar macOS mengizinkan aplikasi menerima atau mengendalikan mouse/keyboard secara global, buka:
   👉 **System Settings** > **Privacy & Security** > **Accessibility** > Tambahkan aplikasi atau Terminal tempat Anda menjalankan biner.

---

### 🪟 3. Cara Build di Windows (Windows 10 / 11)

Driver Windows menggunakan Win32 `SendInput` dengan dukungan DPI Awareness V2 untuk pergerakan kursor yang mulus di multi-monitor dengan scaling resolusi berbeda.

#### Langkah-langkah:
1. Unduh dan jalankan installer Rust dari [https://win.rustup.rs](https://win.rustup.rs) (pilih opsi default dengan MSVC / Visual Studio C++ Build Tools).
2. Buka **Command Prompt (cmd)** atau **PowerShell** dan arahkan ke folder proyek:
   ```cmd
   cd C:\path\to\synergy
   cargo build --release
   ```
3. File executable rilis biner akan berada di:
   ```cmd
   target\release\synergy-next.exe
   ```
   Cukup klik dua kali (double click) file `synergy-next.exe` untuk langsung membuka GUI Barrier 1:1.

---

### 🌐 4. Kompilasi Otomatis via GitHub Actions (CI/CD)

Jika Anda tidak ingin mengompilasi manual di setiap sistem operasi, proyek ini telah dilengkapi dengan workflow CI/CD di [`.github/workflows/release.yml`](.github/workflows/release.yml).

Setiap kali Anda membuat tag rilis Git:
```bash
git tag v0.1.0
git push origin v0.1.0
```
GitHub Actions akan otomatis mengompilasi file executable secara native di runner Linux, macOS, dan Windows, serta menghasilkan file unduhan siap pakai (*Release Assets*):
- 🐧 `synergy-next-linux-x86_64.tar.gz`
- 🍏 `synergy-next-macos-arm64.tar.gz` (Apple Silicon M1/M2/M3/M4)
- 🍏 `synergy-next-macos-intel.tar.gz` (MacBook Intel)
- 🪟 `synergy-next-windows-x86_64.zip` (`synergy-next.exe`)

---

## 🚀 Cara Menjalankan

### Melalui GUI (Default)
Cukup jalankan file executable atau double-click:
- **Linux**: `./dist/synergy-next-linux-x86_64` (atau buka shortcut **"Barrier / Synergy Next"** di menu aplikasi)
- **macOS**: `./synergy-next`
- **Windows**: `synergy-next.exe`

Jendela desktop 1:1 Barrier akan langsung terbuka secara otomatis.

### Melalui Headless CLI (Tanpa GUI)
Jika ingin menjalankan pada server atau background service tanpa membuka jendela GUI, tambahkan opsi `--no-gui`:
```bash
# Sebagai Server
./synergy-next --mode server --no-gui

# Sebagai Client
./synergy-next --mode client --server 192.168.12.61 --no-gui
```
