"""Transfer only the editor's new pigment to the verified inherited wall.

Input wall.png is record 39; input wall-v20.png is the editor's full draft.
Both become identical final PNGs. The numbered JPEG is made in memory.
"""
import hashlib
import importlib.util
import math
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    'wall_thumbnail_40', ROOT / 'shared/wall-thumbnail/thumbnail.py')
thumbnail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thumbnail)

ancestor_path = ROOT / 'artifacts/line-3/wall.png'
draft_path = ROOT / 'artifacts/line-3/wall-v20.png'
ancestor_hash = '6b265ee084c59107492703cd621e77071f21bc971ebe377acaef3eefc5fb8782'
draft_hash = 'bdb8f6c0fbe591586293bc50433402cd6e8b0f7c6d655e2c7425f75dd3f24376'
assert hashlib.sha256(ancestor_path.read_bytes()).hexdigest() == ancestor_hash
assert hashlib.sha256(draft_path.read_bytes()).hexdigest() == draft_hash
w, h, old = thumbnail.png_rgb(ancestor_path)
gw, gh, draft = thumbnail.png_rgb(draft_path)
assert (w, h) == (gw, gh) == (1254, 1254)


def disk(x, y, cx, cy, radius):
    return max(0.0, min(1.0, (radius - math.hypot(x-cx, y-cy)) / 2.0))


def segment(x, y, ax, ay, bx, by, width):
    vx, vy = bx-ax, by-ay
    t = max(0.0, min(1.0, ((x-ax)*vx + (y-ay)*vy) / (vx*vx + vy*vy)))
    return disk(x, y, ax+t*vx, ay+t*vy, width)


def pigment_alpha(x, y):
    # These shapes enclose only the editor's new ring, three stones and links.
    radial = math.hypot((x-503)/65, (y-907)/66)
    ring = max(0.0, min(1.0, (0.145-abs(radial-1.0))*65/3.0))
    stones = max(disk(x, y, 509, 896, 24),
                 disk(x, y, 472, 941, 25),
                 disk(x, y, 532, 942, 25))
    links = max(segment(x, y, 501, 913, 479, 925, 8),
                segment(x, y, 517, 913, 527, 927, 8),
                segment(x, y, 489, 943, 516, 943, 6))
    return max(ring, stones, links)


box = (430, 829, 578, 982)
rows = [bytearray(row) for row in old]
changed = 0
for y in range(box[1], box[3]):
    for x in range(box[0], box[2]):
        alpha = pigment_alpha(x, y)
        if not alpha:
            continue
        pos = 3*x
        for channel in range(3):
            before = old[y][pos+channel]
            after = draft[y][pos+channel]
            rows[y][pos+channel] = round(before*(1-alpha) + after*alpha)
        if rows[y][pos:pos+3] != old[y][pos:pos+3]:
            changed += 1
assert changed > 1000


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


header = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
raw = b''.join(b'\x00' + row for row in rows)
png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header)
       + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))
draft_path.write_bytes(png)
ancestor_path.write_bytes(png)
assert thumbnail.png_rgb(draft_path) == (w, h, [bytes(row) for row in rows])
jpeg = thumbnail.jpeg(thumbnail.resize(w, h, rows, 512))
assert len(jpeg) < 100_000
(ROOT / 'dist/line-3/40.jpg').write_bytes(jpeg)
print('wall_sha256', hashlib.sha256(png).hexdigest())
print('PNG', w, h, 'RGB 8-bit', 'changed_pixels', changed,
      'outside_box_changed', 0)
print('JPEG', 512, 512, 'bytes', len(jpeg))
