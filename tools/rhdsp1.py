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
        if t == 0 and addr <= 0x3C < addr + cnt and stream[i - cnt + 0x3C - addr] == LAND_JMP:
            return out, i                                 # (RD17 on) the landing: the loader's loop ends at the new P:$3C = jmp $100
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


LOADER = 0x080662CC                                   # core 1's 0x40-word loader: a block [0x40, 0, P:$0 .. $3F]
LAND_A, LAND_END = 0x02, 0x46                         # (landing) the final segment P:$2..$45
LAND_STORE, LAND_JMP, HOST_VEC = 0x075F84, 0x0C0100, 0x0D06D0
LAND_FREE = [*range(0x06, 0x0A), *range(0x0C, 0x38), *range(0x3D, 0x40)]      # ours: 51 words (docs/PORTADO.md «RD17»)


def loader_words(img):
    o = LOADER - BASE
    w = [int.from_bytes(img[o + 3 * i:o + 3 * i + 3], "big") for i in range(0x42)]
    assert w[:2] == [0x40, 0], "core 1's loader moved"
    return w[2:]


def landing_words(img, ours):
    """-> the 68 words of the landing segment P:$2..$45: the loader's own words where it may still run or a vector could fire ($2..$5 as the
    loader left them, $A / $B nops), its loop body $38..$3A unchanged, $3B = the P store as it is while P segments load (the image holds the X
    store: written there, the rest of the segment would go to X and core 1 would be dead at boot), $3C = jmp $100 (where the loop goes when
    the segment ends: the landing), $44 = the host vector as the stock's; `ours` = {address: word} only in LAND_FREE; the rest 0 (nop)"""
    ld = loader_words(img)
    assert ld[0x3D] == LAND_STORE and ld[0x3C] == 0x050FCA, "the loader's P store / bra $26 not where expected"
    fin = {a: 0 for a in range(LAND_A, LAND_END)}
    for a in range(0x02, 0x06):
        fin[a] = ld[a]
    for a in (0x38, 0x39, 0x3A):
        fin[a] = ld[a]
    fin[0x3B], fin[0x3C], fin[0x44] = LAND_STORE, LAND_JMP, HOST_VEC
    for a, w in ours.items():
        assert a in LAND_FREE, hex(a)
        fin[a] = w
    return [fin[a] for a in range(LAND_A, LAND_END)]


def install(img, report, base_addr, code, key, low=None, landing=None):
    """code = our P words for P:START..; -> labels.  The terminator / padding patched in place, the wrapper and blocks A / B appended.
    low (RD13 on) = (address, words, index of the count word): a second P segment in the unused vectors (tools/wsola.py), sent between A and
    B as three blocks, the sender's own rule (a block = its two header words + the low 16 bits of its first word of words):
    [0, k] (the segment's type and count), [address, w0 .. w_address], [w_cw, w_cw+1, the rest] with w_cw = k - address - 3.
    landing (RD17 on, with low) = {address: word} in P:$2..$45 (LAND_FREE): a last P segment P:$2..$45 appended to the third low block (its
    count word grows by 3 + 68), block B dropped: the loader's loop ends at the new P:$3C = jmp $100 (docs/PORTADO.md «RD17»)."""
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
    pack = lambda ws: b"".join(w.to_bytes(3, "big") for w in ws)                # noqa: E731
    blks = [blk_a]
    if low:
        la, lw, ci = low
        assert ci == la + 1 and lw[ci] == len(lw) - la - 3 and la > 0x44, "the count word"
        third = lw[ci:]
        if landing is not None:
            lw = list(lw)
            seg = [0, LAND_END - LAND_A, LAND_A] + landing_words(img, landing)
            lw[ci] += len(seg)                                            # (P:$8D, a data word: the third block's length)
            third = lw[ci:] + seg
        blks += [pack([0, len(low[1])]), pack([la] + lw[:ci]), pack(third)]
    if landing is None:
        blks.append(blk_b)

    def gen(ats):
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
        for at in ats:
            imm32(0, at)
            E(movs_imm, 1, 1)
            E(bl, SEND)
        a.label("up_x")
        E(pop_list, [4], pc=True)
        return a.assemble()
    size = len(gen([0] * len(blks))[0])                                   # (fixed size: imm32 is always movw + movt)
    ats, at = [], (base_addr + size + 3) & ~3
    for blk in blks:
        ats.append(at)
        at = (at + len(blk) + 3) & ~3
    code_arm, labels = gen(ats)
    assert (base_addr + len(code_arm) + 3) & ~3 == ats[0]
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_arm
    for at, blk in zip(ats, blks):
        img += bytes([0xFF]) * (at - BASE - len(img)) + blk
    at_a, at_b = ats[0], ats[-1]
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, UPLOAD_BL, f"bl #{SEND:#x}", bl(UPLOAD_BL, labels["c_d1up"]))
    report[key] = dict(labels={k_: hex(v) for k_, v in labels.items() if k_.startswith("c_")}, blk_a=hex(at_a), blk_b=hex(at_b),
                       core1_words=k, start=hex(START))
    if low:
        report[key].update(blocks=[hex(a) for a in ats], low=hex(low[0]), low_words=len(low[1]), landing=landing is not None)
    return labels


def sent(img, report, key):
    """-> the word stream core 1 receives on a mode 0 upload of this image (stock block, then A, then B): for the tests"""
    n, ws = words(img)
    out = [n, 0] + ws
    for at in report[key].get("blocks") or [report[key][k] for k in ("blk_a", "blk_b")]:
        o = int(at, 16) - BASE
        cnt = int.from_bytes(img[o + 1:o + 3], "big")
        out += [int.from_bytes(img[o + 3 * i:o + 3 * i + 3], "big") for i in range(cnt + 2)]
    return out
