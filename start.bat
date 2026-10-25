@echo off
echo ========================================================
echo  ⚡ Menjalankan Synergy Next (Rust Edition) - Windows
echo ========================================================

if exist "dist\synergy-next-windows-x86_64.exe" (
    set BINARY=dist\synergy-next-windows-x86_64.exe
) else if exist "target\release\synergy-next.exe" (
    set BINARY=target\release\synergy-next.exe
) else (
    echo Mengompilasi binary rilis...
    cargo build --release
    set BINARY=target\release\synergy-next.exe
)

start http://localhost:24801
%BINARY% %*
pause
