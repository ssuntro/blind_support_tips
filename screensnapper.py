#!/usr/bin/env python3


import sys
import os
import re
from pathlib import Path

try:
    import cv2
except ImportError:
    print("Error: OpenCV is required. Install it with:")
    print("    pip install opencv-python")
    sys.exit(1)


def parse_timestamp(ts: str) -> float:
    """Convert 'HH:MM:SS' string to total seconds (float)."""
    ts = ts.strip()
    match = re.match(r"^(\d{1,2}):(\d{2}):(\d{2})(?:\.(\d+))?$", ts)
    if not match:
        raise ValueError(f"Invalid timestamp format: '{ts}' (expected HH:MM:SS)")
    hours, minutes, seconds = int(match.group(1)), int(match.group(2)), int(match.group(3))
    frac = float(f"0.{match.group(4)}") if match.group(4) else 0.0
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f"Invalid timestamp values: '{ts}'")
    return hours * 3600 + minutes * 60 + seconds + frac


def parse_timestamp_list(raw: str) -> list:
    """
    Parse the timestamp argument which may come as:
      "[00:00:05, 00:00:12, 00:01:30]"
      "00:00:05,00:00:12,00:01:30"
    or as multiple separate argv items after shell-splitting.
    """
    cleaned = raw.strip().strip("[]")
    parts = [p.strip().rstrip(",") for p in cleaned.split(",")]
    return [p for p in parts if p]


def extract_snapshots(video_path, timestamps, output_dir="snapshots"):
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    print(f"Video: {video_path}")
    print(f"  FPS: {fps:.2f} | Frames: {total_frames} | Duration: {duration:.2f}s\n")

    os.makedirs(output_dir, exist_ok=True)
    video_stem = Path(video_path).stem

    saved_files = []
    for ts in timestamps:
        try:
            seconds = parse_timestamp(ts)
        except ValueError as e:
            print(f"  ✗ Skipping: {e}")
            continue

        if seconds > duration:
            print(f"  ✗ {ts} exceeds video duration ({duration:.2f}s) — skipped")
            continue

        # Seek by millisecond for accuracy, then read the frame
        cap.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
        ret, frame = cap.read()
        if not ret or frame is None:
            print(f"  ✗ Could not read frame at {ts}")
            continue

        safe_ts = ts.replace(":", "-")
        out_path = os.path.join(output_dir, f"{video_stem}_{safe_ts}.png")
        cv2.imwrite(out_path, frame)
        saved_files.append(out_path)
        print(f"  ✓ {ts} → {out_path}")

    cap.release()
    print(f"\nDone. Saved {len(saved_files)} snapshot(s) in '{output_dir}/'")
    return saved_files


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    video_path = sys.argv[1]

    # Support both quoted "[...]" and shell-split argv forms
    raw = " ".join(sys.argv[2:])
    timestamps = parse_timestamp_list(raw)

    if not timestamps:
        print("Error: No timestamps provided.")
        sys.exit(1)

    try:
        extract_snapshots(video_path, timestamps)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
