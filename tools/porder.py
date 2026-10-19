"""Pattern Settings, pads 27 / 28 = the FRACTAL and DECONSTRUCTED play orders (MIT; the pads 27 / 28 and the engine hooks of CIRCUIT-HACKS'
playmode, SC40.8 / SC40.9, for the Circuit Rhythm 5706):

    pad 27  FRACTAL: 1 · 1 2 · 1 2 3 · ... · 1..n over the pattern's steps; the pattern ends (one play) after the last step of the whole run.
    pad 28  DECONSTRUCTED: the diagonals of the 4 x 4 grid, 1 6 11 16 · 2 7 12 13 · 3 8 9 14 · 4 5 10 15 (17-32: the same in the second half);
            a step outside the pattern's first / last step is skipped.
    Pads 27 / 28 and the stock's four direction pads (29-32) exclude each other; they take the direction pads' colours.

The stock of the Rhythm (read in the firmware; the sequencer is the Tracks' code, the same instructions at other addresses):
  * the engine 0x2003C380: [+ 0x20] -> [[+ 0x20]] + 0x2E4 + 0x5140 t + 0xA28 p = the pattern p of track t (the direction getter 0x080470E8 reads
    its byte + 0x103); + 0x30 + 4 t = (pattern, step, tick) of track t;
  * 0x080345F2 in 0x08034584 («the pattern ends at this step»), 0x08034CB4 in the track advance 0x08034BDC (the next step) and its bl to the
    direction getter at 0x08034E24 (the step a pattern starts at): the Tracks' 0x0802C552 / 0x0802CC14 / 0x0802CD84, the same registers;
  * the pattern's settings bytes + 0x100..0x127: + 0 last step, + 1 first, + 2 sync rate, + 3 direction (ST3's three parameters); + 4..+ 0x27
    zero in the 64 patterns of the dump and never written by ST3's commit.
Ours: the order = byte + 7 of the settings (1 fractal, 2 deconstructed), the stock's direction left at forward (a firmware without this plays it
forward); the engine hooks are CIRCUIT-HACKS' (ours, MIT) with the Rhythm's addresses; the fractal's group size a byte per track in rhstate,
cleared by the LED task while the transport is stopped.  The order is not known to be saved with the project (the Rhythm's file is not studied).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm3, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, h, ldr_imm, ldr_sp, ldrb_imm, ldrb_reg,  # noqa: E402
                   lsls_imm, mov_reg, movs_imm, movt, movw, muls, pop_list, push_list, raw, str_sp, strb_imm, strh_reg, subs_imm8)
import countin as CI  # noqa: E402
import playmode as PM  # noqa: E402
import rhstate  # noqa: E402

ENG, ENG_VT = 0x2003C380, 0x08066B34
PAT0_OFF, TRK_SZ, PAT_SZ, SET_OFF = 0x2E4, 0x5140, 0xA28, 0x100
END_HOOK, STEP_HOOK, START_HOOK = 0x080345F2, 0x08034CB4, 0x08034E24
DIR_GET = 0x080470E8
DIR_OLD_TEXT = "ldrb r0, [r0]|cmp r0, #3"
PAD_FRAC, PAD_DEC, PAD_DIR = 26, 27, 28
M_FRAC, M_DEC = 1, 2
O_ORDER = 7
COL_SEL, COL_UNSEL = 0x67, 0x68                            # the stock's direction pads (chosen / not)
O_K = rhstate.OFF["porder"][0]
DIAG = [r * 4 + (r + d) % 4 for d in range(4) for r in range(4)]
ORDER = DIAG + [16 + s for s in DIAG]
PARAM_GET, PARAM_NEW, PARAM_WPTR, COMMIT = CI.PARAM_GET, CI.PARAM_NEW, 0x0803FD26, 0x0803FBEC
LED_CALLS = CI.LED_CALLS


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))
def ldrb_sp(rt, off): return h(0xF89D) + h(rt << 12 | off)


POP_LR, BX_LR = h(0xF85D) + h(0xEB04), h(0x4770)


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    t_ord = base
    E(raw, bytes(ORDER))

    # ---- c_poset(r0 = track, r1 = pattern) -> r0 = its settings bytes (0: none); clobbers r1-r3
    a.label("c_poset")
    E(cmp_imm, 0, 7)
    E(b_cond, "se_0", "hi")
    E(cmp_imm, 1, 7)
    E(b_cond, "se_0", "hi")
    imm32(2, ENG)
    E(ldr_imm, 3, 2, 0)
    imm32(2, ENG_VT)
    E(cmp_reg, 3, 2)
    E(b_cond, "se_0", "ne")
    imm32(2, ENG)
    E(ldr_imm, 2, 2, 0x20)
    E(ldr_imm, 2, 2, 0)                                                   # [[ENG + 0x20]]
    imm32(3, TRK_SZ)
    E(muls, 0, 3)
    E(adds_reg, 2, 2, 0)
    imm32(3, PAT_SZ)
    E(muls, 1, 3)
    E(adds_reg, 2, 2, 1)
    imm32(3, PAT0_OFF + SET_OFF)
    E(adds_reg, 0, 2, 3)
    E(raw, BX_LR)
    a.label("se_0")
    E(movs_imm, 0, 0)
    E(raw, BX_LR)

    # ---- c_pminfo(r0 = track, r1 = pattern) -> r0 = its order (0 = the stock's), r1 = its first step, r2 = its last; clobbers r3
    a.label("c_pminfo")
    E(push_list, [4], lr=True)
    E(bl, "c_poset")
    E(cmp_imm, 0, 0)
    E(b_cond, "in_0", "eq")
    E(mov_reg, 4, 0)
    E(ldrb_imm, 0, 4, O_ORDER)
    E(ldrb_imm, 1, 4, 1)
    E(ldrb_imm, 2, 4, 0)
    E(cmp_imm, 0, M_DEC)
    E(b_cond, "in_0", "hi")
    E(cmp_reg, 1, 2)
    E(b_cond, "in_0", "hi")
    E(cmp_imm, 2, 31)
    E(b_cond, "in_0", "hi")
    E(pop_list, [4], pc=True)
    a.label("in_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_pmdidx(r0 = step) -> r0 = its place in the deconstructed order + 1 (0: none); clobbers r1-r3
    a.label("c_pmdidx")
    imm32(3, t_ord)
    E(movs_imm, 1, 0)
    a.label("di_l")
    E(ldrb_reg, 2, 3, 1)
    E(adds_imm8, 1, 1)
    E(cmp_reg, 2, 0)
    E(b_cond, "di_f", "eq")
    E(cmp_imm, 1, 32)
    E(b_cond, "di_l", "lo")
    E(movs_imm, 1, 0)
    a.label("di_f")
    E(mov_reg, 0, 1)
    E(raw, BX_LR)

    # ---- c_pmdscan(r0 = the place to look from, r1 = the first step, r2 = the last) -> r0 = the next step of the order within them, 0xFF: none
    a.label("c_pmdscan")
    E(push_list, [4], lr=True)
    imm32(4, t_ord)
    a.label("ds_l")
    E(cmp_imm, 0, 32)
    E(b_cond, "ds_0", "hs")
    E(ldrb_reg, 3, 4, 0)
    E(adds_imm8, 0, 1)
    E(cmp_reg, 3, 1)
    E(b_cond, "ds_l", "lo")
    E(cmp_reg, 3, 2)
    E(b_cond, "ds_l", "hi")
    E(mov_reg, 0, 3)
    E(pop_list, [4], pc=True)
    a.label("ds_0")
    E(movs_imm, 0, 0xFF)
    E(pop_list, [4], pc=True)

    # ---- c_pmk(r0 = track) -> r0 = the address of its fractal group byte (0: none); clobbers r1-r3
    a.label("c_pmk")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "pk_x", "eq")
    E(adds_imm8, 0, O_K)
    E(adds_reg, 0, 0, 4)
    a.label("pk_x")
    E(pop_list, [4], pc=True)

    # ---- c_pmend (at 0x080345F2, in place of «ldrb r0, [r0]; cmp r0, #3»): r4 = the track, r6 = the engine, fp = the step, r8 = the
    #      last step -> the direction and its flags for the stock; an order of ours: "forward, at the last step" when the pattern ends here,
    #      else a direction the stock answers "no" to
    a.label("c_pmend")
    E(ldrb_imm, 0, 0, 0)
    E(push_list, [0, 1, 2, 3, 5, 6, 7], lr=True)
    E(lsls_imm, 1, 4, 2)
    E(adds_reg, 1, 1, 6)
    E(ldr_imm, 0, 1, 0x30)
    E(movs_imm, 1, 0)
    E(bl, PARAM_GET)
    E(ldrb_imm, 1, 0, 0)
    E(mov_reg, 0, 4)
    E(bl, "c_pminfo")
    E(cmp_imm, 0, 0)
    E(b_cond, "pe_x", "eq")
    E(mov_reg, 5, 1)
    E(mov_reg, 6, 2)
    E(cmp_imm, 0, M_DEC)
    E(b_cond, "pe_d", "eq")
    E(mov_reg, 0, 4)
    E(bl, "c_pmk")
    E(cmp_imm, 0, 0)
    E(b_cond, "pe_x", "eq")
    E(ldrb_imm, 0, 0, 0)
    E(adds_reg, 0, 0, 5)
    E(mov_reg, 1, 11)
    E(cmp_reg, 1, 0)
    E(b_cond, "pe_n", "lo")                                               # inside the group
    E(cmp_reg, 0, 6)
    E(b_cond, "pe_y", "hs")
    E(b, "pe_n")                                                          # the group is the whole pattern
    a.label("pe_d")
    E(mov_reg, 0, 11)
    E(bl, "c_pmdidx")
    E(mov_reg, 1, 5)
    E(mov_reg, 2, 6)
    E(bl, "c_pmdscan")
    E(cmp_imm, 0, 0xFF)
    E(b_cond, "pe_n", "ne")
    a.label("pe_y")
    E(movs_imm, 0, 0)
    E(str_sp, 0, 0)
    E(mov_reg, 11, 8)
    E(b, "pe_x")
    a.label("pe_n")
    E(movs_imm, 0, 4)
    E(str_sp, 0, 0)
    a.label("pe_x")
    E(pop_list, [0, 1, 2, 3, 5, 6, 7])
    E(raw, POP_LR)
    E(cmp_imm, 0, 3)
    E(raw, BX_LR)

    # ---- c_pmstep (at 0x08034CB4, in place of «ldrb r0, [r0]; cmp r0, #3»): [sp] = the track, r9 = the pattern, r6 = the step,
    #      r4 = the pattern ends, fp = 0 for the playing store -> the direction and its flags; an order of ours: r5 = the next step and a
    #      direction the stock skips
    F = 32
    a.label("c_pmstep")
    E(ldrb_imm, 0, 0, 0)
    E(push_list, [0, 1, 2, 3, 4, 6, 7], lr=True)
    E(raw, ldrb_sp(7, F))
    E(mov_reg, 0, 7)
    E(mov_reg, 1, 9)
    E(bl, "c_pminfo")
    E(cmp_imm, 0, 0)
    E(b_cond, "ps_x", "eq")
    E(ldr_sp, 3, 16)
    E(cmp_imm, 3, 0)
    E(b_cond, "ps_s", "ne")                                               # the pattern ends: the start hook's job
    E(cmp_imm, 0, M_DEC)
    E(b_cond, "ps_d", "eq")
    E(mov_reg, 4, 1)                                                      # r4 = the first step
    E(mov_reg, 0, 7)
    E(bl, "c_pmk")
    E(cmp_imm, 0, 0)
    E(b_cond, "ps_x", "eq")
    E(mov_reg, 3, 0)
    E(ldrb_imm, 0, 3, 0)
    E(adds_reg, 1, 4, 0)
    E(cmp_reg, 6, 1)
    E(b_cond, "ps_g", "hs")
    E(adds_imm3, 5, 6, 1)
    E(b, "ps_s")
    a.label("ps_g")                                                       # the group ends: the next one is a step longer
    E(mov_reg, 5, 4)
    E(mov_reg, 1, 11)
    E(cmp_imm, 1, 0)
    E(b_cond, "ps_s", "ne")
    E(adds_imm8, 0, 1)
    E(strb_imm, 0, 3, 0)
    E(b, "ps_s")
    a.label("ps_d")
    E(mov_reg, 4, 1)
    E(mov_reg, 7, 2)
    E(mov_reg, 0, 6)
    E(bl, "c_pmdidx")
    E(mov_reg, 1, 4)
    E(mov_reg, 2, 7)
    E(bl, "c_pmdscan")
    E(cmp_imm, 0, 0xFF)
    E(b_cond, "ps_o", "ne")
    E(movs_imm, 0, 0)
    E(mov_reg, 1, 4)
    E(mov_reg, 2, 7)
    E(bl, "c_pmdscan")
    a.label("ps_o")
    E(mov_reg, 5, 0)
    a.label("ps_s")
    E(movs_imm, 0, 4)
    E(str_sp, 0, 0)
    a.label("ps_x")
    E(pop_list, [0, 1, 2, 3, 4, 6, 7])
    E(raw, POP_LR)
    E(cmp_imm, 0, 3)
    E(raw, BX_LR)

    # ---- c_pmstart (at 0x08034E24, in place of its bl to the direction getter: r1 = the track, r2 = the pattern that starts) -> the
    #      direction; an order of ours: r5 = its first step, the fractal's group back to one step, and a direction the stock skips
    a.label("c_pmstart")
    E(push_list, [1, 2, 4, 6, 7], lr=True)
    E(bl, DIR_GET)
    E(mov_reg, 6, 0)
    E(ldr_sp, 0, 0)
    E(ldr_sp, 1, 4)
    E(bl, "c_pminfo")
    E(cmp_imm, 0, 0)
    E(b_cond, "pt_x", "eq")
    E(mov_reg, 4, 1)
    E(cmp_imm, 0, M_DEC)
    E(b_cond, "pt_f", "ne")
    E(movs_imm, 0, 0)
    E(bl, "c_pmdscan")
    E(cmp_imm, 0, 0xFF)
    E(b_cond, "pt_x", "eq")
    E(mov_reg, 5, 0)
    E(b, "pt_k")
    a.label("pt_f")
    E(mov_reg, 5, 4)
    a.label("pt_k")
    E(mov_reg, 0, 11)
    E(cmp_imm, 0, 0)
    E(b_cond, "pt_4", "ne")
    E(ldr_sp, 0, 0)
    E(bl, "c_pmk")
    E(cmp_imm, 0, 0)
    E(b_cond, "pt_4", "eq")
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, 0)
    a.label("pt_4")
    E(movs_imm, 6, 4)
    a.label("pt_x")
    E(mov_reg, 0, 6)
    E(pop_list, [1, 2, 4, 6, 7], pc=True)

    # ---- c_poview(r0 = a Pattern Settings view) -> r0 = the settings bytes of the pattern it shows (0: none); clobbers r1-r3
    a.label("c_poview")
    E(push_list, [4], lr=True)
    E(bl, L["c_pmtrk"])
    E(cmp_imm, 0, 7)
    E(b_cond, "pv_0", "hi")
    E(mov_reg, 4, 0)
    imm32(1, ENG + 0x30)
    E(lsls_imm, 0, 0, 2)
    E(adds_reg, 0, 0, 1)
    E(ldr_imm, 0, 0, 0)
    E(movs_imm, 1, 0)
    E(bl, PARAM_NEW)
    E(ldrb_imm, 1, 0, 0)                                                  # the pattern the track plays
    E(mov_reg, 0, 4)
    E(bl, "c_poset")
    E(pop_list, [4], pc=True)
    a.label("pv_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_popad (the Pattern Settings view's slot 0: view, pad, velocity): pads 27 / 28 = our orders, 29-32 the stock's (ours off)
    a.label("c_popad")
    E(cmp_imm, 1, PAD_FRAC)
    E(b_cond, "op_f", "lo")
    E(cmp_imm, 1, 31)
    E(b_cond, "op_f", "hi")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "op_p", "eq")
    E(ldr_sp, 0, 0)
    E(bl, "c_poview")
    E(cmp_imm, 0, 0)
    E(b_cond, "op_p", "eq")
    E(ldr_sp, 1, 4)
    E(cmp_imm, 1, PAD_DIR)
    E(b_cond, "op_d", "hs")
    E(subs_imm8, 1, PAD_FRAC - M_FRAC)
    E(strb_imm, 1, 0, O_ORDER)                                            # our order
    E(ldr_sp, 4, 0)
    E(ldr_imm, 0, 4, 0xC)                                                 # the stock's direction: forward
    E(movs_imm, 1, 2)
    E(bl, PARAM_WPTR)
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, 0)
    E(ldr_imm, 0, 4, 0xC)
    E(bl, COMMIT)
    E(pop_list, [0, 1, 2, 3, 4], pc=True)
    a.label("op_d")
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, O_ORDER)                                            # a stock direction: ours off
    a.label("op_p")
    E(raw, popw([0, 1, 2, 3, 4], lr=True))
    a.label("op_f")
    E(b_w, prev["pad"])

    # ---- c_poled (the view's slot 7: view): the chain, then pads 27 / 28 (and 29-32 with an order of ours); the chain's r0 returned
    a.label("c_poled")
    E(push_list, [0, 1, 4, 5, 6, 7], lr=True)
    E(bl, prev["led"])
    E(str_sp, 0, 4)
    E(ldr_sp, 0, 0)
    E(ldr_imm, 1, 0, 4)
    E(ldr_imm, 5, 1, 0)                                                   # r5 = the pad buffer
    E(bl, "c_poview")
    E(movs_imm, 4, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "ol_m", "eq")
    E(ldrb_imm, 4, 0, O_ORDER)                                            # r4 = our order
    a.label("ol_m")
    for pad, m in ((PAD_FRAC, M_FRAC), (PAD_DEC, M_DEC)):
        E(movs_imm, 1, COL_UNSEL)
        E(cmp_imm, 4, m)
        E(b_cond, f"ol_{pad}", "ne")
        E(movs_imm, 1, COL_SEL)
        a.label(f"ol_{pad}")
        E(movs_imm, 0, 2 * pad)
        E(strh_reg, 1, 5, 0)
    E(cmp_imm, 4, 0)
    E(b_cond, "ol_x", "eq")
    E(cmp_imm, 4, M_DEC)
    E(b_cond, "ol_x", "hi")
    E(movs_imm, 1, COL_UNSEL)                                             # an order of ours: no direction pad chosen
    for pad in range(PAD_DIR, PAD_DIR + 4):
        E(movs_imm, 0, 2 * pad)
        E(strh_reg, 1, 5, 0)
    a.label("ol_x")
    E(ldr_sp, 0, 4)
    E(raw, h(0xB002))                                                     # add sp, #8
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_poledtask (the LED task's calls): the chain; stopped, the fractal groups back to one step
    a.label("c_poledtask")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(bl, prev["ledtask"])
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ot_x", "eq")
    E(mov_reg, 4, 0)
    imm32(0, CI.TRANSPORT)
    E(movs_imm, 1, 0)
    E(bl, PARAM_NEW)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "ot_x", "ne")
    E(movs_imm, 0, 0)
    for t in range(8):
        E(strb_imm, 0, 4, O_K + t)
    a.label("ot_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the three engine hooks, slots 0 / 7 of Pattern Settings (in front of playmode's), the LED task calls."""
    import struct
    import rhbuild
    BASE = rhbuild.BASE
    lab = lambda sec, n: int(report[sec]["labels"][n], 16)
    L = dict(c_rst=lab("rhstate", "c_rst"), c_ciok=lab("countin", "c_ciok"), c_pmtrk=lab("playmode", "c_pmtrk"))
    old = [struct.unpack_from("<I", img, PM.PS_VT + 4 * k - BASE)[0] for k in (0, 7)]
    prev = dict(pad=old[0] & ~1, led=old[1] & ~1, ledtask=rhbuild.bl_target(img, LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, END_HOOK, DIR_OLD_TEXT, bl(END_HOOK, labels["c_pmend"]))
    rhbuild.patch(img, STEP_HOOK, DIR_OLD_TEXT, bl(STEP_HOOK, labels["c_pmstep"]))
    rhbuild.patch(img, START_HOOK, f"bl #{DIR_GET:#x}", bl(START_HOOK, labels["c_pmstart"]))
    rhbuild.patch_word(img, PM.PS_VT, old[0], labels["c_popad"] | 1)
    rhbuild.patch_word(img, PM.PS_VT + 0x1C, old[1], labels["c_poled"] | 1)
    for c in LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_poledtask"]))
    report["porder"] = dict(hooks=[hex(END_HOOK), hex(STEP_HOOK), hex(START_HOOK)], prev={k: hex(v) for k, v in prev.items()},
                            labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
