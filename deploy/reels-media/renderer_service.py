#!/usr/bin/env python3
"""Small async FFmpeg renderer for the n8n -> VPS Reels contract."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, InvalidOperation
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

HOST = os.getenv("REELS_RENDER_HOST", "0.0.0.0")
PORT = int(os.getenv("REELS_RENDER_PORT", "8080"))
API_TOKEN = os.getenv("REELS_RENDER_API_TOKEN", "")
JOBS_ROOT = Path(os.getenv("REELS_JOBS_ROOT", "/media/jobs"))
STATE_ROOT = Path(os.getenv("REELS_STATE_ROOT", "/var/lib/reels-render/jobs"))
PUBLIC_BASE_URL = os.getenv("REELS_PUBLIC_BASE_URL", "").rstrip("/")
MAX_BODY_BYTES = int(os.getenv("REELS_MAX_BODY_BYTES", str(4 * 1024 * 1024)))
MAX_SOURCE_BYTES = int(os.getenv("REELS_MAX_SOURCE_BYTES", str(200 * 1024 * 1024)))
MAX_DURATION_SECONDS = float(os.getenv("REELS_MAX_DURATION_SECONDS", "120"))
RENDER_TIMEOUT_SECONDS = int(os.getenv("REELS_RENDER_TIMEOUT_SECONDS", "180"))
MAX_CONCURRENT = int(os.getenv("REELS_MAX_CONCURRENT", "2"))
HOST_ALLOWLIST = {
    value.strip().lower()
    for value in os.getenv("REELS_SOURCE_HOST_ALLOWLIST", "").split(",")
    if value.strip()
}

JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$")
_jobs_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT)


def utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def error_message(exc: BaseException) -> str:
    message = str(exc).replace("\r", " ").replace("\n", " ")
    message = re.sub(r"https?://\S+", "[url]", message)
    message = re.sub(r"(/|[A-Za-z]:\\)[^ ]+", "[path]", message)
    return message[:500] or exc.__class__.__name__


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    raw = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def validate_font_families() -> None:
    for expected in ("Smithen", "Happy Camper"):
        result = subprocess.run(
            ["fc-match", "-f", "%{family}", expected],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        family = result.stdout.strip()
        if result.returncode != 0 or family != expected:
            detected = family or "indisponivel"
            raise RuntimeError(f"fonte ausente ou fallback detectado: {expected} -> {detected}")


def read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    raw_length = handler.headers.get("Content-Length")
    if not raw_length or not raw_length.isdigit():
        raise ValueError("Content-Length obrigatorio")
    length = int(raw_length)
    if length <= 0 or length > MAX_BODY_BYTES:
        raise ValueError("payload acima do limite")
    try:
        payload = json.loads(handler.rfile.read(length))
    except json.JSONDecodeError as exc:
        raise ValueError("JSON invalido") from exc
    if not isinstance(payload, dict):
        raise ValueError("payload deve ser objeto JSON")
    return payload


def require_auth(handler: BaseHTTPRequestHandler) -> None:
    if not API_TOKEN:
        raise RuntimeError("REELS_RENDER_API_TOKEN nao configurado")
    expected = f"Bearer {API_TOKEN}"
    if handler.headers.get("Authorization") != expected:
        raise PermissionError("autenticacao invalida")


def validate_job_id(value: Any) -> str:
    if not isinstance(value, str) or not JOB_ID_RE.fullmatch(value):
        raise ValueError("job_id invalido")
    return value


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    job_id = validate_job_id(payload.get("job_id", ""))
    item_id = str(payload.get("item_id", "")).strip()
    video_url = str(payload.get("video_url", "")).strip()
    template_id = payload.get("template_id")
    if not item_id or len(item_id) > 120:
        raise ValueError("item_id obrigatorio")
    parsed = urllib.parse.urlparse(video_url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("video_url deve usar HTTPS")
    if not HOST_ALLOWLIST:
        raise ValueError("REELS_SOURCE_HOST_ALLOWLIST nao configurada")
    host = parsed.hostname.lower()
    host_allowed = any(
        host == allowed or host.endswith(f".{allowed.lstrip('*.')}")
        for allowed in HOST_ALLOWLIST
    )
    if not host_allowed:
        raise ValueError("host do video nao esta na allowlist")
    if not isinstance(template_id, int) or not 1 <= template_id <= 10:
        raise ValueError("template_id deve estar entre 1 e 10")
    ass = payload.get("ass_template")
    if not isinstance(ass, str) or not ass.strip():
        encoded = payload.get("ass_template_base64")
        if not isinstance(encoded, str):
            raise ValueError("ass_template obrigatorio")
        try:
            ass = base64.b64decode(encoded, validate=True).decode("utf-8-sig")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("ass_template_base64 invalido") from exc
    if len(ass.encode("utf-8")) > MAX_BODY_BYTES:
        raise ValueError("ASS acima do limite")
    price = format_price(payload.get("price", ""))
    if not price or len(price) > 80:
        raise ValueError("price obrigatorio")
    return {
        "job_id": job_id,
        "item_id": item_id,
        "planned_date": str(payload.get("planned_date", "")),
        "source_dispatch_plan_id": payload.get("source_dispatch_plan_id"),
        "video_url": video_url,
        "price": price,
        "template_id": template_id,
        "ass_template": ass,
    }


def parse_ass_time(value: str) -> float:
    hours, minutes, seconds = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def format_ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    rest = seconds - hours * 3600 - minutes * 60
    return f"{hours}:{minutes:02d}:{rest:05.2f}"


def format_price(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    numeric = raw.upper().replace("R$", "").replace(" ", "")
    if "," in numeric:
        numeric = numeric.replace(".", "").replace(",", ".")
    try:
        amount = Decimal(numeric)
    except InvalidOperation:
        return raw
    formatted = f"{amount:,.2f}"
    return "R$ " + formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def _wrap_ass_text(text: str, max_chars: int) -> str:
    prefix_match = re.match(r"^(\{[^}]*\})", text)
    prefix = prefix_match.group(1) if prefix_match else ""
    body = text[len(prefix) :]
    words = body.split()
    if len(words) < 2:
        return text
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if current and len(candidate) > max_chars:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return prefix + r"\N".join(lines)


def _raise_wrapped_dialogue(text: str, pixels: int = 180) -> str:
    """Move a wrapped bottom dialogue upward to keep it above the price card."""
    match = re.search(r"\\pos\(([-0-9.]+),([-0-9.]+)\)", text)
    if not match:
        return text
    y = float(match.group(2)) - pixels
    replacement = rf"\pos({match.group(1)},{round(y)})"
    return text[: match.start()] + replacement + text[match.end() :]


def _fit_single_line_font(text: str, font_size: float, factor: float) -> str:
    """Fit a long line by preserving font proportions instead of squeezing X."""
    fitted_size = max(1, round(font_size * factor))
    text = re.sub(
        r"\\fscx(-?[0-9]+(?:\.[0-9]+)?)",
        r"\\fscx100",
        text,
    )
    override = re.match(r"^(\{[^}]*\})", text)
    if override:
        block = override.group(1)
        block = block[:-1] + rf"\fs{fitted_size}}}"
        return block + text[len(override.group(1)) :]
    return rf"{{\fs{fitted_size}}}" + text


def fit_ass_text(lines: list[str], max_width: float = 960.0) -> list[str]:
    """Shrink wide dialogue lines while preserving their animation tags."""
    style_sizes: dict[str, float] = {}
    for line in lines:
        if not line.startswith("Style:"):
            continue
        fields = line[6:].split(",")
        if len(fields) >= 3:
            try:
                style_sizes[fields[0].strip()] = float(fields[2])
            except ValueError:
                continue

    fitted: list[str] = []
    for line in lines:
        if not line.startswith("Dialogue:"):
            fitted.append(line)
            continue
        fields = line.split(",", 9)
        if len(fields) != 10:
            fitted.append(line)
            continue
        style_size = style_sizes.get(fields[3], 0.0)
        text = fields[9]
        visible = re.sub(r"\{[^}]*\}", "", text)
        longest_line = max((len(part) for part in visible.split(r"\N")), default=0)
        if not style_size or longest_line <= 1:
            fitted.append(line)
            continue
        scales = [float(value) for value in re.findall(r"\\fscx(-?[0-9]+(?:\.[0-9]+)?)", text)]
        current_scale = max(scales or [100.0]) / 100.0
        estimated_width = longest_line * style_size * 0.50 * current_scale
        factor = min(1.0, max_width / estimated_width) if estimated_width else 1.0
        if factor >= 0.99:
            fitted.append(line)
            continue

        if r"\N" not in text and longest_line > 20:
            single_line_size = round(style_size * factor * current_scale)
            if single_line_size >= 110:
                fields[9] = _fit_single_line_font(
                    text, style_size, factor * current_scale
                )
                fitted.append(",".join(fields))
                continue

            wrap_chars = max(15, round(max_width / (style_size * 0.50)))
            text = _wrap_ass_text(text, wrap_chars)
            visible = re.sub(r"\{[^}]*\}", "", text)
            longest_line = max((len(part) for part in visible.split(r"\N")), default=0)
            wrapped_factor = (
                max_width / (longest_line * style_size * 0.50)
                if longest_line
                else 1.0
            )
            wrapped_factor *= 0.85
            fields[9] = _fit_single_line_font(text, style_size, wrapped_factor)
            fitted.append(",".join(fields))
            continue

        def scale_tag(match: re.Match[str], factor: float = factor) -> str:
            value = float(match.group(1)) * factor
            return f"\\fscx{max(1, round(value))}"

        fields[9] = re.sub(r"\\fscx(-?[0-9]+(?:\.[0-9]+)?)", scale_tag, text)
        if "\\fscx" not in text:
            fields[9] = "{\\fscx" + str(max(1, round(100 * factor))) + "}" + fields[9]
        fitted.append(",".join(fields))
    return fitted


def repeat_ass(ass_text: str, duration: float, price: str) -> str:
    """Repeat one normalized ASS cycle, ending up to 0.10s before the source."""
    if duration <= 0 or duration > MAX_DURATION_SECONDS:
        raise ValueError("duracao fora do limite operacional")
    price = format_price(price)
    lines = ass_text.replace("\r\n", "\n").splitlines()
    lines = fit_ass_text(lines)
    events: list[tuple[float, float, str]] = []
    event_start = next((index for index, line in enumerate(lines) if line == "[Events]"), None)
    if event_start is None:
        raise ValueError("ASS sem secao Events")
    for line in lines[event_start + 1 :]:
        if not line.startswith("Dialogue:"):
            continue
        fields = line.split(",", 9)
        if len(fields) != 10:
            raise ValueError("Dialogue ASS invalido")
        start = parse_ass_time(fields[1])
        end = parse_ass_time(fields[2])
        if end <= start:
            raise ValueError("evento ASS com duracao invalida")
        events.append((start, end, line))
    if not events:
        raise ValueError("ASS sem eventos Dialogue")
    cycle = max(end for _, end, _ in events)
    if cycle <= 0:
        raise ValueError("ciclo ASS invalido")
    output: list[str] = []
    event_index = next(index for index, line in enumerate(lines) if line == "[Events]")
    output.extend(lines[: event_index + 1])
    cutoff = max(0.0, duration - 0.10)
    cycle_start = 0.0
    while cycle_start < cutoff:
        for start, end, original in events:
            actual_start = cycle_start + start
            actual_end = min(cycle_start + end, cutoff)
            if actual_start >= actual_end:
                continue
            fields = original.split(",", 9)
            fields[1] = format_ass_time(actual_start)
            fields[2] = format_ass_time(actual_end)
            fields[9] = fields[9].replace("R$ XX,XX", price).replace("XX,XX", price)
            output.append(",".join(fields))
        cycle_start += cycle
    return "\n".join(output) + "\n"


def run_command(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)


def download_source(url: str, destination: Path) -> int:
    request = urllib.request.Request(url, headers={"User-Agent": "reels-renderer/1.0"})
    total = 0
    with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_SOURCE_BYTES:
                raise ValueError("video de entrada acima do limite")
            output.write(chunk)
    if total == 0:
        raise ValueError("video de entrada vazio")
    return total


def probe(source: Path) -> dict[str, Any]:
    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=width,height,codec_type",
            "-of",
            "json",
            str(source),
        ],
        30,
    )
    if result.returncode != 0:
        raise RuntimeError("ffprobe falhou: " + error_message(result.stderr))
    data = json.loads(result.stdout)
    video = next(
        (stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"),
        None,
    )
    duration = float(data.get("format", {}).get("duration", 0))
    if not video or not duration or not video.get("width") or not video.get("height"):
        raise ValueError("origem sem video valido")
    return {"duration": duration, "width": int(video["width"]), "height": int(video["height"])}


def render_once(job: dict[str, Any], attempt_dir: Path) -> dict[str, Any]:
    source = attempt_dir / "source.mp4"
    ass = attempt_dir / "overlay.ass"
    output = attempt_dir / "output.mp4"
    download_source(job["video_url"], source)
    source_meta = probe(source)
    ass.write_text(
        repeat_ass(job["ass_template"], source_meta["duration"], job["price"]),
        encoding="utf-8",
    )
    result = run_command(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,ass={ass}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output),
        ],
        RENDER_TIMEOUT_SECONDS,
    )
    if result.returncode != 0 or not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("ffmpeg falhou: " + error_message(result.stderr))
    output_meta = probe(output)
    if output_meta["width"] != 1080 or output_meta["height"] != 1920:
        raise RuntimeError("saida fora de 1080x1920")
    return {
        "source_width": source_meta["width"],
        "source_height": source_meta["height"],
        "duration_seconds": round(output_meta["duration"], 3),
        "width": 1080,
        "height": 1920,
        "artifact_size_bytes": output.stat().st_size,
    }


def process_job(job: dict[str, Any]) -> None:
    job_id = job["job_id"]
    job_dir = STATE_ROOT / job_id
    artifact_dir = JOBS_ROOT / job_id
    metadata_path = job_dir / "metadata.json"
    with _jobs_lock:
        state = json.loads(metadata_path.read_text(encoding="utf-8"))
        state["status"] = "running"
        state["started_at"] = utc_timestamp()
        metadata_path.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")
    errors: list[dict[str, Any]] = []
    try:
        for attempt in (1, 2):
            attempt_dir = Path(tempfile.mkdtemp(prefix=f"attempt-{attempt}-", dir=job_dir))
            try:
                metrics = render_once(job, attempt_dir)
                artifact_dir.mkdir(parents=True, exist_ok=True)
                final_output = artifact_dir / "output.mp4"
                shutil.copyfile(attempt_dir / "output.mp4", final_output)
                result = {
                    **state,
                    "status": "succeeded",
                    "render_status": "succeeded",
                    "attempts": attempt,
                    "overlay_applied": True,
                    "published_video_source": "rendered_artifact",
                    "artifact_url": f"{PUBLIC_BASE_URL}/{job_id}/output.mp4",
                    "artifact_mime_type": "video/mp4",
                    "render_engine": "ffmpeg",
                    **metrics,
                    "completed_at": utc_timestamp(),
                    "errors": errors,
                }
                metadata_path.write_text(
                    json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8"
                )
                return
            except Exception as exc:  # one failure must not prevent the fallback attempt
                errors.append(
                    {
                        "attempt": attempt,
                        "code": "FFMPEG_RENDER_FAILED",
                        "message": error_message(exc),
                    }
                )
            finally:
                shutil.rmtree(attempt_dir, ignore_errors=True)
        result = {
            **state,
            "status": "failed",
            "render_status": "failed_fallback_original",
            "attempts": 2,
            "overlay_applied": False,
            "published_video_source": "shopee_original",
            "completed_at": utc_timestamp(),
            "errors": errors,
        }
        metadata_path.write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
    except Exception as exc:
        result = {**state, "status": "failed", "render_status": "failed", "errors": [
            {"attempt": 0, "code": "JOB_INTERNAL_ERROR", "message": error_message(exc)}
        ]}
        metadata_path.write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")


def create_job(payload: dict[str, Any]) -> dict[str, Any]:
    job = validate_payload(payload)
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    job_dir = STATE_ROOT / job["job_id"]
    metadata_path = job_dir / "metadata.json"
    fingerprint = hashlib.sha256(
        json.dumps(
            {key: value for key, value in job.items() if key != "ass_template"},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    with _jobs_lock:
        if metadata_path.exists():
            existing = json.loads(metadata_path.read_text(encoding="utf-8"))
            if existing.get("fingerprint") != fingerprint:
                raise FileExistsError("job_id ja existe com outro payload")
            return existing
        job_dir.mkdir(mode=0o750)
        state = {
            "job_id": job["job_id"],
            "item_id": job["item_id"],
            "planned_date": job["planned_date"],
            "source_dispatch_plan_id": job["source_dispatch_plan_id"],
            "template_id": job["template_id"],
            "status": "queued",
            "render_status": "queued",
            "attempts": 0,
            "fingerprint": fingerprint,
            "created_at": utc_timestamp(),
        }
        metadata_path.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")
    _executor.submit(process_job, job)
    return state


class Handler(BaseHTTPRequestHandler):
    server_version = "reels-renderer/1.0"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            json_response(self, HTTPStatus.OK, {"status": "ok"})
            return
        try:
            require_auth(self)
            prefix = "/v1/render/jobs/"
            if not self.path.startswith(prefix):
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            job_id = validate_job_id(self.path[len(prefix) :].split("/", 1)[0])
            metadata = STATE_ROOT / job_id / "metadata.json"
            if not metadata.exists():
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "job_not_found"})
                return
            json_response(self, HTTPStatus.OK, json.loads(metadata.read_text(encoding="utf-8")))
        except PermissionError as exc:
            json_response(self, HTTPStatus.UNAUTHORIZED, {"error": error_message(exc)})
        except Exception as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": error_message(exc)})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/render/jobs":
            json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            require_auth(self)
            state = create_job(read_json(self))
            json_response(self, HTTPStatus.ACCEPTED, state)
        except PermissionError as exc:
            json_response(self, HTTPStatus.UNAUTHORIZED, {"error": error_message(exc)})
        except FileExistsError as exc:
            json_response(self, HTTPStatus.CONFLICT, {"error": error_message(exc)})
        except Exception as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": error_message(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}", flush=True)


def main() -> None:
    if not API_TOKEN:
        raise SystemExit("REELS_RENDER_API_TOKEN obrigatorio")
    if not PUBLIC_BASE_URL:
        raise SystemExit("REELS_PUBLIC_BASE_URL obrigatorio")
    if not HOST_ALLOWLIST:
        raise SystemExit("REELS_SOURCE_HOST_ALLOWLIST obrigatoria")
    validate_font_families()
    JOBS_ROOT.mkdir(parents=True, exist_ok=True)
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"reels-renderer listening on {HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
