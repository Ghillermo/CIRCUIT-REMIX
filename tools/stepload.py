"""A faster step load in the track's pattern-index listener (MIT; Circuit Rhythm 5706): the same result, a quarter of the calls.

0x08048932(track) loads the current pattern's 32 steps (8 bytes each at [track + 4] + pattern x 0xA28) into the step stores [track + 0x1C]
and [track + 0x20]: per step, 7 setters 0x080549B0-0x08054AB0 each write one byte lane (step & 3) of word (step >> 2) + an offset through
the store's write pointer 0x0803FD26 (first use of a word: copies its active value to the other buffer and marks it written).  Every
lane of every touched word is written, so building each word from its 4 steps and writing it once through the same write pointer leaves
the same buffers and written marks (56 calls instead of 224).  It runs 3 times a track on each Play.
c_stload takes the loop's place (b.w at 0x08048950, before the loop's first instruction); r4 = track, r6 = the pattern's steps, as the
stock leaves them; it goes on at 0x080489A2, which needs only r4, r6 and r8.  r5 and r7 are free there (restored by the function's pop).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from thumb import Asm, adds_imm8, adds_reg, b_cond, b_w, bl, cmp_imm, ldr_imm, ldrb_imm, lsls_imm, mov_reg, movs_imm, orrs_reg, str_imm  # noqa: E402

SITE, AFTER, WPTR = 0x08048950, 0x080489A2, 0x0803FD26
SITE_OLD = "mov r5, r6|ldrb r2, [r5, #3]"
# (store's offset in the track, word offset, the step's byte): the setters in the stock loop's order
FIELDS = ((0x1C, 0x00, 3), (0x1C, 0x10, 2), (0x1C, 0x08, 4), (0x1C, 0x18, 5), (0x20, 0x00, 0), (0x20, 0x08, 1), (0x20, 0x10, 6))


def arm_code(base):
    a = Asm(base)
    E = a.emit
    a.label("c_stload")
    for k, (store, woff, byte) in enumerate(FIELDS):
        E(movs_imm, 7, 0)                              # r7 = word 0-7 of this field
        a.label(f"sl_{k}")
        E(lsls_imm, 5, 7, 5)
        E(adds_reg, 5, 5, 6)                           # r5 = steps 4w .. 4w + 3
        E(ldrb_imm, 0, 5, byte)
        for lane in (1, 2, 3):
            E(ldrb_imm, 1, 5, byte + 8 * lane)
            E(lsls_imm, 1, 1, 8 * lane)
            E(orrs_reg, 0, 1)
        E(mov_reg, 5, 0)
        E(ldr_imm, 0, 4, store)
        E(mov_reg, 1, 7)
        if woff:
            E(adds_imm8, 1, woff)
        E(bl, WPTR)                                    # keeps r4-r7
        E(str_imm, 5, 0, 0)
        E(adds_imm8, 7, 1)
        E(cmp_imm, 7, 8)
        E(b_cond, f"sl_{k}", "lo")
    E(b_w, AFTER)
    return a.assemble()


def install(img, report, base_addr):
    import rh_fw
    import rhbuild
    code, labels = arm_code(base_addr)
    img += bytes([0xFF]) * (base_addr - rh_fw.APP_BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, SITE, SITE_OLD, b_w(SITE, labels["c_stload"]))
    report["stepload"] = dict(labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
