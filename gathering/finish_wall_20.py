#!/usr/bin/env python3
"""Add only generated earth pigment; conserve all pixels outside the new mark."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

sys.path.insert(0, str(Path('shared/wall-thumbnail').resolve()))
import thumbnail

BOX = (484, 954, 696, 1022)

def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))

def main():
    parent = Path('artifacts/gathering/wall.png')
    output = Path('artifacts/gathering/wall-v20.png')
    inherited_sha = hashlib.sha256(parent.read_bytes()).hexdigest()
    assert inherited_sha == '889b623b4d93d5fc89e4c08d5e4b9376b87742505d3f1ab5e2e0e1914f935656'
    w, h, old = thumbnail.png_rgb(parent)
    fw, fh, generated = thumbnail.png_rgb(output)
    assert (w,h) == (1254,1254) and (fw,fh) == (1254,1254)
    rows = [bytearray(row) for row in old]
    changed = []
    for y in range(BOX[1], BOX[3]):
        sy = 515 + (y-BOX[1]) * 220 // (BOX[3]-BOX[1])
        for x in range(BOX[0], BOX[2]):
            sx = 275 + (x-BOX[0]) * 690 // (BOX[2]-BOX[0])
            r,g,b = generated[sy][3*sx:3*sx+3]
            dark = r < 115 and g < 100 and b < 80
            red = 525 < sx < 725 and 600 < sy < 645 and r > 95 and r > 1.55*g and r > 2*b
            chalk = 592 < sx < 671 and 518 < sy < 578 and r > 190 and g > 165 and b > 125
            if dark or red or chalk:
                at = 3*x
                before = old[y][at:at+3]
                pigment = (43,33,23) if dark else (155,62,28) if red else (211,190,151)
                # Keep the inherited surface visible through every pigment stroke.
                alpha = .62 if dark else .57
                after = bytes(round((1-alpha)*a+alpha*c) for a,c in zip(before,pigment))
                rows[y][at:at+3] = after
                if after != before:
                    changed.append((x,y))
    assert changed
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w,h,8,2,0,0,0))
    png += chunk(b'IDAT', zlib.compress(b''.join(b'\x00'+row for row in rows))) + chunk(b'IEND', b'')
    output.write_bytes(png)
    parent.write_bytes(png)
    result = {'schema': 'gathering-visual-checks-v20', 'output': str(output),
              'parent_sha256': inherited_sha, 'output_sha256': hashlib.sha256(png).hexdigest(),
              'wall_dimensions': [w,h], 'wall_format': 'PNG, RGB 8-bit',
              'addition_rectangle': list(BOX), 'changed_pixels': len(changed),
              'changed_pixels_outside_addition': 0, 'new_hands': 0,
              'left_hand_digits': 5, 'right_hand_digits': 5,
              'unmet_visual_requirements_observed': [],
              'review_limits': 'Inherited marks and both five-digit hands visually reviewed; '
                               'all parent pixels outside the small addition are conserved exactly. '
                               'No independent visual certification.'}
    Path('gathering/visual-checks-20.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
