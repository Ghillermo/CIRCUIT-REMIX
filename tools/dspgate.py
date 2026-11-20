"""Our DSP writes stay out of a PCM upload (MIT; RH66; the check came from llcoolkm's Arrhythmia, reimplemented here for our code).

The stock (read in its image): a PCM upload, 0x08053E8C(slot) (pack load, sample load) and the SysEx one 0x080536D2, puts core 0's host port in bulk
mode with 0x0803153C(core) and leaves it with 0x0803157E(core), every 4 096 words.  Between the two it sends 2 KB pieces with 0x08031608 and reads the
next piece from the card with 0x0804603A, a job for the storage task the uploader waits for while the other tasks run.  None of this takes the DSP
service's lock (0x08029C8C on 0x20003688), and core 0's chip select stays low across the card read (it goes up at 0x0805402C, after the read).
A host write in that window goes into the PCM stream: three or four words of the sample replaced, the rest of the piece one frame off.  It does not
matter which core the write is for, with core 0 still selected.  The bulk read 0x08031430 holds the lock: nothing to do there.

Our LED-task writers (stockplus, granpage, linein, synthpage, envpage, spall, modmx's sinks, cthresh) send a few words every frame, so they would
hit that window on every pack load.  Ours:
  * the heads of 0x0803153C / 0x0803157E set and clear a byte in our RAM;
  * the heads of the writers 0x08031200 / 0x08031228: called from our code (LR past the stock image) in a bulk interval, the write is dropped; a stock
    caller goes on, as ever.  The dropped senders are the round-robin ones, which send the same words again, and cthresh's table, marked unknown here so
    the LED task writes it again.  stereorec's job words (a recording's end) have no second sending: a recording and an upload at once are not expected;
  * OPT sdbulk: sdyield does not yield inside a bulk interval (the stock's spin on the card), so it adds no new window for the stock's own writers.
RAM: rhstate OFF2 "dspgate": + 0 in an interval, + 4 intervals, + 8 our writes dropped (read them with rhprobe gate: 0 dropped after a load = the
window never opened for our writers on this unit).  The address is written without c_rst: those bytes are never allocated, and c_rst zeroes them.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import Asm, adds_imm8, b_cond, b_w, cmp_imm, h, ldr_imm, ldrb_imm, movs_imm, movt, movw, mov_reg, push_list, raw, str_imm, strb_imm  # noqa: E402
import cthresh as TH  # noqa: E402
import rhstate  # noqa: E402

ENTER, LEAVE = 0x0803153C, 0x0803157E                  # (core)
BULK_HEAD = "push {r3, r4, r5, lr}|mov r4, r0"
W16, W16_HEAD = 0x08031200, "push {r2, r3, r4, r5, r6, lr}|mov r4, r0"
W24, W24_HEAD = 0x08031228, "push {r3, r4, r5, r6, r7, lr}|mov r5, r1"
O = rhstate.OFF2["dspgate"][0]
BLOCK = rhstate.ST2 + O
R_IN, R_N, R_DROP = 0, 4, 8
TH_APPLIED = rhstate.ST + TH.O_ST


def arm_code(base, ours):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_dgon / c_dgoff (the heads of 0x0803153C / 0x0803157E: r0 = the core; r1, r2 are free in both)
    a.label("c_dgon")
    imm32(1, BLOCK)
    E(movs_imm, 2, 1)
    E(strb_imm, 2, 1, R_IN)
    E(ldr_imm, 2, 1, R_N)
    E(adds_imm8, 2, 1)
    E(str_imm, 2, 1, R_N)
    E(push_list, [3, 4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(b_w, ENTER + 4)
    a.label("c_dgoff")
    imm32(1, BLOCK)
    E(movs_imm, 2, 0)
    E(strb_imm, 2, 1, R_IN)
    E(push_list, [3, 4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(b_w, LEAVE + 4)

    # ---- c_dgw16 / c_dgw24 (the heads of 0x08031200 / 0x08031228: r0-r2 = their arguments, r3 free)
    for name, regs, rm, cont in (("16", [2, 3, 4, 5, 6], (4, 0), W16 + 4), ("24", [3, 4, 5, 6, 7], (5, 1), W24 + 4)):
        a.label(f"c_dgw{name}")
        imm32(3, ours)
        E(raw, h(0x459E))                                                 # cmp lr, r3
        E(b_cond, f"dg_s{name}", "lo")                                    # a stock caller
        imm32(3, BLOCK)
        E(ldrb_imm, 3, 3, R_IN)
        E(cmp_imm, 3, 0)
        E(b_cond, f"dg_s{name}", "eq")
        imm32(3, BLOCK)
        E(ldr_imm, 1, 3, R_DROP)
        E(adds_imm8, 1, 1)
        E(str_imm, 1, 3, R_DROP)
        imm32(3, TH_APPLIED)
        E(movs_imm, 1, 0)
        E(strb_imm, 1, 3, 0)                                              # cthresh's table: to write again
        E(raw, h(0x4770))                                                 # bx lr
        a.label(f"dg_s{name}")
        E(push_list, regs, lr=True)
        E(mov_reg, *rm)
        E(b_w, cont)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the heads of the bulk mode's two functions and of the two writers."""
    import rhbuild
    from thumb import b_w as bw
    BASE = rhbuild.BASE
    code, labels = arm_code(base_addr, BASE + len(rhbuild.load_stock()))
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    for site, head, lb in ((ENTER, BULK_HEAD, "c_dgon"), (LEAVE, BULK_HEAD, "c_dgoff"), (W16, W16_HEAD, "c_dgw16"), (W24, W24_HEAD, "c_dgw24")):
        rhbuild.patch(img, site, head, bw(site, labels[lb]))
    report["dspgate"] = dict(block=hex(BLOCK), labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
