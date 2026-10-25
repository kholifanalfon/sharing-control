"""
TLS / SSL Socket Security Manager for Synergy/Barrier.
Supports modern OpenSSL 3 / TLS 1.3 encryption and certificate generation.
"""

import os
import ssl
import socket
import subprocess
from pathlib import Path
from typing import Optional, Tuple


def get_default_cert_paths() -> Tuple[Path, Path]:
    cert_dir = Path.home() / ".config" / "synergy-next" / "ssl"
    cert_dir.mkdir(parents=True, exist_ok=True)
    cert_path = cert_dir / "Synergy.pem"
    key_path = cert_dir / "Synergy.key"
    return cert_path, key_path


def generate_self_signed_cert(cert_path: Path, key_path: Path, days: int = 365) -> bool:
    """Generate self-signed certificate using system openssl CLI."""
    if cert_path.exists() and key_path.exists():
        return True

    cmd = [
        "openssl",
        "req",
        "-x509",
        "-nodes",
        "-days",
        str(days),
        "-subj",
        "/CN=Synergy-Next/O=SynergyNext/C=US",
        "-newkey",
        "rsa:2048",
        "-keyout",
        str(key_path),
        "-out",
        str(cert_path),
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except Exception as e:
        print(f"[Crypto] Certificate generation failed: {e}")
        return False


def create_server_ssl_context(cert_path: Optional[Path] = None, key_path: Optional[Path] = None) -> ssl.SSLContext:
    if cert_path is None or key_path is None:
        c, k = get_default_cert_paths()
        cert_path = cert_path or c
        key_path = key_path or k

    if not cert_path.exists() or not key_path.exists():
        generate_self_signed_cert(cert_path, key_path)

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def create_client_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context
