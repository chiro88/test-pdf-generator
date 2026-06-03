"""D23 read-only web-editor server (stdlib http.server only).

Serves the static viewer + a small read-only JSON/PNG API over a RunContext.
No bbox editing, no save, no ruler (those are D24).
"""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import manifest_view, page_render
from .models import RUN_SCHEMA_VERSION, RunContext

_STATIC = Path(__file__).parent / "static"
_STATIC_TYPES = {".html": "text/html", ".js": "application/javascript", ".css": "text/css"}


def make_handler(ctx: RunContext):
    class Handler(BaseHTTPRequestHandler):
        server_version = "picker-web-editor/0"

        def log_message(self, *args):  # quiet
            pass

        def _send(self, code: int, body, ctype: str = "application/json"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _static(self, rel: str):
            f = _STATIC / rel
            if not f.is_file():
                return self._send(404, {"ok": False, "error": "static not found"})
            return self._send(200, f.read_bytes(), _STATIC_TYPES.get(f.suffix, "application/octet-stream"))

        def do_GET(self):
            parsed = urlparse(self.path)
            path, q = parsed.path, parse_qs(parsed.query)
            try:
                if path == "/":
                    return self._static("index.html")
                if path.startswith("/static/"):
                    return self._static(path[len("/static/"):])
                if path == "/api/health":
                    return self._send(200, {"ok": True, "status": "healthy"})
                if path == "/api/run":
                    return self._send(200, {
                        "ok": True, "schema_version": RUN_SCHEMA_VERSION,
                        "source_pdf": ctx.source_pdf, "manifest": str(ctx.manifest_path),
                        "page_count": ctx.page_count,
                        "coordinate_unit": "pdf_pt", "coordinate_origin": "top-left",
                    })
                if path == "/api/manifest":
                    return self._send(200, ctx.manifest)
                if path == "/api/pages":
                    return self._send(200, {"pages": [p.get("page") for p in ctx.pages]})

                m = re.match(r"^/api/page/(\d+)/png$", path)
                if m:
                    page = int(m.group(1))
                    try:
                        scale = float(q.get("scale", ["1.5"])[0])
                    except ValueError:
                        scale = 1.5
                    try:
                        png = page_render.render_page_png(ctx.source_pdf, page, scale)
                    except Exception as exc:
                        return self._send(404, {"ok": False, "error": f"cannot render page {page}: {exc}"})
                    return self._send(200, png, "image/png")

                m = re.match(r"^/api/page/(\d+)/objects$", path)
                if m:
                    po = manifest_view.page_objects(ctx.manifest, int(m.group(1)))
                    return self._send(200, po) if po else self._send(404, {"ok": False, "error": "page not found"})

                m = re.match(r"^/api/page/(\d+)/overlays$", path)
                if m:
                    ov = manifest_view.overlays(ctx.manifest, int(m.group(1)))
                    return self._send(200, ov) if ov else self._send(404, {"ok": False, "error": "page not found"})

                m = re.match(r"^/api/object/(.+)$", path)
                if m:
                    oid = unquote(m.group(1))
                    found = manifest_view.find_object(ctx.manifest, oid)
                    if not found:
                        return self._send(404, {"ok": False, "error": "object not found"})
                    page, kind, obj = found
                    return self._send(200, {"object_id": oid, "page": page,
                                            "kind": kind[:-1] if kind.endswith("s") else kind, "object": obj})

                return self._send(404, {"ok": False, "error": "not found"})
            except Exception as exc:  # never crash the server thread on a bad request
                return self._send(500, {"ok": False, "error": str(exc)})

    return Handler


def make_server(ctx: RunContext, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(ctx))


def serve(ctx: RunContext, host: str = "127.0.0.1", port: int = 8765) -> None:
    srv = make_server(ctx, host, port)
    actual = srv.server_address[1]
    print(f"picker web editor (read-only) on http://{host}:{actual}  run-dir={ctx.run_dir}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
