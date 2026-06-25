#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servidor local do Painel Tributario RS.

O `python -m http.server` padrao NAO atende requisicoes de faixa de bytes
(cabecalho HTTP "Range"). O motor de consulta do painel (DuckDB-WASM) le os
arquivos .parquet por faixas (so o rodape, depois os blocos necessarios); sem
suporte a Range, arquivos grandes falham com "No magic bytes found at end of
file". Este servidor adiciona suporte a Range (HTTP 206) e os cabecalhos certos.

Uso: python servidor.py [porta]   (porta padrao 8777)
"""
import os
import re
import sys
import socketserver
from http.server import SimpleHTTPRequestHandler

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8777


class RangeHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Anuncia suporte a Range e evita cache agressivo dos .parquet
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def do_GET(self):
        rng = self.headers.get("Range")
        if rng is None:
            return super().do_GET()

        m = re.match(r"bytes=(\d*)-(\d*)", rng.strip())
        if not m:
            return super().do_GET()

        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return super().do_GET()

        size = os.path.getsize(path)
        start_s, end_s = m.group(1), m.group(2)
        if start_s == "":
            # bytes=-N  -> ultimos N bytes
            length = int(end_s)
            start = max(0, size - length)
            end = size - 1
        else:
            start = int(start_s)
            end = int(end_s) if end_s else size - 1
        end = min(end, size - 1)
        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", "bytes */%d" % size)
            self.end_headers()
            return

        length = end - start + 1
        ctype = self.guess_type(path)
        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return
        self.send_response(206)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        self.send_header("Content-Length", str(length))
        self.end_headers()
        f.seek(start)
        remaining = length
        chunk = 64 * 1024
        while remaining > 0:
            data = f.read(min(chunk, remaining))
            if not data:
                break
            self.wfile.write(data)
            remaining -= len(data)
        f.close()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with Server(("", PORT), RangeHandler) as httpd:
        print("Servidor do painel rodando em http://localhost:%d/painel_rs.html" % PORT)
        print("(NAO feche esta janela enquanto usar o painel)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
