from __future__ import annotations

from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urlparse
import webbrowser


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
        asset_dir: Path = ASSET_DIR,
        **kwargs,
    ) -> None:
        self.corpus_path = corpus_path
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
        asset_name = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        asset_path = (self.asset_dir / asset_name).resolve()
        if not asset_path.is_file() or self.asset_dir.resolve() not in asset_path.parents:
            self.send_error(HTTPStatus.NOT_FOUND, "Viewer asset not found.")
            return
        self._send_file(asset_path, ASSET_TYPES.get(asset_path.suffix, "application/octet-stream"))

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


def serve_viewer(
    corpus_path: Path,
    *,
    host: str,
    port: int,
    open_browser: bool,
    echo: Callable[[str], None] = print,
) -> None:
    corpus_path = corpus_path.resolve()
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus JSON does not exist: {corpus_path}")
    handler = partial(CorpusViewerHandler, corpus_path=corpus_path)
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
