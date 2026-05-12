from __future__ import annotations

import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Protocol
from urllib.parse import quote


class PdfConverter(Protocol):
    def convert(self, html_path: Path, pdf_path: Path, root_dir: Path) -> None:
        pass


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: Path, **kwargs):
        super().__init__(*args, directory=str(directory), **kwargs)

    def log_message(self, format, *args):
        pass


class PlaywrightPdfConverter:
    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        extra_wait_ms: int = 1500,
        timeout_ms: int = 60000,
    ) -> None:
        self.host = host
        self.extra_wait_ms = extra_wait_ms
        self.timeout_ms = timeout_ms

    def convert(self, html_path: Path, pdf_path: Path, root_dir: Path) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "HTML to PDF conversion requires Playwright. Run `uv sync` and "
                "`uv run playwright install chromium` before syncing html articles."
            ) from exc

        root = root_dir.resolve()
        html = html_path.resolve()
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        server = self._start_http_server(root)
        port = server.server_address[1]
        try:
            rel_path = html.relative_to(root).as_posix()
            url = f"http://{self.host}:{port}/{quote(rel_path, safe='/')}"
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    page.goto(url, wait_until="load", timeout=self.timeout_ms)
                    page.wait_for_timeout(self.extra_wait_ms)
                    page.pdf(
                        path=str(pdf_path),
                        format="A4",
                        print_background=True,
                        margin={
                            "top": "10mm",
                            "bottom": "10mm",
                            "left": "10mm",
                            "right": "10mm",
                        },
                    )
                finally:
                    browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def _start_http_server(self, root_dir: Path) -> ThreadingHTTPServer:
        server = ThreadingHTTPServer(
            (self.host, 0),
            lambda *args, **kwargs: QuietHandler(*args, directory=root_dir, **kwargs),
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server
