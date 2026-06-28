from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from ofertas_bot.cloud_runner import (
    CloudRunnerError,
    build_catalog_sync_plan_window,
    confirm_delivery,
    confirm_window_deliveries,
    health_payload,
    load_dispatch_window,
    run_finalize_window,
    run_prepare_window,
    run_window,
    upload_catalog_sync,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HTTP runner cloud para o fluxo de ofertas")
    parser.add_argument("--host", default="0.0.0.0", help="Host de bind do servidor HTTP")
    parser.add_argument("--port", type=int, default=8080, help="Porta do servidor HTTP")
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), build_handler())
    print(f"INFO | Cloud runner ouvindo em http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("INFO | Cloud runner interrompido.")
    finally:
        server.server_close()
    return 0


def build_handler() -> type[BaseHTTPRequestHandler]:
    routes: dict[tuple[str, str], Callable[[dict[str, Any]], dict[str, Any]]] = {
        ("GET", "/health"): lambda payload: health_payload(),
        ("POST", "/catalog-sync-plan"): lambda payload: build_catalog_sync_plan_window(**payload),
        ("POST", "/catalog-sync-upload"): lambda payload: upload_catalog_sync(**payload),
        ("POST", "/prepare-window"): lambda payload: run_prepare_window(**payload),
        ("POST", "/finalize-window"): lambda payload: run_finalize_window(**payload),
        ("POST", "/dispatch-window"): lambda payload: load_dispatch_window(**payload),
        ("POST", "/run-window"): lambda payload: run_window(**payload),
        ("POST", "/confirm-delivery"): lambda payload: confirm_delivery(**payload),
        (
            "POST",
            "/confirm-window-deliveries",
        ): lambda payload: confirm_window_deliveries(**payload),
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self._dispatch("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch("POST")

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _dispatch(self, method: str) -> None:
            route = routes.get((method, self.path))
            if route is None:
                self._write_json(
                    HTTPStatus.NOT_FOUND,
                    {"status": "error", "error_code": "not_found", "path": self.path},
                )
                return

            try:
                payload = self._read_json_body() if method == "POST" else {}
                response = route(payload)
            except CloudRunnerError as error:
                self._write_json(
                    HTTPStatus.BAD_REQUEST,
                    {
                        "status": "error",
                        "error_code": "invalid_request",
                        "message": str(error),
                    },
                )
                return
            except json.JSONDecodeError:
                self._write_json(
                    HTTPStatus.BAD_REQUEST,
                    {
                        "status": "error",
                        "error_code": "invalid_json",
                        "message": "Corpo JSON invalido",
                    },
                )
                return
            except Exception as error:  # noqa: BLE001
                self._write_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "status": "error",
                        "error_code": "internal_error",
                        "message": str(error),
                    },
                )
                return

            self._write_json(HTTPStatus.OK, {"status": "ok", "result": response})

        def _read_json_body(self) -> dict[str, Any]:
            raw_length = self.headers.get("Content-Length", "0")
            content_length = int(raw_length)
            raw_payload = self.rfile.read(content_length) if content_length > 0 else b"{}"
            payload = json.loads(raw_payload.decode("utf-8"))
            if not isinstance(payload, dict):
                msg = "Corpo JSON deve ser um objeto"
                raise CloudRunnerError(msg)
            return payload

        def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status.value)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
