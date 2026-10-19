"""Circuit Rhythm firmware SysEx <-> image (pure Python, no dependencies; MIT, from CIRCUIT-HACKS' ct_fw.py).

Same update stream as the Circuit Tracks, verified byte for byte on circuitrhythm-firmware-5706.syx:

  F0 00 20 29 00 71  01 63 00 00 | 07 03 01 (proto 0x731, 4 nibbles)  F7   UPDATE_INIT   (0x63 = Circuit Rhythm)
  F0 00 20 29 00 7C  00 | ver(6 nib) | size(8 nib) | crc32(8 nib)    F7   UPDATE_HEADER
  F0 00 20 29 00 72  <37 bytes: 32 image bytes in 7-bit groups>      F7   UPDATE_WRITE (blocks 1..N-1)
  F0 00 20 29 00 73  <37 bytes: block 0 = the vector table>          F7   UPDATE_FINISH

CRC-32/MPEG-2 over `size` image bytes; the image is linked at 0x08010000.

  python tools/rh_fw.py stock/circuitrhythm-firmware-5706-STOCK.syx [-o image.bin]   decode + check CRC and round trip
  python tools/rh_fw.py image.bin -o out.syx                                          encode
"""

from __future__ import annotations

import hashlib
from pathlib import Path

APP_BASE = 0x08010000
FLASH_END = 0x08080000
MAX_IMAGE_SIZE = FLASH_END - APP_BASE          # physical limit (the Tracks bootloader accepts this much; not verified on the Rhythm)
HDR = bytes((0xF0, 0x00, 0x20, 0x29, 0x00))
UPDATE_INIT, UPDATE_WRITE, UPDATE_FINISH, UPDATE_HEADER = 0x71, 0x72, 0x73, 0x7C
PRODUCT_RHYTHM = 0x63

STOCK_5706 = {
    "syx_sha256": "11d604a6b6bef0d41378da03718658c7fe9c959ac24e7fef6563796b9932afaf",
    "image_sha256": "d5b9ff5dadf2e284f80d69ecb7087486cf0df315a697bed8272af9de0e90df15",
    "size": 0x5A570,
    "crc": 0x9EEE802C,
    "proto_version": 0x731,
}
# version block compared by the bootloader (image offset 0x1C8, 0x26 bytes: "DR1.1.5143.5706" + zeros); our 6-byte marker goes in its zero tail
INFO_OFF, INFO_LEN = 0x1C8, 0x26
MARK_OFF = INFO_OFF + 0x20


def crc32_mpeg2(data: bytes) -> int:
    table = []
    for i in range(256):
        c = i << 24
        for _ in range(8):
            c = ((c << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if c & 0x80000000 else (c << 1) & 0xFFFFFFFF
        table.append(c)
    crc = 0xFFFFFFFF
    for b in data:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ table[((crc >> 24) ^ b) & 0xFF]
    return crc


def nibbles(value: int, count: int) -> bytes:
    return bytes((value >> (4 * (count - 1 - i))) & 0xF for i in range(count))


def from_nibbles(data: bytes) -> int:
    v = 0
    for b in data:
        if b > 0xF:
            raise ValueError("nibble out of range")
        v = (v << 4) | b
    return v


def pack_block(block: bytes) -> bytes:
    assert len(block) == 32
    bits = int.from_bytes(block, "big") << 3
    return bytes((bits >> (7 * (36 - i))) & 0x7F for i in range(37))


def unpack_block(payload: bytes) -> bytes:
    if len(payload) != 37 or any(b & 0x80 for b in payload):
        raise ValueError("bad packed block")
    bits = 0
    for b in payload:
        bits = (bits << 7) | b
    return (bits >> 3).to_bytes(32, "big")


def split(syx: bytes):
    msgs, i = [], 0
    while i < len(syx):
        s = syx.index(0xF0, i)
        e = syx.index(0xF7, s)
        raw = syx[s:e + 1]
        if not raw.startswith(HDR):
            raise ValueError(f"not a Novation message at {s}")
        msgs.append((raw[5], raw[6:-1]))
        i = e + 1
    return msgs


def decode(syx: bytes) -> dict:
    msgs = split(syx)
    cmds = [c for c, _ in msgs]
    if cmds[0] != UPDATE_INIT or cmds[1] != UPDATE_HEADER or cmds[-1] != UPDATE_FINISH:
        raise ValueError("unexpected message order")
    if any(c != UPDATE_WRITE for c in cmds[2:-1]):
        raise ValueError("unexpected message inside data stream")
    init, hdr = msgs[0][1], msgs[1][1]
    size = from_nibbles(hdr[7:15])
    crc = from_nibbles(hdr[15:23])
    blocks = [unpack_block(msgs[-1][1])] + [unpack_block(p) for _, p in msgs[2:-1]]
    image = b"".join(blocks)
    if len(image) < size:
        raise ValueError("stream shorter than header size")
    tail, image = image[size:], image[:size]
    if crc32_mpeg2(image) != crc:
        raise ValueError("CRC mismatch")
    return dict(product=init[1], proto=from_nibbles(init[2:8]), header_version=from_nibbles(hdr[1:7]), size=size, crc=crc,
                image=image, tail_all_ff=set(tail) <= {0xFF})


def encode(image: bytes, proto: int = STOCK_5706["proto_version"], product: int = PRODUCT_RHYTHM) -> bytes:
    if len(image) > MAX_IMAGE_SIZE:
        raise ValueError("image larger than physical flash")
    padded = image + b"\xFF" * (-len(image) % 32)
    blocks = [padded[i:i + 32] for i in range(0, len(padded), 32)]
    out = bytearray()
    out += HDR + bytes((UPDATE_INIT, 0x01, product, 0x00, 0x00)) + nibbles(proto, 4) + b"\xF7"
    out += HDR + bytes((UPDATE_HEADER, 0x00)) + nibbles(proto, 6) + nibbles(len(image), 8) \
        + nibbles(crc32_mpeg2(image), 8) + b"\xF7"
    for blk in blocks[1:]:
        out += HDR + bytes((UPDATE_WRITE,)) + pack_block(blk) + b"\xF7"
    out += HDR + bytes((UPDATE_FINISH,)) + pack_block(blocks[0]) + b"\xF7"
    return bytes(out)


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help=".syx (decode) or .bin (encode)")
    ap.add_argument("-o", "--output", type=Path)
    a = ap.parse_args()
    data = a.input.read_bytes()
    if a.input.suffix.lower() == ".syx":
        info = decode(data)
        print({k: (hex(v) if isinstance(v, int) else v) for k, v in info.items() if k != "image"})
        print("image sha256", sha256(info["image"]))
        print("round trip identical:", encode(info["image"], info["proto"], info["product"]) == data)
        if a.output:
            a.output.write_bytes(info["image"])
    else:
        syx = encode(data)
        print("syx sha256", sha256(syx), "size", len(syx))
        if a.output:
            a.output.write_bytes(syx)
