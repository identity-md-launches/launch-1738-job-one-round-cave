#!/usr/bin/env python3
"""Conserve the image editor's tiny addition and produce record 40's outputs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib

ROOT = Path.cwd().resolve()
WALL = ROOT / 'artifacts/line-4/wall.png'
OUTPUT = ROOT / 'artifacts/line-4/wall-v20.png'
THUMB = ROOT / 'dist/line-4/40.jpg'
RECORD = ROOT / 'dist/line-4/40.json'
ANCESTOR = '444fec03059f0b7133a6e0a3bd96dd511c0585f8ce2e4a1ad93579577000d1d2'
PATCH = (1010, 500, 1115, 570)


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


def main():
    assert hashlib.sha256(WALL.read_bytes()).hexdigest() == ANCESTOR
    assert not THUMB.exists() and not RECORD.exists()
    spec = importlib.util.spec_from_file_location('codec40',
        ROOT / 'line-4/tools/call-rehearsal/thumbnail.py')
    codec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(codec)
    width, height, old = codec.png_rgb(WALL)
    sw, sh, generated = codec.png_rgb(OUTPUT)
    assert (width, height) == (sw, sh) == (1254, 1254)
    generated_hash = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    rows = [bytearray(row) for row in old]
    left, top, right, bottom = PATCH
    for y in range(top, bottom):
        for x in range(left, right):
            i = 3*x
            previous = old[y][i:i+3]
            red, green, blue = generated[y][i:i+3]
            difference = sum(abs(previous[c] - (red, green, blue)[c]) for c in range(3))
            ochre = red > 1.28*green and red-green > 30 and green > blue
            charcoal = red < 115 and green < 85 and blue < 70
            yellow = red > 125 and green > 73 and red > 1.15*green and green > 1.5*blue
            # Select the generated earth pigment, retaining unpainted stone.
            if difference > 70 and (ochre or charcoal or yellow):
                rows[y][i:i+3] = generated[y][i:i+3]
    inside = outside = 0
    for y in range(height):
        for x in range(width):
            i = 3*x
            if rows[y][i:i+3] != old[y][i:i+3]:
                if left <= x < right and top <= y < bottom:
                    inside += 1
                else:
                    outside += 1
    assert inside > 500 and outside == 0
    png = (b'\x89PNG\r\n\x1a\n' +
           chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) +
           chunk(b'IDAT', zlib.compress(b''.join(b'\0' + bytes(row) for row in rows), 9)) +
           chunk(b'IEND', b''))
    jpeg = codec.jpeg(codec.resize(width, height, rows, 512))
    assert len(jpeg) < 100_000
    OUTPUT.write_bytes(png)
    WALL.write_bytes(png)
    THUMB.write_bytes(jpeg)
    checks = {'ancestor_sha256': ANCESTOR, 'generated_sha256': generated_hash,
              'wall_sha256': hashlib.sha256(png).hexdigest(),
              'wall': {'width': width, 'height': height, 'format': 'PNG',
                       'mode': 'RGB', 'bytes': len(png)},
              'thumbnail': {'width': 512, 'height': 512, 'format': 'JPEG', 'bytes': len(jpeg)},
              'addition_rectangle': list(PATCH), 'changed_pixels_inside': inside,
              'changed_pixels_outside': outside,
              'unmet_visual_requirements': [
                  'Inherited tiny three-pronged trail motifs cannot be certified as five-digit handprints; preserved unchanged.']}
    (ROOT / 'line-4/delivery-checks-40.json').write_text(json.dumps(checks, indent=2) + '\n')
    record = {'name': 'The Covered Embers',
              'image': 'https://api.imd.fun/artifacts/' + checks['wall_sha256'],
              'attributes': [
                  {'trait_type': 'Cave', 'value': 'Moss'},
                  {'trait_type': 'Wall', 'value': 'Line 4'},
                  {'trait_type': 'Number', 'value': 40},
                  {'trait_type': 'Left behind', 'value': 'Gas Cap Rehearsal'},
                  {'trait_type': 'Meaning', 'value': 'A charcoal cover bounds the embers before their heat is trusted.'},
                  {'trait_type': 'One thing', 'value': 'Rehearse Ethereum contract calls before submission'}]}
    RECORD.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()
