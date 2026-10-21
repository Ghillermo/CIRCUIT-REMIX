"""Code of ours in the Circuit Rhythm 5706's DSP core 1 (MIT), without copying its 42 KB program.

The stock (read in the firmware, tools/rhdsp.py; tests/emu_rd5.py):
  * core 1 gets the fixed 0x40-word loader 0x080662CC, then the block of 0x08031658[2] (mode 0: 0x080101F0, 0x376B words) by
    0x080310B0(block, core) (the bl at 0x08031170; it sends the block's two header words and its n words, n = bytes 1-2 of the first word);
  * the loader reads two header words, then segments {type 0 / 1 / 2 = P / X / Y, count, address, the words} until a type above 2, and jumps
    to P:$100; the stock stream ends with 0x000100 and five more 0x000100 (they reach the running program's host port: its handler takes a
    lone word as «set the address», harmless);
  * core 1's program ends at P:$D31.
Ours: the terminator and the padding words after it become segments (in place: P, 2 words at P:$D32 (the padding, never run), then P again),
so the loader goes on reading; the wrapper of the bl at 0x08031170 sends, after the stock block (mode 0 only), block A = [k, START, our k
words] (its header words are the segment's count and address) and block B = [0x030000, 0x000100] (the terminator, then one stray word, as
the stock's).  Our code starts at P:START = $D34; a stock word is changed only after its old value is checked (patch_p).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rhdsp  # noqa: E402
from thumb import Asm, b_cond, bl, cmp_reg, mov_reg, movs_imm, movt, movw, pop_list, push_list  # noqa: E402

BASE = rhdsp.BASE
UPLOAD_BL, SEND = 0x08031170, 0x080310B0
BLK1 = 0x080101F0                                     # core 1's mode 0 block (0x08031658[2])
P_END, START = 0xD32, 0xD34
TERM, TAIL_N = 0x000100, 5
TERM_B = 0x030000


def words(img, blk=BLK1):
    o = blk - BASE
    n = int.from_bytes(img[o:o + 3], "big")
    return n, [int.from_bytes(img[o + 6 + 3 * i:o + 9 + 3 * i], "big") for i in range(n)]


def parse(stream):
    """[header n, load] + words -> [(space, address, [words])] as the loader places them, and the index of the terminator"""
    out, i = [], 2
    while i < len(stream):
        t = stream[i]
        if t > 2:
            return out, i
        cnt, addr = stream[i + 1], stream[i + 2]
        out.append(("pxy"[t], addr, stream[i + 3:i + 3 + cnt]))
        i += 3 + cnt
    raise AssertionError("no terminator")


def where(img, paddr):
    """-> the image offset of P:paddr inside core 1's stock block"""
    n, ws = words(img)
    i = 0
    while i < n:
        t, cnt, addr = ws[i], ws[i + 1], ws[i + 2]
        assert t <= 2
        if t == 0 and addr <= paddr < addr + cnt:
            return BLK1 - BASE + 6 + 3 * (i + 3 + paddr - addr)
        i += 3 + cnt
    raise AssertionError(hex(paddr))


def patch_p(img, paddr, old, new):
    o = where(img, paddr)
    have = int.from_bytes(img[o:o + 3], "big")
    assert have == old, (hex(paddr), hex(have), hex(old))
    img[o:o + 3] = new.to_bytes(3, "big")


def install(img, report, base_addr, code, key):
    """code = our P words for P:START..; -> labels.  The terminator / padding patched in place, the wrapper and blocks A / B appended."""
    import rhbuild
    n, ws = words(img)
    assert struct.unpack_from("<I", img, rhdsp.TABLE + 8 - BASE)[0] == BLK1, "core 1's mode 0 block moved"
    segs, ti = parse([n, 0] + ws)
    assert ti - 2 == n - 1 - TAIL_N and ws[ti - 2:] == [TERM] * (1 + TAIL_N), [hex(w) for w in ws[-8:]]
    assert max(a + len(w) for sp, a, w in segs if sp == "p") == P_END, "core 1's program grew"
    o = BLK1 - BASE + 6 + 3 * (ti - 2)
    for k, w in enumerate((0, 2, P_END, TERM, TERM, 0)):                  # P, 2 words at $D32 (the padding), P (block A's segment)
        img[o + 3 * k:o + 3 * k + 3] = w.to_bytes(3, "big")
    assert rhbuild.bl_target(img, UPLOAD_BL) == SEND
    k = len(code)
    blk_a = b"".join(w.to_bytes(3, "big") for w in [k, START] + list(code))
    blk_b = b"".join(w.to_bytes(3, "big") for w in (TERM_B, TERM))
    def gen(at_a, at_b):
        a = Asm(base_addr)
        E = a.emit

        def imm32(rd, v):
            E(movw, rd, v & 0xFFFF)
            E(movt, rd, (v >> 16) & 0xFFFF)
        a.label("c_d1up")                                                 # (r0 = block, r1 = core): the stock's send, then ours after core 1's mode 0
        E(push_list, [4], lr=True)
        E(mov_reg, 4, 0)
        E(bl, SEND)
        imm32(0, BLK1)
        E(cmp_reg, 4, 0)
        E(b_cond, "up_x", "ne")
        for at in (at_a, at_b):
            imm32(0, at)
            E(movs_imm, 1, 1)
            E(bl, SEND)
        a.label("up_x")
        E(pop_list, [4], pc=True)
        return a.assemble()
    size = len(gen(0, 0)[0])                                              # (fixed size: imm32 is always movw + movt)
    at_a = (base_addr + size + 3) & ~3
    at_b = (at_a + len(blk_a) + 3) & ~3
    code_arm, labels = gen(at_a, at_b)
    assert (base_addr + len(code_arm) + 3) & ~3 == at_a
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_arm
    img += bytes([0xFF]) * (at_a - BASE - len(img)) + blk_a
    img += bytes([0xFF]) * (at_b - BASE - len(img)) + blk_b
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, UPLOAD_BL, f"bl #{SEND:#x}", bl(UPLOAD_BL, labels["c_d1up"]))
    report[key] = dict(labels={k_: hex(v) for k_, v in labels.items() if k_.startswith("c_")}, blk_a=hex(at_a), blk_b=hex(at_b),
                       core1_words=k, start=hex(START))
    return labels


def sent(img, report, key):
    """-> the word stream core 1 receives on a mode 0 upload of this image (stock block, then A, then B): for the tests"""
    n, ws = words(img)
    out = [n, 0] + ws
    for k in ("blk_a", "blk_b"):
        o = int(report[key][k], 16) - BASE
        cnt = int.from_bytes(img[o + 1:o + 3], "big")
        out += [int.from_bytes(img[o + 3 * i:o + 3 * i + 3], "big") for i in range(cnt + 2)]
    return out
