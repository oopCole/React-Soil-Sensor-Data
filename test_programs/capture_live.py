"""
read ESP32-S3-EYE image_capture firmware over serial and save JPEG files.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

try:
    import serial
except ImportError:
    print("install pyserial: pip install pyserial", file=sys.stderr)
    raise

_SCRIPT_DIR = Path(__file__).resolve().parent
_DEFAULT_OUT = _SCRIPT_DIR / "captured_images"


def read_one_jpeg(ser: serial.Serial, timeout_s: float = 120.0) -> bytes:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        line = ser.readline()
        if not line:
            continue
        if line.startswith(b"IMG_BEGIN"):
            break
    else:
        raise TimeoutError("no IMG_BEGIN before timeout")

    parts = line.decode("utf-8", errors="replace").strip().split()
    if len(parts) < 5 or parts[0].upper() != "IMG_BEGIN" or parts[1].upper() != "JPEG":
        raise ValueError(f"bad header: {line!r}")

    expected = int(parts[2])
    data = bytearray()
    seen_end = False

    while time.time() < deadline and len(data) < expected:
        raw = ser.readline()
        if not raw:
            continue
        s = raw.decode("utf-8", errors="replace").strip()
        if s == "IMG_END":
            seen_end = True
            break
        if not s or s.upper().startswith("IMG_"):
            continue
        for part in s.split(","):
            if len(data) >= expected:
                break
            part = part.strip()
            if not part:
                continue
            data.append(int(part) & 0xFF)

    while not seen_end and time.time() < deadline:
        raw = ser.readline()
        if not raw:
            continue
        if raw.strip() == b"IMG_END":
            seen_end = True
            break

    if len(data) != expected:
        print(
            f"warning: got {len(data)} bytes, header expected {expected}",
            file=sys.stderr,
        )
    return bytes(data[:expected]) if len(data) >= expected else bytes(data)


def main() -> int:
    ap = argparse.ArgumentParser(description="capture JPEGs over serial (sends 'c' to device)")
    ap.add_argument("--port", required=True, help="serial port e.g. COM13")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--count", type=int, default=4, help="number of frames to save")
    ap.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=_DEFAULT_OUT,
        help="output directory",
    )
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    ser = serial.Serial(args.port, args.baud, timeout=0.5)
    time.sleep(0.4)
    ser.reset_input_buffer()

    for i in range(args.count):
        print("get ready please", flush=True)
        time.sleep(2.0)
        ser.write(b"c\n")
        ser.flush()
        time.sleep(0.1)
        try:
            jpeg = read_one_jpeg(ser)
        except Exception as e:
            print(f"frame {i + 1} failed: {e}", file=sys.stderr)
            ser.close()
            return 1
        out = args.out_dir / f"capture_{i + 1:02d}.jpg"
        out.write_bytes(jpeg)
        print(f"wrote {out} ({len(jpeg)} bytes)")

    ser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
