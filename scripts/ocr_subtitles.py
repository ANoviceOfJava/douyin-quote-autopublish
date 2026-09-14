"""Extract burned-in subtitles and stable timestamp segments with OCR."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import cv2
from imageio_ffmpeg import get_ffmpeg_exe
from rapidocr_onnxruntime import RapidOCR


def extract_frames(video: Path, frame_dir: Path, fps: float, max_seconds: float | None) -> None:
    command = [get_ffmpeg_exe(), "-y", "-v", "error", "-i", str(video)]
    if max_seconds is not None:
        command += ["-t", f"{max_seconds:g}"]
    command += ["-vf", f"fps={fps:g}", str(frame_dir / "%06d.png")]
    subprocess.run(command, check=True)


def read_items(engine: RapidOCR, image_path: Path, top: float, bottom: float, min_score: float) -> list[dict[str, Any]]:
    image = cv2.imread(str(image_path))
    if image is None:
        return []
    height = image.shape[0]
    y0 = int(height * top)
    y1 = int(height * bottom)
    result, _ = engine(image[y0:y1, :])
    items: list[dict[str, Any]] = []
    for box, text, score in result or []:
        clean = re.sub(r"\s+", "", str(text)).strip()
        if not clean or float(score) < min_score:
            continue
        points = [float(point[1]) for point in box]
        items.append(
            {
                "text": clean,
                "score": round(float(score), 3),
                "y0": round((y0 + min(points)) / height, 4),
                "y1": round((y0 + max(points)) / height, 4),
            }
        )
    return items


def merge_segments(rows: list[dict[str, Any]], frame_step: float) -> list[dict[str, Any]]:
    active: dict[str, dict[str, Any]] = {}
    segments: list[dict[str, Any]] = []
    max_gap = frame_step * 1.05
    for row in rows:
        seen: set[str] = set()
        for item in row["items"]:
            key = item["text"]
            seen.add(key)
            current = active.get(key)
            if current is not None and row["t"] - current["end"] <= max_gap:
                current["end"] = row["t"]
                current["score"] = max(current["score"], item["score"])
                current["y0"] = min(current["y0"], item["y0"])
                current["y1"] = max(current["y1"], item["y1"])
            else:
                if current is not None:
                    segments.append(current)
                active[key] = {
                    "text": key,
                    "start": row["t"],
                    "end": row["t"],
                    "score": item["score"],
                    "y0": item["y0"],
                    "y1": item["y1"],
                }
        for key in list(active):
            if key not in seen and row["t"] - active[key]["end"] > max_gap:
                segments.append(active.pop(key))
    segments.extend(active.values())
    segments.sort(key=lambda item: (item["start"], item["y0"], item["text"]))
    return segments


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--band-top", type=float, default=0.72)
    parser.add_argument("--band-bottom", type=float, default=0.92)
    parser.add_argument("--fps", type=float, default=2.0)
    parser.add_argument("--max-seconds", type=float)
    parser.add_argument("--min-score", type=float, default=0.7)
    args = parser.parse_args()

    video = Path(args.video).resolve()
    output = Path(args.out).resolve()
    if not video.is_file():
        raise SystemExit(f"video does not exist: {video}")
    if args.fps <= 0:
        raise SystemExit("--fps must be positive")
    if not 0 <= args.band_top < args.band_bottom <= 1:
        raise SystemExit("band bounds must satisfy 0 <= top < bottom <= 1")

    output.parent.mkdir(parents=True, exist_ok=True)
    engine = RapidOCR()
    frame_step = 1.0 / args.fps
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="quote-ocr-") as temp_name:
        frame_dir = Path(temp_name)
        extract_frames(video, frame_dir, args.fps, args.max_seconds)
        for frame_path in sorted(frame_dir.glob("*.png")):
            index = int(frame_path.stem)
            seconds = round((index - 1) * frame_step, 3)
            rows.append(
                {
                    "t": seconds,
                    "items": read_items(engine, frame_path, args.band_top, args.band_bottom, args.min_score),
                }
            )

    segments = merge_segments(rows, frame_step)
    payload = {
        "video": str(video),
        "band_top": args.band_top,
        "band_bottom": args.band_bottom,
        "fps": args.fps,
        "rows": rows,
        "segments": segments,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for segment in segments:
        if segment["score"] >= 0.85 and len(segment["text"]) >= 2 and segment["end"] - segment["start"] >= 0.4:
            print(
                f"{segment['start']:>7.2f}-{segment['end']:>7.2f}s  "
                f"s={segment['score']:.2f} y={segment['y0']:.2f}-{segment['y1']:.2f}  {segment['text']}"
            )
    print(f"JSON -> {output}", file=sys.stderr)


if __name__ == "__main__":
    main()