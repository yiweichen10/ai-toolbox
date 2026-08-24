#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地开发服务器：静态站点 + /api/* 反向代理到 AI 助手后端
用法：
  python scripts/dev_site_server.py [port] [api_port]
默认：http://127.0.0.1:8090  ->  /api/* 转发到 http://127.0.0.1:8123
"""

from __future__ import print_function

import io
import json
import os
import sys
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
try:
    from http.server import ThreadingMixIn
except ImportError:
    from socketserver import ThreadingMixIn


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
API_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8123
API_TARGET = 'http://127.0.0.1:%d' % API_PORT

MIME = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.xml': 'application/xml; charset=utf-8',
    '.txt': 'text/plain; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.webp': 'image/webp',
}


class Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _send_bytes(self, code, body, ctype):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _proxy(self):
        length = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(length) if length > 0 else None
        url = API_TARGET + self.path
        req = urllib.request.Request(
            url, data=body, method=self.command,
            headers={'Content-Type': 'application/json'},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=180)
            data = resp.read()
            ctype = resp.headers.get('Content-Type', 'application/json')
            self.send_response(resp.status)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass
        except urllib.error.HTTPError as e:
            data = e.read()
            self._send_bytes(e.code, data, 'application/json')
        except Exception:
            self._send_bytes(502, json.dumps({'error': 'backend unavailable'}).encode(), 'application/json')

    def do_GET(self):
        if self.path.startswith('/api/'):
            return self._proxy()
        self._serve_file()

    def do_POST(self):
        if self.path.startswith('/api/'):
            return self._proxy()
        self._send_bytes(405, b'not allowed', 'text/plain')

    def _serve_file(self):
        path = self.path.split('?')[0]
        if path == '/':
            path = '/index.html'
        rel = path.lstrip('/')
        if '..' in rel:
            return self._send_bytes(403, b'forbidden', 'text/plain')
        full = os.path.join(BASE_DIR, rel.replace('/', os.sep))
        if os.path.isdir(full):
            full = os.path.join(full, 'index.html')
        if not os.path.isfile(full):
            return self._send_bytes(404, b'not found', 'text/plain')
        ext = os.path.splitext(full)[1].lower()
        ctype = MIME.get(ext, 'application/octet-stream')
        with io.open(full, 'rb') as fh:
            data = fh.read()
        self._send_bytes(200, data, ctype)


def main():
    srv = Server(('127.0.0.1', PORT), Handler)
    print('Dev site: http://127.0.0.1:%d  (API -> %s)' % (PORT, API_TARGET))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.server_close()


if __name__ == '__main__':
    main()
