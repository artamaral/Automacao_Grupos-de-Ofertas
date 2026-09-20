#!/usr/bin/env python3
"""Split the ten showcase templates from one ASS file into one-cycle files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TEMPLATE_RE = re.compile(r"^T(?P<id>\d{2})_")
DIALOGUE_RE = re.compile(
    r"^Dialogue:\s*[^,]+,(?P<start>[^,]+),(?P<end>[^,]+),(?P<style>[^,]+),"
)


def parse_time(value: str) -> int:
    hours, minutes, seconds = value.strip().split(":")
    whole, centiseconds = seconds.split(".")
    return ((int(hours) * 60 + int(minutes)) * 60 + int(whole)) * 100 + int(
        centiseconds[:2].ljust(2, "0")
    )


def format_time(total_centiseconds: int) -> str:
    total_centiseconds = max(0, total_centiseconds)
    hours, remainder = divmod(total_centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def split_dialogue(line: str, shift: int) -> tuple[str, str, str] | None:
    match = DIALOGUE_RE.match(line)
    if not match:
        return None
    fields = line.split(",", 9)
    if len(fields) != 10:
        raise ValueError(f"linha Dialogue invalida: {line}")
    start = parse_time(match.group("start")) - shift
    end = parse_time(match.group("end")) - shift
    if start < 0 or end <= start:
        raise ValueError(f"intervalo invalido apos normalizacao: {line}")
    fields[1] = format_time(start)
    fields[2] = format_time(end)
    return ",".join(fields), match.group("style"), fields[0]


def build_template(source: Path, output_dir: Path, template_id: int) -> dict[str, object]:
    lines = source.read_text(encoding="utf-8-sig").splitlines()
    try:
        styles_start = lines.index("[V4+ Styles]")
        events_start = lines.index("[Events]")
    except ValueError as exc:
        raise ValueError("ASS sem secoes [V4+ Styles] e [Events]") from exc

    template = f"T{template_id:02d}_"
    style_lines = [
        line
        for line in lines[styles_start + 1 : events_start]
        if line.startswith("Format:") or line.startswith(f"Style: {template}")
    ]
    raw_events = [
        line
        for line in lines[events_start + 1 :]
        if line.startswith("Dialogue:") and f",{template}" in line
    ]
    if not style_lines or not raw_events:
        raise ValueError(f"template {template_id:02d} sem estilos ou eventos")

    starts = [parse_time(DIALOGUE_RE.match(line).group("start")) for line in raw_events]  # type: ignore[union-attr]
    shift = min(starts)
    normalized_events: list[str] = []
    event_styles: set[str] = set()
    for line in raw_events:
        result = split_dialogue(line, shift)
        if result is None:
            raise ValueError(f"Dialogue nao interpretado: {line}")
        normalized, style, _layer = result
        normalized_events.append(normalized)
        event_styles.add(style)

    cycle_end = max(
        parse_time(DIALOGUE_RE.match(line).group("end")) - shift  # type: ignore[union-attr]
        for line in raw_events
    )
    info = lines[:styles_start]
    output_lines = [
        "[Script Info]",
        "; PRODUCTION TEMPLATE — extracted from testeFonte.ass",
        f"; template_id: {template_id}",
        "; This file contains one normalized cycle; the renderer repeats it.",
        *[line for line in info if not line.startswith("[Script Info]")],
        "",
        "[V4+ Styles]",
        *style_lines,
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        *normalized_events,
        "",
    ]
    output_path = output_dir / f"template_{template_id:02d}.ass"
    output_path.write_text("\n".join(output_lines), encoding="utf-8")
    return {
        "template_id": template_id,
        "file_name": output_path.name,
        "source_file": source.name,
        "cycle_duration_seconds": cycle_end / 100,
        "style_names": sorted(event_styles),
        "event_count": len(normalized_events),
        "status": "draft_split",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    if not args.source.is_file():
        parser.error(f"arquivo ASS nao encontrado: {args.source}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = [
        build_template(args.source, args.output_dir, template_id)
        for template_id in range(1, 11)
    ]
    (args.output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "source_file": args.source.name,
                "status": "draft_split",
                "templates": manifest,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"OK: {len(manifest)} templates separados em {args.output_dir}")
    for item in manifest:
        print(
            f"template_id={item['template_id']} file={item['file_name']} "
            f"duration={item['cycle_duration_seconds']} events={item['event_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
