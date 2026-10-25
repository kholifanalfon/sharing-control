#!/usr/bin/env bash
# Build Script for Multiplatform Synergy Next Releases

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

mkdir -p dist

echo "========================================================"
echo " ⚡ Building Synergy Next Release Executables (Rust)"
echo "========================================================"

# 1. Native Host Binary (Linux x86_64)
echo "[1/3] Building native Linux binary (x86_64)..."
$HOME/.cargo/bin/cargo build --release
rm -f dist/synergy-next-linux-x86_64
cp target/release/synergy-next dist/synergy-next-linux-x86_64
chmod +x dist/synergy-next-linux-x86_64
echo "✅ Linux: dist/synergy-next-linux-x86_64 ($(ls -lh dist/synergy-next-linux-x86_64 | awk '{print $5}'))"

echo ""
echo "========================================================"
echo "✨ Build completed successfully!"
echo "To build for macOS or Windows, push a git tag to trigger"
echo "GitHub Actions CI/CD or run cargo on the respective OS."
echo "========================================================"
