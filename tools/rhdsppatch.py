"""Patch the Circuit Rhythm 5706's DSP programs inside the ARM image (MIT; the method of CIRCUIT-HACKS' SC16 relocate_dsp, for the Rhythm).

The ARM uploads core 0 at every power-on: first the stock's 8-word stub 0x08031638 (OMR: MS = 1, bit 22 = 1, bit 21 = 0, then the bootstrap,
the same stub as the Tracks': 16K words of program RAM), then the block the table 0x08031658[0] points to (word count, load address 0, the
words; sent in pieces of 0xAA words by 0x080310B0).  Core 0's stock program is 0x1FED words at P:$0, so P:$1FED..$3FFF is ours.

    relocate(img, extra)        copy core 0's block (with any patches made to it) + our words to the end of the image, point the table at it
    patch(words, addr, old, new)  change program words, checking the stock's words first
    asm(lines)                  assemble with dsptool (../CIRCUIT-HACKS/ext/bin or $DSPTOOL), cached in tools/rhdsp_asm_cache.json so a
                                build needs no dsptool once the cache holds its lines
    jmp / jsr / jcc (long forms; dsptool's asm only takes the short ones)

Notes for writing the code: dsptool prints bit numbers in hex (`bclr #$15,x:$12` = bit 21), absolute moves need `x:>$addr`, and nothing of
the stock DSP program is copied: the block is the user's own stock image's, patched in place.
"""
from __future__ import annotations

import atexit
import json
import os
import struct
import subprocess
from pathlib import Path

import rhdsp

BASE, TABLE = rhdsp.BASE, rhdsp.TABLE
STUB0 = 0x08031638
CORE0_WORDS, P_END = 0x1FED, 0x4000
CC = dict(cc=0, hs=0, ge=1, ne=2, pl=3, nn=4, ec=5, lc=6, gt=7, cs=8, lo=8, lt=9, eq=0xA, mi=0xB, nr=0xC, es=0xD, ls=0xE, le=0xF)
CACHE = Path(__file__).resolve().parent / "rhdsp_asm_cache.json"
_cache: dict[str, list[int]] = {}
_new = False
try:
    _cache.update(json.loads(CACHE.read_text()))
except (OSError, ValueError):
    pass


def jmp(a): return [0x0AF080, a & 0xFFFFFF]
def jsr(a): return [0x0BF080, a & 0xFFFFFF]
def jcc(cond, a): return [0x0AF0A0 | CC[cond], a & 0xFFFFFF]
def jscc(cond, a): return [0x0BF0A0 | CC[cond], a & 0xFFFFFF]


def asm(lines):
    """-> the words of the lines, in order (one list)."""
    global _new
    todo = [l for l in dict.fromkeys(lines) if l not in _cache]
    if todo:
        out = subprocess.run([rhdsp.TOOL, "asm"], input="\n".join(todo) + "\n", capture_output=True, text=True).stdout.splitlines()
        assert len(out) == len(todo), "dsptool did not answer every line"
        for l, o in zip(todo, out):
            p = o.split()
            assert p and p[0] != "ERR", (l, o)
            _cache[l] = [int(x, 16) for x in p[1:]]
        _new = True
    return [w for l in lines for w in _cache[l]]


@atexit.register
def _save():
    if _new:
        CACHE.write_text(json.dumps(_cache, indent=0, sort_keys=True))


def core0(img):
    """-> (block address, [program words]) as the table points now."""
    a = struct.unpack_from("<I", img, TABLE - BASE)[0]
    o = a - BASE
    n, load = int.from_bytes(img[o:o + 3], "big"), int.from_bytes(img[o + 3:o + 6], "big")
    assert load == 0
    return a, [int.from_bytes(img[o + 6 + 3 * i:o + 9 + 3 * i], "big") for i in range(n)]


def stock_checks(img):
    """The stock's own stub and block, as this module expects them."""
    o = STUB0 - BASE
    stub = [int.from_bytes(img[o + 6 + 3 * i:o + 9 + 3 * i], "big") for i in range(8)]
    assert int.from_bytes(img[o:o + 3], "big") == 8 and stub[:5] == [0x0444BA, 0x0AC467, 0x0AC476, 0x0AC455, 0x04C4BA], stub
    a, ws = core0(img)
    assert len(ws) == CORE0_WORDS, hex(len(ws))
    return a, ws


def patch(words, addr, old, new):
    assert len(old) == len(new), (old, new)
    have = words[addr:addr + len(old)]
    assert have == old, (hex(addr), [hex(x) for x in have], [hex(x) for x in old])
    words[addr:addr + len(new)] = new


def relocate(img: bytearray, words, extra):
    """Write [words] + [extra] as a new core 0 block at the end of the image; point the table at it.  -> (block address, total words)."""
    total = len(words) + len(extra)
    assert total <= P_END, hex(total)
    blk = total.to_bytes(3, "big") + b"\0\0\0" + b"".join((w & 0xFFFFFF).to_bytes(3, "big") for w in list(words) + list(extra))
    at = (len(img) + BASE + 3) & ~3
    img += b"\xFF" * (at - BASE - len(img)) + blk
    while len(img) % 4:
        img += b"\xFF"
    struct.pack_into("<I", img, TABLE - BASE, at)
    return at, total
