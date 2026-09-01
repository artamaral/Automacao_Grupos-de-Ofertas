from __future__ import annotations

import hmac
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

WEBHOOK_PATH = "/webhook/instagram-interactions"
MAX_POST_BYTES = 1_048_576
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def verify_challenge(query: dict[str, list[str]], verify_token: str) -> str | None:
    mode = query.get("hub.mode", [""])[0]
    provided_token = query.get("hub.verify_token", [""])[0]
    challenge = query.get("hub.challenge", [""])[0]
    if mode != "subscribe" or not challenge:
        return None
    if not hmac.compare_digest(provided_token, verify_token):
        return None
    return challenge


class InstagramWebhookVerifier(BaseHTTPRequestHandler):
    server_version = "InstagramWebhookVerifier/1.0"

    @property
    def verify_token(self) -> str:
        return self.server.verify_token  # type: ignore[attr-defined]

    @property
    def n8n_target(self) -> str:
        return self.server.n8n_target  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlsplit(self.path)
        if parsed.path != WEBHOOK_PATH:
            self.send_error(404)
            return
        query = parse_qs(parsed.query, keep_blank_values=True)
        challenge = verify_challenge(query, self.verify_token)
        if challenge is None:
            self.send_error(403)
            return
        body = challenge.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if urlsplit(self.path).path != WEBHOOK_PATH:
            self.send_error(404)
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length < 0 or content_length > MAX_POST_BYTES:
            self.send_error(413)
            return
        body = self.rfile.read(content_length)
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in HOP_BY_HOP_HEADERS | {"host", "content-length"}
        }
        headers["Content-Length"] = str(len(body))
        request = Request(self.n8n_target, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=15) as response:  # noqa: S310
                response_body = response.read()
                self._forward_response(response.status, response.headers.items(), response_body)
        except HTTPError as error:
            self._forward_response(error.code, error.headers.items(), error.read())

    def _forward_response(self, status: int, headers: object, body: bytes) -> None:
        self.send_response(status)
        for key, value in headers:  # type: ignore[union-attr]
            if key.lower() not in HOP_BY_HOP_HEADERS | {"content-length"}:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def main() -> None:
    verify_token = os.environ.get("INSTAGRAM_WEBHOOK_VERIFY_TOKEN", "").strip()
    token_is_hex = all(char in "0123456789abcdefABCDEF" for char in verify_token)
    if len(verify_token) != 64 or not token_is_hex:
        raise SystemExit("INSTAGRAM_WEBHOOK_VERIFY_TOKEN is missing or invalid")
    host = os.environ.get("INSTAGRAM_WEBHOOK_BIND_HOST", "0.0.0.0")
    port = int(os.environ.get("INSTAGRAM_WEBHOOK_BIND_PORT", "8080"))
    target = os.environ.get("N8N_WEBHOOK_TARGET", "http://n8n:5678" + WEBHOOK_PATH)
    server = ThreadingHTTPServer((host, port), InstagramWebhookVerifier)
    server.verify_token = verify_token  # type: ignore[attr-defined]
    server.n8n_target = target  # type: ignore[attr-defined]
    server.serve_forever()


if __name__ == "__main__":
    main()
