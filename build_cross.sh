#!/usr/bin/env bash
# Synergy Next Multiplatform Build Script

set -e

# Load Cargo environment if not already in PATH
if ! command -v cargo >/dev/null 2>&1; then
    if [ -f "$HOME/.cargo/env" ]; then
        source "$HOME/.cargo/env"
    fi
fi

echo "========================================================"
echo " ⚡ Building Synergy Next Release Executables (Rust)"
echo "========================================================"

# 1. Build Linux native binary
echo "[1/3] Building native Linux binary (x86_64)..."
cargo build --release
mkdir -p dist
cp target/release/synergy-next dist/synergy-next-linux-x86_64
echo " -> Created: dist/synergy-next-linux-x86_64"

# 2. Check for cross / cargo-zigbuild
echo ""
echo "[2/3] Checking cross-compilation tools..."
if command -v cross >/dev/null 2>&1; then
    echo " -> 'cross' detected. Building for Windows (x86_64-pc-windows-gnu)..."
    cross build --release --target x86_64-pc-windows-gnu || true
    if [ -f target/x86_64-pc-windows-gnu/release/synergy-next.exe ]; then
        cp target/x86_64-pc-windows-gnu/release/synergy-next.exe dist/synergy-next-windows-x86_64.exe
        echo " -> Created: dist/synergy-next-windows-x86_64.exe"
    fi
else
    echo " -> Tip: To cross-compile Windows .exe directly on Linux, run: cargo install cross"
fi

echo ""
echo "[3/3] Build summary:"
ls -lh dist/
echo "Done! Linux binary ready in target/release/synergy-next and dist/"
