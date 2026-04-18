#!/usr/bin/env python3
"""Servidor HTTP simple para servir la interfaz visual de Miniverse."""

from __future__ import annotations

import http.server
import os
import socketserver
import sys
from pathlib import Path

PORT = int(os.getenv("MINIVERSE_UI_PORT", "7777"))
BASE_DIR = Path(__file__).resolve().parent.parent / "public"


class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def end_headers(self):
        """Agregar headers para cache y CORS."""
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    if not BASE_DIR.exists():
        print(f"[ui-server][error] no existe el directorio public: {BASE_DIR}")
        sys.exit(1)

    try:
        with ReusableTCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
            print(f"[ui-server] Sirviendo {BASE_DIR} en http://localhost:{PORT}")
            print(f"[ui-server] Abre http://localhost:{PORT} en tu navegador")
            print("[ui-server] Presiona Ctrl+C para detener")
            httpd.serve_forever()
    except OSError as exc:
        print(f"[ui-server][error] no se pudo abrir puerto {PORT}: {exc}")
        sys.exit(2)
    except KeyboardInterrupt:
        print("\n[ui-server] Detenido")
