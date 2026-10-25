#!/usr/bin/env bash
# Synergy Next Launcher (Linux / macOS)

set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "⚡ Menjalankan Synergy Next (Rust Edition)..."

if [ -f "$DIR/dist/synergy-next-linux-x86_64" ]; then
    BINARY="$DIR/dist/synergy-next-linux-x86_64"
elif [ -f "$DIR/target/release/synergy-next" ]; then
    BINARY="$DIR/target/release/synergy-next"
else
    echo "Mengompilasi binary rilis..."
    cargo build --release
    BINARY="$DIR/target/release/synergy-next"
fi

echo "Membuka antarmuka Studio di browser Anda (http://localhost:24801)..."
# Automatically opens default web browser
if command -v xdg-open >/dev/null 2>&1; then
    (sleep 1.2 && xdg-open http://localhost:24801) &
elif command -v open >/dev/null 2>&1; then
    (sleep 1.2 && open http://localhost:24801) &
fi

exec "$BINARY" "$@"
