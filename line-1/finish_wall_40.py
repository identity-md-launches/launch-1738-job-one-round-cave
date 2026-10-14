#!/usr/bin/env python3
"""Lay one transparent pigment motif over a bounded patch of an RGB PNG wall."""
import struct
import sys
import zlib
from pathlib import Path


def png(path):
    data = Path(path).read_bytes(); assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos, packed = 8, bytearray()
    while pos < len(data):
        n = int.from_bytes(data[pos:pos+4], 'big'); kind = data[pos+4:pos+8]
        payload = data[pos+8:pos+8+n]; assert zlib.crc32(kind + payload) == int.from_bytes(data[pos+8+n:pos+12+n], 'big')
        if kind == b'IHDR':
            width, height, depth, color, comp, filt, interlace = struct.unpack('>IIBBBBB', payload)
            assert depth == 8 and color in (2, 6) and comp == filt == interlace == 0
        elif kind == b'IDAT': packed += payload
        elif kind == b'IEND': break
        pos += n + 12
    channels = 3 if color == 2 else 4; stride = width * channels
    raw = zlib.decompress(packed); assert len(raw) == height * (stride + 1)
    previous, rows = bytearray(stride), []
    for y in range(height):
        mode = raw[y*(stride+1)]; row = bytearray(raw[y*(stride+1)+1:(y+1)*(stride+1)])
        for x in range(stride):
            a = row[x-channels] if x >= channels else 0; b = previous[x]; c = previous[x-channels] if x >= channels else 0
            if mode == 1: p = a
            elif mode == 2: p = b
            elif mode == 3: p = (a+b)//2
            elif mode == 4:
                guess = a+b-c; p = min((a,b,c), key=lambda v: abs(guess-v))
            else: p = 0
            row[x] = (row[x] + p) & 255
        rows.append(row); previous = row
    return width, height, channels, rows


def write_rgb(path, width, height, rows):
    raw = b''.join(b'\0' + bytes(row) for row in rows)
    def chunk(kind, body): return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind+body)&0xffffffff)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def main():
    ancestor, pigment, output = map(Path, sys.argv[1:4])
    aw, ah, ac, wall = png(ancestor); pw, ph, pc, art = png(pigment)
    assert (aw, ah, ac) == (1254, 1254, 3) and pc == 4
    opaque = [(x, y) for y in range(ph) for x in range(pw) if art[y][4*x+3] > 24]
    x0, x1 = min(x for x, _ in opaque), max(x for x, _ in opaque)
    y0, y1 = min(y for _, y in opaque), max(y for _, y in opaque)
    # Addition rectangle deliberately occupies unpainted upper-middle stone.
    dx, dy, dw, dh = 724, 105, 160, 100
    for oy in range(dh):
        sy = y0 + (y1-y0+1)*oy//dh
        for ox in range(dw):
            sx = x0 + (x1-x0+1)*ox//dw
            r, g, b, alpha = art[sy][4*sx:4*sx+4]
            if alpha <= 24: continue
            at = alpha / 255; offset = 3*((dy+oy)*aw + dx+ox)
            for c, value in enumerate((r, g, b)):
                wall[dy+oy][3*(dx+ox)+c] = round(wall[dy+oy][3*(dx+ox)+c]*(1-at) + value*at)
    write_rgb(output, aw, ah, wall)
    print(f'addition_box={dx},{dy},{dx+dw},{dy+dh}')


if __name__ == '__main__': main()
