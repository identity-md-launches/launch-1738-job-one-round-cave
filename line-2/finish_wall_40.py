#!/usr/bin/env python3
"""Add one in-memory transparent pigment mark to the verified Pepe 39 wall."""

import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import termios

import finish_wall_26 as imageops

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA256 = '768e2cdf01cfd8edd9b47e2d71b15517c7a0a8fa4a90d47c461620974d91dd37'
PLACEMENT = (690, 478, 170, 28)


def main():
    source = (ROOT / 'artifacts/line-2/wall.png').read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('refusing a wall other than verified record 39')
    width, height, channels, old = imageops.decode(source)
    if (width, height, channels) != (1254, 1254, 3):
        raise ValueError('unexpected inherited PNG format')
    if sys.argv[1:] == ['--terminal-base64']:
        original = termios.tcgetattr(0)
        raw = termios.tcgetattr(0)
        raw[3] &= ~(termios.ECHO | termios.ICANON)
        termios.tcsetattr(0, termios.TCSANOW, raw)
        print('ready for in-memory insert', flush=True)
        try:
            encoded = sys.stdin.buffer.readline(4_000_001)
            if len(encoded) > 4_000_000 or not encoded.endswith(b'\n'):
                raise ValueError('insert transport too large or unterminated')
            insert = base64.b64decode(encoded.strip(), validate=True)
        finally:
            termios.tcsetattr(0, termios.TCSANOW, original)
    elif not sys.argv[1:]:
        insert = sys.stdin.buffer.read(3_000_001)
        if len(insert) > 3_000_000:
            raise ValueError('insert too large')
    else:
        raise ValueError('unknown arguments')
    mw, mh, mark_channels, markrows = imageops.decode(insert)
    if mark_channels != 4 or mw < 1700:
        raise ValueError('unexpected transparent insert geometry')
    def crop_mark(left, right):
        return right-left, mh, 4, [row[4*left:4*right] for row in markrows]
    imageops.PLACE_X, imageops.PLACE_Y, imageops.PLACE_W, imageops.PLACE_H = (690, 478, 65, 28)
    result, left_bounds = imageops.composite(old, crop_mark(0, 650))
    imageops.PLACE_X, imageops.PLACE_Y, imageops.PLACE_W, imageops.PLACE_H = (795, 478, 65, 28)
    result, right_bounds = imageops.composite(result, crop_mark(mw-650, mw))
    x, y, w, h = PLACEMENT
    for sy, (a, b) in enumerate(zip(old, result)):
        if not y <= sy < y+h:
            assert a == b
        else:
            assert a[:3*x] == b[:3*x] and a[3*(x+w):] == b[3*(x+w):]
    png = imageops.encode(width, height, result)
    artifact_dir = ROOT / 'artifacts/line-2'
    for filename in ('wall.png', 'wall-v20.png'):
        (artifact_dir / filename).write_bytes(png)
    spec = importlib.util.spec_from_file_location('thumbnail', ROOT / 'shared/wall-thumbnail/thumbnail.py')
    thumbnail = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(thumbnail)
    jpeg = thumbnail.jpeg(thumbnail.resize(width, height, result, 512))
    if len(jpeg) > 100_000:
        raise ValueError('JPEG exceeds 100 KB delivery limit')
    (ROOT / 'dist/line-2/40.jpg').write_bytes(jpeg)
    digest = hashlib.sha256(png).hexdigest()
    record = {
        'name': 'The Missing Trail',
        'image': 'https://api.imd.fun/artifacts/' + digest,
        'attributes': [
            {'trait_type': 'Cave', 'value': 'Moss'},
            {'trait_type': 'Wall', 'value': 'Line 2'},
            {'trait_type': 'Number', 'value': 40},
            {'trait_type': 'Left behind', 'value': 'Approval Coverage Map'},
            {'trait_type': 'Meaning', 'value': 'Two ochre trails expose the unpainted span where approvals may hide.'},
            {'trait_type': 'One thing', 'value': 'ERC-20 spending-permission audits'},
        ],
    }
    (ROOT / 'dist/line-2/40.json').write_text(json.dumps(record, indent=2) + '\n')
    changed = sum(a[i:i+3] != b[i:i+3] for a, b in zip(old, result)
                  for i in range(0, len(a), 3))
    checks = {
        'source_sha256': SOURCE_SHA256,
        'output_sha256': digest,
        'dimensions': [width, height],
        'format': 'PNG',
        'channels': '8-bit RGB',
        'placement': list(PLACEMENT),
        'insert_alpha_bounds': [left_bounds, right_bounds],
        'changed_pixels': changed,
        'outside_placement_unchanged': True,
        'preview': {'format': 'JPEG', 'dimensions': [512, 512], 'bytes': len(jpeg)},
        'unmet_visual_requirements': [],
        'visual_review': 'Pending inspection of final wall and JPEG.',
    }
    (ROOT / 'line-2/visual-checks-40.json').write_text(json.dumps(checks, indent=2) + '\n')
    print(json.dumps(checks), flush=True)


if __name__ == '__main__':
    main()
