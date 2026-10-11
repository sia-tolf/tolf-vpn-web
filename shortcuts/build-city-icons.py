"""Build flat city power icons for MobileConfig using only the standard library."""
import base64, json, math, struct, zlib
from pathlib import Path

COLORS = {"moscow": "#AD5555", "riga": "#793D52"}
def png(color):
    bg = bytes.fromhex(color.lstrip("#"))
    size, scale = 180, 4
    rows = bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            hits = 0
            for sy in range(scale):
                for sx in range(scale):
                    dx = x + (sx + .5)/scale - 90
                    dy = y + (sy + .5)/scale - 95
                    ring = abs(math.hypot(dx,dy)-46) <= 5 and not (dy < 0 and abs(dx) < 23)
                    bar = math.hypot(dx, max(43-(y+(sy+.5)/scale), 0, (y+(sy+.5)/scale)-87)) <= 5
                    hits += ring or bar
            rows.extend(round(c + (255-c)*hits/(scale*scale)) for c in bg)
    def chunk(kind, data):
        return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
    return b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",size,size,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(rows,9))+chunk(b"IEND",b"")
if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    module = root / "setup/anyconnect/tolf_oc_webclips.py"
    icons = {city: base64.b64encode(png(color)).decode() for city,color in COLORS.items()}
    lines = module.read_text().splitlines()
    lines = ["ICONS = " + json.dumps(icons) if line.startswith("ICONS") else line for line in lines]
    module.write_text("\n".join(lines)+"\n")
