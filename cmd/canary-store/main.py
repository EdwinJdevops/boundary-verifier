#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, re, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HOST=os.getenv("CANARY_STORE_HOST","0.0.0.0"); PORT=int(os.getenv("CANARY_STORE_PORT","8080"))
MAX_BODY=4096; RUN_ID=re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_store={}; _lock=threading.Lock()

class Handler(BaseHTTPRequestHandler):
    server_version="boundary-verifier-canary-store/0.1"
    def _json(self,status,payload):
        body=json.dumps(payload,separators=(",",":"),sort_keys=True).encode()
        self.send_response(status); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store")
        self.end_headers(); self.wfile.write(body)
    def _run_id(self):
        parts=urlparse(self.path).path.strip("/").split("/")
        return parts[1] if len(parts)==2 and parts[0]=="v1" and RUN_ID.fullmatch(parts[1]) else None
    def do_PUT(self):
        run_id=self._run_id()
        if run_id is None: return self._json(404,{"error":"not_found"})
        try: length=int(self.headers.get("Content-Length","0"))
        except ValueError: return self._json(400,{"error":"invalid_content_length"})
        if length<1 or length>MAX_BODY: return self._json(413,{"error":"invalid_body_size"})
        try: value=self.rfile.read(length).decode("utf-8",errors="strict")
        except UnicodeDecodeError: return self._json(400,{"error":"body_must_be_utf8"})
        with _lock: _store[run_id]=value
        self._json(201,{"run_id":run_id,"sha256":hashlib.sha256(value.encode()).hexdigest()})
    def do_GET(self):
        if self.path=="/healthz": return self._json(200,{"status":"ok"})
        run_id=self._run_id()
        if run_id is None: return self._json(404,{"error":"not_found"})
        with _lock: value=_store.get(run_id)
        if value is None: return self._json(404,{"error":"canary_not_found","run_id":run_id})
        self._json(200,{"run_id":run_id,"value":value})
    def log_message(self,fmt,*args):
        print(json.dumps({"remote":self.client_address[0],"message":fmt%args}),flush=True)

if __name__=="__main__": ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
