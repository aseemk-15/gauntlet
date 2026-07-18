"""Mission-log server: static files from repo root, /api/latest for the newest run,
POST /api/attack to run the gauntlet on a pasted discharge summary (real run, spawned
as a subprocess — the mission log follows it live)."""
import json
import os
import subprocess
import sys
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("GAUNTLET_UI_PORT", "3010"))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def do_GET(self):
        if self.path == "/api/latest":
            runs = sorted((ROOT / "runs").glob("*/")) if (ROOT / "runs").exists() else []
            body = json.dumps({"run": f"runs/{runs[-1].name}" if runs else None}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/":
            self.path = "/ui/index.html"
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/attack":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length))
            encounter = str(body["encounter"])
            summary = str(body.get("summary", "")).strip()
        except (json.JSONDecodeError, KeyError):
            self.send_error(400, "expected JSON {encounter, summary}")
            return
        stamp = time.strftime("%Y%m%d-%H%M%S")
        cmd = [str(ROOT / "gauntlet-cli"), "run", "--encounter", encounter]
        if summary:
            sub = ROOT / "runs" / f"_submitted-{stamp}.md"
            sub.parent.mkdir(exist_ok=True)
            sub.write_text(summary)
            cmd += ["--summary", str(sub)]
        log = open(ROOT / "runs" / f"_submitted-{stamp}.log", "w")
        subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        payload = json.dumps({"ok": True, "launched": cmd[2:]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"mission log: http://localhost:{PORT}/")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
