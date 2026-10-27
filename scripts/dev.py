#!/usr/bin/env python3
"""Собирает сайт и запускает локальное превью. Пересборка при обновлении страницы."""
from __future__ import annotations
import argparse
import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from build import ROOT, OUT
import build as builder
import importlib

_lock=threading.Lock()
_fingerprint=()

def fingerprint():
    paths=[]
    for folder in ('content','templates','assets'):
        paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file())
    paths.append(ROOT/'scripts/build.py')
    return tuple((str(p.relative_to(ROOT)),p.stat().st_mtime_ns,p.stat().st_size) for p in sorted(paths))

def rebuild_if_changed():
    global _fingerprint
    with _lock:
        now=fingerprint()
        if now!=_fingerprint:
            pages=importlib.reload(builder).build()
            _fingerprint=now
            print(f'Rebuilt {len(pages)} pages.',flush=True)

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path=urlparse(self.path).path
        if path.endswith('/') or path.endswith('.html'):
            try:
                rebuild_if_changed()
            except Exception as exc:
                self.send_error(500,f'Build failed. Check terminal: {type(exc).__name__}')
                print(f'Build failed: {exc}',flush=True)
                return
        super().do_GET()

    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()

    def list_directory(self,path):
        self.send_error(404,'Not found')
        return None

    def send_error(self,code,message=None,explain=None):
        custom=OUT/'404.html'
        if code==404 and custom.is_file():
            body=custom.read_bytes()
            self.send_response(404)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(body)))
            self.end_headers()
            if self.command!='HEAD':self.wfile.write(body)
            return
        super().send_error(code,message,explain)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--host',default='0.0.0.0')
    args=parser.parse_args()
    if not 1<=args.port<=65535:parser.error('Port must be in 1..65535')
    rebuild_if_changed()
    handler=functools.partial(Handler,directory=str(OUT))
    try:
        server=ThreadingHTTPServer((args.host,args.port),handler)
    except OSError as exc:
        parser.exit(1,f'Cannot start preview: {exc}. Try --port 8001.\n')
    print(f'Preview: http://localhost:{args.port}\nEN: /   RU: /ru/\nEdit source files, then refresh the browser. Ctrl+C to stop.',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nPreview stopped.')
    finally:
        server.server_close()
