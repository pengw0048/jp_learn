from __future__ import annotations

import json
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urlparse
import webbrowser

from .env import load_dotenv
from .viewer_jobs import ViewerJobRunner, explain_reader_usage, maintenance_status, save_viewer_config


ASSET_DIR = Path(__file__).with_name("viewer_assets")
ASSET_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}


class CorpusViewerHandler(SimpleHTTPRequestHandler):
    def __init__(
        self,
        *args,
        corpus_path: Path,
        job_runner: ViewerJobRunner | None = None,
        asset_dir: Path = ASSET_DIR,
        **kwargs,
    ) -> None:
        self.corpus_path = corpus_path
        self.job_runner = job_runner
        self.asset_dir = asset_dir
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        request_path = unquote(urlparse(self.path).path)
        if request_path == "/corpus.json":
            self._send_file(self.corpus_path, "application/json; charset=utf-8")
            return
        if request_path == "/healthz":
            self._send_bytes(b"ok\n", "text/plain; charset=utf-8")
            return
        if request_path == "/api/maintenance":
            self._send_json(maintenance_status(self.job_runner))
            return
        if request_path == "/api/jobs/current":
            self._send_json({"job": self.job_runner.current_job() if self.job_runner else None})
            return
        asset_name = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        asset_path = (self.asset_dir / asset_name).resolve()
        if not asset_path.is_file() or self.asset_dir.resolve() not in asset_path.parents:
            self.send_error(HTTPStatus.NOT_FOUND, "Viewer asset not found.")
            return
        self._send_file(asset_path, ASSET_TYPES.get(asset_path.suffix, "application/octet-stream"))

    def do_POST(self) -> None:
        request_path = unquote(urlparse(self.path).path)
        if request_path not in {"/api/jobs/maintenance", "/api/config", "/api/explain"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Viewer API endpoint not found.")
            return
        if self.job_runner is None:
            self._send_json({"error": "Maintenance API is disabled."}, status=HTTPStatus.FORBIDDEN)
            return
        try:
            payload = self._read_json()
            if request_path == "/api/config":
                config = save_viewer_config(payload)
                self._send_json({"config": config})
                return
            if request_path == "/api/explain":
                self._send_json(explain_reader_usage(payload))
                return
            job = self.job_runner.start_maintenance(payload)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"job": job}, status=HTTPStatus.ACCEPTED)

    def _send_file(self, path: Path, content_type: str) -> None:
        try:
            content = path.read_bytes()
        except FileNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND, f"File not found: {path}")
            return
        self._send_bytes(content, content_type)

    def _send_bytes(self, content: bytes, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        content = self.rfile.read(length)
        payload = json.loads(content.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON request body must be an object.")
        return payload

    def _send_json(self, payload: dict, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)


def serve_viewer(
    corpus_path: Path,
    *,
    host: str,
    port: int,
    open_browser: bool,
    echo: Callable[[str], None] = print,
) -> None:
    load_dotenv()
    corpus_path = corpus_path.resolve()
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus JSON does not exist: {corpus_path}")
    job_runner = ViewerJobRunner(corpus_path=corpus_path) if _is_loopback_host(host) else None
    handler = partial(CorpusViewerHandler, corpus_path=corpus_path, job_runner=job_runner)
    server = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{server.server_port}/"
    echo(f"Serving corpus viewer: {url}")
    echo(f"Corpus JSON: {corpus_path}")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        echo("Stopped corpus viewer.")
    finally:
        server.server_close()


def _is_loopback_host(host: str) -> bool:
    return host in {"127.0.0.1", "localhost", "::1"}
