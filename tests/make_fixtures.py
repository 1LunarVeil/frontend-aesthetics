"""Generate tiny PNG fixtures for the image diff tests (standard library only).

Run from the plugin root: python -B tests/make_fixtures.py

Writes tests/fixtures/png/flat.png (one colour) and tests/fixtures/png/box.png
(a background with a contrasting rectangle), which is enough to exercise
decoding, per-filter reconstruction, statistics and diffing without shipping
binary blobs that cannot be reviewed.
"""

import struct
import sys
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent / "fixtures" / "png"
WIDTH, HEIGHT = 64, 40


def _chunk(kind, body):
    return (
        struct.pack(">I", len(body))
        + kind
        + body
        + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
    )


def write_png(path, rows):
    """Encode RGB rows (list of bytearrays, 3 bytes per pixel) as a PNG."""
    raw = bytearray()
    for row in rows:
        raw += b"\x00"  # filter type 0 (None) keeps the fixture readable
        raw += row
    header = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    data = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )
    path.write_bytes(data)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    background = bytes((246, 247, 249))
    accent = bytes((37, 99, 235))

    flat = [bytearray(background * WIDTH) for _ in range(HEIGHT)]
    write_png(OUT / "flat.png", flat)

    box = []
    for y in range(HEIGHT):
        row = bytearray(background * WIDTH)
        if 8 <= y < 24:
            for x in range(10, 40):
                row[x * 3:x * 3 + 3] = accent
        box.append(row)
    write_png(OUT / "box.png", box)

    print(f"wrote {OUT / 'flat.png'} and {OUT / 'box.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
