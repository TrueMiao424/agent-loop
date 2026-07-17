"""Generate favicon.ico / apple-touch-icon.png for Agent Loop."""
import pathlib
import struct
import zlib


def png_rgba(size: int, pixels: bytes) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + pixels[y * size * 4 : (y + 1) * size * 4] for y in range(size))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def draw(size: int) -> bytes:
    out = bytearray(size * size * 4)
    corner = max(2, int(size * 0.22))
    for y in range(size):
        for x in range(size):
            cx = min(x, size - 1 - x)
            cy = min(y, size - 1 - y)
            inside = True
            if cx < corner and cy < corner:
                dx, dy = corner - cx, corner - cy
                inside = dx * dx + dy * dy <= corner * corner
            i = (y * size + x) * 4
            if not inside:
                out[i : i + 4] = b"\x00\x00\x00\x00"
                continue
            t = (x + y) / (2 * (size - 1))
            out[i] = lerp(0x63, 0x8B, t)
            out[i + 1] = lerp(0x66, 0x5C, t)
            out[i + 2] = lerp(0xF1, 0xF6, t)
            out[i + 3] = 255

    cx, cy = size // 2, int(size * 0.42)
    rx, ry = int(size * 0.28), int(size * 0.22)
    thickness = max(1, size // 12)
    for y in range(size):
        for x in range(size):
            dx = (x - cx) / max(rx, 1)
            dy = (y - cy) / max(ry, 1)
            d = dx * dx + dy * dy
            if 0.72 <= d <= 1.05:
                i = (y * size + x) * 4
                if out[i + 3]:
                    out[i : i + 3] = b"\xff\xff\xff"

    for y in range(int(size * 0.55), int(size * 0.78)):
        for x in range(int(size * 0.28), int(size * 0.48)):
            if abs((x - size * 0.32) - (y - size * 0.55) * 0.55) < thickness and y > size * 0.58:
                i = (y * size + x) * 4
                if out[i + 3]:
                    out[i : i + 3] = b"\xff\xff\xff"

    for ox in (-int(size * 0.12), 0, int(size * 0.12)):
        dx0, dy0 = cx + ox, cy
        rad = max(1, size // 16)
        for y in range(dy0 - rad - 1, dy0 + rad + 2):
            for x in range(dx0 - rad - 1, dx0 + rad + 2):
                if 0 <= x < size and 0 <= y < size and (x - dx0) ** 2 + (y - dy0) ** 2 <= rad * rad:
                    i = (y * size + x) * 4
                    if out[i + 3]:
                        out[i : i + 3] = b"\xff\xff\xff"
    return bytes(out)


def ico_from_pngs(pngs_with_sizes):
    count = len(pngs_with_sizes)
    offset = 6 + 16 * count
    data = bytearray(struct.pack("<HHH", 0, 1, count))
    blobs = []
    for size, png in pngs_with_sizes:
        w = 0 if size >= 256 else size
        h = 0 if size >= 256 else size
        data += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(png), offset)
        blobs.append(png)
        offset += len(png)
    for blob in blobs:
        data += blob
    return bytes(data)


def main():
    out_dir = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "public"
    out_dir.mkdir(parents=True, exist_ok=True)
    sizes = [16, 32, 48]
    png_map = {s: png_rgba(s, draw(s)) for s in sizes}
    (out_dir / "favicon.ico").write_bytes(ico_from_pngs([(s, png_map[s]) for s in sizes]))
    (out_dir / "apple-touch-icon.png").write_bytes(png_rgba(180, draw(180)))
    (out_dir / "favicon-32.png").write_bytes(png_map[32])
    print("written:", sorted(p.name for p in out_dir.iterdir()))


if __name__ == "__main__":
    main()
