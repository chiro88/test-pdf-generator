"""picker_cmc web-editor server (stdlib http.server only).

Serves the static viewer + JSON/PNG API over a Workspace of detector runs:
- D23 read-only viewer (pages/objects/overlays)
- D24 bbox edit / save / save-as / ruler
- D25 reopen saved manifest + post-edit export
- D26 setup-YAML workflow (template / validate / run) + run launcher

Local single-user only. No auth, sessions, DB, or cloud.
"""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from setup.errors import SetupError
from setup.template import render_template
from . import editing, manifest_view, page_render, workflow
from .models import RUN_SCHEMA_VERSION, RunContext, Workspace, WebEditorError, load_run

_STATIC = Path(__file__).parent / "static"
_STATIC_TYPES = {".html": "text/html", ".js": "application/javascript", ".css": "text/css"}


def _run_summary(ctx: RunContext) -> dict:
    return {"ok": True, "schema_version": RUN_SCHEMA_VERSION, "run_id": ctx.run_dir.name,
            "source_pdf": ctx.source_pdf, "manifest": str(ctx.manifest_path),
            "page_count": ctx.page_count, "coordinate_unit": "pdf_pt", "coordinate_origin": "top-left"}


def make_handler(ws: Workspace):
    class Handler(BaseHTTPRequestHandler):
        server_version = "picker-web-editor/0"

        def log_message(self, *args):
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

        def _cur(self):
            if ws.current is None:
                self._send(409, {"ok": False, "error_code": "NO_RUN_OPEN", "error": "no run is open"})
                return None
            return ws.current

        def _body(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b""
            return json.loads(raw) if raw else {}

        def do_GET(self):
            parsed = urlparse(self.path)
            path, q = parsed.path, parse_qs(parsed.query)
            try:
                if path == "/":
                    return self._static("index.html")
                if path.startswith("/static/"):
                    return self._static(path[len("/static/"):])
                if path == "/api/health":
                    return self._send(200, {"ok": True, "status": "healthy", "has_run": ws.current is not None})
                if path == "/api/setup/template":
                    return self._send(200, render_template(), "text/plain; charset=utf-8")
                if path == "/api/runs":
                    return self._send(200, {"ok": True, "runs": ws.list_runs()})

                m = re.match(r"^/api/run/(.+)$", path)
                if m:
                    try:
                        return self._send(200, _run_summary(ws.open(unquote(m.group(1)))))
                    except WebEditorError as exc:
                        return self._send(404, exc.to_dict())

                if path == "/api/run":
                    ctx = self._cur()
                    return self._send(200, _run_summary(ctx)) if ctx else None
                if path == "/api/manifest":
                    ctx = self._cur(); return self._send(200, ctx.manifest) if ctx else None
                if path == "/api/pages":
                    ctx = self._cur(); return self._send(200, {"pages": [p.get("page") for p in ctx.pages]}) if ctx else None
                if path == "/api/edit-state":
                    ctx = self._cur(); return self._send(200, editing.edit_state(ctx)) if ctx else None

                m = re.match(r"^/api/page/(\d+)/png$", path)
                if m:
                    ctx = self._cur()
                    if not ctx:
                        return None
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
                    ctx = self._cur()
                    if not ctx:
                        return None
                    po = manifest_view.page_objects(ctx.manifest, int(m.group(1)))
                    return self._send(200, po) if po else self._send(404, {"ok": False, "error": "page not found"})

                m = re.match(r"^/api/page/(\d+)/overlays$", path)
                if m:
                    ctx = self._cur()
                    if not ctx:
                        return None
                    ov = manifest_view.overlays(ctx.manifest, int(m.group(1)))
                    return self._send(200, ov) if ov else self._send(404, {"ok": False, "error": "page not found"})

                m = re.match(r"^/api/object/(.+)$", path)
                if m:
                    ctx = self._cur()
                    if not ctx:
                        return None
                    oid = unquote(m.group(1))
                    found = manifest_view.find_object(ctx.manifest, oid)
                    if not found:
                        return self._send(404, {"ok": False, "error": "object not found"})
                    page, kind, obj = found
                    return self._send(200, {"object_id": oid, "page": page,
                                            "kind": kind[:-1] if kind.endswith("s") else kind, "object": obj})

                return self._send(404, {"ok": False, "error": "not found"})
            except Exception as exc:
                return self._send(500, {"ok": False, "error": str(exc)})

        def do_POST(self):
            path = urlparse(self.path).path
            try:
                body = self._body()
            except (ValueError, json.JSONDecodeError):
                return self._send(400, {"ok": False, "error_code": "BAD_JSON", "message": "invalid JSON body"})
            try:
                if path == "/api/setup/validate":
                    try:
                        from setup.validator import validate_setup
                        validate_setup(workflow.parse_setup(body))
                        return self._send(200, {"ok": True})
                    except SetupError as exc:
                        return self._send(400, exc.to_dict())
                if path == "/api/setup/run":
                    try:
                        run_dir = workflow.run_from_setup(workflow.parse_setup(body))
                    except SetupError as exc:
                        return self._send(400, exc.to_dict())
                    ctx = load_run(run_dir)
                    run_id = ws.register(ctx)
                    return self._send(200, {"ok": True, "run_id": run_id, "run_dir": str(run_dir),
                                            "page_count": ctx.page_count, "source_pdf": ctx.source_pdf})

                ctx = self._cur()
                if not ctx:
                    return None
                if path == "/api/edit/bbox":
                    return self._send(200, editing.edit_bbox(ctx, body.get("object_id"),
                                                             body.get("region"), body.get("bbox")))
                if path == "/api/save":
                    return self._send(200, editing.save(ctx))
                if path == "/api/save-as":
                    return self._send(200, editing.save_as(ctx, str(body.get("path", ""))))
                return self._send(404, {"ok": False, "error": "not found"})
            except editing.EditError as exc:
                return self._send(400, exc.to_dict())
            except Exception as exc:
                return self._send(500, {"ok": False, "error": str(exc)})

    return Handler


def _as_workspace(target) -> Workspace:
    if isinstance(target, Workspace):
        return target
    if isinstance(target, RunContext):
        ws = Workspace(runs_root=target.run_dir.parent)
        ws.register(target)
        return ws
    raise TypeError("make_server expects a Workspace or RunContext")


def make_server(target, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(_as_workspace(target)))


def serve(target, host: str = "127.0.0.1", port: int = 8765) -> None:
    srv = make_server(target, host, port)
    print(f"picker web editor on http://{host}:{srv.server_address[1]}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
