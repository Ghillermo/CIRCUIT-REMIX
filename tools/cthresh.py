"""The master compressor's threshold on K5 of the Sidechain view (MIT; for the Circuit Rhythm 5706).  The user (2026-10-20): «K7 / K8, K6 right
and left. -> add threshold»; «añade el umbral del compresor solo si es viable».

The stock of the Rhythm (read in core 0's DSP program, tools/rhdsp.py; checked on the device's X dump, probe/dsp0_x.bin, RD3):
  * the compressor's loop (P:$1A36 / P:$1A7B) follows the peak of the two channels (X:$1BCA, release X:$1BCB), takes a target gain from a table
    of 129 words at X:$1BD4 (index = the top 7 bits of the envelope, linear, interpolated), smooths it (X:$1BCC; attack X:$1BCD, release
    X:$1BCE) and multiplies the samples by it, x 4.  Nothing sets the threshold: the table is copied at boot from P:$1B62 + 10 (P:$1B6C, the
    stock image's 0x0801FA82, 3 bytes a word) with the 138 other words of the block; flat (0.157, -4 dB of make-up) up to an envelope of
    0.625 (-4 dBFS), then a ratio near 4:1 - the reason the compressor is so subtle;
  * the ARM writes X of core 0 with the master sender's own accessor 0x08031200(core, value << 8, address) (command 0x00, under the DSP
    service's lock; X:a = a); the program is uploaded by 0x08031110(mode) (0x080278CC mode 0 at power-up, 0x080278A8 mode 1, another program).
Ours:
  * K5 of the Sidechain view (which the stock and RH12 leave free): the threshold value 0..127 (127 = the stock's), Clear + K5 = 127; kept in the
    record's tail (rhrec "cthresh": "TH", the value, a check byte), so it is saved with the project; a project without it = 127;
  * the LED task writes the table when the value the project wants is not the one applied (rhstate "cthresh"): 16 steps (value >> 3); step 15
    = the stock's own words, read from the stock image's DSP block; steps 0..14 = our curve: the stock's flat gain up to the threshold
    T = 0.625 x 10^(-1.6 (15 - step) / 20) (-4 dBFS .. -28 dBFS), then a ratio of 4:1 (gain x (e / T)^-0.75);
  * nothing is written before the LED task has seen an upload of the mode 0 program (while the DSP is being loaded, a host write would be
    taken as program words): from then on the table is the stock's, applied = unknown, written again; after mode 1 nothing is written
    (another program) until the next mode 0 upload; if our RAM could not be set up at that upload, the threshold stays the stock's;
  * the knob's LED: white, its value as brightness (kbright's overlay).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldrb_imm, ldrb_reg, lsls_imm,  # noqa: E402
                   lsrs_imm, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list, push_list, raw, strb_imm, ldrb_w, strb_w, strh_w_imm,
                   strh_imm)
import countin as CI  # noqa: E402
import kbright as KB  # noqa: E402
import rhrec  # noqa: E402
import rhstate  # noqa: E402
import sckn as SK  # noqa: E402

CTRL = CI.CTRL
WR16 = 0x08031200                                     # (core, value << 8, address): X:a = a, under the DSP service's lock
UPLOAD = 0x08031110
UPLOAD_CALLS = {0x080278CC: 0, 0x080278A8: 1}         # the bl and the mode it uploads (movs r0, #mode just before)
TAB_X, TAB_N, TAB_P = 0x1BD4, 129, 0x1B6C              # the table in X, its words, its source in P
TAB_FLASH = 0x0801FA82                                # P:$1B6C in the stock image (core 0's block 0x0801A838 + 6 + 3 x 0x1B6C)
KNOB = 4                                              # K5
BIT_CLEAR = 23
BLK, BLK_LEN = rhrec.OFF["cthresh"]
O_ST = rhstate.OFF["cthresh"][0]                      # + 0 the value applied + 0x80 (0 = unknown), + 1 the program in core 0 (READY / BLOCKED)
MARK0, MARK1, CHECK = ord("T"), ord("H"), 0xA5
BLOCKED, READY = 0xB1, 0xA0                           # (0 = no upload seen since our RAM was set up: nothing is written)
STOCK_V = 127
STEPS, T_TOP, DB_STEP, RATIO = 16, 0.625, 1.6, 4.0
O_KB = rhstate.OFF["kbright"][0]
INV = SK.INV
assert BLK_LEN == 4


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def flash_table(img):
    """the stock's 129 words (read from the user's image: the default, never copied into our code)"""
    o = TAB_FLASH - 0x08010000
    return [int.from_bytes(img[o + 3 * i:o + 3 * i + 3], "big") for i in range(TAB_N)]


def curve(step, g0):
    """our table for a step 0..14: g0 flat up to the threshold, then RATIO:1 (24-bit fractions)"""
    t = T_TOP * 10 ** (-DB_STEP * (STEPS - 1 - step) / 20)
    out = []
    for i in range(TAB_N):
        e = i / 128
        g = g0 if e <= t else g0 * (e / t) ** (1 / RATIO - 1)
        out.append(max(0, min(0x7FFFFF, round(g * (1 << 23)))))
    return out


def tables(g0):
    """steps 0..14 as the words 0x08031200 takes (value << 8, little-endian): not the DSP's 3-byte format (the flat part of a table in that
    format repeats the Tracks image's own compressor table, which provenance() refuses)"""
    return b"".join((w << 8).to_bytes(4, "little") for s in range(STEPS - 1) for w in curve(s, g0))


def arm_code(base, L, prev, g0):
    a = Asm(base)
    E = a.emit
    zc = [0]

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_h{zc[0]}"
        E(b_cond, n, INV[cond])
        E(b, target)
        a.label(n)
    t_tabs = base
    E(raw, tables(g0))

    # ---- c_thblk() -> r0 = our block in the record's tail, 0 without a record; clobbers r1, r2
    a.label("c_thblk")
    E(push_list, [3], lr=True)
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "bk_x", "eq")
    imm32(1, BLK)
    E(adds_reg, 0, 0, 1)
    a.label("bk_x")
    E(pop_list, [3], pc=True)

    # ---- c_thval() -> r0 = the project's value (its block's, else 127); clobbers r1-r3
    a.label("c_thval")
    E(push_list, [4], lr=True)
    E(bl, "c_thblk")
    E(movs_imm, 4, STOCK_V)
    E(cmp_imm, 0, 0)
    E(b_cond, "tv_x", "eq")
    E(ldrb_imm, 1, 0, 0)
    E(cmp_imm, 1, MARK0)
    E(b_cond, "tv_x", "ne")
    E(ldrb_imm, 1, 0, 1)
    E(cmp_imm, 1, MARK1)
    E(b_cond, "tv_x", "ne")
    E(ldrb_imm, 2, 0, 2)
    E(cmp_imm, 2, 0x7F)
    E(b_cond, "tv_x", "hi")
    E(ldrb_imm, 1, 0, 3)
    E(movs_imm, 3, CHECK)
    E(eors_reg, 3, 2)
    E(cmp_reg, 1, 3)
    E(b_cond, "tv_x", "ne")
    E(mov_reg, 4, 2)
    a.label("tv_x")
    E(mov_reg, 0, 4)
    E(pop_list, [4], pc=True)

    # ---- c_thwrite(r0 = value): the table of its step into X of core 0 (129 words); clobbers r0-r3, r12
    a.label("c_thwrite")
    E(push_list, [4, 5, 6], lr=True)
    E(lsrs_imm, 0, 0, 3)
    imm32(4, TAB_FLASH)
    E(movs_imm, 6, 0)                                                     # r6 = 0: the stock's words in flash (3 bytes, big-endian)
    E(cmp_imm, 0, STEPS - 1)
    E(b_cond, "tw_g", "hs")                                               # step 15: the stock's
    E(movw, 1, 4 * TAB_N)
    E(muls, 0, 1)
    imm32(4, t_tabs)
    E(adds_reg, 4, 4, 0)                                                  # r4 = the step's words (value << 8)
    E(movs_imm, 6, 1)
    a.label("tw_g")
    E(movs_imm, 5, 0)                                                     # r5 = the word
    a.label("tw_l")
    E(cmp_imm, 6, 0)
    E(b_cond, "tw_s", "eq")
    E(ldr_imm, 1, 4, 0)
    E(adds_imm8, 4, 4)
    E(b, "tw_w")
    a.label("tw_s")
    E(ldrb_imm, 1, 4, 0)
    E(lsls_imm, 1, 1, 24)
    E(ldrb_imm, 2, 4, 1)
    E(lsls_imm, 2, 2, 16)
    E(orrs_reg, 1, 2)
    E(ldrb_imm, 2, 4, 2)
    E(lsls_imm, 2, 2, 8)
    E(orrs_reg, 1, 2)                                                     # r1 = the word << 8
    E(adds_imm8, 4, 3)
    a.label("tw_w")
    E(movw, 2, TAB_X)
    E(adds_reg, 2, 2, 5)                                                  # r2 = X:$1BD4 + i
    E(movs_imm, 0, 0)                                                     # core 0
    E(bl, WR16)
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, TAB_N)
    E(b_cond, "tw_l", "lo")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_thknob (the container's slot 4: view, knob, delta): K5 in the Sidechain view = the threshold
    a.label("c_thknob")
    E(cmp_imm, 1, KNOB)
    bc("tk_f", "ne")
    E(push_list, [0, 1, 2, 4, 5, 6], lr=True)
    imm32(3, SK.O_MODE)
    E(raw, h(0x5CC3))                                                     # ldrb r3, [r0, r3]
    E(cmp_imm, 3, SK.MODE_SC)
    bc("tk_p", "ne")
    E(mov_reg, 5, 2)                                                      # r5 = the turn
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("tk_p", "eq")
    E(bl, "c_thblk")
    E(cmp_imm, 0, 0)
    bc("tk_p", "eq")
    E(mov_reg, 6, 0)                                                      # r6 = our block
    imm32(0, CTRL)
    E(raw, h(0xF8D0) + h(0x10A0))                                         # ldr.w r1, [r0, #0xa0]: the held buttons
    E(movs_imm, 4, STOCK_V)
    E(lsls_imm, 1, 1, 31 - BIT_CLEAR)
    E(b_cond, "tk_w", "mi")                                               # Clear held: the stock's
    E(bl, "c_thval")
    E(adds_reg, 4, 0, 5)
    E(cmp_imm, 4, 0)
    E(b_cond, "tk_hi", "ge")
    E(movs_imm, 4, 0)
    a.label("tk_hi")
    E(cmp_imm, 4, 0x7F)
    E(b_cond, "tk_w", "le")
    E(movs_imm, 4, 0x7F)
    a.label("tk_w")
    E(movs_imm, 0, MARK0)
    E(strb_imm, 0, 6, 0)
    E(movs_imm, 0, MARK1)
    E(strb_imm, 0, 6, 1)
    E(strb_imm, 4, 6, 2)
    E(movs_imm, 0, CHECK)
    E(eors_reg, 0, 4)
    E(strb_imm, 0, 6, 3)
    E(raw, h(0xB003))                                                     # add sp, #12
    E(pop_list, [4, 5, 6], pc=True)
    a.label("tk_p")
    E(raw, popw([0, 1, 2, 4, 5, 6], lr=True))
    a.label("tk_f")
    E(b_w, prev["knob"])

    # ---- c_thled (the LED task's calls: ctrl, frame): the chain; the table when the project wants another; K5's LED in the Sidechain view
    a.label("c_thled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the frame
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("tl_x", "eq")
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    bc("tl_x", "eq")
    E(mov_reg, 6, 0)                                                      # r6 = our RAM
    E(bl, "c_thval")
    E(mov_reg, 4, 0)                                                      # r4 = the value wanted
    E(ldrb_w, 0, 6, O_ST + 1)
    E(cmp_imm, 0, READY)
    E(b_cond, "tl_v", "ne")
    E(movs_imm, 0, 0x80)
    E(orrs_reg, 0, 4)
    E(ldrb_w, 1, 6, O_ST)
    E(cmp_reg, 0, 1)
    E(b_cond, "tl_v", "eq")
    E(strb_w, 0, 6, O_ST)
    E(mov_reg, 0, 4)
    E(bl, "c_thwrite")
    a.label("tl_v")
    imm32(0, CTRL)
    E(ldr_imm, 1, 0, 0x7C)
    imm32(0, SK.CONT)
    E(cmp_reg, 0, 1)
    bc("tl_x", "ne")
    imm32(1, SK.O_MODE)
    E(raw, h(0x5C41))                                                     # ldrb r1, [r0, r1]
    E(cmp_imm, 1, SK.MODE_SC)
    bc("tl_x", "ne")
    imm32(0, SK.COL_WHITE)
    E(strh_w_imm, 0, 5, 2 * (SK.LED_KNOB0 + KNOB))
    E(mov_reg, 7, 6)
    E(adds_imm8, 7, O_KB)                                                 # kbright's overlay: K5 = the value, white
    E(ldrb_imm, 1, 7, KB.K_MASK)
    E(movs_imm, 2, 1 << KNOB)
    E(orrs_reg, 1, 2)
    E(strb_imm, 1, 7, KB.K_MASK)
    E(strb_imm, 4, 7, KB.K_VAL + KNOB)
    E(strh_imm, 0, 7, KB.K_CODE + 2 * KNOB)
    a.label("tl_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_thup0 / c_thup1 (in place of the two upload calls: r0 = the mode): the upload, then mode 0 = the table to write again, mode 1 = none
    for mode in (0, 1):
        a.label(f"c_thup{mode}")
        E(push_list, [4], lr=True)
        E(bl, UPLOAD)
        E(mov_reg, 4, 0)                                                  # (its result kept)
        E(bl, L["c_rst"])
        E(cmp_imm, 0, 0)
        E(b_cond, f"tu{mode}_x", "eq")
        E(movs_imm, 1, READY if mode == 0 else BLOCKED)
        E(strb_w, 1, 0, O_ST + 1)
        if mode == 0:
            E(movs_imm, 1, 0)
            E(strb_w, 1, 0, O_ST)                                         # applied = unknown
        a.label(f"tu{mode}_x")
        E(mov_reg, 0, 4)
        E(pop_list, [4], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; slot 4 of the track views' container (in front of clrknob's / sckn's), the LED task calls, the two program uploads."""
    import struct
    import rhbuild
    import rhdsp
    BASE = rhbuild.BASE
    blk, n, load, _ = rhdsp.block(bytes(img), 0, 0)
    assert blk + 6 + 3 * (TAB_P - load) == TAB_FLASH and n > TAB_P + TAB_N, "core 0's block moved"
    g0 = flash_table(img)[0] / (1 << 23)
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]
    lab = lambda m, k: int(report[m]["labels"][k], 16)
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rrt=lab("rhrec", "c_rrt"), c_ciok=lab("countin", "c_ciok"))
    assert "kbright" in report, "cthresh draws through kbright's overlay"
    for c, mode in UPLOAD_CALLS.items():
        assert rhbuild.bl_target(img, c) == UPLOAD, hex(c)
        assert bytes(img[c - 2 - BASE:c - BASE]) == bytes([mode, 0x20]), hex(c)          # movs r0, #mode
    prev = dict(knob=u(SK.SLOT_KNOB) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code, labels = arm_code(base_addr, L, prev, g0)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, SK.SLOT_KNOB, prev["knob"] | 1, labels["c_thknob"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_thled"]))
    for c, mode in UPLOAD_CALLS.items():
        rhbuild.patch(img, c, f"bl #{UPLOAD:#x}", bl(c, labels[f"c_thup{mode}"]))
    report["cthresh"] = dict(prev={k: hex(v) for k, v in prev.items()}, g0=g0, tables=hex(base_addr),
                             labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
