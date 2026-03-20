"""
parse a terminal log that contains IMG_BEGIN ... IMG_END blocks and save JPEG files.

works if the log is one long line or many lines, and if the first frame is truncated
(missing IMG_BEGIN) — only complete IMG_BEGIN ... IMG_END blocks are extracted.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np

_SCRIPT_DIR = Path(__file__).resolve().parent
_DEFAULT_OUT = _SCRIPT_DIR / "captured_images"
# default log name under test_programs (save platformio serial output here)
_DEFAULT_LOG = _SCRIPT_DIR / "platformoutput.txt"

# matches IMG_BEGIN anywhere in the file (not only start of line)
_HEADER_RE = re.compile(
    r"IMG_BEGIN\s+JPEG\s+(\d+)\s+(\d+)\s+(\d+)",
    re.IGNORECASE,
)


def _bytes_from_chunk(chunk: str, expected: int) -> bytearray:
    data = bytearray()
    for raw in re.split(r"[\s,;]+", chunk):
        t = raw.strip().strip(",")
        if not t or not t.isdigit():
            continue
        v = int(t)
        if 0 <= v <= 255:
            data.append(v)
        if len(data) >= expected:
            break
    return data


def extract_jpegs_from_text(text: str) -> list[bytes]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    jpegs: list[bytes] = []

    for m in _HEADER_RE.finditer(text):
        expected = int(m.group(1))
        tail = text[m.end() :]

        # prefer a line that is only IMG_END; else any IMG_END token
        end_match = re.search(r"(?m)^\s*IMG_END\s*$", tail)
        if not end_match:
            end_match = re.search(r"\bIMG_END\b", tail)
        if not end_match:
            print(
                f"warning: no IMG_END after header at {m.start()}; skip block",
                file=sys.stderr,
            )
            continue

        chunk = tail[: end_match.start()]
        data = _bytes_from_chunk(chunk, expected)
        if len(data) != expected:
            print(
                f"warning: block wanted {expected} bytes, parsed {len(data)}",
                file=sys.stderr,
            )
        if len(data) == 0:
            continue
        jpegs.append(bytes(data[:expected]) if len(data) >= expected else bytes(data))

    return jpegs


def main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "convert logged serial JPEG dump to .jpg files "
            f"(default log: {_DEFAULT_LOG.name})"
        )
    )
    p.add_argument(
        "log_file",
        type=Path,
        nargs="?",
        default=_DEFAULT_LOG,
        help=f"path to saved serial log (default: {_DEFAULT_LOG})",
    )
    p.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=_DEFAULT_OUT,
        help="output directory (default: test_programs/captured_images)",
    )
    args = p.parse_args()

    log_path = args.log_file
    if not log_path.is_file():
        print(f"not found: {log_path}", file=sys.stderr)
        print(
            f"save your PlatformIO serial output as: {_DEFAULT_LOG}",
            file=sys.stderr,
        )
        return 1

    text = log_path.read_text(encoding="utf-8", errors="replace")
    jpegs = extract_jpegs_from_text(text)
    if not jpegs:
        print(
            "no complete IMG_BEGIN JPEG ... IMG_END blocks found",
            file=sys.stderr,
        )
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for idx, jpeg in enumerate(jpegs, start=1):
        out = args.out_dir / f"capture_{idx:02d}.jpg"
        out.write_bytes(jpeg)
        arr = np.frombuffer(jpeg, dtype=np.uint8)
        print(f"wrote {out} ({len(jpeg)} bytes), numpy shape {arr.shape}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
