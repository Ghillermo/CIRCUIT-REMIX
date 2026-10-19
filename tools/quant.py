"""Shift + Play = the pattern of the selected track, quantized to its steps (MIT; CIRCUIT-HACKS' quant of SC43.7, «Shift+play: quantize current
pattern», moved to the Circuit Rhythm 5706: only its drum part, the Rhythm's eight tracks are all sample tracks).

The stock of the Rhythm (read in the firmware and on the RAM dump, emulated):
  * Shift + Play = Play (as the Tracks); button 17 = Play, LED 49 = Play (it lights when the transport runs);
  * the selected track = p0 of the store [0x20048B9C + 0x25C] (the active container, vtable 0x080678DC; the track buttons 0-7 set it);
  * a track's pattern: 8 patterns of 0xA28 B from [listener + 4]; 32 steps of 8 B: + 0 the note of the hit, + 1 its gate (micro steps), + 2 the
    micro step mask (bit k = micro step k, 0..5: the sixths of a step), + 3 velocity (0 = no hit), + 4 probability (7 = always), + 5 sample flip
    (0xFF = none), + 6 bit 0 tie; the settings at + 0x100 (+ 0 the last step, + 1 the first), the automation lanes at + 0x128;
    an empty step as the stock leaves it: 00 06 00 00 07 FF 00 00 (the drum player's slots 1 / 2, 0x0804AEEE / 0x0804AFBC, read it);
  * like the Tracks' drums (drumstore.py of CIRCUIT-HACKS) each track has an edit copy of its pattern's steps in two parameter stores, and every
    stock edit writes them whole into the pattern (their listener 0x08048208, class 0x080696A0): the probability view of track t (0x2004C7B8 +
    0x40 t, vtable 0x08067E6C) -> [view + 0xC] = ctx; ST1 = [ctx] (32 words of 4 steps: 0-7 velocity, 8-15 probability, 16-23 micro steps,
    24-31 sample flip; [ST1 + 0x18] = that pattern + 0x128), ST2 = [ctx + 4] (24 words: 0-7 note, 8-15 gate, 16-23 byte 6); the listener =
    the first of ST1's list ([[ST1 + 0x14]]): [L + 4] the track's patterns, [L + 0x28] the store of the pattern it shows (p0).

Ours (the head of the button chain; Shift is countin's c_cishift): Play with Shift held (not the count-in's own press) does not reach the stock;
over the pattern's first..last step, first a step with one hit on micro steps 1-2 moves it to micro step 0, then one on 3-5 to micro step 0 of
the next step (the last's to the first; so a hit late in a step and one early in the next end as one hit): an empty one takes the whole step (note, gate, velocity, probability, flip), else it gets its bit 0; the old step is
left empty; a roll (several hits) stays.  Only when both stores hold exactly that pattern (checked word by word before anything is written),
and then both copies of each store get the new words, so the stock's next edit keeps them.
The Play LED while Shift is held: yellow (available), green once quantized, red when refused (until Shift is let go).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, ands_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, h, ldr_imm, ldr_sp, ldrb_imm, ldrb_reg,  # noqa: E402
                   lsls_imm, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list, push_list, raw, str_imm, str_sp,
                   strb_imm, strb_reg, subs_imm3, subs_reg, add_sp_imm, sub_sp_imm)
import countin as CI  # noqa: E402
import rhstate  # noqa: E402

ID_PLAY, LED_PLAY = 17, 49
CONT, CONT_VT, SEL_OFF = 0x20048B9C, 0x080678DC, 0x25C
PV0, PV_SZ, PV_VT = 0x2004C7B8, 0x40, 0x08067E6C
LIS_VT = 0x080696A0
PAT_SZ, SET_OFF, LANES_OFF, STEP_SZ = 0xA28, 0x100, 0x128, 8
EMPTY = (0x00000600, 0x0000FF07)                         # an empty step: 00 06 00 00 07 FF 00 00
ST1_MAP, ST2_MAP = (3, 4, 2, 5), (0, 1, 6)                # the step byte of each group of 8 words
PARAM_NEW = CI.PARAM_NEW
DQ_OFF = 0x108                                             # (v2) drumpat's byte of a step: the pattern + 0x108 + step
O_Q = rhstate.OFF["quant"][0]
Q_DONE, Q_NO = 0xD1, 0xD0
COL_AV, COL_DONE, COL_NO = 0x2F, 0x1E, 0x55              # yellow, green, red (Tracks 0x2D, 0x17, 0x53)
LED_CALLS = CI.LED_CALLS


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))
def ldr_reg(rt, rn, rm): return h(0x5800 | rm << 6 | rn << 3 | rt)
def str_reg(rt, rn, rm): return h(0x5000 | rm << 6 | rn << 3 | rt)


def packed(m, write):
    """A store's map for c_qzst: the step byte of group g in bits 4g.., the number of words in bits 16-23, bit 31 = write."""
    v = sum(off << 4 * g for g, off in enumerate(m)) | (8 * len(m)) << 16
    return v | (1 << 31 if write else 0)


def arm_code(base, L, prev, v2=False):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    INV = dict(ne="eq", hi="ls")
    nfail = [0]

    def fail(cond):                                                       # a far branch to qd_0
        nfail[0] += 1
        E(b_cond, f"qf_{nfail[0]}", INV[cond])
        E(b, "qd_0")
        a.label(f"qf_{nfail[0]}")

    # ---- c_qzw(r0 = the byte of step 4w in the pattern) -> r0 = the store's word of steps 4w..4w+3; clobbers r1, r2
    a.label("c_qzw")
    E(ldrb_imm, 1, 0, 0)
    for k in (1, 2, 3):
        E(ldrb_imm, 2, 0, STEP_SZ * k)
        E(lsls_imm, 2, 2, 8 * k)
        E(orrs_reg, 1, 2)
    E(mov_reg, 0, 1)
    E(raw, h(0x4770))

    # ---- c_qzst(r0 = store, r1 = pattern, r2 = packed map) -> r0 = 0: (compare) every word is the pattern's / (write) written into both
    #      copies; 1: a word differs
    a.label("c_qzst")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(sub_sp_imm, 8)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(mov_reg, 6, 2)
    E(movs_imm, 7, 0)                                                     # r7 = the word
    a.label("st_l")
    E(lsrs_imm, 0, 7, 3)
    E(lsls_imm, 0, 0, 2)                                                  # 4 x the group
    E(mov_reg, 1, 6)
    E(lsrs_reg, 1, 0)
    E(lsls_imm, 1, 1, 28)
    E(lsrs_imm, 1, 1, 28)                                                 # the step byte
    E(lsls_imm, 0, 7, 29)
    E(lsrs_imm, 0, 0, 24)                                                 # (w & 7) x 32
    E(adds_reg, 0, 0, 1)
    E(adds_reg, 0, 0, 5)
    E(bl, "c_qzw")
    E(cmp_imm, 6, 0)
    E(b_cond, "st_c", "ge")                                               # bit 31 clear: compare
    E(lsls_imm, 2, 7, 2)
    E(ldr_imm, 1, 4, 0xC)
    E(raw, str_reg(0, 1, 2))
    E(ldr_imm, 1, 4, 0x10)
    E(raw, str_reg(0, 1, 2))
    E(b, "st_n")
    a.label("st_c")
    E(str_sp, 0, 0)
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 7)
    E(bl, PARAM_NEW)
    E(ldr_imm, 0, 0, 0)
    E(ldr_sp, 1, 0)
    E(cmp_reg, 0, 1)
    E(b_cond, "st_bad", "ne")
    a.label("st_n")
    E(adds_imm8, 7, 1)
    E(lsls_imm, 0, 6, 8)
    E(lsrs_imm, 0, 0, 24)                                                 # the number of words
    E(cmp_reg, 7, 0)
    E(b_cond, "st_l", "lo")
    E(movs_imm, 0, 0)
    E(b, "st_x")
    a.label("st_bad")
    E(movs_imm, 0, 1)
    a.label("st_x")
    E(add_sp_imm, 8)
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_qzhit(r0 = pattern, r1 = step, r2 = the next step, 0xFF: none, 0xFE: no move in this pass): its hit quantized; clobbers r0-r3
    a.label("c_qzhit")
    E(push_list, [4, 5, 6], lr=True)
    E(lsls_imm, 1, 1, 3)
    E(adds_reg, 4, 0, 1)                                                  # r4 = the step
    E(ldrb_imm, 5, 4, 2)                                                  # r5 = its micro steps
    E(cmp_imm, 5, 1)
    E(b_cond, "qh_x", "ls")
    E(subs_imm3, 3, 5, 1)
    E(ands_reg, 3, 5)
    E(cmp_imm, 3, 0)
    E(b_cond, "qh_x", "ne")                                               # several hits: kept
    E(cmp_imm, 5, 8)
    E(b_cond, "qh_m", "hs")
    a.label("qh_z")
    E(movs_imm, 1, 1)
    E(strb_imm, 1, 4, 2)
    E(b, "qh_x")
    a.label("qh_m")
    E(cmp_imm, 2, 0xFE)
    E(b_cond, "qh_x", "eq")
    E(cmp_imm, 2, 0xFF)
    E(b_cond, "qh_z", "eq")
    E(lsls_imm, 2, 2, 3)
    E(adds_reg, 6, 0, 2)                                                  # r6 = the next step
    E(ldrb_imm, 1, 6, 2)
    E(cmp_imm, 1, 0)
    E(b_cond, "qh_d", "ne")
    E(movs_imm, 3, 0)
    a.label("qh_c")                                                       # an empty one: the whole step
    E(ldrb_reg, 1, 4, 3)
    E(strb_reg, 1, 6, 3)
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, 7)
    E(b_cond, "qh_c", "lo")
    E(movs_imm, 1, 0)
    a.label("qh_d")
    if v2:                                                                # the step's byte of drumpat goes with the hit (moved into an empty step)
        E(mov_reg, 2, 4)
        E(subs_reg, 2, 2, 0)
        E(lsrs_imm, 2, 2, 3)
        E(adds_reg, 2, 2, 0)
        E(adds_imm8, 2, 0xFF)
        E(adds_imm8, 2, DQ_OFF - 0xFF)                                    # r2 = the old step's byte
        E(mov_reg, 3, 6)
        E(subs_reg, 3, 3, 0)
        E(lsrs_imm, 3, 3, 3)
        E(adds_reg, 3, 3, 0)
        E(adds_imm8, 3, 0xFF)
        E(adds_imm8, 3, DQ_OFF - 0xFF)                                    # r3 = the next step's
        E(cmp_imm, 1, 0)
        E(b_cond, "qh_b0", "ne")
        E(ldrb_imm, 5, 2, 0)
        E(strb_imm, 5, 3, 0)
        a.label("qh_b0")
        E(movs_imm, 5, 0)
        E(strb_imm, 5, 2, 0)
    E(movs_imm, 3, 1)
    E(orrs_reg, 1, 3)
    E(strb_imm, 1, 6, 2)
    imm32(1, EMPTY[0])                                                    # the old step emptied
    E(str_imm, 1, 4, 0)
    imm32(1, EMPTY[1])
    E(str_imm, 1, 4, 4)
    a.label("qh_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_qzdo() -> r0 = 1: the pattern of the selected track quantized; 0: refused (nothing written)
    a.label("c_qzdo")
    E(push_list, [2, 3, 4, 5, 6, 7], lr=True)
    E(sub_sp_imm, 12)
    imm32(0, CONT)
    E(ldr_imm, 1, 0, 0)
    imm32(2, CONT_VT)
    E(cmp_reg, 1, 2)
    fail("ne")
    imm32(1, SEL_OFF)
    E(raw, ldr_reg(0, 0, 1))
    E(movs_imm, 1, 0)
    E(bl, PARAM_NEW)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 7)
    fail("hi")                                               # r0 = the track
    E(lsls_imm, 0, 0, 6)
    imm32(1, PV0)
    E(adds_reg, 0, 0, 1)
    E(ldr_imm, 1, 0, 0)
    imm32(2, PV_VT)
    E(cmp_reg, 1, 2)
    fail("ne")
    E(ldr_imm, 0, 0, 0xC)
    E(ldr_imm, 6, 0, 0)                                                   # r6 = ST1
    E(ldr_imm, 7, 0, 4)                                                   # r7 = ST2
    E(ldr_imm, 0, 6, 0x14)
    E(ldr_imm, 4, 0, 0)                                                   # r4 = the listener
    E(ldr_imm, 1, 4, 0)
    imm32(2, LIS_VT)
    E(cmp_reg, 1, 2)
    fail("ne")
    E(ldr_imm, 1, 4, 0x1C)
    E(cmp_reg, 1, 6)
    fail("ne")
    E(ldr_imm, 1, 4, 0x20)
    E(cmp_reg, 1, 7)
    fail("ne")
    E(ldr_imm, 0, 4, 0x28)
    E(movs_imm, 1, 0)
    E(bl, PARAM_NEW)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 7)
    fail("hi")
    imm32(1, PAT_SZ)
    E(muls, 0, 1)
    E(ldr_imm, 1, 4, 4)
    E(adds_reg, 5, 0, 1)                                                  # r5 = the pattern
    E(ldr_imm, 0, 6, 0x18)
    imm32(1, LANES_OFF)
    E(adds_reg, 1, 1, 5)
    E(cmp_reg, 0, 1)
    fail("ne")                                               # ST1 is another pattern's
    for st, m in ((6, ST1_MAP), (7, ST2_MAP)):
        E(mov_reg, 0, st)
        E(mov_reg, 1, 5)
        imm32(2, packed(m, False))
        E(bl, "c_qzst")
        E(cmp_imm, 0, 0)
        fail("ne")                                           # the stores do not hold it
    imm32(0, SET_OFF)
    E(adds_reg, 0, 0, 5)
    E(ldrb_imm, 2, 0, 0)                                                  # the last step
    E(ldrb_imm, 1, 0, 1)                                                  # the first
    E(cmp_imm, 1, 31)
    fail("hi")
    E(cmp_imm, 2, 31)
    fail("hi")
    E(cmp_reg, 1, 2)
    E(b_cond, "qd_o", "ls")
    E(mov_reg, 3, 1)
    E(mov_reg, 1, 2)
    E(mov_reg, 2, 3)
    a.label("qd_o")
    E(str_sp, 1, 0)
    E(str_sp, 2, 4)
    E(movs_imm, 0, 0)
    E(str_sp, 0, 8)                                                       # pass 0: micro steps 1-2 to 0; pass 1: the moves
    a.label("qd_p")
    E(ldr_sp, 4, 0)                                                       # r4 = the step
    a.label("qd_l")
    E(ldr_sp, 2, 4)
    E(cmp_reg, 4, 2)
    E(b_cond, "qd_n1", "ne")
    E(ldr_sp, 2, 0)                                                       # the last one's next = the first
    E(b, "qd_n2")
    a.label("qd_n1")
    E(mov_reg, 2, 4)
    E(adds_imm8, 2, 1)
    a.label("qd_n2")
    E(cmp_reg, 2, 4)
    E(b_cond, "qd_n3", "ne")
    E(movs_imm, 2, 0xFF)
    a.label("qd_n3")
    E(ldr_sp, 0, 8)
    E(cmp_imm, 0, 0)
    E(b_cond, "qd_n4", "ne")
    E(movs_imm, 2, 0xFE)
    a.label("qd_n4")
    E(mov_reg, 0, 5)
    E(mov_reg, 1, 4)
    E(bl, "c_qzhit")
    E(adds_imm8, 4, 1)
    E(ldr_sp, 2, 4)
    E(cmp_reg, 4, 2)
    E(b_cond, "qd_l", "ls")
    E(ldr_sp, 0, 8)
    E(adds_imm8, 0, 1)
    E(str_sp, 0, 8)
    E(cmp_imm, 0, 2)
    E(b_cond, "qd_p", "lo")
    for st, m in ((6, ST1_MAP), (7, ST2_MAP)):                            # the stores: both copies
        E(mov_reg, 0, st)
        E(mov_reg, 1, 5)
        imm32(2, packed(m, True))
        E(bl, "c_qzst")
    E(movs_imm, 0, 1)
    E(b, "qd_x")
    a.label("qd_0")
    E(movs_imm, 0, 0)
    a.label("qd_x")
    E(add_sp_imm, 12)
    E(pop_list, [2, 3, 4, 5, 6, 7], pc=True)

    # ---- c_qzbtn (the head of the button chain: r0 = ctrl, r1 = id): Shift + Play = quantize
    a.label("c_qzbtn")
    E(cmp_imm, 1, ID_PLAY)
    E(b_cond, "qb_f", "ne")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "qb_p", "eq")
    E(mov_reg, 4, 0)
    E(ldrb_imm, 0, 4, CI.O_PASS)
    E(cmp_imm, 0, 0)
    E(b_cond, "qb_p", "ne")                                               # the count-in's own press
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "qb_p", "eq")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "qb_p", "eq")
    if v2:                                                                # stopped: Shift + Play is the stock's (play from where it stopped)
        imm32(0, CI.TRANSPORT)
        E(movs_imm, 1, 0)
        E(bl, L["c_cinew"])
        E(cmp_imm, 0, 0)
        E(b_cond, "qb_p", "eq")
    E(bl, "c_qzdo")
    E(movs_imm, 1, Q_NO)
    E(cmp_imm, 0, 0)
    E(b_cond, "qb_w", "eq")
    E(movs_imm, 1, Q_DONE)
    a.label("qb_w")
    E(strb_imm, 1, 4, O_Q)
    E(pop_list, [0, 1, 2, 3, 4], pc=True)
    a.label("qb_p")
    E(raw, popw([0, 1, 2, 3, 4], lr=True))
    a.label("qb_f")
    E(b_w, prev["btn"])

    # ---- c_qzled (the LED task's calls: r0 = ctrl, r1 = frame): the chain; with Shift the Play LED yellow / green / red
    a.label("c_qzled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ql_x", "eq")
    E(mov_reg, 4, 0)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ql_x", "eq")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ql_s", "ne")
    E(strb_imm, 0, 4, O_Q)                                                # Shift let go: the result forgotten
    E(b, "ql_x")
    a.label("ql_s")
    if v2:                                                                # stopped: the stock's Play LED
        imm32(0, CI.TRANSPORT)
        E(movs_imm, 1, 0)
        E(bl, L["c_cinew"])
        E(cmp_imm, 0, 0)
        E(b_cond, "ql_x", "eq")
    E(ldrb_imm, 0, 4, O_Q)
    E(movs_imm, 1, COL_AV)
    E(cmp_imm, 0, Q_DONE)
    E(b_cond, "ql_n", "ne")
    E(movs_imm, 1, COL_DONE)
    a.label("ql_n")
    E(cmp_imm, 0, Q_NO)
    E(b_cond, "ql_w", "ne")
    E(movs_imm, 1, COL_NO)
    a.label("ql_w")
    E(movs_imm, 0, 2 * LED_PLAY)
    E(raw, h(0x5229))                                                     # strh r1, [r5, r0]
    a.label("ql_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr, v2=False):
    """Append the code; the head of the button chain, the two LED task calls.  v2 (RH11): Shift + Play only while playing (stopped it is the
    stock's «play from where it stopped», as the Play LED with Shift); a hit moved into an empty step takes the step's drumpat byte along."""
    import rhbuild
    BASE = rhbuild.BASE
    lab = lambda sec, n: int(report[sec]["labels"][n], 16)
    L = dict(c_rst=lab("rhstate", "c_rst"), c_ciok=lab("countin", "c_ciok"), c_cishift=lab("countin", "c_cishift"),
             c_cinew=lab("countin", "c_cinew"))
    prev = dict(btn=rhbuild.bw_target(img, CI.BTN_ENTRY), ledtask=rhbuild.bl_target(img, LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in LED_CALLS)
    code, labels = arm_code(base_addr, L, prev, v2)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, CI.BTN_ENTRY, f"b.w #{prev['btn']:#x}", b_w(CI.BTN_ENTRY, labels["c_qzbtn"]))
    for c in LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_qzled"]))
    report["quant"] = dict(btn_entry=hex(CI.BTN_ENTRY), led_calls=[hex(c) for c in LED_CALLS],
                           prev={k: hex(v) for k, v in prev.items()},
                           labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
